"""
GOLDEN TEST 001v2 — 全业务闭环，逐行对照《小企业会计准则》

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts, Purchase, Sale, FixedAsset, Expense, CashFlow

_engine, _SessionLocal = make_engine()
H = {"X-Account-ID": "1", "X-Operator": "golden_test"}

# ═══ L1 业务事实（硬编码）═══
BANK_OPEN = Decimal("10000")
VAT_RATE = Decimal("0.13")

QTY_BUY = 10
UNIT_COST = Decimal("100")
QTY_SELL = 5
UNIT_PRICE = Decimal("200")

EXPENSE = Decimal("100")

ASSET_COST = Decimal("2000")
ASSET_MONTHS = 60


class TestGolden001v2:
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
            acc.taxpayer_type_l3 = "general"
            acc.enable_vat_deduction = True
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

    def test_accounting_rules_compliance(self, client):
        c = client; s = {}

        # ── 期初建账 §84 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "准则银行", "account_number": "KJ2201", "balance": 0,
        }, headers=H)
        assert r.status_code == 200; s["bank_id"] = r.json().get("entity", r.json()).get("id")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPEN), "inventory_value": 0,
            "accounts_receivable": 0, "accounts_payable": 0,
            "fixed_assets_original": 0, "accumulated_depreciation": 0,
            "intangible_assets_original": 0, "accumulated_amortization": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPEN), "retained_earnings": 0,
        }, headers=H)
        assert r.status_code == 200

        r = c.post("/api/products", json={
            "name": "准则产品", "sku": "KJ", "category": "原材料", "unit": "件",
            "purchase_price": float(UNIT_COST), "sale_price": float(UNIT_PRICE),
            "min_stock": 0, "track_inventory": True,
        }, headers=H)
        assert r.status_code == 200; s["pid"] = _get_id(r, "product")
        r = c.post("/api/suppliers", json={"name": "准则供应商"}, headers=H)
        s["sup_id"] = _get_id(r, "supplier")
        r = c.post("/api/customers", json={"name": "准则客户"}, headers=H)
        s["cus_id"] = _get_id(r, "customer")

        # 1. 采购入库
        purchase_amount = Decimal(QTY_BUY) * UNIT_COST
        purchase_tax = (purchase_amount * VAT_RATE).quantize(Decimal("0.01"))
        purchase_total = purchase_amount + purchase_tax
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_BUY,
                       "unit_price": float(UNIT_COST), "tax_rate": float(VAT_RATE)}],
            "business_date": "2026-01-05",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["po"] = r.json().get("entity", r.json()).get("entity_id")

        # 2. 采购付款
        r = c.post("/api/payments", json={
            "payment_type": "purchase", "related_entity_type": "purchase_order",
            "related_entity_id": s["po"], "amount": float(purchase_total),
            "payment_date": "2026-01-06", "bank_account_id": s["bank_id"],
        }, headers=H)
        assert r.status_code == 200

        # 3. 销售出库
        sale_amount = Decimal(QTY_SELL) * UNIT_PRICE
        sale_tax = (sale_amount * VAT_RATE).quantize(Decimal("0.01"))
        sale_total = sale_amount + sale_tax
        r = c.post("/api/sales", json={
            "customer_id": s["cus_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_SELL,
                       "unit_price": float(UNIT_PRICE), "tax_rate": float(VAT_RATE)}],
            "business_date": "2026-01-10", "deduct_inventory": True, "has_invoice": True,
        }, headers=H)
        assert r.status_code == 200, r.text
        s["so"] = r.json().get("entity", r.json()).get("entity_id")

        # 4. 收款
        r = c.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order",
            "related_entity_id": s["so"], "amount": float(sale_total),
            "receipt_date": "2026-01-13", "bank_account_id": s["bank_id"],
        }, headers=H)
        assert r.status_code == 200

        # 5. 费用
        r = c.post("/api/expenses", json={
            "category": "办公用品", "functional_category": "管理费用",
            "amount": float(EXPENSE), "expense_date": "2026-01-15",
            "payment_method": "company",
        }, headers=H)
        assert r.status_code == 200, r.text
        ex_id = r.json().get("entity", r.json()).get("entity_id")
        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": ex_id, "amount": float(EXPENSE),
            "payment_date": "2026-01-15", "bank_account_id": s["bank_id"],
        }, headers=H)
        assert r.status_code == 200

        # 6. 固定资产
        r = c.post("/api/fixed-assets", json={
            "asset_code": "KJ-FA01", "name": "准则设备", "category": "机器设备",
            "original_value": float(ASSET_COST), "salvage_rate": 0,
            "useful_life": ASSET_MONTHS, "depreciation_method": "年限平均法",
            "start_date": "2025-12-01",
        }, headers=H)
        assert r.status_code == 200, r.text

        # 7. 月结
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=H)
        assert r.status_code == 200, r.text

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
            purchases=[Purchase(Decimal(QTY_BUY), UNIT_COST, VAT_RATE)],
            sales=[Sale(Decimal(QTY_SELL), UNIT_PRICE, VAT_RATE)],
            fixed_assets=[FixedAsset(ASSET_COST, ASSET_MONTHS)],
            expenses=[Expense(EXPENSE, paid=True)],
            cash_flows=CashFlow(purchase_payment=purchase_total, sale_receipt=sale_total),
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
        assert abs(Decimal(str(bs["inventory"])) - expected.balance_sheet.inventory) <= tol, \
            f"§84存货: 实际{bs['inventory']} != 期望{expected.balance_sheet.inventory}"
        assert abs(Decimal(str(bs["fixed_assets_net"])) - expected.balance_sheet.fixed_assets_net) <= tol, \
            f"§84固定资产净值: 实际{bs['fixed_assets_net']} != 期望{expected.balance_sheet.fixed_assets_net}"
        assert abs(Decimal(str(bs["accounts_payable"])) - expected.balance_sheet.accounts_payable) <= tol, \
            f"§84应付账款: 实际{bs['accounts_payable']} != 期望{expected.balance_sheet.accounts_payable}"
        assert abs(Decimal(str(bs["income_tax_liability"])) - expected.balance_sheet.income_tax_liability) <= tol, \
            f"§84应交所得税: 实际{bs['income_tax_liability']} != 期望{expected.balance_sheet.income_tax_liability}"
        assert abs(Decimal(str(bs["retained_earnings"])) - expected.balance_sheet.retained_earnings) <= tol, \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{expected.balance_sheet.retained_earnings}"

        assert abs(Decimal(str(pl["revenue"])) - expected.income_statement.revenue) <= tol, \
            f"§84营业收入: 实际{pl['revenue']} != 期望{expected.income_statement.revenue}"
        assert abs(Decimal(str(pl["cost_of_goods_sold"])) - expected.income_statement.cost_of_goods_sold) <= tol, \
            f"§84营业成本: 实际{pl['cost_of_goods_sold']} != 期望{expected.income_statement.cost_of_goods_sold}"
        assert abs(Decimal(str(pl["income_tax_expense"])) - expected.income_statement.income_tax) <= tol, \
            f"§84所得税费用: 实际{pl['income_tax_expense']} != 期望{expected.income_statement.income_tax}"
        assert abs(Decimal(str(pl["net_profit"])) - expected.income_statement.net_profit) <= tol, \
            f"§84净利润: 实际{pl['net_profit']} != 期望{expected.income_statement.net_profit}"
