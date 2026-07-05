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
from lineage import writes, derives, reads, TIER_L1, TIER_L2, TIER_L3, TIER_L4
from rules import enforce_rules


class FixedAssetEngine:
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id

    @reads("FixedAsset.salvage_rate_l3", tier=TIER_L3, source="policy")
    @reads("FixedAsset.useful_life_l3", tier=TIER_L3, source="policy")
    def calculate_monthly(self, asset: models.FixedAsset) -> Decimal:
        """计算月折旧额（年限平均法）

        返回实际可计提金额，已满额则返回 0。
        """
        original = Decimal(str(asset.original_value_l1))
        salvage_rate = Decimal(str(asset.salvage_rate_l3))
        useful_life = int(asset.useful_life_l3)
        accumulated = Decimal(str(asset.accumulated_depreciation_l4))

        if useful_life <= 0:
            return Decimal("0")

        depreciable = (original * (1 - salvage_rate)).quantize(Q2)
        monthly = (depreciable / useful_life).quantize(Q2)

        remaining = depreciable - accumulated
        if remaining <= 0:
            return Decimal("0")
        return min(monthly, remaining)

    @writes("FixedAssetDepreciation.amount_l2", tier=TIER_L2, source="engine")
    @writes("FixedAssetDepreciation.accumulated_before_l2", tier=TIER_L2, source="engine")
    @writes("FixedAssetDepreciation.accumulated_after_l2", tier=TIER_L2, source="engine")
    @derives("FixedAsset.accumulated_depreciation_l4", from_fields=["FixedAssetDepreciation.amount_l2"])
    def record_depreciation(self, asset_id: int, period: str
                            ) -> Optional[models.FixedAssetDepreciation]:
        """计提单个资产的月折旧

        1. 校验资产状态
        2. 幂等检查（同期间跳过）
        3. 计算月折旧额
        4. 写 FixedAssetDepreciation 流水
        5. 更新 accumulated_depreciation 缓存
        6. 生成会计凭证 借:6601(管理费用) 贷:1602(累计折旧)
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
        if asset.start_date_l1:
            dep_year, dep_month = map(int, period.split("-"))
            if dep_year < asset.start_date_l1.year or (
                dep_year == asset.start_date_l1.year and dep_month <= asset.start_date_l1.month
            ):
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

        accumulated_before = Decimal(str(asset.accumulated_depreciation_l4))
        accumulated_after = accumulated_before + monthly

        # 写折旧流水（真相源）
        dep = models.FixedAssetDepreciation(
            asset_id=asset_id,
            account_id=self.account_id,
            period=period,
            amount_l2=monthly,
            accumulated_before_l2=accumulated_before,
            accumulated_after_l2=accumulated_after,
        )
        self.db.add(dep)

        # 更新缓存
        asset.accumulated_depreciation_l4 = accumulated_after
        self.db.flush()

        # 生成会计凭证：借:6601（管理费用）贷:1602（累计折旧）
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

        # AS-05 折旧公式 + 累计折旧上限校验
        enforce_rules(self.db, ["AS-05"], {"asset_id": asset_id})

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

    @derives("FixedAsset.accumulated_depreciation_l4", from_fields=["FixedAssetDepreciation.amount_l2"])
    def record_disposal(self, asset_id: int, disposal_price: Decimal = Decimal("0"),
                        disposal_date: Optional[date] = None,
                        bank_account_id: Optional[int] = None) -> None:
        """处置（报废/出售）固定资产

        1. 更新资产状态为"报废"
        2. 生成处置凭证（冲销账面价值 + 处置损益）
        3. 处置价格 > 0 且提供 bank_account_id 时：
           - 创建 BankTransaction（inflow，投资活动现金流）
           - 同步银行账户余额（与 1002 总账科目保持一致）

        小企业会计准则：固定资产处置损益一律计入营业外收支，不使用"资产处置损益"科目。
        处置价格 > 账面净值 → 营业外收入（6301）
        处置价格 < 账面净值 → 营业外支出（6701）
        处置价格 = 账面净值 → 无损益

        BR-22: disposal_date 默认用今天，但允许调用方传入业务日期，
        避免 BS 按 cutoff 过滤时资产处置凭证被排除（与 reverse_journal 同类问题）。
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

        original = Decimal(str(asset.original_value_l1))
        accumulated = Decimal(str(asset.accumulated_depreciation_l4))
        net_value = original - accumulated
        disposal_price = Decimal(str(disposal_price))
        diff = disposal_price - net_value

        # 修复 #7：强制要求 disposal_date，避免跨月补录时凭证日期为 today
        # 原代码 disposal_date or date.today() 导致跨月处置时 BS 不平。
        # 与 sale_date/return_date 一致，要求显式传入业务日期。
        if disposal_date is None:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="处置日期不能为空，请提供业务发生日期",
                ai_instruction="STOP_RETRYING. disposal_date 必填，请提供处置业务日期（如 2025-06-28）。"
            )
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

        # AS-07 处置凭证科目校验(必须用 6301/6701 营业外收支,非 6111/6711 资产处置损益)
        enforce_rules(self.db, ["AS-07"], {"asset_id": asset_id})

        # 处置价格 > 0 → 银行收到处置款，同步创建银行流水（与 1002 总账科目保持一致）
        # 未提供 bank_account_id 时按原逻辑仅更新总账（向后兼容）
        if disposal_price > 0 and bank_account_id is not None:
            from engine_bank import BankEngine
            # 经 BankEngine.record_transaction 统一入口写入
            # 处置固定资产属于投资活动现金流（CAS 31）
            BankEngine(self.db, self.account_id).record_transaction(
                bank_account_id=bank_account_id,
                transaction_type="inflow",
                amount=disposal_price,
                transaction_date=disposal_date,
                description=f"固定资产处置款: {asset.name}",
                flow_category="investing",
                related_entity_type="fixed_asset_disposal",
                related_entity_id=asset_id,
            )


def _period_to_date(period: str) -> date:
    """YYYY-MM → 该月最后一天"""
    year, month = map(int, period.split("-"))
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)
