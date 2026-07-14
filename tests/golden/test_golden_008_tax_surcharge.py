"""
GOLDEN TEST 008 — 全税种覆盖：增值税 + 附加税 + 所得税 §3 §6.4 §7.1 §84

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts, Purchase, Sale, FixedAsset, TaxesAndSurcharges, CashFlow

_engine, _SessionLocal = make_engine()
H = {"X-Account-ID": "1", "X-Operator": "user"}

# ═══ L1 业务事实（硬编码）═══
BANK_OPEN = Decimal("10000")
VAT_RATE = Decimal("0.13")

QTY_BUY = 10
UNIT_COST = Decimal("100")
QTY_SELL = 8
UNIT_PRICE = Decimal("500")

FA_ORIG = Decimal("2000")
FA_MONTHS = 60

SURCHARGE_URBAN = Decimal("4.55")
SURCHARGE_EDU = Decimal("1.95")
SURCHARGE_LOCAL_EDU = Decimal("1.30")


class TestGolden008:
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
            acc.surcharge_halved_l3 = True
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

    def test_full_tax_cycle(self, client):
        c = client; s = {}

        # ── 期初建账 §84 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "税金测试银行", "account_number": "62220200008", "balance": 0,
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

        # ── 基础数据 ──
        r = c.post("/api/products", json={
            "name": "税金商品", "sku": "SKU-TAX", "category": "测试",
            "unit": "件", "purchase_price": 100, "sale_price": 500,
            "min_stock": 0, "track_inventory": True,
        }, headers=H)
        assert r.status_code == 200; s["pid"] = _get_id(r, "product")
        r = c.post("/api/suppliers", json={"name": "税金供应商"}, headers=H)
        assert r.status_code == 200; s["sup_id"] = _get_id(r, "supplier")
        r = c.post("/api/customers", json={"name": "税金客户"}, headers=H)
        assert r.status_code == 200; s["cus_id"] = _get_id(r, "customer")

        # Step 1: 采购10件
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_BUY,
                       "unit_price": 100, "tax_rate": float(VAT_RATE)}],
            "business_date": "2026-01-05",
        }, headers=H)
        assert r.status_code == 200, r.text
        s["po"] = r.json().get("entity", r.json()).get("entity_id")

        # Step 2: 录进项发票并认证
        purchase_amount = Decimal(QTY_BUY) * UNIT_COST
        purchase_tax = (purchase_amount * VAT_RATE).quantize(Decimal("0.01"))
        purchase_total = purchase_amount + purchase_tax
        r = c.post("/api/invoices/quick", json={
            "invoice_no": "INV-TAX-IN", "direction": "in", "invoice_type": "special",
            "seller_name": "税金供应商", "buyer_name": "本公司",
            "amount_with_tax": float(purchase_total), "tax_rate": float(VAT_RATE),
            "tax_amount": float(purchase_tax),
            "counterparty_name": "税金供应商", "issue_date": "2026-01-05",
            "related_order_id": s["po"], "related_order_type": "purchase_order",
            "purchase_order_action": "link_existing",
            "items": [{"product_id": s["pid"], "quantity": QTY_BUY,
                       "unit_price": 100, "tax_rate": float(VAT_RATE)}],
        }, headers=H)
        assert r.status_code in (200, 201), f"进项发票创建失败: {r.text}"
        s["inv_in"] = _get_id(r, "invoice")

        r = c.post(f"/api/invoices/{s['inv_in']}/certify",
                   json={"certification_date": "2026-01-05"}, headers=H)
        assert r.status_code == 200, f"发票认证失败: {r.text}"

        # Step 3: 采购付款
        r = c.post("/api/payments", json={
            "payment_type": "purchase", "related_entity_type": "purchase_order",
            "related_entity_id": s["po"], "amount": float(purchase_total),
            "payment_date": "2026-01-06", "bank_account_id": s["bank_id"],
        }, headers=H)
        assert r.status_code == 200

        # Step 4: 销售8件
        r = c.post("/api/sales", json={
            "customer_id": s["cus_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_SELL,
                       "unit_price": 500, "tax_rate": float(VAT_RATE)}],
            "business_date": "2026-01-10", "deduct_inventory": True, "has_invoice": True,
        }, headers=H)
        assert r.status_code == 200, r.text
        s["so"] = r.json().get("entity", r.json()).get("entity_id")

        # Step 5: 录销项发票
        sale_amount = Decimal(QTY_SELL) * UNIT_PRICE
        sale_tax = (sale_amount * VAT_RATE).quantize(Decimal("0.01"))
        sale_total = sale_amount + sale_tax
        r = c.post("/api/invoices/quick", json={
            "invoice_no": "INV-TAX-OUT", "direction": "out", "invoice_type": "special",
            "seller_name": "本公司", "buyer_name": "税金客户",
            "amount_with_tax": float(sale_total), "tax_rate": float(VAT_RATE),
            "tax_amount": float(sale_tax),
            "counterparty_name": "税金客户", "issue_date": "2026-01-10",
            "related_order_id": s["so"], "related_order_type": "sale_order",
            "sale_order_action": "link_existing",
            "items": [{"product_id": s["pid"], "quantity": QTY_SELL,
                       "unit_price": 500, "tax_rate": float(VAT_RATE)}],
        }, headers=H)
        assert r.status_code in (200, 201), f"销项发票创建失败: {r.text}"

        # Step 6: 销售收款
        r = c.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order",
            "related_entity_id": s["so"], "amount": float(sale_total),
            "receipt_date": "2026-01-12", "bank_account_id": s["bank_id"],
        }, headers=H)
        assert r.status_code == 200

        # Step 7: 固定资产入账（价税分离）
        r = c.post("/api/fixed-assets", json={
            "asset_code": "FA-TAX01", "name": "税金设备", "category": "机器设备",
            "original_value": float(FA_ORIG), "salvage_rate": 0,
            "useful_life": FA_MONTHS, "depreciation_method": "年限平均法",
            "start_date": "2025-12-01", "tax_rate": float(VAT_RATE),
        }, headers=H)
        assert r.status_code == 200, r.text

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
            income_tax_rate=Decimal("0.05"),  # 小微企业实际税负（独立从税务局核定单确认）
            purchases=[Purchase(Decimal(QTY_BUY), UNIT_COST, VAT_RATE)],
            sales=[Sale(Decimal(QTY_SELL), UNIT_PRICE, VAT_RATE)],
            fixed_assets=[FixedAsset(FA_ORIG, FA_MONTHS, tax_rate=VAT_RATE)],
            cash_flows=CashFlow(purchase_payment=purchase_total, sale_receipt=sale_total),
            taxes_and_surcharges=TaxesAndSurcharges(SURCHARGE_URBAN, SURCHARGE_EDU, SURCHARGE_LOCAL_EDU),
        ))
        assert expected.interlock_ok, expected.interlock_messages

        # Step 8: VAT 申报
        r = c.post("/api/tax/declare", json={
            "period": "2026-01", "taxpayer_type": "general",
        }, headers=H)
        assert r.status_code == 200, f"VAT申报失败: {r.text}"
        vat_result = r.json().get("data", r.json())
        # VAT 申报应交增值税 = 销项税 - 进项税（含固定资产进项税），与独立引擎一致
        assert abs(Decimal(str(vat_result["vat_payable_l1"])) - expected.balance_sheet.vat_payable_l1) <= Decimal("0.01"), \
            f"VAT申报应交增值税: 实际{vat_result['vat_payable_l1']} != 期望{expected.balance_sheet.vat_payable_l1}"

        # Step 9: 附加税录入
        r = c.post("/api/tax/surcharge-declaration", json={
            "period": "2026-01",
            "urban_construction_tax_l1": float(SURCHARGE_URBAN),
            "education_surcharge_l1": float(SURCHARGE_EDU),
            "local_education_surcharge_l1": float(SURCHARGE_LOCAL_EDU),
            "notes": "税务局核定附加税（六税两费减半）",
        }, headers=H)
        assert r.status_code == 200, f"附加税录入失败: {r.text}"

        # Step 10: 月结
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=H)
        assert r.status_code == 200, f"月结失败: {r.text}"

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
        assert abs(Decimal(str(bs["vat_payable_l1"])) - expected.balance_sheet.vat_payable_l1) <= tol, \
            f"§84应交增值税: 实际{bs['vat_payable_l1']} != 期望{expected.balance_sheet.vat_payable_l1}"
        # VAT 申报结果与月结后报表应交增值税必须一致（月结不应改变 VAT 负债）
        assert abs(Decimal(str(bs["vat_payable_l1"])) - Decimal(str(vat_result["vat_payable_l1"]))) <= tol, \
            f"VAT口径不一致: 申报{vat_result['vat_payable_l1']} != 报表{bs['vat_payable_l1']}"
        assert abs(Decimal(str(bs["surcharge_liability"])) - expected.balance_sheet.tax_surcharge_payable) <= tol, \
            f"§84附加税负债: 实际{bs['surcharge_liability']} != 期望{expected.balance_sheet.tax_surcharge_payable}"
        assert abs(Decimal(str(bs["income_tax_liability"])) - expected.balance_sheet.income_tax_liability) <= tol, \
            f"§84应交所得税: 实际{bs['income_tax_liability']} != 期望{expected.balance_sheet.income_tax_liability}"
        assert abs(Decimal(str(bs["retained_earnings"])) - expected.balance_sheet.retained_earnings) <= tol, \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{expected.balance_sheet.retained_earnings}"

        assert abs(Decimal(str(pl["revenue"])) - expected.income_statement.revenue) <= tol, \
            f"§84营业收入: 实际{pl['revenue']} != 期望{expected.income_statement.revenue}"
        assert abs(Decimal(str(pl["cost_of_goods_sold"])) - expected.income_statement.cost_of_goods_sold) <= tol, \
            f"§84营业成本: 实际{pl['cost_of_goods_sold']} != 期望{expected.income_statement.cost_of_goods_sold}"
        assert abs(Decimal(str(pl["tax_surcharges"])) - expected.income_statement.taxes_and_surcharges) <= tol, \
            f"§84税金及附加: 实际{pl['tax_surcharges']} != 期望{expected.income_statement.taxes_and_surcharges}"
        assert abs(Decimal(str(pl["income_tax_expense"])) - expected.income_statement.income_tax) <= tol, \
            f"§84所得税费用: 实际{pl['income_tax_expense']} != 期望{expected.income_statement.income_tax}"
        assert abs(Decimal(str(pl["net_profit"])) - expected.income_statement.net_profit) <= tol, \
            f"§84净利润: 实际{pl['net_profit']} != 期望{expected.income_statement.net_profit}"
