"""提交 VAT 声明 + 附加税声明 + 三层校验 + 三大报表（v2 直接写文件）"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, date, timedelta
from decimal import Decimal

from database import SessionLocal, set_maintenance_mode
import models
from models_finance import Ledger, AccountMove
from uow import unit_of_work
from commands.base import dispatch
from commands.tax_declaration_commands import DeclareVAT, DeclareSurcharge

ACCOUNT_ID = 1

# Debug log file
DEBUG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "debug_validate.txt")
_debug_lines = []

def dprint(msg):
    print(msg, flush=True)
    _debug_lines.append(msg)

SURCHARGE_DATA = [
    ("2025-Q4", "small_scale", Decimal("0.69"), Decimal("0"), Decimal("0")),
    ("2026-Q1", "small_scale", Decimal("2.50"), Decimal("0"), Decimal("0")),
    ("2026-Q2", "small_scale", Decimal("1.46"), Decimal("0"), Decimal("0")),
    ("2026-06", "general",     Decimal("43.26"), Decimal("0"), Decimal("0")),
]


def submit_declarations():
    dprint("=" * 80)
    dprint("  提交 VAT 声明 + 附加税声明")
    dprint("=" * 80)
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        for period, taxpayer_type, urban, edu, local_edu in SURCHARGE_DATA:
            dprint(f"\n--- {period} ({taxpayer_type}) ---")
            try:
                with unit_of_work(db):
                    result = dispatch(DeclareVAT(
                        account_id=ACCOUNT_ID,
                        operator="sim",
                        period=period,
                        taxpayer_type=taxpayer_type,
                    ), db)
                dprint(f"  VAT: vat_payable={result.get('vat_payable', 0):.2f}")
            except Exception as e:
                dprint(f"  VAT: skip ({e})")

            try:
                with unit_of_work(db):
                    result = dispatch(DeclareSurcharge(
                        account_id=ACCOUNT_ID,
                        operator="sim",
                        period=period,
                        urban_construction_tax=urban,
                        education_surcharge=edu,
                        local_education_surcharge=local_edu,
                    ), db)
                dprint(f"  Surcharge: total={result.get('total', 0):.2f}, posted={result.get('posted')}")
                cascade = result.get("cascade", {})
                if cascade:
                    dprint(f"  Cascade: rerun={cascade.get('period_close_rerun')}, "
                          f"tax_adj={cascade.get('income_tax_adjusted', 0):.2f}")
            except Exception as e:
                dprint(f"  Surcharge: skip ({e})")
                import traceback
                dprint(traceback.format_exc())

        db.commit()
        dprint("\n[Done] All declarations submitted")
    finally:
        db.close()
        set_maintenance_mode(False)


def run_validation():
    dprint("\n" + "=" * 80)
    dprint("  三层架构验证 (P3 + P1 + P2)")
    dprint("=" * 80)
    db = SessionLocal()
    try:
        acc = db.query(models.Account).filter(models.Account.id == ACCOUNT_ID).first()
        ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
        ledger_id = ledger.id

        from rules import check_journal_rule, check_global_balance, check_accounting_equation
        moves = db.query(AccountMove).filter(AccountMove.state == "posted").all()
        v3 = 0
        for m in moves:
            v3 += len(check_journal_rule(db, m.id))
        dprint(f"[P3] JournalRule: {len(moves)} moves, {v3} violations")

        v1 = check_global_balance(db, {})
        dprint(f"[P1] Global balance: {len(v1)} violations")

        v2 = check_accounting_equation(db, {"report_date": date(2026, 6, 30), "ledger_id": ledger_id})
        dprint(f"[P1] Equation 2026-06-30: {len(v2)} violations")

        v2b = check_accounting_equation(db, {"report_date": date(2025, 12, 31), "ledger_id": ledger_id})
        dprint(f"[P1] Equation 2025-12-31: {len(v2b)} violations")

        from crud.finance._snapshot import LedgerSnapshot
        from reports.engine import ReportEngine
        from reports.reconcile import ReportReconciliation
        from reports.definitions.balance_sheet import BALANCE_SHEET
        from reports.definitions.income_statement import INCOME_STATEMENT

        qd = datetime(2026, 6, 30) + timedelta(days=1) - timedelta(seconds=1)
        sn = LedgerSnapshot(db, ACCOUNT_ID, bs_cutoff=qd)
        engine = ReportEngine()
        result = engine.execute(BALANCE_SHEET, sn, source_mode="invoice")
        recon_values = {k: v for k, v in result.items()
                        if not k.startswith("_") and isinstance(v, (int, float))}
        recon = ReportReconciliation(db, sn, report_type="balance_sheet")
        r = recon.reconcile(BALANCE_SHEET, recon_values, source_mode="invoice")
        bs_s = r.to_dict()["summary"]
        dprint(f"[P2] BS: total={bs_s['total']} matched={bs_s['matched']} mismatched={bs_s['mismatched']}")

        sd = datetime(2026, 1, 1)
        ed = datetime(2026, 6, 30) + timedelta(days=1) - timedelta(seconds=1)
        sn2 = LedgerSnapshot(db, ACCOUNT_ID, bs_cutoff=ed, period_start=sd, period_end=ed)
        result2 = engine.execute(INCOME_STATEMENT, sn2)
        recon_values2 = {k: v for k, v in result2.items()
                         if not k.startswith("_") and isinstance(v, (int, float))}
        recon2 = ReportReconciliation(db, sn2, report_type="income_statement")
        r2 = recon2.reconcile(INCOME_STATEMENT, recon_values2)
        is_s = r2.to_dict()["summary"]
        dprint(f"[P2] IS: total={is_s['total']} matched={is_s['matched']} mismatched={is_s['mismatched']}")

        all_pass = (v3 == 0 and len(v1) == 0 and len(v2) == 0 and len(v2b) == 0
                    and bs_s["mismatched"] == 0 and is_s["mismatched"] == 0)
        dprint(f"\n{'PASS' if all_pass else 'FAIL'}")

    finally:
        db.close()

    # BS check
    db = SessionLocal()
    try:
        from crud.finance import generate_balance_sheet, generate_income_statement
        from crud.finance._ledger_helpers import _bal

        bs = generate_balance_sheet(db, ACCOUNT_ID, "2026-06-30")
        ta = Decimal(str(bs.get("total_assets", 0)))
        tle = Decimal(str(bs.get("total_liabilities_and_equity", 0)))
        diff = ta - tle
        dprint(f"\n[BS] assets={ta:.2f} le={tle:.2f} diff={diff:.2f} balanced={abs(diff)<Decimal('0.01')}")

        is_data = generate_income_statement(db, ACCOUNT_ID, "2026-01-01", "2026-06-30")
        np = Decimal(str(is_data.get("net_profit", 0)))
        dprint(f"[IS] revenue={is_data.get('revenue')} cogs={is_data.get('cost_of_goods_sold')} "
              f"surcharge={is_data.get('tax_surcharges')} net_profit={np:.2f}")

        acc = db.query(models.Account).filter(models.Account.id == ACCOUNT_ID).first()
        ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
        re_end = (Decimal(str(_bal(db, ledger, "4104", datetime(2026, 6, 30, 23, 59, 59))))
                  + Decimal(str(_bal(db, ledger, "4103", datetime(2026, 6, 30, 23, 59, 59)))))
        re_begin = Decimal(str(_bal(db, ledger, "4104", datetime(2025, 12, 31, 23, 59, 59))))
        dprint(f"[Cross] re_end={re_end:.2f} re_begin={re_begin:.2f} delta={re_end-re_begin:.2f} np={np:.2f} match={abs(re_end-re_begin-np)<Decimal('0.01')}")
    finally:
        db.close()


def main():
    dprint(f"DEBUG_FILE={DEBUG_FILE}")
    dprint(f"Python {sys.version}")
    submit_declarations()
    run_validation()
    # Write debug log
    with open(DEBUG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(_debug_lines))
    dprint(f"\nDebug log written to {DEBUG_FILE}")


if __name__ == "__main__":
    main()
