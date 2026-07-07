"""P4-2 端到端验证：三层架构 + API 集成路径

模拟 routers/financial_reports.py 的 ?reconcile=true 调用路径，
确认三层架构在 API 层正常工作。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, date
from database import SessionLocal
from crud.finance._snapshot import LedgerSnapshot
from reports.engine import ReportEngine
from reports.reconcile import ReportReconciliation
from reports.definitions.balance_sheet import BALANCE_SHEET
from reports.definitions.income_statement import INCOME_STATEMENT
from rules import check_global_balance, check_accounting_equation, check_journal_rule
from models_finance import AccountMove, Ledger
import models


def main():
    db = SessionLocal()
    account_id = 1
    acc = db.query(models.Account).filter(models.Account.id == account_id).first()
    ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
    ledger_id = ledger.id

    # ── 环节3: P2 ReportReconciliation（API 路径模拟）──
    qd = datetime(2026, 6, 30) + timedelta(days=1) - timedelta(seconds=1)
    sn = LedgerSnapshot(db, account_id, bs_cutoff=qd)
    engine = ReportEngine()

    # BS ?reconcile=true
    result = engine.execute(BALANCE_SHEET, sn, source_mode="invoice")
    recon_values = {k: v for k, v in result.items()
                    if not k.startswith("_") and isinstance(v, (int, float))}
    recon = ReportReconciliation(db, sn, report_type="balance_sheet")
    r = recon.reconcile(BALANCE_SHEET, recon_values, source_mode="invoice")
    bs_summary = r.to_dict()["summary"]
    print(f"[P2] BS  reconcile: total={bs_summary['total']} "
          f"verified={bs_summary['verified']} "
          f"matched={bs_summary['matched']} "
          f"mismatched={bs_summary['mismatched']}")

    # IS ?reconcile=true (2026-01 ~ 2026-06)
    sd = datetime(2026, 1, 1)
    ed = datetime(2026, 6, 30) + timedelta(days=1) - timedelta(seconds=1)
    sn2 = LedgerSnapshot(db, account_id, bs_cutoff=ed, period_start=sd, period_end=ed)
    result2 = engine.execute(INCOME_STATEMENT, sn2)
    recon_values2 = {k: v for k, v in result2.items()
                     if not k.startswith("_") and isinstance(v, (int, float))}
    recon2 = ReportReconciliation(db, sn2, report_type="income_statement")
    r2 = recon2.reconcile(INCOME_STATEMENT, recon_values2)
    is_summary = r2.to_dict()["summary"]
    print(f"[P2] IS  reconcile: total={is_summary['total']} "
          f"verified={is_summary['verified']} "
          f"matched={is_summary['matched']} "
          f"mismatched={is_summary['mismatched']}")

    # ── 环节2: P1 LedgerInvariantGuard ──
    v1 = check_global_balance(db, {})
    print(f"[P1] Global balance: violations={len(v1)}")

    v2 = check_accounting_equation(db, {"report_date": date(2026, 6, 30), "ledger_id": ledger_id})
    print(f"[P1] Equation (2026-06-30): violations={len(v2)}")

    v3 = check_accounting_equation(db, {"report_date": date(2025, 12, 31), "ledger_id": ledger_id})
    print(f"[P1] Equation (2025-12-31): violations={len(v3)}")

    # ── 环节1: P3 JournalRuleRegistry ──
    moves = db.query(AccountMove).filter(AccountMove.state == "posted").all()
    violations_total = 0
    for m in moves:
        violations_total += len(check_journal_rule(db, m.id))
    print(f"[P3] JournalRule: {len(moves)} posted moves, {violations_total} violations")

    # ── 总结 ──
    all_pass = (
        bs_summary["mismatched"] == 0
        and is_summary["mismatched"] == 0
        and len(v1) == 0
        and len(v2) == 0
        and len(v3) == 0
        and violations_total == 0
    )
    print()
    print("=" * 80)
    if all_pass:
        print("OVERALL: PASS — 三层架构端到端验证全部通过")
    else:
        print("OVERALL: FAIL — 存在不一致")
    print("=" * 80)


if __name__ == "__main__":
    main()
