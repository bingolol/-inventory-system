from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from crud.finance import aggregate_vat_invoices
from crud.finance.income_statement import generate_income_statement
from crud.finance.tax_declarations import compute_carry_forward
from policy.entity_profile import build_profile
from policy.policy_engine import (
    calculate_vat as policy_vat,
    calculate_income_tax as policy_income_tax,
)
from policy.surcharge_facts import load_surcharge_facts
from policy.vat_facts import (
    VAT_SMALL_SCALE_QUARTERLY_EXEMPTION,
    VAT_SMALL_SCALE_REDUCED_RATE,
)
from utils import _d, Q2


def build_module_vat(db: Session, account_id: int, start_date: datetime, end_date: datetime, account):
    agg = aggregate_vat_invoices(db, account_id, start_date, end_date)
    profile = build_profile(account, ref_date=start_date.date())
    carry_forward_l1 = compute_carry_forward(db, account, start_date)

    vat_result = policy_vat(
        profile=profile, total_revenue_l1=agg["output_total"],
        input_tax_l1=agg["input_tax_l1"], output_tax_l1=agg["output_tax_l1"],
        ordinary_revenue=agg["ordinary_revenue"], special_revenue=agg["special_revenue"],
        carry_forward_l1=carry_forward_l1,
    )

    total_revenue_l1 = agg["output_total"].quantize(Q2)
    ordinary_rev = agg["ordinary_revenue"].quantize(Q2)
    special_rev = agg["special_revenue"].quantize(Q2)
    exemption_threshold = float(VAT_SMALL_SCALE_QUARTERLY_EXEMPTION.value)
    is_under = float(total_revenue_l1) <= exemption_threshold

    return {
        "taxpayer_type": profile.vat_type,
        "taxpayer_type_label": "小规模纳税人" if profile.vat_type == "small_scale" else "一般纳税人",
        "quarterly_total": float(total_revenue_l1),
        "exemption_threshold": exemption_threshold, "is_under_threshold": is_under,
        "ordinary_revenue": float(ordinary_rev),
        "ordinary_tax": float(vat_result.tax_payable_gross.quantize(Q2)),
        "special_revenue": float(special_rev),
        "special_tax_rate": float(VAT_SMALL_SCALE_REDUCED_RATE.value) if profile.vat_type == "small_scale" else None,
        "vat_payable_l1": float(vat_result.tax_payable.quantize(Q2)),
        "reduction_item": vat_result.reduction_item,
        "input_tax_l1": float(agg["input_tax_l1"].quantize(Q2)),
        "output_tax_l1": float(agg["output_tax_l1"].quantize(Q2)) if profile.vat_type == "general" else None,
        "carry_forward_l1": float(carry_forward_l1.quantize(Q2)) if profile.vat_type == "general" else None,
    }


def build_module_surcharge(vat_payable_l1: float, surcharge_halved_l3: bool):
    """附加税 = 城建税 + 教育费附加 + 地方教育附加，附在增值税之上。

    税率从 policy/surcharge_facts.py 事实源读取，禁止硬编码。
    """
    facts = load_surcharge_facts()
    full_rate = facts.total_rate
    halving = facts.halving_factor if surcharge_halved_l3 else Decimal("1")
    effective_rate = full_rate * halving

    base = Decimal(str(vat_payable_l1 or 0))
    total = (base * effective_rate).quantize(Q2)

    def _item(name: str, rate: Decimal, law: str) -> dict:
        amount = (base * rate * halving).quantize(Q2)
        return {"name": name, "rate": f"{float(rate) * 100:.0f}%", "amount": float(amount), "law": law}

    breakdown = [
        _item("城市建设维护税", facts.urban_construction_tax_rate, "《城市维护建设税法》"),
        _item("教育费附加", facts.education_surcharge_rate, "《征收教育费附加暂行规定》"),
        _item("地方教育附加", facts.local_education_surcharge_rate, "财税〔2011〕13号"),
    ]

    return {
        "vat_payable_l1": float(base),
        "breakdown": breakdown,
        "total": float(total),
        "full_rate": f"{float(full_rate) * 100:.0f}%",
        "effective_rate": f"{float(effective_rate) * 100:.1f}%",
        "is_halved": surcharge_halved_l3,
        "reduction_note": "您是小型微利企业/个体工商户/小规模纳税人，享受六税两费减半征收。" if surcharge_halved_l3 else "按法定税率全额征收。",
    }


