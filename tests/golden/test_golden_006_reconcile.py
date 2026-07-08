"""
GOLDEN TEST 006 — 银行对账 §6.1 银行流水核销

【准则覆盖】§6.1 银行存款, §48 其他应付款, §7.1 利润, §84 报表
【AS规则】 AS-01 借贷平衡, AS-15 冲红凭证日期一致

==================== 独立会计师完整验算 ====================
  Step 1: 费用 600 (dr 6601, cr 2202)               §6.1
  Step 2: 付款 600 (dr 2202, cr 1002)               §6.1
  Step 3: 对账标记                                   §6.1
  Step 4: 冲红费用 (cr 6601, dr 2202)               §6.1 §48
  Step 5: 月结 → 6601=0, 4103=0                      §7.1 §84

  注: 费用创建时贷方为 2202(应付), 非直接扣银行。
       付款时才扣 1002(银行)。冲红仅冲费用凭证, 不冲付款。
       冲红后 2202 出现借方余额(预付/多付), 1002 仍为 9400。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database
from models import Account, Expense
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from helpers import (
    make_engine, _ledger_balance, _credit_balance, _trace_bal, _get_id,
)

_engine, _SessionLocal = make_engine()
ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}

def _db(): return _SessionLocal()

# ═══ 独立会计师期望值 ═══
BANK_OPENING = Decimal("10000")
EXPENSE_AMOUNT = Decimal("600")    # §6.1 费用金额

# §6.1 费用创建: dr 6601, cr 2202 (不直接扣银行)
# §6.1 付款后: dr 2202, cr 1002 → 银行余额 10000 - 600 = 9400
BANK_ENDING = BANK_OPENING - EXPENSE_AMOUNT

# §7.1 冲红后: 6601=0, 2202 借方余额 600 (多付), 1002=9400
# §7.1 利润: 冲红后无费用 → 利润=0
PROFIT = Decimal("0")           # §7.1: 冲红后无费用
INCOME_TAX = Decimal("0")          # §7.1: 无利润不计提
NET_PROFIT = PROFIT                # 0

# §84 BS (冲红后: 1002=9400, 2202 借方 600 显示为负应付)
TOTAL_ASSETS = BANK_ENDING         # 9400
TOTAL_LIABILITIES = -EXPENSE_AMOUNT  # -600 (2202 借方余额为负负债)
TOTAL_EQUITY = BANK_OPENING + NET_PROFIT  # 10000

# §84 IS (冲红后无费用)
IS_REVENUE = Decimal("0")
IS_MGMT_EXPENSE = Decimal("0")    # §6.1: 冲红后无费用


class TestBankReconcile:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setattr(database, '_engine', _engine)
        monkeypatch.setattr(database, 'SessionLocal', _SessionLocal)
        Base.metadata.create_all(bind=_engine)
        init_db()
        from factories import ensure_default_account
        db = _SessionLocal()
        try:
            ensure_default_account(db)
            acc = db.query(Account).first()
            if acc:
                acc.taxpayer_type_l3 = "general"
                acc.enable_vat_deduction = True
                db.commit()
        finally:
            db.close()
        def _get_db():
            db = _SessionLocal()
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db] = _get_db
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_bank_reconcile_flow(self, client):
        c = client; s = {}

        # ── 期初建账 §84 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": "62220200001", "balance": 0,
        }, headers=HEADERS)
        assert r.status_code == 200; s["bank_id"] = _get_id(r, "bank_account")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPENING), "accounts_receivable": 0,
            "inventory_value": 0, "fixed_assets_original": 0,
            "accumulated_depreciation": 0, "intangible_assets_original": 0,
            "accumulated_amortization": 0, "accounts_payable": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPENING), "retained_earnings": 0,
        }, headers=HEADERS)
        assert r.status_code == 200

        # ═══ Step 1: 费用 600 §6.1 ═══
        r = c.post("/api/expenses", json={
            "category": "办公用品", "functional_category": "管理费用",
            "amount": float(EXPENSE_AMOUNT), "expense_date": "2026-01-10",
            "payment_method": "company",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["expense_id"] = r.json().get("entity", r.json()).get("entity_id")

        db = _db()
        try:
            assert _ledger_balance(db, "6601") == EXPENSE_AMOUNT, \
                f"§6.1 6601余额 != {EXPENSE_AMOUNT}"
            # 费用创建时贷方为 2202(应付), 非直接扣 1002
            ap = _credit_balance(db, "2202")
            assert ap == EXPENSE_AMOUNT, \
                f"§6.1 2202贷方余额 != {EXPENSE_AMOUNT}, 实际{ap}"
        finally: db.close()

        # 付款
        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": s["expense_id"], "amount": float(EXPENSE_AMOUNT),
            "payment_date": "2026-01-10", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        db = _db()
        try:
            # 付款后: 1002 减少, 2202 归零
            assert _ledger_balance(db, "1002") == BANK_ENDING, \
                f"§6.1 付款后1002余额 != {BANK_ENDING}"
            assert _credit_balance(db, "2202") == Decimal("0"), \
                f"§6.1 付款后2202应为0"
        finally: db.close()

        # ═══ Step 2: 银行对账标记 §6.1 ═══
        db = _db()
        try:
            # 查找银行流水
            from models import BankTransaction
            txns = db.query(BankTransaction).filter(
                BankTransaction.bank_account_id == s["bank_id"]
            ).all()
            assert len(txns) >= 1, "§6.1 应有银行流水"

            # 标记对账
            for txn in txns:
                txn.is_reconciled = True
                txn.reconciled_at = "2026-01-11T00:00:00"
            db.commit()
        finally: db.close()

        # ═══ Step 3: 冲红费用 §6.1 §48 ═══
        r = c.post(f"/api/expenses/{s['expense_id']}/reverse", headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            # 冲红后 6601 应归零
            assert _ledger_balance(db, "6601") == Decimal("0"), \
                f"§6.1 冲红后6601应为0, 实际{_ledger_balance(db, '6601')}"
            # 银行余额不变 (付款未被冲红)
            assert _ledger_balance(db, "1002") == BANK_ENDING, \
                f"§6.1 冲红后1002应仍为{BANK_ENDING}, 实际{_ledger_balance(db, '1002')}"
            # 2202 出现借方余额 (多付): _ledger_balance 返回借-贷 = 600
            assert _ledger_balance(db, "2202") == EXPENSE_AMOUNT, \
                f"§6.1 冲红后2202借方余额应为{EXPENSE_AMOUNT}, 实际{_ledger_balance(db, '2202')}"

            # 验证冲红凭证 (检查 6601 的冲红分录)
            _, traces_6601 = _trace_bal(db, "6601")
            rev_traces = [t for t in traces_6601 if t[3] == True]
            assert len(rev_traces) >= 1, "§6.1 缺少 is_reversal 冲红分录"

            # AS-15: 冲红凭证日期一致性
            from rules import enforce_rules
            for t in rev_traces:
                aml = db.query(AccountMoveLine).filter(AccountMoveLine.id == t[0]).first()
                if aml:
                    try:
                        enforce_rules(db, ["AS-15"], {"move_id": aml.move_id})
                    except Exception as e:
                        pytest.fail(f"AS-15 冲红日期校验失败: {e}")
        finally: db.close()

        # ═══ Step 4: 月结 §7.1 §84 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _ledger_balance(db, "6601") == Decimal("0"), "§84 6601月结后归零"
            profit_4103 = _ledger_balance(db, "4103")
            assert profit_4103 == Decimal("0"), \
                f"§7.1 4103余额 {profit_4103} != 0 (冲红后无费用)"
        finally: db.close()

        # ═══ 5. 财务报表验证 §84 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200; bs = r.json()
        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200; pl = r.json()

        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"§84 BS不平衡, diff={diff}"
        assert abs(Decimal(str(bs["monetary_funds"])) - BANK_ENDING) <= Decimal("0.05"), \
            f"§84货币资金: 实际{bs['monetary_funds']} != 期望{BANK_ENDING}"
        assert abs(Decimal(str(bs["total_liabilities"])) - TOTAL_LIABILITIES) <= Decimal("0.05")
        assert abs(Decimal(str(bs["paid_in_capital"])) - BANK_OPENING) <= Decimal("0.05")
        assert abs(Decimal(str(bs["retained_earnings"])) - Decimal("0")) <= Decimal("0.05")
        assert abs(Decimal(str(bs["total_assets"])) - BANK_ENDING) <= Decimal("0.05")
        assert abs(Decimal(str(pl["revenue"])) - IS_REVENUE) <= Decimal("0.05")
        assert abs(Decimal(str(pl["net_profit"])) - Decimal("0")) <= Decimal("0.05")

        # ═══ 6. AS-01 全量不变量 ═══
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        except Exception as e:
            pytest.fail(f"AS-01 校验失败: {e}")
        finally: db.close()

        print("\nALL GOLDEN ASSERTIONS PASSED")
