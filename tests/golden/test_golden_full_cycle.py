"""
GOLDEN TEST FULL_CYCLE — 完整业务周期 §1.3 存货 §5.1 销售 §7.1 成本 §31 折旧 §84 报表

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import (
    calculate, Facts, Purchase, Sale, Return, FixedAsset, CashFlow,
    Expense, EmployeeFundedExpense,
)

_engine, _SessionLocal = make_engine()
ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}


class TestFullCycle:

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
                acc.taxpayer_type_l3 = "general"
                acc.enable_vat_deduction = True
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

    def test_full_cycle(self, client):
        c = client
        s = {}

        # ═══ L1 业务事实 ═══
        # 独立假设：一般纳税人销售货物增值税率 13%，小微企业所得税实际税负 5%
        VAT_RATE = Decimal("0.13")
        BANK_OPEN = Decimal("10000")
        QTY = Decimal("10")
        UC = Decimal("100")
        SQTY = Decimal("3")
        UP = Decimal("200")
        RET_SQTY = Decimal("1")
        RET_PQTY = Decimal("1")
        FA_ORIG = Decimal("5000")
        FA_MONTHS = 60

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
                       "unit_price": float(UC), "tax_rate": float(VAT_RATE)}],
            "business_date": "2026-01-05",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["purchase_id"] = r.json().get("entity", r.json()).get("entity_id")

        # ═══ Step 2: 录进项发票 AS-02 ═══
        purchase_amount = (QTY * UC).quantize(Decimal("0.01"))
        purchase_tax = (purchase_amount * VAT_RATE).quantize(Decimal("0.01"))
        purchase_total = purchase_amount + purchase_tax
        r = c.post("/api/invoices/quick", json={
            "invoice_no": "INV-FC-IN", "direction": "in", "invoice_type": "special",
            "seller_name": "供应商A", "buyer_name": "本公司",
            "amount_without_tax": float(purchase_amount), "tax_rate": float(VAT_RATE),
            "tax_amount": float(purchase_tax), "amount_with_tax": float(purchase_total),
            "counterparty_name": "供应商A", "issue_date": "2026-01-05",
            "related_order_id": s["purchase_id"], "related_order_type": "purchase_order",
            "certification_status": "certified", "purchase_order_action": "link_existing",
            "items": [{"product_id": s["product_id"], "quantity": int(QTY),
                       "unit_price": float(UC), "tax_rate": float(VAT_RATE)}],
        }, headers=HEADERS)
        assert r.status_code in (200, 201), f"Invoice fail: {r.text}"

        # ═══ Step 3: 销售3件 §5.1 §7.1 ═══
        r = c.post("/api/sales", json={
            "customer_id": s["customer_id"],
            "has_invoice": True,
            "items": [{"product_id": s["product_id"], "quantity": int(SQTY),
                       "unit_price": float(UP), "tax_rate": float(VAT_RATE)}],
            "business_date": "2026-01-10", "deduct_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["sale_id"] = r.json().get("entity", r.json()).get("entity_id")

        # ═══ Step 4: 销售退货1件 §5.1 §7.1 ═══
        r = c.post(f"/api/sales/{s['sale_id']}/return", json={
            "return_date": "2026-01-12", "reason": "质量",
            "items": [{"product_id": s["product_id"], "quantity": int(RET_SQTY)}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        # ═══ Step 5: 采购退货1件 §1.3 ═══
        r = c.post(f"/api/purchases/{s['purchase_id']}/return", json={
            "return_date": "2026-01-13", "reason": "质量",
            "items": [{"product_id": s["product_id"], "quantity": int(RET_PQTY)}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        # ═══ 付款 & 收款 ═══
        net_purchase_pay = ((QTY - RET_PQTY) * UC * (Decimal("1") + VAT_RATE)).quantize(Decimal("0.01"))
        net_sale_receive = ((SQTY - RET_SQTY) * UP * (Decimal("1") + VAT_RATE)).quantize(Decimal("0.01"))

        r = c.post("/api/payments", json={
            "payment_type": "purchase", "related_entity_type": "purchase_order",
            "related_entity_id": s["purchase_id"], "amount": float(net_purchase_pay),
            "payment_date": "2026-01-14", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        r = c.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order",
            "related_entity_id": s["sale_id"], "amount": float(net_sale_receive),
            "receipt_date": "2026-01-15", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        # ═══ Step 6: 固定资产 §31 ═══
        r = c.post("/api/fixed-assets", json={
            "asset_code": "FA001", "name": "设备", "category": "机器",
            "original_value": float(FA_ORIG), "salvage_rate": 0,
            "useful_life": FA_MONTHS, "depreciation_method": "年限平均法",
            "start_date": "2025-12-01",
        }, headers=HEADERS)
        assert r.status_code == 200
        s["fa_id"] = _get_id(r, "fixed_asset")

        # ═══ Step 7: 房租 500 挂账 → 付款 → 红冲付款 §6.1 §48 ═══
        RENT = Decimal("500")
        r = c.post("/api/expenses", json={
            "amount": float(RENT),
            "category": "房租",
            "functional_category": "管理费用",
            "expense_date": "2026-01-16",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["expense_rent_id"] = _get_id(r, "expense_rent")

        r = c.post("/api/payments", json={
            "payment_type": "expense",
            "related_entity_type": "expense",
            "related_entity_id": s["expense_rent_id"],
            "bank_account_id": s["bank_id"],
            "amount": float(RENT),
            "payment_date": "2026-01-16",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["payment_rent_id"] = _get_id(r, "payment_rent")

        # 红冲付款：净效果为房租费用仍挂账 500，银行恢复
        r = c.post(f"/api/payments/{s['payment_rent_id']}/reverse", headers=HEADERS)
        assert r.status_code == 200, r.text

        # ═══ Step 8: 水电费 300 挂账并现金支付 §6.1 ═══
        UTILITIES = Decimal("300")
        r = c.post("/api/expenses", json={
            "amount": float(UTILITIES),
            "category": "水电",
            "functional_category": "管理费用",
            "expense_date": "2026-01-17",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["expense_utilities_id"] = _get_id(r, "expense_utilities")

        r = c.post("/api/payments", json={
            "payment_type": "expense",
            "related_entity_type": "expense",
            "related_entity_id": s["expense_utilities_id"],
            "bank_account_id": s["bank_id"],
            "amount": float(UTILITIES),
            "payment_date": "2026-01-17",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        # ═══ Step 9: 个人垫付税金 1000 → 偿还 → 红冲偿还 §48 ═══
        ADV_TAX = Decimal("1000")
        r = c.post("/api/personal-advances", json={
            "advancer_name": "张老板",
            "amount": float(ADV_TAX),
            "advance_date": "2026-01-18",
            "debit_account_code": "6601",
            "description": "垫付税金",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["adv_id"] = _get_id(r, "advance")

        r = c.post(f"/api/personal-advances/{s['adv_id']}/repay", json={
            "amount": float(ADV_TAX),
            "repayment_date": "2026-01-19",
            "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        body = r.json()
        s["repay_id"] = (
            body.get("entity_id")
            or body.get("entity", {}).get("entity_id")
            or body.get("data", {}).get("id")
        )
        assert s["repay_id"] is not None, f"无法获取 repayment_id: {body}"

        r = c.post(
            f"/api/personal-advances/{s['adv_id']}/repayments/{s['repay_id']}/reverse",
            headers=HEADERS,
        )
        assert r.status_code == 200, r.text

        # ═══ Step 10: 月结 §7.1 §84 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
            income_tax_rate=Decimal("0.05"),  # 小微企业实际税负（独立从税务局核定单确认）
            purchases=[Purchase(QTY, UC, VAT_RATE)],
            sales=[Sale(SQTY, UP, VAT_RATE)],
            returns=[
                Return("sale", RET_SQTY, UP, UC, VAT_RATE),
                Return("purchase", RET_PQTY, UC, Decimal("0"), VAT_RATE),
            ],
            fixed_assets=[FixedAsset(FA_ORIG, FA_MONTHS)],
            expenses=[
                Expense(RENT, paid=False),      # 房租红冲付款后净挂账
                Expense(UTILITIES, paid=True),  # 水电费现金支付
            ],
            employee_funded_expenses=[
                # 员工垫付 1000 → 报销 1000 → 红冲报销 1000
                # 净效果：费用确认 1000，仍欠员工 1000，银行无净流出
                EmployeeFundedExpense(ADV_TAX, reimbursed=ADV_TAX, reversed_reimbursement=ADV_TAX),
            ],
            cash_flows=CashFlow(
                purchase_payment=net_purchase_pay,
                sale_receipt=net_sale_receive,
            ),
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
        assert abs(Decimal(str(bs["fixed_assets_net"])) - expected.balance_sheet.fixed_assets_net) <= tol, \
            f"§84固定资产净值: 实际{bs['fixed_assets_net']} != 期望{expected.balance_sheet.fixed_assets_net}"
        assert abs(Decimal(str(bs["prepaid_tax"])) - expected.balance_sheet.prepaid_tax) <= tol, \
            f"§84预付税款: 实际{bs['prepaid_tax']} != 期望{expected.balance_sheet.prepaid_tax}"
        assert abs(Decimal(str(bs["accounts_payable"])) - expected.balance_sheet.accounts_payable) <= tol, \
            f"§84应付账款: 实际{bs['accounts_payable']} != 期望{expected.balance_sheet.accounts_payable}"
        assert abs(Decimal(str(bs["other_payable"])) - expected.balance_sheet.other_payable) <= tol, \
            f"§84其他应付款: 实际{bs['other_payable']} != 期望{expected.balance_sheet.other_payable}"
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
        assert abs(Decimal(str(pl["income_tax_expense"])) - expected.income_statement.income_tax) <= tol, \
            f"§7.1所得税费用: 实际{pl['income_tax_expense']} != 期望{expected.income_statement.income_tax}"

        print("\nALL GOLDEN ASSERTIONS PASSED")
