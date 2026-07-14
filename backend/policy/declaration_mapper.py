"""层 4：申报表映射器（Declaration Mapper）

将 policy_engine 输出映射到税局表格行次（2026/1/1《增值税法》施行后版本）。
"""

from typing import Dict, Any
from decimal import Decimal
from policy.policy_engine import VATResult, IncomeTaxResult
from policy.entity_profile import EntityProfile


def map_vat_to_main_form(
    result: VATResult,
    profile: EntityProfile,
    input_tax_l1: Decimal = Decimal("0"),
    carry_forward_l1: Decimal = Decimal("0"),
) -> Dict[str, Any]:
    """增值税纳税申报表主表行次映射（2026 版）。

    Args:
        result: policy_engine.calculate_vat() 输出
        profile: 主体画像
        input_tax_l1: 当期进项税额
        carry_forward_l1: 上期期末留抵税额
    """
    deductible_total = input_tax_l1 + carry_forward_l1
    actual_deduction = min(deductible_total, result.tax_payable_gross) if result.tax_payable_gross > 0 else Decimal("0")
    ending_carry_forward = max(deductible_total - actual_deduction, Decimal("0"))

    rows = {
        "row_1": float(result.total_revenue_l1),
        "row_2": float(result.total_revenue_l1),
        "row_3": 0.0,
        "row_4": 0.0,
        "row_5": 0.0,
        "row_11": float(result.tax_payable_gross),
        "row_12": float(input_tax_l1),
        "row_13": float(carry_forward_l1),
        "row_14": 0.0,
        "row_17": float(deductible_total),
        "row_18": float(actual_deduction),
        "row_19": float(result.tax_payable),
        "row_20": float(ending_carry_forward),
        "row_21": 0.0,
        "row_22": 0.0,
        "row_23": 0.0,                                      # 2026版：留抵退税转出
        "row_24": float(result.tax_payable),
        "row_25": 0.0,
        "row_27": 0.0,
        "row_30": 0.0,
        "row_32": float(result.tax_payable),
        "row_34": float(result.tax_payable),
    }

    return {
        "taxpayer_type": profile.vat_type,
        "vat_payable_l1": float(result.tax_payable),
        "reduction_item": result.reduction_item,
        "reduction_amount": float(result.reduction_amount),
        "tax_reduction": float(result.tax_reduction),
        "input_tax_l1": float(input_tax_l1),
        "carry_forward_l1": float(carry_forward_l1),
        "deductible_total": float(deductible_total),
        "actual_deduction": float(actual_deduction),
        "ending_carry_forward": float(ending_carry_forward),
        "rows": rows,
        "form_version": "2026",
    }


def map_income_tax_to_prepayment_form(
    result: IncomeTaxResult,
    profile: EntityProfile,
    revenue: float = 0.0,
    cost: float = 0.0,
    expenses: float = 0.0,
) -> Dict[str, Any]:
    """企业所得税预缴申报表（A 类）行次映射。"""
    rows = {
        "row_1": revenue,
        "row_2": cost,
        "row_3": expenses,
        "row_4": revenue - cost - expenses,
        "row_5": 0.0,
        "row_6": 0.0,
        "row_7": 0.0,
        "row_8": 0.0,
        "row_9": float(result.profit),
        "row_10": float(result.tax_rate),
        "row_11": float(result.tax_payable),
        "row_12": float(result.reduction_amount),
        "row_13": 0.0,
        "row_14": float(result.actual_tax),
    }

    return {
        "income_type": profile.income_type,
        "reduction_item": result.reduction_item,
        "rows": rows,
    }
