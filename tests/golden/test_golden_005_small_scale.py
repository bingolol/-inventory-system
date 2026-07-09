"""
GOLDEN TEST 005 — 小规模纳税人买卖 §1.3 存货 §5.1 销售 §7.1 成本 §84 报表

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts, Purchase, Sale, CashFlow

_engine, _SessionLocal = make_engine()
ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}


class TestSmallScaleTrade:

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
            if acc:
                acc.taxpayer_type_l3 = "small_scale"    # §1.3: 小规模纳税人
                acc.enable_vat_deduction = False         # §1.3: 不可抵扣
                db.commit()
        finally:
            db.close()
        def _get_db():
            db = _SessionLocal()
            try:
                yield db
            finally:
                db.close()
        app.dependency_overrides[get_db] = _get_db
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_small_scale_buy_sell(self, client):
        c = client
        s = {}

        # ═══ L1 业务事实 ═══
        # 独立假设：小规模纳税人销售货物按 3% 征收率，但系统 enable_vat_deduction=False 时不价税分离
        BANK_OPEN = Decimal("10000")
        QTY = Decimal("10")
        UC = Decimal("100")
        SQTY = Decimal("5")
        UP = Decimal("200")

        # ── 期初建账 §84 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": "62220200001", "balance": 0,
        }, headers=HEADERS)
        assert r.status_code == 200
        s["bank_id"] = _get_id(r, "bank_account")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPEN), "accounts_receivable": 0,
            "inventory_value": 0, "fixed_assets_original": 0,
            "accumulated_depreciation": 0, "intangible_assets_original": 0,
            "accumulated_amortization": 0, "accounts_payable": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPEN), "retained_earnings": 0,
        }, headers=HEADERS)
        assert r.status_code == 200

        # ── 基础数据 ──
        r = c.post("/api/products", json={
            "name": "商品A", "sku": "SKU-A", "category": "测试",
            "unit": "件", "purchase_price": 100, "sale_price": 200,
            "min_stock": 0, "track_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200
        s["product_id"] = _get_id(r, "product")

        r = c.post("/api/suppliers", json={"name": "供应商A"}, headers=HEADERS)
        assert r.status_code == 200
        s["supplier_id"] = _get_id(r, "supplier")

        r = c.post("/api/customers", json={"name": "客户A"}, headers=HEADERS)
        assert r.status_code == 200
        s["customer_id"] = _get_id(r, "customer")

        # ═══ Step 1: 采购10件 §1.3 ═══
        r = c.post("/api/purchases", json={
            "supplier_id": s["supplier_id"],
            "items": [{"product_id": s["product_id"], "quantity": int(QTY),
                       "unit_price": float(UC), "tax_rate": 0}],
            "business_date": "2026-01-05",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["purchase_id"] = r.json().get("entity", r.json()).get("entity_id")

        # 付款
        r = c.post("/api/payments", json={
            "payment_type": "purchase", "related_entity_type": "purchase_order",
            "related_entity_id": s["purchase_id"], "amount": float(QTY * UC),
            "payment_date": "2026-01-06", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        # ═══ Step 2: 销售5件 §5.1 §7.1 ═══
        r = c.post("/api/sales", json={
            "customer_id": s["customer_id"],
            "items": [{"product_id": s["product_id"], "quantity": int(SQTY),
                       "unit_price": float(UP), "tax_rate": 0}],
            "business_date": "2026-01-10", "deduct_inventory": True,
            "has_invoice": True,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["sale_id"] = r.json().get("entity", r.json()).get("entity_id")

        # 收款
        r = c.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order",
            "related_entity_id": s["sale_id"], "amount": float(SQTY * UP),
            "receipt_date": "2026-01-12", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        # ═══ Step 3: 月结 §7.1 §84 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
            enable_vat_deduction=False,
            purchases=[Purchase(QTY, UC, Decimal("0"))],
            sales=[Sale(SQTY, UP, Decimal("0"))],
            cash_flows=CashFlow(purchase_payment=QTY * UC, sale_receipt=SQTY * UP),
        ))
        assert expected.interlock_ok, expected.interlock_messages

        # ═══ L3 报表 API 验证 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200
        bs = r.json()

        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200
        pl = r.json()

        tol = Decimal("0.05")
        assert abs(Decimal(str(bs["total_assets"])) - expected.balance_sheet.total_assets) <= tol, \
            f"§84资产总计: 实际{bs['total_assets']} != 期望{expected.balance_sheet.total_assets}"
        assert abs(Decimal(str(bs["total_liabilities"])) - expected.balance_sheet.total_liabilities) <= tol, \
            f"§84负债合计: 实际{bs['total_liabilities']} != 期望{expected.balance_sheet.total_liabilities}"
        assert abs(Decimal(str(bs["total_equity"])) - expected.balance_sheet.total_equity) <= tol, \
            f"§84权益合计: 实际{bs['total_equity']} != 期望{expected.balance_sheet.total_equity}"
        assert abs(Decimal(str(bs["monetary_funds"])) - expected.balance_sheet.monetary_funds) <= tol, \
            f"§84货币资金: 实际{bs['monetary_funds']} != 期望{expected.balance_sheet.monetary_funds}"
        assert abs(Decimal(str(bs["inventory"])) - expected.balance_sheet.inventory) <= tol, \
            f"§84存货: 实际{bs['inventory']} != 期望{expected.balance_sheet.inventory}"
        assert abs(Decimal(str(bs["income_tax_liability"])) - expected.balance_sheet.income_tax_liability) <= tol, \
            f"§84应交所得税: 实际{bs['income_tax_liability']} != 期望{expected.balance_sheet.income_tax_liability}"
        assert abs(Decimal(str(bs["retained_earnings"])) - expected.balance_sheet.retained_earnings) <= tol, \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{expected.balance_sheet.retained_earnings}"

        assert abs(Decimal(str(pl["revenue"])) - expected.income_statement.revenue) <= tol, \
            f"§5.1营业收入: 实际{pl['revenue']} != 期望{expected.income_statement.revenue}"
        assert abs(Decimal(str(pl["cost_of_goods_sold"])) - expected.income_statement.cost_of_goods_sold) <= tol, \
            f"§7.1营业成本: 实际{pl['cost_of_goods_sold']} != 期望{expected.income_statement.cost_of_goods_sold}"
        assert abs(Decimal(str(pl["net_profit"])) - expected.income_statement.net_profit) <= tol, \
            f"§7.1净利润: 实际{pl['net_profit']} != 期望{expected.income_statement.net_profit}"
