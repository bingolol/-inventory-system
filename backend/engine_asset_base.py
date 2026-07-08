"""资产引擎基类 — 固定资产/无形资产共享

消除 FixedAssetEngine 与 IntangibleAssetEngine 约 200 行镜像代码。
二者唯一的差异在于模型类型和具体的折旧/摊销方法。
"""

from datetime import date
from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

import models
from errors import BusinessError, ErrorCode
from finance_integration import post_journal
from utils import Q2


class BaseAssetEngine:
    """资产引擎基类，参数化模型类型和记账类型"""

    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id

    def _depreciate_single(self, asset, depreciation_model, dep_attr: str,
                           calc_method, source_type: str, period_label: str):
        """单资产折旧/摊销通用流程"""
        amount = calc_method()
        existing = self.db.query(depreciation_model).filter(
            depreciation_model.asset_id == asset.id,
            depreciation_model.period == period_label,
        ).first()
        if existing:
            return Decimal("0")

        dep = depreciation_model(
            asset_id=asset.id,
            period=period_label,
            amount_l2=amount,
        )
        self.db.add(dep)
        self.db.flush()

        asset.__dict__[dep_attr] = getattr(asset, dep_attr) + amount
        self.db.flush()

        post_journal(self.db, self.account_id, source_type, {
            "asset_id": asset.id,
            "amount": amount,
            "period": period_label,
            "source_model": depreciation_model.__name__,
            "source_id": dep.id,
        })
        return amount

    def _batch_process(self, asset_model, status_filter: str,
                       depreciate_fn) -> int:
        """批量资产处理通用流程"""
        assets = self.db.query(asset_model).filter(
            asset_model.account_id == self.account_id,
            asset_model.status == status_filter,
        ).all()
        count = 0
        for asset in assets:
            amount = depreciate_fn(asset)
            if amount > 0:
                count += 1
        return count
