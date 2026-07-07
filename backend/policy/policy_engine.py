"""层 3：政策引擎（Policy Engine）— 纯函数演算核心

替代散落的 calculate_vat / calculate_income_tax，所有税率/门槛/减免从事实源取值。
输入：EntityProfile + Facts → 输出：TaxResult
"""

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from policy.vat_facts import load_vat_facts
from policy.income_tax_facts import load_income_tax_facts
from policy.entity_profile import EntityProfile
from utils import _d, Q2

logger = logging.getLogger("inventory")


@dataclass
class VATResult:
    total_revenue: Decimal
    tax_rate: Decimal
    tax_payable_gross: Decimal
    tax_reduction: Decimal
    tax_payable: Decimal
    reduction_item: str
    reduction_amount: Decimal


@dataclass
class IncomeTaxResult:
    profit: Decimal
    tax_rate: Decimal
    tax_payable: Decimal
    reduction_amount: Decimal
    actual_tax: Decimal
    reduction_item: str


def calculate_vat(
    profile: EntityProfile,
    total_revenue: Decimal,
    input_tax: Decimal = Decimal("0"),
    output_tax: Optional[Decimal] = None,
    ordinary_revenue: Decimal = Decimal("0"),
    special_revenue: Decimal = Decimal("0"),
    carry_forward: Decimal = Decimal("0"),
    ref_date: Optional[date] = None,
) -> VATResult:
    vat_facts = load_vat_facts(ref_date)

    total_revenue = _d(total_revenue)
    input_tax = _d(input_tax)

    if profile.vat_type not in ("small_scale", "general"):
        raise ValueError(f"无效的增值税纳税人类型: {profile.vat_type}")

    if profile.vat_type == "general":
        if output_tax is None:
            raise ValueError("一般纳税人必须提供 output_tax（销项税额）")

        tax_payable_gross = _d(output_tax).quantize(Q2, rounding=ROUND_HALF_UP)
        tax_rate = (
            (tax_payable_gross / total_revenue).quantize(Decimal("0.01"))
            if total_revenue != 0
            else Decimal("0")
        )
        tax_payable = max(tax_payable_gross - input_tax - carry_forward, Decimal("0"))

        tax_reduction = Decimal("0")
        reduction_item = "一般纳税人"
    else:
        tax_rate = vat_facts.small_scale_syndicated_rate
        tax_payable_gross = (total_revenue * tax_rate).quantize(Q2, rounding=ROUND_HALF_UP)

        ordinary_rev = _d(ordinary_revenue)
        special_rev = _d(special_revenue)

        if total_revenue <= vat_facts.small_scale_quarterly_exemption:
            ordinary_tax = Decimal("0")
            special_tax = (special_rev * vat_facts.small_scale_reduced_rate).quantize(Q2, rounding=ROUND_HALF_UP)
            reduction_item = f"小规模普票免征增值税（季≤{vat_facts.small_scale_quarterly_exemption}），专票减按{vat_facts.small_scale_reduced_rate}征收"
        else:
            ordinary_tax = (ordinary_rev * vat_facts.small_scale_reduced_rate).quantize(Q2, rounding=ROUND_HALF_UP)
            special_tax = (special_rev * vat_facts.small_scale_reduced_rate).quantize(Q2, rounding=ROUND_HALF_UP)
            reduction_item = f"小规模纳税人减按{vat_facts.small_scale_reduced_rate}征收"

        tax_payable = (ordinary_tax + special_tax).quantize(Q2, rounding=ROUND_HALF_UP)
        tax_reduction = (tax_payable_gross - tax_payable).quantize(Q2, rounding=ROUND_HALF_UP)

    return VATResult(
        total_revenue=total_revenue,
        tax_rate=tax_rate,
        tax_payable_gross=tax_payable_gross.quantize(Q2),
        tax_reduction=tax_reduction,
        tax_payable=tax_payable.quantize(Q2),
        reduction_item=reduction_item,
        reduction_amount=tax_reduction,
    )


def calculate_income_tax(
    profile: EntityProfile,
    profit: Decimal,
    ref_date: Optional[date] = None,
) -> IncomeTaxResult:
    income_facts = load_income_tax_facts(ref_date)
    profit = _d(profit)

    if profile.income_type == "personal":
        return IncomeTaxResult(
            profit=profit, tax_rate=Decimal("0"), tax_payable=Decimal("0"),
            reduction_amount=Decimal("0"), actual_tax=Decimal("0"),
            reduction_item="个体工商户缴纳个人所得税，不计提企业所得税",
        )

    if profit < Decimal("0"):
        return IncomeTaxResult(
            profit=profit, tax_rate=Decimal("0"), tax_payable=Decimal("0"),
            reduction_amount=Decimal("0"), actual_tax=Decimal("0"),
            reduction_item="亏损，不计提所得税",
        )

    statutory_rate = income_facts.statutory_rate
    reduction_amount = Decimal("0")
    reduction_item = ""

    if profile.income_type == "small_micro" and profit <= income_facts.small_micro_threshold:
        tax_payable = (profit * income_facts.small_micro_deduction_rate * income_facts.small_micro_rate).quantize(Q2, rounding=ROUND_HALF_UP)
        reduction_item = f"小型微利企业减免（≤{income_facts.small_micro_threshold}，实际税负{income_facts.small_micro_effective_rate}）"
        reduction_amount = (profit * statutory_rate - tax_payable).quantize(Q2, rounding=ROUND_HALF_UP)
    else:
        tax_payable = (profit * statutory_rate).quantize(Q2, rounding=ROUND_HALF_UP)
        if profile.income_type == "small_micro":
            reduction_item = f"不符合小型微利企业优惠条件（>{income_facts.small_micro_threshold}）"
        else:
            reduction_item = "一般企业（法定税率25%）"

    return IncomeTaxResult(
        profit=profit, tax_rate=statutory_rate, tax_payable=tax_payable,
        reduction_amount=reduction_amount, actual_tax=tax_payable,
        reduction_item=reduction_item,
    )


class PolicyEngine:
    """政策引擎实例（兼容 AccountingEngine 接口风格）"""
    @staticmethod
    def calculate_vat(*args, **kwargs) -> VATResult:
        return calculate_vat(*args, **kwargs)

    @staticmethod
    def calculate_income_tax(*args, **kwargs) -> IncomeTaxResult:
        return calculate_income_tax(*args, **kwargs)
