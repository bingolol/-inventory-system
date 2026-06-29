"""利润表 (会小企02表)"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

import models
from utils import _d, Q2
from errors import BusinessError, ErrorCode
from models_finance import Ledger

from ._ledger_helpers import _lp, _pdr

def generate_income_statement(db: Session, account_id: int, start_date: str, end_date: str):
    """生成利润表"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

    # ── 利润表全从总账取数 ──
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    ledger_is = account and db.query(Ledger).filter(Ledger.code == account.code).first()

    # 营业收入 = 主营业务收入(6001) + 其他业务收入(6051)
    rev_d, rev_c = _lp(db, ledger_is, "6001", start_dt, end_dt)
    other_rev_d, other_rev_c = _lp(db, ledger_is, "6051", start_dt, end_dt)
    revenue = (rev_c - rev_d + other_rev_c - other_rev_d).quantize(Q2)
    cogs_d, cogs_c = _lp(db, ledger_is, "6401", start_dt, end_dt)
    cost_of_goods_sold = (cogs_d - cogs_c).quantize(Q2)
    administrative_expenses = _pdr(db, ledger_is, "6601", start_dt, end_dt).quantize(Q2)
    selling_expenses = _pdr(db, ledger_is, "6602", start_dt, end_dt).quantize(Q2)
    financial_expenses = _pdr(db, ledger_is, "6603", start_dt, end_dt).quantize(Q2)
    depr_d, depr_c = _lp(db, ledger_is, "1602", start_dt, end_dt)
    depreciation_expense = depr_c.quantize(Q2)
    total_operating_expenses = (selling_expenses + administrative_expenses + financial_expenses).quantize(Q2)

    # ── 营业毛利 ──
    gross_profit = revenue - cost_of_goods_sold

    # ── 营业利润 ──
    operating_profit = gross_profit - total_operating_expenses

    # ── 税金及附加 + 所得税 — 纯总账取数（月结后自动体现）──
    sur_d, sur_c = _lp(db, ledger_is, "6403", start_dt, end_dt)
    tax_surcharges = (sur_d - sur_c).quantize(Q2)
    total_operating_expenses = (total_operating_expenses + tax_surcharges).quantize(Q2)
    operating_profit = gross_profit - total_operating_expenses

    # ── 营业外收支 ──
    # 营业外收入 = 税收减免(6301) + 资产处置收益(6111)
    noi_d, noi_c = _lp(db, ledger_is, "6301", start_dt, end_dt)
    ado_d, ado_c = _lp(db, ledger_is, "6111", start_dt, end_dt)
    non_operating_income = (noi_c + ado_c).quantize(Q2)
    # 营业外支出 = 营业外支出(6701) + 资产处置损失(6711)
    noe_d, noe_c = _lp(db, ledger_is, "6701", start_dt, end_dt)
    adl_d, adl_c = _lp(db, ledger_is, "6711", start_dt, end_dt)
    non_operating_expense = (noe_d + adl_d).quantize(Q2)

    # ── 利润总额 ──
    gross_profit_total = operating_profit + non_operating_income - non_operating_expense

    # ── 所得税 = 期内 6801 净发生额 ──
    it_d, it_c = _lp(db, ledger_is, "6801", start_dt, end_dt)
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
        "total_operating_expenses": total_operating_expenses.quantize(Q2),
        "operating_profit": operating_profit.quantize(Q2),
        "non_operating_income": non_operating_income.quantize(Q2),
        "non_operating_expense": non_operating_expense.quantize(Q2),
        "gross_profit_total": gross_profit_total.quantize(Q2),
        "income_tax_expense": income_tax_expense.quantize(Q2),
        "net_profit": net_profit.quantize(Q2)
    }
