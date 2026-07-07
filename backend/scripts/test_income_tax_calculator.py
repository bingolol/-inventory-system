"""独立所得税计算器 — 两条纯 SQL 路径对比

路径 A：纯 SQL 查损益类科目（6001/6401/6601/6602/6603/6403/6301/6701）期间发生额
        手算累计利润 → 算所得税 target → 算 delta
        不调任何系统函数（engine_tax / snapshot / policy_engine / _profit）

路径 B：纯 SQL 查 222105 应交所得税期间发生额
        直接看系统实际写了多少所得税凭证

两条路径查的科目完全不同，互不依赖。
如果系统逻辑正确：A.delta 应该 = B.delta
"""
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal, set_maintenance_mode
from sqlalchemy import text


# ──────────────────────────────────────────────────────
# 路径 A：纯 SQL 查损益类科目，手算累计利润 + 所得税
# ──────────────────────────────────────────────────────

def query_account_period_net_sql(db, code: str, period_start: str, period_end: str) -> Decimal:
    """纯 SQL 查某科目在 [period_start, period_end] 的净借方（借-贷）

    用于损益类科目：收入净额=贷-借，费用净额=借-贷
    这里返回 借-贷，调用方按科目方向转换

    重要：损益类科目年结后余额归零（年结凭证把余额转到 4103），
    查累计利润必须排除 period_close/year_close 凭证，否则净额=0。
    这是会计准则要求，不是系统逻辑盲点。
    """
    sql = text("""
        SELECT COALESCE(SUM(aml.debit_l2 - aml.credit_l2), 0)
        FROM account_move_lines aml
        JOIN account_moves am ON aml.move_id = am.id
        JOIN ledger_accounts la ON aml.ledger_account_id = la.id
        WHERE la.code = :code
          AND am.date_l1 >= :ps
          AND am.date_l1 <= :pe
          AND am.source_model NOT IN ('period_close', 'year_close')
    """)
    result = db.execute(sql, {"code": code, "ps": period_start, "pe": period_end}).scalar()
    return Decimal(str(result or 0))


def query_account_period_net_with_subaccounts_sql(db, code_prefix: str, period_start: str, period_end: str) -> Decimal:
    """纯 SQL 查某科目及其所有子科目（按前缀匹配）的净借方（排除年结凭证）"""
    sql = text("""
        SELECT COALESCE(SUM(aml.debit_l2 - aml.credit_l2), 0)
        FROM account_move_lines aml
        JOIN account_moves am ON aml.move_id = am.id
        JOIN ledger_accounts la ON aml.ledger_account_id = la.id
        WHERE la.code LIKE :prefix
          AND am.date_l1 >= :ps
          AND am.date_l1 <= :pe
          AND am.source_model NOT IN ('period_close', 'year_close')
    """)
    result = db.execute(sql, {"prefix": f"{code_prefix}%", "ps": period_start, "pe": period_end}).scalar()
    return Decimal(str(result or 0))


def compute_cumulative_profit_path_a(db, year_start: str, period_end: str) -> Decimal:
    """路径 A：纯 SQL 查损益类科目累计发生额，手算累计利润

    利润 = 收入(贷-借) - 成本(借-贷) - 费用(借-贷) - 附加税(借-贷)
           + 营业外收入(贷-借) - 营业外支出(借-贷)
    """
    # 6001/6051 收入：贷-借 = -(借-贷)
    rev_net = -(query_account_period_net_sql(db, "6001", year_start, period_end)
                + query_account_period_net_sql(db, "6051", year_start, period_end))
    # 6401 成本：借-贷
    cogs_net = query_account_period_net_sql(db, "6401", year_start, period_end)
    # 6601/6602/6603 费用：借-贷
    exp_net = (query_account_period_net_sql(db, "6601", year_start, period_end)
               + query_account_period_net_sql(db, "6602", year_start, period_end)
               + query_account_period_net_sql(db, "6603", year_start, period_end))
    # 6403 附加税（含子科目）：借-贷，用 LIKE 匹配主+子
    sur_net = query_account_period_net_with_subaccounts_sql(db, "6403", year_start, period_end)
    # 6301/6111 营业外收入：贷-借
    noi_net = -(query_account_period_net_sql(db, "6301", year_start, period_end)
                + query_account_period_net_sql(db, "6111", year_start, period_end))
    # 6701/6711 营业外支出：借-贷
    noe_net = (query_account_period_net_sql(db, "6701", year_start, period_end)
               + query_account_period_net_sql(db, "6711", year_start, period_end))

    profit = rev_net - cogs_net - exp_net - sur_net + noi_net - noe_net
    return profit.quantize(Decimal("0.01"))


