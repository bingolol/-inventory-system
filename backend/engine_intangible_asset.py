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
from cost_engine import straight_line_depreciation
from lineage import writes, derives, reads, TIER_L2, TIER_L3, TIER_L4
from rules import enforce_rules
from engine_asset_base import BaseAssetEngine
from utils.period import period_bounds


class IntangibleAssetEngine(BaseAssetEngine):

    asset_model = models.IntangibleAsset
    depreciation_model = models.IntangibleAssetAmortization
    accumulated_attr = "accumulated_amortization_l4"
    contra_account_code = "1702"
    depreciation_source_model = "intangible_asset_amortization"
    depreciation_move_name = "无形资产摊销"

    @reads("IntangibleAsset.useful_life_l3", tier=TIER_L3, source="policy")
    def calculate_monthly(self, asset: models.IntangibleAsset) -> Decimal:
        original = Decimal(str(asset.original_value_l1))
        useful_life = int(asset.useful_life_l3)
        accumulated = Decimal(str(asset.accumulated_amortization_l4 or 0))
        return straight_line_depreciation(original, useful_life, accumulated, Decimal("0"))

    @writes("IntangibleAssetAmortization.amount_l2", tier=TIER_L2, source="engine")
    @writes("IntangibleAssetAmortization.accumulated_before_l2", tier=TIER_L2, source="engine")
    @writes("IntangibleAssetAmortization.accumulated_after_l2", tier=TIER_L2, source="engine")
    @derives("IntangibleAsset.accumulated_amortization_l4", from_fields=["IntangibleAssetAmortization.amount_l2"])
    def record_amortization(self, asset_id: int, period: str
                            ) -> Optional[models.IntangibleAssetAmortization]:
        return self._record_depreciation(asset_id, period)

    def batch_amortize(self, period: str
                       ) -> List[models.IntangibleAssetAmortization]:
        return self._batch_depreciate(period)

    def _raise_asset_not_found(self, asset_id: int):
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                            data={"order_type": "无形资产", "order_id": asset_id})

    def _is_eligible(self, asset, period: str) -> bool:
        return asset.status != "已报废"

    def _date_rule_ok(self, asset, period: str) -> bool:
        if not asset.start_date_l1:
            return True
        _, period_end = period_bounds(period)
        return asset.start_date_l1 <= period_end

    def _rule_param(self, asset_id: int) -> dict:
        return {"intangible_asset_id": asset_id}

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
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"无形资产处置日期不可为空: id={asset_id}"})

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
