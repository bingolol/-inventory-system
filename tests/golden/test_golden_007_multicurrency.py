"""
GOLDEN TEST 007 — 多币种（仅验证多币种创建不崩溃）

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts

_engine, _SessionLocal = make_engine()
H = {"X-Account-ID": "1", "X-Operator": "golden_test"}

# ═══ L1 业务事实（硬编码）═══
BANK_OPEN = Decimal("10000")


class TestGolden007MultiCurrency:
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
            acc = db.query(models.Account).first()
            acc.taxpayer_type_l3 = "general"; acc.enable_vat_deduction = True
            db.commit()
        finally: db.close()
        def _g():
            db = _SessionLocal()
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db] = _g
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_multi_currency(self, client):
        pytest.skip("多币种业务暂时不涵盖，避免假绿灯（原测试用 if r.status_code==200 吞失败且独立引擎未覆盖多币种费用）")

        # ── 期初建账 §84 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": "62220200001", "balance": 0,
        }, headers=H)
        assert r.status_code == 200; s["bank_id"] = _get_id(r, "bank_account")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPEN), "accounts_receivable": 0,
            "inventory_value": 0, "fixed_assets_original": 0,
            "accumulated_depreciation": 0, "intangible_assets_original": 0,
            "accumulated_amortization": 0, "accounts_payable": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPEN), "retained_earnings": 0,
        }, headers=H)
        assert r.status_code == 200

        # Step 1: 创建外币银行账户
        r = c.post("/api/bank-accounts", json={
            "bank_name": "美元账户", "account_number": "62220200002",
            "balance": 0, "currency": "USD",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["usd_bank_id"] = _get_id(r, "bank_account")

        # Step 2: 创建多币种费用（验证不崩溃）
        r = c.post("/api/expenses", json={
            "category": "国际运费", "functional_category": "管理费用",
            "amount": 100.0, "expense_date": "2026-01-10",
            "payment_method": "company", "currency": "USD",
        }, headers=H)
        if r.status_code == 200:
            s["expense_id"] = r.json().get("entity", r.json()).get("entity_id")

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
        ))
        assert expected.interlock_ok, expected.interlock_messages

        # ═══ L3 报表 API 验证 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=H)
        assert r.status_code == 200; bs = r.json()

        tol = Decimal("0.05")
        assert abs(Decimal(str(bs["total_assets"])) - expected.balance_sheet.total_assets) <= tol, \
            f"§84资产总计: 实际{bs['total_assets']} != 期望{expected.balance_sheet.total_assets}"
        assert abs(Decimal(str(bs["total_liabilities"])) - expected.balance_sheet.total_liabilities) <= tol, \
            f"§84负债合计: 实际{bs['total_liabilities']} != 期望{expected.balance_sheet.total_liabilities}"
        assert abs(Decimal(str(bs["total_equity"])) - expected.balance_sheet.total_equity) <= tol, \
            f"§84权益合计: 实际{bs['total_equity']} != 期望{expected.balance_sheet.total_equity}"
