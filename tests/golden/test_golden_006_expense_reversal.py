"""
GOLDEN TEST 006 — 费用冲红 + 多科目费用独立验算

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts, Expense

_engine, _SessionLocal = make_engine()
H = {"X-Account-ID": "1", "X-Operator": "golden_test"}

# ═══ L1 业务事实（硬编码）═══
BANK_OPEN = Decimal("10000")
EXPENSE_MGMT = Decimal("100")
EXPENSE_SELL = Decimal("200")
EXPENSE_FIN = Decimal("50")


class TestGolden006:
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

    def test_expense_reversal_flow(self, client):
        c = client; s = {}

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

        # Step 1: 管理费用 100 挂账并付款
        r = c.post("/api/expenses", json={
            "amount": float(EXPENSE_MGMT), "category": "办公用品",
            "functional_category": "管理费用", "expense_date": "2026-01-10",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["expense_mgmt_id"] = _get_id(r, "expense_mgmt")

        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": s["expense_mgmt_id"], "bank_account_id": s["bank_id"],
            "amount": float(EXPENSE_MGMT), "payment_date": "2026-01-10",
        }, headers=H)
        assert r.status_code == 200, r.text

        # Step 2: 销售费用 200 挂账并付款
        r = c.post("/api/expenses", json={
            "amount": float(EXPENSE_SELL), "category": "运费",
            "functional_category": "销售费用", "expense_date": "2026-01-12",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["expense_sell_id"] = _get_id(r, "expense_sell")

        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": s["expense_sell_id"], "bank_account_id": s["bank_id"],
            "amount": float(EXPENSE_SELL), "payment_date": "2026-01-12",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["payment_sell_id"] = _get_id(r, "payment_sell")

        # Step 3: 冲红销售费用及付款
        r = c.post(f"/api/expenses/{s['expense_sell_id']}/reverse", headers=H)
        assert r.status_code == 200, r.text
        r = c.post(f"/api/payments/{s['payment_sell_id']}/reverse", headers=H)
        assert r.status_code == 200, r.text

        # Step 4: 财务费用 50 挂账并付款
        r = c.post("/api/expenses", json={
            "amount": float(EXPENSE_FIN), "category": "其他",
            "functional_category": "财务费用", "expense_date": "2026-01-15",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["expense_fin_id"] = _get_id(r, "expense_fin")

        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": s["expense_fin_id"], "bank_account_id": s["bank_id"],
            "amount": float(EXPENSE_FIN), "payment_date": "2026-01-15",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["payment_fin_id"] = _get_id(r, "payment_fin")

        # Step 5: 冲红财务费用及付款
        r = c.post(f"/api/expenses/{s['expense_fin_id']}/reverse", headers=H)
        assert r.status_code == 200, r.text
        r = c.post(f"/api/payments/{s['payment_fin_id']}/reverse", headers=H)
        assert r.status_code == 200, r.text

        # Step 6: 月结
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=H)
        assert r.status_code == 200, r.text

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
            expenses=[Expense(EXPENSE_MGMT, paid=True)],
        ))
        assert expected.interlock_ok, expected.interlock_messages

        # ═══ L3 报表 API 验证 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=H)
        assert r.status_code == 200; bs = r.json()
        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=H)
        assert r.status_code == 200; pl = r.json()

        tol = Decimal("0.05")
        assert abs(Decimal(str(bs["total_assets"])) - expected.balance_sheet.total_assets) <= tol, \
            f"§84资产总计: 实际{bs['total_assets']} != 期望{expected.balance_sheet.total_assets}"
        assert abs(Decimal(str(bs["total_liabilities"])) - expected.balance_sheet.total_liabilities) <= tol, \
            f"§84负债合计: 实际{bs['total_liabilities']} != 期望{expected.balance_sheet.total_liabilities}"
        assert abs(Decimal(str(bs["total_equity"])) - expected.balance_sheet.total_equity) <= tol, \
            f"§84权益合计: 实际{bs['total_equity']} != 期望{expected.balance_sheet.total_equity}"
        assert abs(Decimal(str(bs["monetary_funds"])) - expected.balance_sheet.monetary_funds) <= tol, \
            f"§84货币资金: 实际{bs['monetary_funds']} != 期望{expected.balance_sheet.monetary_funds}"
        assert abs(Decimal(str(bs["retained_earnings"])) - expected.balance_sheet.retained_earnings) <= tol, \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{expected.balance_sheet.retained_earnings}"

        assert abs(Decimal(str(pl["revenue"])) - expected.income_statement.revenue) <= tol, \
            f"§84营业收入: 实际{pl['revenue']} != 期望{expected.income_statement.revenue}"
        assert abs(Decimal(str(pl["net_profit"])) - expected.income_statement.net_profit) <= tol, \
            f"§84净利润: 实际{pl['net_profit']} != 期望{expected.income_statement.net_profit}"
