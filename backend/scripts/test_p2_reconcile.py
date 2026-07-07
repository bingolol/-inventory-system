"""P2 双路径对账测试脚本 — ReportReconciliation

验证 ReportReconciliation 从 DSL Source 派生独立 SQL 路径，
与 ReportEngine 的正常 resolve 路径对比，发现 bug。

用例：
1. BS 对账 @ 2026-06-30（截止日，bs_cutoff）
2. IS 对账 @ 2026-01-01 ~ 2026-06-30（半年累计）
3. IS 月度对账 @ 2026-06-01 ~ 2026-06-30（单月）

对账对象：account_id=1, ledger_id=1（巧游电子科技）
"""
import sys
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal, set_maintenance_mode
import models
from models_finance import Ledger
from crud.finance._snapshot import LedgerSnapshot
from reports.engine import ReportEngine
from reports.reconcile import ReportReconciliation
from reports.definitions.balance_sheet import BALANCE_SHEET
from reports.definitions.income_statement import INCOME_STATEMENT


ACCOUNT_ID = 1
LEDGER_ID = 1
BS_CUTOFF = datetime(2026, 6, 30, 23, 59, 59)


def _summary_dict(result) -> dict:
    """从 ReconciliationResult 属性构造 summary 视图
    （ReconciliationResult 没有 .summary 属性，只有 to_dict()['summary']）"""
    return {
        "total": result.total_count,
        "verified": result.verified_count,
        "matched": result.matched_count,
        "mismatched": result.mismatched_count,
        "skipped": result.skipped_count,
        "all_matched": result.all_matched,
    }


def _print_summary(result):
    s = _summary_dict(result)
    print(f"  summary: total={s['total']}, verified={s['verified']}, "
          f"matched={s['matched']}, mismatched={s['mismatched']}, "
          f"skipped={s['skipped']}, all_matched={s['all_matched']}")


def _print_all_fields(result):
    """完整打印每个字段：key/label/engine_value/sql_value/diff/status"""
    print(f"  {'KEY':<35} {'LABEL':<22} {'ENGINE':>14} {'SQL':>14} {'DIFF':>12} {'STATUS':<6}")
    print(f"  {'-'*35} {'-'*22} {'-'*14} {'-'*14} {'-'*12} {'-'*6}")
    for f in result.fields:
        eng = f"{float(f.engine_value):.4f}"
        if f.sql_value is not None:
            sql = f"{float(f.sql_value):.4f}"
            diff = f"{float(f.diff):.4f}"
        else:
            sql = "N/A"
            diff = "N/A"
        status = "SKIP" if f.skipped else ("PASS" if f.matched else "FAIL")
        print(f"  {f.key:<35} {(f.label or ''):<22} {eng:>14} {sql:>14} {diff:>12} {status:<6}")
        if f.note:
            print(f"      note: {f.note}")
        if f.skipped and f.skip_reason:
            print(f"      skip_reason: {f.skip_reason}")


def _print_mismatches(result):
    """打印 mismatched 字段明细（key/label/engine_value/sql_value/diff）"""
    ms = result.mismatches()
    if not ms:
        print("  mismatches: (none)")
        return
    print(f"  mismatches ({len(ms)}):")
    for f in ms:
        print(f"    - key={f.key}, label={f.label or ''}")
        print(f"      engine_value={float(f.engine_value):.4f}, "
              f"sql_value={float(f.sql_value):.4f}, "
              f"diff={float(f.diff):.4f}")
        if f.note:
            print(f"      note: {f.note}")


def _run_reconcile(db, snapshot, fields, report_type, source_mode="invoice"):
    """运行一次对账：engine.execute → recon.reconcile"""
    engine = ReportEngine()
    engine_values = engine.execute(fields, snapshot)
    recon = ReportReconciliation(db, snapshot, report_type=report_type)
    result = recon.reconcile(fields, engine_values, source_mode=source_mode)
    return engine_values, result


