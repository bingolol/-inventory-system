"""
GOLDEN TEST 006 — 供应商多付款（费用冲红不冲付款）§48 应付账款

场景：已付款费用被冲红（仅冲费用，不冲付款），
净效果是企业对供应商享有债权（银行存款已付，费用不再确认），
预付账款（资产）增加。

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。

L1/L2 职责分离说明：
- L1 输入用系统 API 必填字段（functional_category/payment_method 等），
  这些是系统内部概念，不影响独立计算；
- L2 独立引擎只用 amount 和 paid 两个事实做独立计算，不依赖系统内部字段；
- 独立会计师从原始凭证能确认的事实：费用 600 元已通过银行付款，后费用被冲红。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts, SupplierOverpayment

_engine, _SessionLocal = make_engine()
H = {"X-Account-ID": "1", "X-Operator": "golden_test"}

# ═══ L1 业务事实（硬编码）═══
BANK_OPEN = Decimal("10000")
EXPENSE_AMOUNT = Decimal("600")


class TestGolden006SupplierOverpayment:
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

    def test_supplier_overpayment_flow(self, client):
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

        # Step 1: 费用 600 挂账并付款
        r = c.post("/api/expenses", json={
            "category": "办公用品", "functional_category": "管理费用",
            "amount": float(EXPENSE_AMOUNT), "expense_date": "2026-01-10",
            "payment_method": "company",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["expense_id"] = r.json().get("entity", r.json()).get("entity_id")

        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": s["expense_id"], "amount": float(EXPENSE_AMOUNT),
            "payment_date": "2026-01-10", "bank_account_id": s["bank_id"],
        }, headers=H)
        assert r.status_code == 200

        # Step 2: 冲红费用
        r = c.post(f"/api/expenses/{s['expense_id']}/reverse", headers=H)
        assert r.status_code == 200, r.text

        # Step 3: 月结
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=H)
        assert r.status_code == 200, r.text

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
            income_tax_rate=Decimal("0.05"),  # 小微企业实际税负（独立从税务局核定单确认）
            # SupplierOverpayment 场景：银行存款已付，费用不确认，预付账款（资产）增加
            supplier_overpayments=[SupplierOverpayment(EXPENSE_AMOUNT)],
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
        # 预付账款（对供应商债权）应为 EXPENSE_AMOUNT=600，accounts_payable 应为 0
        assert abs(Decimal(str(bs["prepayments"])) - expected.balance_sheet.prepayments) <= tol, \
            f"§84预付账款: 实际{bs['prepayments']} != 期望{expected.balance_sheet.prepayments}"
        assert abs(Decimal(str(bs["accounts_payable"])) - expected.balance_sheet.accounts_payable) <= tol, \
            f"§84应付账款: 实际{bs['accounts_payable']} != 期望{expected.balance_sheet.accounts_payable}"
        assert abs(Decimal(str(bs["retained_earnings"])) - expected.balance_sheet.retained_earnings) <= tol, \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{expected.balance_sheet.retained_earnings}"

        assert abs(Decimal(str(pl["revenue"])) - expected.income_statement.revenue) <= tol, \
            f"§84营业收入: 实际{pl['revenue']} != 期望{expected.income_statement.revenue}"
        assert abs(Decimal(str(pl["net_profit"])) - expected.income_statement.net_profit) <= tol, \
            f"§84净利润: 实际{pl['net_profit']} != 期望{expected.income_statement.net_profit}"
