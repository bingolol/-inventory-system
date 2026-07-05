"""利润表 (会小企02表)"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

import models
from utils import _d, Q2
from errors import BusinessError, ErrorCode
from models_finance import Ledger
from lineage import reads, TIER_L1, TIER_L2, TIER_L4

from ._ledger_helpers import _lp, _pdr

@reads("AccountMoveLine.debit_l2", tier=TIER_L2, source="engine")
@reads("AccountMoveLine.credit_l2", tier=TIER_L2, source="engine")
def generate_income_statement(db: Session, account_id: int, start_date: str, end_date: str):
    """生成利润表"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    # ── 利润表全从总账取数 ──
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    ledger_is = account and db.query(Ledger).filter(Ledger.code == account.code).first()

    # 排除损益结转凭证：月结 period_close 会把损益科目余额清零到 4103，
    # 年末 year_close 进一步把 4103 清零到 4104。
    # 若不排除，收入/费用的借方（结转出去）会与贷方（实现收入）相互抵消，
    # 导致利润表所有项目显示为 0。
    _exclude = ["period_close", "year_close"]

    # 营业收入 = 主营业务收入(6001) + 其他业务收入(6051)
    rev_d, rev_c = _lp(db, ledger_is, "6001", start_dt, end_dt, exclude_source_models=_exclude)
    other_rev_d, other_rev_c = _lp(db, ledger_is, "6051", start_dt, end_dt, exclude_source_models=_exclude)
    revenue = (rev_c - rev_d + other_rev_c - other_rev_d).quantize(Q2)
    cogs_d, cgs_c = _lp(db, ledger_is, "6401", start_dt, end_dt, exclude_source_models=_exclude)
    cost_of_goods_sold = (cogs_d - cgs_c).quantize(Q2)
    administrative_expenses = _pdr(db, ledger_is, "6601", start_dt, end_dt, exclude_source_models=_exclude).quantize(Q2)
    selling_expenses = _pdr(db, ledger_is, "6602", start_dt, end_dt, exclude_source_models=_exclude).quantize(Q2)
    fin_d, fin_c = _lp(db, ledger_is, "6603", start_dt, end_dt, exclude_source_models=_exclude)
    financial_expenses = (fin_d - fin_c).quantize(Q2)
    depr_d, depr_c = _lp(db, ledger_is, "1602", start_dt, end_dt, exclude_source_models=_exclude)
    depreciation_expense = depr_c.quantize(Q2)
    total_operating_expenses = (selling_expenses + administrative_expenses + financial_expenses).quantize(Q2)

    # ── 营业毛利 ──
    gross_profit = revenue - cost_of_goods_sold

    # ── 营业利润 ──
    operating_profit = gross_profit - total_operating_expenses

    # ── 税金及附加 + 所得税 — 纯总账取数（月结后自动体现）──
    # 总账取数兼容旧 6403 和新的明细科目
    sur_d, sur_c = _lp(db, ledger_is, "6403", start_dt, end_dt, exclude_source_models=_exclude)
    tax_surcharges = (sur_d - sur_c).quantize(Q2)
    # 明细科目
    surcharge_detail_codes = {
        "consumption_tax": "640301",
        "urban_construction_tax": "640302",
        "education_surcharge": "640303",
        "local_education_surcharge": "640304",
        "resource_tax": "640305",
        "land_appreciation_tax": "640306",
        "property_tax": "640307",
        "land_use_tax": "640308",
        "vehicle_vessel_tax": "640309",
        "stamp_tax": "640310",
        "environmental_tax": "640311",
    }
    surcharge_details = {}
    for key, code in surcharge_detail_codes.items():
        d, c = _lp(db, ledger_is, code, start_dt, end_dt, exclude_source_models=_exclude)
        surcharge_details[key] = (d - c).quantize(Q2)
    # 若 6403 有旧数据而明细为 0，总额用 6403；否则用明细合计
    detail_total = sum(surcharge_details.values())
    if tax_surcharges == Decimal("0") and detail_total != Decimal("0"):
        tax_surcharges = detail_total
    total_operating_expenses = (total_operating_expenses + tax_surcharges).quantize(Q2)
    operating_profit = gross_profit - total_operating_expenses

    # ── 营业外收支 ──
    # 营业外收入 = 税收减免(6301) + 资产处置收益(6111)
    noi_d, noi_c = _lp(db, ledger_is, "6301", start_dt, end_dt, exclude_source_models=_exclude)
    ado_d, ado_c = _lp(db, ledger_is, "6111", start_dt, end_dt, exclude_source_models=_exclude)
    non_operating_income = (noi_c + ado_c).quantize(Q2)
    # 营业外支出 = 营业外支出(6701) + 资产处置损失(6711)
    noe_d, noe_c = _lp(db, ledger_is, "6701", start_dt, end_dt, exclude_source_models=_exclude)
    adl_d, adl_c = _lp(db, ledger_is, "6711", start_dt, end_dt, exclude_source_models=_exclude)
    non_operating_expense = (noe_d + adl_d).quantize(Q2)

    # ── 利润总额 ──
    gross_profit_total = operating_profit + non_operating_income - non_operating_expense

    # ── 所得税 = 期内 6801 净发生额 ──
    it_d, it_c = _lp(db, ledger_is, "6801", start_dt, end_dt, exclude_source_models=_exclude)
    income_tax_expense = (it_d - it_c).quantize(Q2)

    # ── 净利润 ──
    net_profit = gross_profit_total - income_tax_expense

    # ── 公式交叉校验 ──
    # 校验1：营业毛利 = 营业收入 - 营业成本
    expected_gross_profit = revenue - cost_of_goods_sold
    if abs(gross_profit - expected_gross_profit) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.INCOME_STATEMENT_INVALID,
            message=f"利润表公式错误：营业毛利 {gross_profit} ≠ 营业收入 {revenue} - 营业成本 {cost_of_goods_sold}",
            data={"gross_profit": float(gross_profit), "revenue": float(revenue), "cost_of_goods_sold": float(cost_of_goods_sold)}
        )

    # 校验2：营业利润 = 营业毛利 - 营业费用
    expected_operating_profit = gross_profit - total_operating_expenses
    if abs(operating_profit - expected_operating_profit) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.INCOME_STATEMENT_INVALID,
            message=f"利润表公式错误：营业利润 {operating_profit} ≠ 营业毛利 {gross_profit} - 营业费用 {total_operating_expenses}",
            data={"operating_profit": float(operating_profit), "gross_profit": float(gross_profit), "total_operating_expenses": float(total_operating_expenses)}
        )

    # 校验3：利润总额 = 营业利润 + 营业外收入 - 营业外支出
    expected_gross_profit_total = operating_profit + non_operating_income - non_operating_expense
    if abs(gross_profit_total - expected_gross_profit_total) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.INCOME_STATEMENT_INVALID,
            message=f"利润表公式错误：利润总额 {gross_profit_total} ≠ 营业利润 {operating_profit} + 营业外收入 {non_operating_income} - 营业外支出 {non_operating_expense}",
            data={"gross_profit_total": float(gross_profit_total), "operating_profit": float(operating_profit), "non_operating_income": float(non_operating_income), "non_operating_expense": float(non_operating_expense)}
        )

    # 校验4：净利润 = 利润总额 - 所得税费用
    expected_net_profit = gross_profit_total - income_tax_expense
    if abs(net_profit - expected_net_profit) > Decimal('0.01'):
        raise BusinessError(
            code=ErrorCode.INCOME_STATEMENT_INVALID,
            message=f"利润表公式错误：净利润 {net_profit} ≠ 利润总额 {gross_profit_total} - 所得税费用 {income_tax_expense}",
            data={"net_profit": float(net_profit), "gross_profit_total": float(gross_profit_total), "income_tax_expense": float(income_tax_expense)}
        )

    return {
        "period": f"{start_date} 至 {end_date}",
        "revenue": revenue.quantize(Q2),
        "cost_of_goods_sold": cost_of_goods_sold.quantize(Q2),
        "gross_profit": gross_profit.quantize(Q2),
        "selling_expenses": selling_expenses.quantize(Q2),
        "administrative_expenses": administrative_expenses.quantize(Q2),
        "financial_expenses": financial_expenses.quantize(Q2),
        "tax_surcharges": tax_surcharges.quantize(Q2),
        **{k: v.quantize(Q2) for k, v in surcharge_details.items()},
        "total_operating_expenses": total_operating_expenses.quantize(Q2),
        "operating_profit": operating_profit.quantize(Q2),
        "non_operating_income": non_operating_income.quantize(Q2),
        "non_operating_expense": non_operating_expense.quantize(Q2),
        "gross_profit_total": gross_profit_total.quantize(Q2),
        "income_tax_expense": income_tax_expense.quantize(Q2),
        "net_profit": net_profit.quantize(Q2)
    }
