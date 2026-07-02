"""无形资产引擎 — 摊销计提/处置的唯一入口

IntangibleAssetAmortization 是摊销事实的真相源，
IntangibleAsset.accumulated_amortization 仅为缓存。

日期规则（小企业会计准则第四十一条）：
- 当月增加，当月摊销；
- 处置当月不再摊销。
"""
from datetime import date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.orm import Session

import models
from errors import BusinessError, ErrorCode
from finance_integration import post_journal
from utils import Q2
from lineage import writes, derives, reads, TIER_L1, TIER_L2, TIER_L3, TIER_L4
from rules import enforce_rules


class IntangibleAssetEngine:
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id

    @reads("IntangibleAsset.useful_life_l3", tier=TIER_L3, source="policy")
    def calculate_monthly(self, asset: models.IntangibleAsset) -> Decimal:
        """计算月摊销额（年限平均法，无残值）

        返回实际可摊销金额，已满额则返回 0。
        """
        original = Decimal(str(asset.original_value_l1))
        useful_life = int(asset.useful_life_l3)
        accumulated = Decimal(str(asset.accumulated_amortization_l4 or 0))

        if useful_life <= 0:
            return Decimal("0")

        monthly = (original / useful_life).quantize(Q2)
        remaining = original - accumulated
        if remaining <= 0:
            return Decimal("0")
        return min(monthly, remaining)

    @writes("IntangibleAssetAmortization.amount_l2", tier=TIER_L2, source="engine")
    @writes("IntangibleAssetAmortization.accumulated_before_l2", tier=TIER_L2, source="engine")
    @writes("IntangibleAssetAmortization.accumulated_after_l2", tier=TIER_L2, source="engine")
    @derives("IntangibleAsset.accumulated_amortization_l4", from_fields=["IntangibleAssetAmortization.amount_l2"])
    def record_amortization(self, asset_id: int, period: str
                            ) -> Optional[models.IntangibleAssetAmortization]:
        """计提单个无形资产的月摊销

        1. 校验资产状态
        2. 日期规则检查（当月增加当月摊；处置当月不再摊）
        3. 幂等检查（同期间跳过）
        4. 计算月摊销额
        5. 写 IntangibleAssetAmortization 流水
        6. 更新 accumulated_amortization 缓存
        7. 生成会计凭证 借:6601(管理费用) 贷:1702(累计摊销)
        """
        asset = self.db.query(models.IntangibleAsset).filter(
            models.IntangibleAsset.id == asset_id,
            models.IntangibleAsset.account_id == self.account_id,
        ).first()
        if not asset:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                                data={"order_type": "无形资产", "order_id": asset_id})
        if asset.status == "已报废":
            return None

        period_start, period_end = _period_bounds(period)

        # 当月增加当月摊：开始日期在当月或之前即应摊
        if asset.start_date_l1:
            if asset.start_date_l1 > period_end:
                return None
        # 处置当月不再摊：已报废资产在 dispose_date 所在月不摊
        # （status=已报废 已在上面拦截；若未来增加 disposal_date 字段，可在此扩展）

        # 幂等检查
        existing = self.db.query(models.IntangibleAssetAmortization).filter(
            models.IntangibleAssetAmortization.asset_id == asset_id,
            models.IntangibleAssetAmortization.period == period,
        ).first()
        if existing:
            return existing

        monthly = self.calculate_monthly(asset)
        if monthly <= 0:
            return None

        accumulated_before = Decimal(str(asset.accumulated_amortization_l4 or 0))
        accumulated_after = accumulated_before + monthly

        # 写摊销流水（真相源）
        amort = models.IntangibleAssetAmortization(
            asset_id=asset_id,
            account_id=self.account_id,
            period=period,
            amount_l2=monthly,
            accumulated_before_l2=accumulated_before,
            accumulated_after_l2=accumulated_after,
        )
        self.db.add(amort)

        # 更新缓存
        asset.accumulated_amortization_l4 = accumulated_after
        self.db.flush()

        # 生成会计凭证：借:6601（管理费用）贷:1702（累计摊销）
        source = {
            "amount": monthly,
            "expense_account_code": "6601",
            "contra_account_code": "1702",
            "source_model": "intangible_asset_amortization",
            "source_id": amort.id,
            "date": period_end,
            "description": f"无形资产摊销: {asset.name} {period}",
        }
        post_journal(self.db, self.account_id, "depreciation", source)

        # AS-05 摊销公式 + 累计摊销上限校验
        enforce_rules(self.db, ["AS-05"], {"intangible_asset_id": asset_id})

        return amort

    def batch_amortize(self, period: str
                       ) -> List[models.IntangibleAssetAmortization]:
        """批量计提所有在用无形资产的摊销"""
        assets = self.db.query(models.IntangibleAsset).filter(
            models.IntangibleAsset.account_id == self.account_id,
            models.IntangibleAsset.status != "已报废",
        ).all()

        results = []
        for asset in assets:
            amort = self.record_amortization(asset.id, period)
            if amort:
                results.append(amort)
        return results

    @derives("IntangibleAsset.accumulated_amortization_l4", from_fields=["IntangibleAssetAmortization.amount_l2"])
    def record_disposal(self, asset_id: int, disposal_date: Optional[date] = None) -> None:
        """处置（报废）无形资产

        1. 更新资产状态为"已报废"
        2. 生成处置凭证（冲销账面价值 + 处置损益）

        小企业会计准则：无形资产处置损益一律计入营业外收支。
        """
        asset = self.db.query(models.IntangibleAsset).filter(
            models.IntangibleAsset.id == asset_id,
            models.IntangibleAsset.account_id == self.account_id,
        ).first()
        if not asset:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                                data={"order_type": "无形资产", "order_id": asset_id})
        if asset.status == "已报废":
            return

        asset.status = "已报废"
        self.db.flush()

        original = Decimal(str(asset.original_value_l1))
        accumulated = Decimal(str(asset.accumulated_amortization_l4 or 0))
        net_value = original - accumulated

        if disposal_date is None:
            disposal_date = date.today()

        source = {
            "original_value": original,
            "accumulated_depreciation": accumulated,
            "net_value": net_value,
            "diff": -net_value,
            "source_model": "intangible_asset_disposal",
            "source_id": asset_id,
            "date": disposal_date,
            "description": f"无形资产处置: {asset.name}",
            "asset_account_code": "1701",
            "contra_account_code": "1702",
        }
        post_journal(self.db, self.account_id, "asset_disposal", source)


def _period_bounds(period: str) -> tuple[date, date]:
    """YYYY-MM → (该月第一天, 该月最后一天)"""
    year, month = map(int, period.split("-"))
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)
