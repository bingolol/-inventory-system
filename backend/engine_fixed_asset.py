"""固定资产引擎 — 折旧计提/处置的唯一入口

FixedAssetDepreciation 是折旧事实的真相源，
FixedAsset.accumulated_depreciation 仅为缓存。
"""
from datetime import date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session

import models
from errors import BusinessError, ErrorCode
from finance_integration import post_journal, reverse_journal
from utils import Q2


class FixedAssetEngine:
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id

    def calculate_monthly(self, asset: models.FixedAsset) -> Decimal:
        """计算月折旧额（年限平均法）

        返回实际可计提金额，已满额则返回 0。
        """
        original = Decimal(str(asset.original_value))
        salvage_rate = Decimal(str(asset.salvage_rate))
        useful_life = int(asset.useful_life)
        accumulated = Decimal(str(asset.accumulated_depreciation))

        if useful_life <= 0:
            return Decimal("0")

        depreciable = (original * (1 - salvage_rate)).quantize(Q2)
        monthly = (depreciable / useful_life).quantize(Q2)

        remaining = depreciable - accumulated
        if remaining <= 0:
            return Decimal("0")
        return min(monthly, remaining)

    def record_depreciation(self, asset_id: int, period: str
                            ) -> Optional[models.FixedAssetDepreciation]:
        """计提单个资产的月折旧

        1. 校验资产状态
        2. 幂等检查（同期间跳过）
        3. 计算月折旧额
        4. 写 FixedAssetDepreciation 流水
        5. 更新 accumulated_depreciation 缓存
        6. 生成会计凭证 借:6602 贷:1602
        """
        asset = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.id == asset_id,
            models.FixedAsset.account_id == self.account_id,
        ).first()
        if not asset:
            raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND,
                                data={"asset_id": asset_id})
        if asset.status != "在用":
            return None

        # 当月增加下月提（第三十一条）
        if asset.start_date:
            dep_year, dep_month = map(int, period.split("-"))
            if dep_year == asset.start_date.year and dep_month == asset.start_date.month:
                return None

        # 幂等检查
        existing = self.db.query(models.FixedAssetDepreciation).filter(
            models.FixedAssetDepreciation.asset_id == asset_id,
            models.FixedAssetDepreciation.period == period,
        ).first()
        if existing:
            return existing

        monthly = self.calculate_monthly(asset)
        if monthly <= 0:
            return None

        accumulated_before = Decimal(str(asset.accumulated_depreciation))
        accumulated_after = accumulated_before + monthly

        # 写折旧流水（真相源）
        dep = models.FixedAssetDepreciation(
            asset_id=asset_id,
            account_id=self.account_id,
            period=period,
            amount=monthly,
            accumulated_before=accumulated_before,
            accumulated_after=accumulated_after,
        )
        self.db.add(dep)

        # 更新缓存
        asset.accumulated_depreciation = accumulated_after
        self.db.flush()

        # 生成会计凭证：借:6602（管理费用—折旧费）贷:1602（累计折旧）
        dep_date = _period_to_date(period)
        source = {
            "amount": monthly,
            "expense_account_code": "6601",
            "contra_account_code": "1602",
            "source_model": "fixed_asset_depreciation",
            "source_id": dep.id,
            "date": dep_date,
            "description": f"固定资产折旧: {asset.name} {period}",
        }
        post_journal(self.db, self.account_id, "depreciation", source)

        return dep

    def batch_depreciate(self, period: str
                         ) -> List[models.FixedAssetDepreciation]:
        """批量计提所有在用资产的折旧"""
        assets = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.account_id == self.account_id,
            models.FixedAsset.status == "在用",
        ).all()

        results = []
        for asset in assets:
            dep = self.record_depreciation(asset.id, period)
            if dep:
                results.append(dep)
        return results

    def record_disposal(self, asset_id: int, disposal_price: Decimal = Decimal("0")) -> None:
        """处置（报废/出售）固定资产

        1. 更新资产状态为"报废"
        2. 生成处置凭证（冲销账面价值 + 处置损益）

        处置价格 > 账面净值 → 资产处置收益（6111）
        处置价格 < 账面净值 → 营业外支出（6711）
        处置价格 = 账面净值 → 无损益
        """
        asset = self.db.query(models.FixedAsset).filter(
            models.FixedAsset.id == asset_id,
            models.FixedAsset.account_id == self.account_id,
        ).first()
        if not asset:
            raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND,
                                data={"asset_id": asset_id})
        if asset.status == "报废":
            return

        asset.status = "报废"
        self.db.flush()

        original = Decimal(str(asset.original_value))
        accumulated = Decimal(str(asset.accumulated_depreciation))
        net_value = original - accumulated
        disposal_price = Decimal(str(disposal_price))
        diff = disposal_price - net_value

        disposal_date = date.today()
        source = {
            "original_value": original,
            "accumulated_depreciation": accumulated,
            "net_value": net_value,
            "disposal_price": disposal_price,
            "diff": diff,
            "source_model": "fixed_asset_disposal",
            "source_id": asset_id,
            "date": disposal_date,
            "description": f"固定资产处置: {asset.name}",
        }
        post_journal(self.db, self.account_id, "asset_disposal", source)


def _period_to_date(period: str) -> date:
    """YYYY-MM → 该月最后一天"""
    year, month = map(int, period.split("-"))
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)
