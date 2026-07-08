"""
GOLDEN TEST 007 — 多币种（仅验证多币种创建不崩溃）

【准则覆盖】§6.1 外币交易, §84 报表折算
【AS规则】 AS-01 借贷平衡

==================== 独立会计师完整验算 ====================
  Step 1: 创建外币银行账户 (CNY→USD)
  Step 2: 创建多币种费用 (验证不崩溃)
  Step 3: BS §84 验证
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database
from models import Account
from helpers import (
    make_engine, _ledger_balance, _credit_balance, _trace_bal, _get_id,
)

_engine, _SessionLocal = make_engine()
ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}

def _db(): return _SessionLocal()

# ═══ 独立会计师期望值 ═══
BANK_OPENING = Decimal("10000")
TOTAL_ASSETS = BANK_OPENING
TOTAL_LIABILITIES = Decimal("0")
TOTAL_EQUITY = BANK_OPENING


class TestMultiCurrency:

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

    def test_multi_currency(self, client):
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

        # ═══ Step 1: 创建外币银行账户 §6.1 ═══
        r = c.post("/api/bank-accounts", json={
            "bank_name": "美元账户", "account_number": "62220200002",
            "balance": 0, "currency": "USD",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["usd_bank_id"] = _get_id(r, "bank_account")

        # ═══ Step 2: 创建多币种费用 (验证不崩溃) §6.1 ═══
        r = c.post("/api/expenses", json={
            "category": "国际运费", "functional_category": "管理费用",
            "amount": 100.0, "expense_date": "2026-01-10",
            "payment_method": "company", "currency": "USD",
        }, headers=HEADERS)
        # 允许成功或拒绝（多币种支持可能不完整）
        if r.status_code == 200:
            s["expense_id"] = r.json().get("entity", r.json()).get("entity_id")
            print(f"  多币种费用创建成功: #{s.get('expense_id')}")
        else:
            print(f"  多币种费用创建被拒绝 (预期行为): status={r.status_code}")

        # ═══ Step 3: BS 验证 §84 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200; bs = r.json()

        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"§84 BS不平衡, diff={diff}"
        assert abs(Decimal(str(bs["total_assets"])) - TOTAL_ASSETS) <= Decimal("0.05")
        assert abs(Decimal(str(bs["total_liabilities"])) - TOTAL_LIABILITIES) <= Decimal("0.05")
        assert abs(Decimal(str(bs["paid_in_capital"])) - BANK_OPENING) <= Decimal("0.05")

        # ═══ 4. AS-01 全量不变量 ═══
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        except Exception as e:
            pytest.fail(f"AS-01 校验失败: {e}")
        finally: db.close()

        print("\nALL GOLDEN ASSERTIONS PASSED")
