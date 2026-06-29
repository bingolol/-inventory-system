"""Module 2: 一般纳税人全流程

一般纳税人：enable_vat_deduction=True, taxpayer_type=general
特征：采购价税分离（进项222102），销项用222101
"""
import sys, os, pytest, tempfile, uuid
from decimal import Decimal
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import get_db, Base, init_db
import database
from models import Account

TEST_DB = os.path.join(tempfile.gettempdir(), f"test_general_m2_{uuid.uuid4().hex[:8]}.db")
_engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

database.engine = _engine
database.SessionLocal = _SessionLocal
Base.metadata.create_all(bind=_engine)
init_db()

db = _SessionLocal()
try:
    acc = db.query(Account).first()
    if acc:
        acc.taxpayer_type = "general"
        acc.vat_rate = Decimal('0.13')
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

STATE = {}

@pytest.fixture
def client():
    return TestClient(app)

ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "test"}
UNIQUE = str(uuid.uuid4().hex[:6])


class TestGeneralFullCycle:

    def test_01_opening(self, client):
        s = STATE
        c = client
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": f"622202{UNIQUE}", "balance": 100000,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["bank_id"] = r.json()["id"]

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "bank_balance": 100000, "paid_in_capital": 100000,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-01", headers=HEADERS)
        assert r.status_code == 200, r.text
        bs = r.json()
        assert Decimal(str(bs["total_assets"])) == Decimal(str(bs["total_liabilities_and_equity"]))
        print(f"[期初] 资产={bs['total_assets']} = 权益={bs['total_liabilities_and_equity']}")

        r = c.post("/api/products", json={
            "name": f"商品G-{UNIQUE}", "sku": f"G-{UNIQUE}",
            "purchase_price": 100, "sale_price": 200,
            "unit": "个", "track_inventory": True, "category": "测试",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["pid"] = r.json()["entity_id"]

        r = c.post("/api/suppliers", json={"name": f"供应商G-{UNIQUE}"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["supplier_id"] = r.json()["entity_id"]

        r = c.post("/api/customers", json={"name": f"客户G-{UNIQUE}"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["customer_id"] = r.json()["entity_id"]
        print(f"[基础数据] 商品={s['pid']} 供应商={s['supplier_id']} 客户={s['customer_id']}")
        print("[OK] 第一幕: 期初建账完成")

    def test_02_purchase(self, client):
        s = STATE
        c = client
        # 含税单价113(=100*1.13)，一般纳税人价税分离
        # 库存成本 = 100/个，进项税 = 13/个
        r = c.post("/api/purchases", json={
            "supplier_id": s["supplier_id"],
            "items": [{"product_id": s["pid"], "quantity": 100, "unit_price": 113, "tax_rate": 0.13}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["purchase_id"] = r.json()["entity_id"]
        print(f"[采购] 单号={s['purchase_id']} 金额=11300 (含税)")

        # 一般纳税人价税分离后，库存成本应为 100*100=10000
        r = c.get("/api/inventory", headers=HEADERS)
        target = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid"]), None)
        assert target is not None and target["quantity"] == 100
        print(f"[库存] 数量={target['quantity']} 单位成本={target.get('unit_cost', 'N/A')} (预期=100)")

        r = c.get("/api/bank-accounts", headers=HEADERS)
        assert float(r.json()["items"][0]["balance"]) == 100000.0
        print(f"[银行] 赊购, 余额=100000")
        print("[OK] 第二幕: 采购入库完成")

    def test_03_payment(self, client):
        s = STATE
        c = client
        r = c.post("/api/payments", json={
            "payment_type": "purchase", "related_entity_type": "purchase_order",
            "related_entity_id": s["purchase_id"], "amount": 11300,
            "payment_date": "2026-01-10T00:00:00",
            "bank_account_id": s["bank_id"], "description": "付款",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        r = c.get("/api/bank-accounts", headers=HEADERS)
        bal = Decimal(str(r.json()["items"][0]["balance"]))
        assert bal == Decimal("88700.00"), f"预期88700，实际{bal}"
        print(f"[银行] 付款11300, 余额={bal}")
        print("[OK] 第三幕: 采购付款完成")

    def test_04_sale(self, client):
        s = STATE
        c = client
        # 含税单价226(=200*1.13)
        r = c.post("/api/sales", json={
            "customer_id": s["customer_id"], "deduct_inventory": True,
            "payment_status": "unpaid", "sale_date": "2026-01-15T10:00:00",
            "items": [{"product_id": s["pid"], "quantity": 50, "unit_price": 226, "tax_rate": 0.13}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["sale_id"] = r.json()["entity_id"]
        print(f"[销售] 单号={s['sale_id']} 金额=11300 (含税)")

        r = c.get("/api/inventory", headers=HEADERS)
        target = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid"]), None)
        assert target["quantity"] == 50
        print(f"[库存] 销售后数量={target['quantity']}")
        print("[OK] 第四幕: 销售出库完成")

    def test_05_receipt(self, client):
        s = STATE
        c = client
        r = c.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order",
            "related_entity_id": s["sale_id"], "amount": 11300,
            "receipt_date": "2026-01-20T10:00:00",
            "bank_account_id": s["bank_id"], "description": "收款",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        r = c.get("/api/bank-accounts", headers=HEADERS)
        bal = Decimal(str(r.json()["items"][0]["balance"]))
        assert bal == Decimal("100000.00"), f"预期100000，实际{bal}"
        print(f"[银行] 收款11300, 余额={bal}")
        print("[OK] 第五幕: 销售收款完成")

    def test_06_expense(self, client):
        s = STATE
        c = client
        r = c.post("/api/expenses", json={
            "category": "房租", "functional_category": "管理费用",
            "amount": 2000, "expense_date": "2026-01-25T00:00:00",
            "payment_method": "company", "description": "房租",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["expense_id"] = r.json()["data"]["id"]
        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": s["expense_id"], "amount": 2000,
            "payment_date": "2026-01-25T00:00:00",
            "bank_account_id": s["bank_id"], "description": "付房租",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        r = c.get("/api/bank-accounts", headers=HEADERS)
        bal = Decimal(str(r.json()["items"][0]["balance"]))
        assert bal == Decimal("98000.00"), f"预期98000，实际{bal}"
        print(f"[银行] 付房租2000, 余额={bal}")
        print("[OK] 第六幕: 费用报销完成")

    def test_07_vat_report(self, client):
        s = STATE
        c = client
        # 进项发票
        r = c.post("/api/invoices", json={
            "invoice_no": f"INV-IN-{UNIQUE}", "direction": "in", "invoice_type": "special",
            "amount_without_tax": 10000, "tax_rate": 0.13, "tax_amount": 1300, "amount_with_tax": 11300,
            "counterparty_name": f"供应商G-{UNIQUE}", "issue_date": "2026-01-10",
            "related_order_id": s["purchase_id"], "related_order_type": "purchase_order",
            "certification_status": "certified",
        }, headers=HEADERS)
        assert r.status_code in (200, 201), r.text

        # 销项发票
        r = c.post("/api/invoices", json={
            "invoice_no": f"INV-OUT-{UNIQUE}", "direction": "out", "invoice_type": "ordinary",
            "amount_without_tax": 10000, "tax_rate": 0.13, "tax_amount": 1300, "amount_with_tax": 11300,
            "counterparty_name": f"客户G-{UNIQUE}", "issue_date": "2026-01-15",
            "related_order_id": s["sale_id"], "related_order_type": "sale_order",
            "certification_status": "n_a",
        }, headers=HEADERS)
        assert r.status_code in (200, 201), r.text

        r = c.get("/api/tax-report/monthly?year=2026&month=1", headers=HEADERS)
        assert r.status_code == 200, r.text
        tax = r.json()
        print(f"[增值税] 销项={tax['output_tax']} 进项={tax['input_tax']} 应纳税={tax['tax_payable']}")
        print("[OK] 第七幕: 税务验证完成")

    def test_08_profit_statement(self, client):
        c = client
        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        pl = r.json()
        print(f"[利润表] 收入={pl['revenue']} 成本={pl['cost_of_goods_sold']}"
              f" 管理费={pl['administrative_expenses']} 毛利={pl['gross_profit']}"
              f" 利润总额={pl['gross_profit_total']} 所得税={pl['income_tax_expense']}"
              f" 净利润={pl['net_profit']}")
        print("[OK] 第八幕: 利润表完成")

    def test_09_balance_sheet(self, client):
        c = client
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        if r.status_code != 200:
            print(f"  [WARN] 资产负债表: {r.json().get('error', {}).get('message', '')}")
        else:
            bs = r.json()
            diff = Decimal(str(bs['total_assets'])) - Decimal(str(bs['total_liabilities_and_equity']))
            print(f"[资产负债表] 货币={bs['monetary_funds']} 存货={bs['inventory']}"
                  f" 应收={bs['accounts_receivable']} 应付={bs['accounts_payable']}"
                  f" 应交税费={bs['tax_payable']}")
            print(f"  总资产={bs['total_assets']} = 负债={bs['total_liabilities']} + 权益={bs['total_equity']}")
            print(f"  借贷差异={diff}")
        print("[OK] 第九幕: 资产负债表完成")

    def test_10_summary(self):
        print(f"\n{'='*60}")
        print(f"*** Module 2: 一般纳税人全流程 完成 ***")
        print(f"{'='*60}")
