"""资产引擎基类 — 固定资产/无形资产共享

消除 FixedAssetEngine 与 IntangibleAssetEngine 的镜像代码。
子类通过类属性配置模型、科目、状态规则等差异。
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from errors import BusinessError, ErrorCode
from finance_integration import post_journal
from rules import enforce_rules
from utils.period import period_end_date


class BaseAssetEngine:
    """资产引擎基类，子类配置模型与业务规则差异"""

    # 子类必须覆盖
    asset_model = None
    depreciation_model = None
    accumulated_attr: str = ""
    contra_account_code: str = ""
    depreciation_source_model: str = ""
    depreciation_move_name: str = "折旧/摊销"
    expense_account_code: str = "6601"

    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id

    def _raise_asset_not_found(self, asset_id: int):
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                            data={"asset_id": asset_id})

    def _is_eligible(self, asset, period: str) -> bool:
        """资产当前是否应计提折旧/摊销"""
        return asset.status == "在用"

    def _date_rule_ok(self, asset, period: str) -> bool:
        """开始日期与计提期间的规则"""
        return True

    def _rule_param(self, asset_id: int) -> dict:
        """传给 enforce_rules 的参数"""
        return {"asset_id": asset_id}

    def calculate_monthly(self, asset) -> Decimal:
        raise NotImplementedError

    def _record_depreciation(self, asset_id: int, period: str):
        """计提单个资产的月折旧/摊销"""
        asset = self.db.query(self.asset_model).filter(
            self.asset_model.id == asset_id,
            self.asset_model.account_id == self.account_id,
        ).first()
        if not asset:
            self._raise_asset_not_found(asset_id)

        if not self._is_eligible(asset, period):
            return None

        if not self._date_rule_ok(asset, period):
            return None

        existing = self.db.query(self.depreciation_model).filter(
            self.depreciation_model.asset_id == asset_id,
            self.depreciation_model.period == period,
        ).first()
        if existing:
            return existing

        monthly = self.calculate_monthly(asset)
        if monthly <= 0:
            return None

        accumulated_before = Decimal(str(getattr(asset, self.accumulated_attr) or 0))
        accumulated_after = accumulated_before + monthly

        dep = self.depreciation_model(
            asset_id=asset_id,
            account_id=self.account_id,
            period=period,
            amount_l2=monthly,
            accumulated_before_l2=accumulated_before,
            accumulated_after_l2=accumulated_after,
        )
        self.db.add(dep)

        setattr(asset, self.accumulated_attr, accumulated_after)
        self.db.flush()

        source = {
            "amount": monthly,
            "expense_account_code": self.expense_account_code,
            "contra_account_code": self.contra_account_code,
            "source_model": self.depreciation_source_model,
            "source_id": dep.id,
            "date": period_end_date(period),
            "description": f"{self.depreciation_move_name}: {asset.name} {period}",
        }
        post_journal(self.db, self.account_id, "depreciation", source)

        enforce_rules(self.db, ["AS-05"], self._rule_param(asset_id))

        return dep

    def _batch_depreciate(self, period: str) -> list:
        """批量计提所有应计提资产"""
        assets = self.db.query(self.asset_model).filter(
            self.asset_model.account_id == self.account_id,
        ).all()
        results = []
        for asset in assets:
            dep = self._record_depreciation(asset.id, period)
            if dep:
                results.append(dep)
        return results