def main():
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        # ── 1. 定位 Account / Ledger ──
        acc = db.query(models.Account).filter(models.Account.id == ACCOUNT_ID).first()
        if not acc:
            print(f"FAIL: 未找到 account_id={ACCOUNT_ID}")
            return
        ledger = db.query(Ledger).filter(Ledger.id == LEDGER_ID).first()
        if not ledger:
            print(f"FAIL: 未找到 ledger_id={LEDGER_ID}")
            return

        print("=" * 95)
        print(" P2 ReportReconciliation 双路径对账测试")
        print("=" * 95)
        print(f"Account: id={acc.id}, code='{acc.code}', name='{acc.name}'")
        print(f"Ledger:  id={ledger.id}, code='{ledger.code}', name='{ledger.name}'")
        print()

        all_pass = True
        results = {}

        # ── 2. Test 1: BS 对账 @ 2026-06-30 ──
        print("-" * 95)
        print("Test 1: BS 对账 (bs_cutoff=2026-06-30 23:59:59, source_mode=invoice)")
        print("-" * 95)
        sn_bs = LedgerSnapshot(db, ACCOUNT_ID, bs_cutoff=BS_CUTOFF)
        _eng_bs, res_bs = _run_reconcile(
            db, sn_bs, BALANCE_SHEET, "balance_sheet", source_mode="invoice"
        )
        _print_summary(res_bs)
        print()
        _print_all_fields(res_bs)
        print()
        _print_mismatches(res_bs)
        results["BS"] = res_bs
        if not res_bs.all_matched:
            all_pass = False
        print()

        # ── 3. Test 2: IS 半年对账 ──
        print("-" * 95)
        print("Test 2: IS 半年对账 (period 2026-01-01 ~ 2026-06-30, source_mode=invoice)")
        print("-" * 95)
        sn_is = LedgerSnapshot(
            db, ACCOUNT_ID,
            bs_cutoff=BS_CUTOFF,
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 6, 30, 23, 59, 59),
        )
        _eng_is, res_is = _run_reconcile(
            db, sn_is, INCOME_STATEMENT, "income_statement", source_mode="invoice"
        )
        _print_summary(res_is)
        print()
        _print_all_fields(res_is)
        print()
        _print_mismatches(res_is)
        results["IS_6m"] = res_is
        if not res_is.all_matched:
            all_pass = False
        print()

        # ── 4. Test 3: IS 月度对账 (2026-06) ──
        print("-" * 95)
        print("Test 3: IS 月度对账 (period 2026-06-01 ~ 2026-06-30, source_mode=invoice)")
        print("-" * 95)
        sn_is_jun = LedgerSnapshot(
            db, ACCOUNT_ID,
            bs_cutoff=BS_CUTOFF,
            period_start=datetime(2026, 6, 1),
            period_end=datetime(2026, 6, 30, 23, 59, 59),
        )
        _eng_is_jun, res_is_jun = _run_reconcile(
            db, sn_is_jun, INCOME_STATEMENT, "income_statement_jun", source_mode="invoice"
        )
        _print_summary(res_is_jun)
        print()
        _print_all_fields(res_is_jun)
        print()
        _print_mismatches(res_is_jun)
        results["IS_jun"] = res_is_jun
        if not res_is_jun.all_matched:
            all_pass = False
        print()

        # ── 5. 汇总 ──
        print("=" * 95)
        print(" SUMMARY")
        print("=" * 95)
        for name, res in results.items():
            status = "PASS" if res.all_matched else "FAIL"
            s = _summary_dict(res)
            print(f"  {name:<10}: {status}  "
                  f"(total={s['total']}, verified={s['verified']}, "
                  f"matched={s['matched']}, mismatched={s['mismatched']}, "
                  f"skipped={s['skipped']})")
        print()
        overall = "PASS" if all_pass else "FAIL"
        print(f"  OVERALL:   {overall}")
        print("=" * 95)

    finally:
        db.close()
        set_maintenance_mode(False)


if __name__ == "__main__":
    main()