def build_module_income_tax(db: Session, account_id: int, start_date: datetime, end_date: datetime, account):
    is_data = generate_income_statement(
        db, account_id,
        start_date.strftime("%Y-%m-%d"),
        (end_date - timedelta(days=1)).strftime("%Y-%m-%d")
    )
    revenue = _d(is_data.get("revenue", 0)).quantize(Q2)
    cost = _d(is_data.get("cost_of_goods_sold", 0)).quantize(Q2)
    tax_surcharge = _d(is_data.get("tax_surcharges", 0)).quantize(Q2)
    admin_exp = _d(is_data.get("administrative_expenses", 0)).quantize(Q2)
    selling_exp = _d(is_data.get("selling_expenses", 0)).quantize(Q2)
    fin_exp = _d(is_data.get("financial_expenses", 0)).quantize(Q2)
    total_opex = (admin_exp + selling_exp + fin_exp).quantize(Q2)
    non_op_income = _d(is_data.get("non_operating_income", 0)).quantize(Q2)
    non_op_expense = _d(is_data.get("non_operating_expense", 0)).quantize(Q2)
    taxable_income = _d(is_data.get("gross_profit_total", 0)).quantize(Q2)
    if taxable_income < 0:
        taxable_income = Decimal("0")

    profile = build_profile(account, ref_date=start_date.date())
    tax_result = policy_income_tax(profile=profile, profit=taxable_income)

    steps = []
    steps.append({"label": "营业收入", "value": float(revenue),
                  "explain": "这个季度卖货收到的全部钱（不含增值税）。对应科目 6001 主营业务收入 + 6051 其他业务收入", "cls": "positive"})
    if cost > 0:
        steps.append({"label": "减：营业成本", "value": float(-cost),
                      "explain": "卖掉这批货，当初你进货花了多少钱。对应科目 6401 主营业务成本", "cls": "negative"})
    if admin_exp > 0:
        steps.append({"label": "减：管理费用", "value": float(-admin_exp),
                      "explain": "房租、水电、办公用品、工资等日常运营开销，科目代码 6601", "cls": "negative"})
    if selling_exp > 0:
        steps.append({"label": "减：销售费用", "value": float(-selling_exp),
                      "explain": "广告宣传、运输包装等销售相关支出，科目代码 6602", "cls": "negative"})
    if fin_exp > 0:
        steps.append({"label": "减：财务费用", "value": float(-fin_exp),
                      "explain": "银行手续费、贷款利息等，科目代码 6603", "cls": "negative"})
    if tax_surcharge > 0:
        steps.append({"label": "减：税金及附加", "value": float(-tax_surcharge),
                      "explain": "附加税（城建税、教育费附加等），科目代码 6403", "cls": "negative"})
    if non_op_income > 0:
        steps.append({"label": "加：营业外收入", "value": float(non_op_income),
                      "explain": "非日常经营带来的收入，如小规模增值税免税转入。科目 6301 + 6111", "cls": "positive"})
    if non_op_expense > 0:
        steps.append({"label": "减：营业外支出", "value": float(-non_op_expense),
                      "explain": "非日常经营的支出，如资产报废损失。科目 6701 + 6711", "cls": "negative"})

    steps.append({"label": "应纳税所得额", "value": float(taxable_income),
                  "explain": f"利润 = 收入 {float(revenue)} - 成本 {float(cost)} - 费用 {float(total_opex)} - 税金 {float(tax_surcharge)} + 营业外 {float(non_op_income - non_op_expense)} = {float(taxable_income)}",
                  "cls": "subtotal"})

    entity_label = ""
    if profile.income_type == "personal":
        entity_label = "个体工商户，不缴纳企业所得税（缴个人所得税，本系统不处理）"
    elif profile.income_type == "small_micro":
        entity_label = "小型微利企业（年利润 ≤ 300 万适用），实际税率 5%（= 法定税率 25% × 优惠减按 20%）"
    else:
        entity_label = "一般企业，法定税率 25%"

    steps.append({"label": "适用税率", "value": f"{float(tax_result.tax_rate) * 100:.1f}%",
                  "explain": entity_label, "cls": "rate"})
    if float(tax_result.reduction_amount) > 0:
        steps.append({"label": "减免税额", "value": float(-tax_result.reduction_amount),
                      "explain": tax_result.reduction_item, "cls": "reduction"})
    steps.append({"label": "应纳企业所得税", "value": float(tax_result.tax_payable),
                  "explain": f"应纳税所得额 {float(taxable_income)} × 实际税率 {float(tax_result.tax_rate) if tax_result.tax_rate > 0 else 0} = {float(tax_result.tax_payable)} 元",
                  "cls": "result"})

    return {
        "revenue": float(revenue), "cost": float(cost), "total_opex": float(total_opex),
        "tax_surcharge": float(tax_surcharge), "non_op_income": float(non_op_income),
        "non_op_expense": float(non_op_expense), "taxable_income": float(taxable_income),
        "tax_rate": float(tax_result.tax_rate), "tax_payable": float(tax_result.tax_payable),
        "reduction_amount": float(tax_result.reduction_amount), "reduction_item": tax_result.reduction_item,
        "entity_type": profile.income_type,
        "is_loss": float(taxable_income) <= 0 and profile.income_type != "personal",
        "is_personal": profile.income_type == "personal", "steps": steps,
    }
