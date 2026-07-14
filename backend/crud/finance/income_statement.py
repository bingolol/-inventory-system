"""利润表 (会小企02表)"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, or_

import models
from utils import _d, Q2, end_of_day
from errors import BusinessError, ErrorCode
from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
from lineage import reads, TIER_L1, TIER_L2, TIER_L4

from ._snapshot import LedgerSnapshot
from ._profit import compute_cumulative_profit

# 损益类科目清单（与 _profit.py 保持一致，用于独立总账直查校验）
_REVENUE_CODES = ["6001", "6051"]
_COST_CODES = ["6401"]
_EXPENSE_CODES = ["6601", "6602", "6603", "6403"]
# 6403 税金及附加明细子科目（主科目余额为 0 时回退，与 _profit.py SURCHARGE_SUB_CODES 一致）
_SURCHARGE_SUB_CODES = [
    "640301", "640302", "640303", "640304", "640305",
    "640306", "640307", "640308", "640309", "640310", "640311",
]
_NON_OP_INCOME_CODES = ["6301", "6111"]
_NON_OP_EXPENSE_CODES = ["6701", "6711"]
# 月结结转凭证不计入损益发生额（避免收入/费用被结平后双重计数）
_CLOSE_SOURCE_MODELS = {"period_close", "year_close"}


def _ledger_independent_profit(db: Session, ledger: Ledger, start_dt: datetime, end_dt: datetime) -> Decimal:
    """独立总账直查损益类科目净额（不经过 LedgerSnapshot 缓存）。

    作为 compute_cumulative_profit 的对账基准，两条路径独立取数：
      - 报表路径：LedgerSnapshot.pnl_dc（内存计算）
      - 校验路径：本函数 SQL 直查（数据库聚合）
    若两者不一致，说明 snapshot 加载/聚合逻辑有缺陷。
    """

    def _net(codes: list[str], debit_positive: bool) -> Decimal:
        # AccountMove.date_l1 是 Date 类型，用 date 对象比较避免 SQLite 字符串比较歧义
        start_d = start_dt.date() if hasattr(start_dt, 'date') and not isinstance(start_dt, date) else start_dt
        end_d = end_dt.date() if hasattr(end_dt, 'date') and not isinstance(end_dt, date) else end_dt
        rows = db.query(
            LedgerAccount.code,
            sqlfunc.sum(AccountMoveLine.debit_l2),
            sqlfunc.sum(AccountMoveLine.credit_l2),
        ).join(
            AccountMoveLine, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(
            AccountMove, AccountMoveLine.move_id == AccountMove.id
        ).filter(
            LedgerAccount.ledger_id == ledger.id,
            LedgerAccount.code.in_(codes),
            AccountMove.date_l1 >= start_d,
            AccountMove.date_l1 <= end_d,
            # source_model 为 NULL 时不算结转凭证（旧数据/手工凭证），需包含
            or_(AccountMove.source_model == None, ~AccountMove.source_model.in_(_CLOSE_SOURCE_MODELS)),
        ).group_by(LedgerAccount.code).all()
        total = Decimal("0")
        for _, d_sum, c_sum in rows:
            d = _d(d_sum)
            c = _d(c_sum)
            total += (d - c) if debit_positive else (c - d)
        return total

    revenue = _net(_REVENUE_CODES, debit_positive=False)
    cogs = _net(_COST_CODES, debit_positive=True)
    # 6403 子科目回退：主科目余额为 0 时汇总明细科目（与 _profit.py 逻辑一致）
    main_6403 = _net(["6403"], debit_positive=True)
    if main_6403 == Decimal("0"):
        surcharge_sub = _net(_SURCHARGE_SUB_CODES, debit_positive=True)
        expenses = _net(["6601", "6602", "6603"], debit_positive=True) + surcharge_sub
    else:
        expenses = _net(_EXPENSE_CODES, debit_positive=True)
    non_op_income = _net(_NON_OP_INCOME_CODES, debit_positive=False)
    non_op_expense = _net(_NON_OP_EXPENSE_CODES, debit_positive=True)
    return (revenue - cogs - expenses + non_op_income - non_op_expense).quantize(Q2)


@reads("AccountMoveLine.debit_l2", tier=TIER_L2, source="engine")
@reads("AccountMoveLine.credit_l2", tier=TIER_L2, source="engine")
def generate_income_statement(db: Session, account_id: int, start_date: str, end_date: str):
    """生成利润表"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = end_of_day(datetime.strptime(end_date, "%Y-%m-%d"))

    sn = LedgerSnapshot(db, account_id, bs_cutoff=end_dt, period_start=start_dt, period_end=end_dt)

    # 营业收入
    rev_d, rev_c = sn.pnl_dc("6001", start_dt, end_dt)
    other_rev_d, other_rev_c = sn.pnl_dc("6051", start_dt, end_dt)
    revenue = (rev_c - rev_d + other_rev_c - other_rev_d).quantize(Q2)
    cogs_d, cgs_c = sn.pnl_dc("6401", start_dt, end_dt)
    cost_of_goods_sold = (cogs_d - cgs_c).quantize(Q2)
    # 费用科目取净额（借方 - 贷方），处理贷方冲减
    _adm_d, _adm_c = sn.pnl_dc("6601", start_dt, end_dt)
    administrative_expenses = (_adm_d - _adm_c).quantize(Q2)
    _sell_d, _sell_c = sn.pnl_dc("6602", start_dt, end_dt)
    selling_expenses = (_sell_d - _sell_c).quantize(Q2)
    fin_d, fin_c = sn.pnl_dc("6603", start_dt, end_dt)
    financial_expenses = (fin_d - fin_c).quantize(Q2)
    depr_d, depr_c = sn.pnl_dc("1602", start_dt, end_dt)
    depreciation_expense = depr_c.quantize(Q2)
    total_operating_expenses = (selling_expenses + administrative_expenses + financial_expenses).quantize(Q2)

    # ── 营业毛利 ──
    gross_profit = revenue - cost_of_goods_sold

    # ── 营业利润 ──
    operating_profit = gross_profit - total_operating_expenses

    # ── 税金及附加 + 所得税 ──
    sur_d, sur_c = sn.pnl_dc("6403", start_dt, end_dt)
    tax_surcharges = (sur_d - sur_c).quantize(Q2)
    # 明细科目
    surcharge_detail_codes = {
        "consumption_tax": "640301",
        "urban_construction_tax_l1": "640302",
        "education_surcharge_l1": "640303",
        "local_education_surcharge_l1": "640304",
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
        d, c = sn.pnl_dc(code, start_dt, end_dt)
        surcharge_details[key] = (d - c).quantize(Q2)
    # 若 6403 有旧数据而明细为 0，总额用 6403；否则用明细合计
    detail_total = sum(surcharge_details.values())
    if tax_surcharges == Decimal("0") and detail_total != Decimal("0"):
        tax_surcharges = detail_total
    total_operating_expenses = (total_operating_expenses + tax_surcharges).quantize(Q2)
    operating_profit = gross_profit - total_operating_expenses

    # ── 营业外收支 ──
    noi_d, noi_c = sn.pnl_dc("6301", start_dt, end_dt)
    ado_d, ado_c = sn.pnl_dc("6111", start_dt, end_dt)
    non_operating_income = (noi_c + ado_c).quantize(Q2)
    noe_d, noe_c = sn.pnl_dc("6701", start_dt, end_dt)
    adl_d, adl_c = sn.pnl_dc("6711", start_dt, end_dt)
    non_operating_expense = (noe_d + adl_d).quantize(Q2)

    # ── 利润总额（复用统一损益汇总）──
    gross_profit_total = compute_cumulative_profit(sn, start_dt, end_dt)

    # ── 所得税 ──
    it_d, it_c = sn.pnl_dc("6801", start_dt, end_dt)
    income_tax_expense = (it_d - it_c).quantize(Q2)

    # ── 净利润 ──
    net_profit = gross_profit_total - income_tax_expense

    # ── 真校验：报表利润总额 vs 独立总账直查 ──
    # 两条独立取数路径：snapshot 内存聚合 vs SQL 直查聚合。
    # 之前用同源公式自我校验恒等不报错，现改为对比两条独立路径。
    if sn._ledger is not None:
        independent_profit = _ledger_independent_profit(db, sn._ledger, start_dt, end_dt)
        if abs(gross_profit_total - independent_profit) > Decimal('0.01'):
            raise BusinessError(
                code=ErrorCode.INCOME_STATEMENT_INVALID,
                message=(
                    f"利润表校验失败：报表利润总额 {gross_profit_total} ≠ 总账独立直查 {independent_profit}，"
                    f"差异 {(gross_profit_total - independent_profit).quantize(Q2)}，"
                    f"说明 LedgerSnapshot 加载/聚合逻辑与 SQL 直查不一致"
                ),
                data={
                    "report_profit": float(gross_profit_total),
                    "ledger_independent_profit": float(independent_profit),
                    "diff": float((gross_profit_total - independent_profit).quantize(Q2)),
                    "period": f"{start_date} 至 {end_date}",
                }
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