def compute_income_tax_delta_path_a(db, year_start: str, period_start: str, period_end: str) -> Decimal:
    """路径 A：计算 period 月的所得税 delta

    delta = (累计利润 × 5%) - (本年到上月底已计提)
    注意：累计利润用本年累计，但 2025 年只有 12 月
    """
    # 当月累计利润
    cum_profit = compute_cumulative_profit_path_a(db, year_start, period_end)
    if cum_profit <= 0:
        return Decimal("0")

    target = (cum_profit * Decimal("0.05")).quantize(Decimal("0.01"))

    # 本年到上月底的累计利润（算已计提）
    # 找上个月的月末
    ps_date = datetime.strptime(period_start, "%Y-%m-%d")
    if ps_date.month == 1:
        prev_end = f"{ps_date.year - 1}-12-31"
    else:
        # 上个月末
        if ps_date.month == 3:
            prev_end = f"{ps_date.year}-02-28"
        elif ps_date.month == 5 or ps_date.month == 7 or ps_date.month == 10 or ps_date.month == 12:
            prev_end = f"{ps_date.year}-{ps_date.month - 1:02d}-30"
        elif ps_date.month == 2 or ps_date.month == 4 or ps_date.month == 6 or ps_date.month == 8 or ps_date.month == 9 or ps_date.month == 11:
            prev_end = f"{ps_date.year}-{ps_date.month - 1:02d}-31"
        else:
            prev_end = f"{ps_date.year}-{ps_date.month - 1:02d}-30"

    # 如果上月底早于 year_start，已计提 = 0
    if prev_end < year_start:
        already_accrued = Decimal("0")
    else:
        prev_cum = compute_cumulative_profit_path_a(db, year_start, prev_end)
        already_accrued = (prev_cum * Decimal("0.05")).quantize(Decimal("0.01")) if prev_cum > 0 else Decimal("0")

    return (target - already_accrued).quantize(Decimal("0.01"))


# ──────────────────────────────────────────────────────
# 路径 B：纯 SQL 查 222105 发生额
# ──────────────────────────────────────────────────────

def query_222105_period_net_sql(db, period_start: str, period_end: str) -> Decimal:
    """纯 SQL 查 222105 在 [period_start, period_end] 的净贷方（贷-借）"""
    sql = text("""
        SELECT COALESCE(SUM(aml.credit_l2 - aml.debit_l2), 0)
        FROM account_move_lines aml
        JOIN account_moves am ON aml.move_id = am.id
        JOIN ledger_accounts la ON aml.ledger_account_id = la.id
        WHERE la.code = '222105'
          AND am.date_l1 >= :ps
          AND am.date_l1 <= :pe
    """)
    result = db.execute(sql, {"ps": period_start, "pe": period_end}).scalar()
    return Decimal(str(result or 0))


# ──────────────────────────────────────────────────────
# 对比
# ──────────────────────────────────────────────────────

