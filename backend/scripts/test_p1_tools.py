"""P1 校验工具测试脚本 — check_global_balance / check_accounting_equation

验证两条独立 SQL 路径：
1. check_global_balance: 全局借贷平衡 Σ(debit)==Σ(credit)
2. check_accounting_equation: 会计方程式 资产 == 负债 + 权益 + 当期损益净额

用例：
- 全局平衡（空 context，所有凭证）
- 会计方程式 @ 2026-06-30（期末）
- 会计方程式 @ 2025-12-31（早期）
"""
import sys
from pathlib import Path
from datetime import date

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal, set_maintenance_mode
from rules import check_global_balance, check_accounting_equation
import models
from models_finance import Ledger


def _print_violations(violations):
    """打印违规明细"""
    if not violations:
        print("  PASS: 无违规")
        return False
    print(f"  FAIL: 发现 {len(violations)} 条违规")
    for v in violations:
        print(f"  - [{v.rule_id}] {v.rule_name} ({v.severity})")
        print(f"    message: {v.message}")
        if v.fix_hint:
            print(f"    fix_hint: {v.fix_hint}")
        if v.field:
            print(f"    field: {v.field}")
        if v.detail:
            print(f"    detail: {v.detail}")
    return True


def main():
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        # ── 1. 查找 Account / Ledger ──
        acc = db.query(models.Account).filter(
            models.Account.type == "company"
        ).order_by(models.Account.id).first()
        if not acc:
            print("FAIL: 未找到 company 类型的 Account")
            return
        account_id = acc.id

        ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
        if not ledger:
            print(f"FAIL: 未找到与 Account.code='{acc.code}' 匹配的 Ledger")
            return
        ledger_id = ledger.id

        print("=" * 80)
        print(" P1 校验工具测试")
        print("=" * 80)
        print(f"Account: id={account_id}, code='{acc.code}', name='{acc.name}'")
        print(f"Ledger:  id={ledger_id}, code='{ledger.code}', name='{ledger.name}'")
        print()

        all_pass = True

        # ── 2. check_global_balance (空 context → 所有凭证) ──
        print("-" * 80)
        print("Test 1: check_global_balance(context={}) — 全部凭证")
        print("-" * 80)
        violations = check_global_balance(db, {})
        if _print_violations(violations):
            all_pass = False
        print()

        # ── 3. check_accounting_equation @ 2026-06-30 ──
        print("-" * 80)
        print("Test 2: check_accounting_equation(report_date=2026-06-30)")
        print("-" * 80)
        ctx = {"report_date": date(2026, 6, 30), "ledger_id": ledger_id}
        violations = check_accounting_equation(db, ctx)
        if _print_violations(violations):
            all_pass = False
        print()

        # ── 4. check_accounting_equation @ 2025-12-31 ──
        print("-" * 80)
        print("Test 3: check_accounting_equation(report_date=2025-12-31)")
        print("-" * 80)
        ctx = {"report_date": date(2025, 12, 31), "ledger_id": ledger_id}
        violations = check_accounting_equation(db, ctx)
        if _print_violations(violations):
            all_pass = False
        print()

        # ── 5. 汇总 ──
        print("=" * 80)
        if all_pass:
            print(" SUMMARY: PASS — 三项校验全部通过，无违规")
        else:
            print(" SUMMARY: FAIL — 存在违规，详见上方明细")
        print("=" * 80)

    finally:
        db.close()
        set_maintenance_mode(False)


if __name__ == "__main__":
    main()