def main():
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        print("=" * 110)
        print(" 独立所得税计算器 — 路径A(SQL查损益类手算) vs 路径B(SQL查222105)")
        print("=" * 110)

        periods = [
            ("2025-12", "2025-12-01", "2025-12-31"),
            ("2026-01", "2026-01-01", "2026-01-31"),
            ("2026-02", "2026-02-01", "2026-02-28"),
            ("2026-03", "2026-03-01", "2026-03-31"),
            ("2026-04", "2026-04-01", "2026-04-30"),
            ("2026-05", "2026-05-01", "2026-05-31"),
            ("2026-06", "2026-06-01", "2026-06-30"),
        ]

        print(f"{'期间':<10}{'A累计利润':>14}{'A.target':>12}{'A.delta':>12}"
              f"{'B.delta(222105)':>16}{'差异(A-B)':>14}")
        print("-" * 78)

        all_match = True
        for period, ps, pe in periods:
            # year_start: 2025 年只有 12 月，2026 年从 1 月开始
            if period.startswith("2025"):
                year_start = "2025-12-01"
            else:
                year_start = "2026-01-01"

            cum_a = compute_cumulative_profit_path_a(db, year_start, pe)
            target_a = (cum_a * Decimal("0.05")).quantize(Decimal("0.01")) if cum_a > 0 else Decimal("0")
            delta_a = compute_income_tax_delta_path_a(db, year_start, ps, pe)

            # 路径 B：纯 SQL 查当月 222105 净贷方
            delta_b = query_222105_period_net_sql(db, ps, pe)

            diff = delta_a - delta_b
            mark = "OK" if abs(diff) < Decimal("0.01") else "***"
            if abs(diff) >= Decimal("0.01"):
                all_match = False
            print(f"{period:<10}{cum_a:>14.2f}{target_a:>12.2f}{delta_a:>12.2f}"
                  f"{delta_b:>16.2f}{diff:>+14.2f}  {mark}")

        print("\n" + "=" * 110)
        if all_match:
            print(" 结论：路径 A = 路径 B，所得税计算完全正确")
        else:
            print(" 结论：存在差异，说明 engine_tax 写的 222105 凭证金额与损益类科目反推的不符")
        print("=" * 110)

        # ── 累计对比 ──
        print(f"\n{'期间':<10}{'A.target(累计)':>16}{'B.ytd(222105累计)':>20}{'差异':>12}")
        print("-" * 58)
        for period, ps, pe in periods:
            if period.startswith("2025"):
                year_start = "2025-12-01"
            else:
                year_start = "2026-01-01"
            cum_a = compute_cumulative_profit_path_a(db, year_start, pe)
            target_a = (cum_a * Decimal("0.05")).quantize(Decimal("0.01")) if cum_a > 0 else Decimal("0")
            ytd_b = query_222105_period_net_sql(db, year_start, pe)
            diff = target_a - ytd_b
            print(f"{period:<10}{target_a:>16.2f}{ytd_b:>20.2f}{diff:>+12.2f}")

        # ── 逐科目明细（便于定位）──
        print(f"\n逐科目累计净发生额（路径 A 明细）：")
        print(f"{'期间':<10}{'6001/6051':>12}{'6401':>10}{'6601':>10}{'6602':>10}{'6603':>10}{'6403*':>10}{'6301':>10}{'6701':>10}")
        print("-" * 92)
        for period, ps, pe in periods:
            if period.startswith("2025"):
                year_start = "2025-12-01"
            else:
                year_start = "2026-01-01"
            rev = -(query_account_period_net_sql(db, "6001", year_start, pe)
                    + query_account_period_net_sql(db, "6051", year_start, pe))
            cogs = query_account_period_net_sql(db, "6401", year_start, pe)
            e1 = query_account_period_net_sql(db, "6601", year_start, pe)
            e2 = query_account_period_net_sql(db, "6602", year_start, pe)
            e3 = query_account_period_net_sql(db, "6603", year_start, pe)
            sur = query_account_period_net_with_subaccounts_sql(db, "6403", year_start, pe)
            noi = -query_account_period_net_sql(db, "6301", year_start, pe)
            noe = query_account_period_net_sql(db, "6701", year_start, pe)
            print(f"{period:<10}{rev:>12.2f}{cogs:>10.2f}{e1:>10.2f}{e2:>10.2f}{e3:>10.2f}{sur:>10.2f}{noi:>10.2f}{noe:>10.2f}")

    finally:
        db.close()
        set_maintenance_mode(False)


if __name__ == "__main__":
    main()
