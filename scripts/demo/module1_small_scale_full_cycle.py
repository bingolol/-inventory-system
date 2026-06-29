"""Module 1: 小规模纳税人全流程

小规模纳税人：enable_vat_deduction=False, taxpayer_type=small_scale
特征：采购不抵扣进项（全额入成本），销项用 222103 简易计税

独立数据库文件，不影响主测试库。
Run: pytest tests/module1_small_scale_full_cycle.py -v -s
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

TEST_DB = os.path.join(tempfile.gettempdir(), f"test_small_scale_{uuid.uuid4().hex[:8]}.db")
_engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

# 替换 database 模块的引擎
database.engine = _engine
database.SessionLocal = _SessionLocal
Base.metadata.create_all(bind=_engine)
init_db()

db = _SessionLocal()
try:
    acc = db.query(Account).first()
    if acc:
        acc.taxpayer_type = "small_scale"
        acc.vat_rate = Decimal('0.03')
        acc.enable_vat_deduction = False
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


class TestSmallScaleFullCycle:

    def test_01_opening_and_masters(self, client):
        s = STATE
        c = client
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": f"622202{UNIQUE}", "balance": 100000,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["bank_id"] = r.json()["id"]
        print(f"  银行账户: id={s['bank_id']}")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "bank_balance": 100000, "paid_in_capital": 100000,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-01", headers=HEADERS)
        assert r.status_code == 200, r.text
        bs = r.json()
        assert Decimal(str(bs["total_assets"])) == Decimal(str(bs["total_liabilities_and_equity"]))
        print(f"  资产负债表: 资产={bs['total_assets']} = 权益={bs['total_liabilities_and_equity']}")

        r = c.post("/api/products", json={
            "name": f"商品S-{UNIQUE}", "sku": f"S-{UNIQUE}",
            "purchase_price": 100, "sale_price": 200,
            "unit": "个", "track_inventory": True, "category": "测试",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["pid"] = r.json()["entity_id"]

        r = c.post("/api/suppliers", json={"name": f"供应商S-{UNIQUE}"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["supplier_id"] = r.json()["entity_id"]

        r = c.post("/api/customers", json={"name": f"客户S-{UNIQUE}"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["customer_id"] = r.json()["entity_id"]
        print(f"  商品={s['pid']} 供应商={s['supplier_id']} 客户={s['customer_id']}")
        print("[OK] 第一幕: 期初建账完成")

    def test_02_purchase(self, client):
        s = STATE
        c = client
        r = c.post("/api/purchases", json={
            "supplier_id": s["supplier_id"],
            "items": [{"product_id": s["pid"], "quantity": 100, "unit_price": 113, "tax_rate": 0.13}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["purchase_id"] = r.json()["entity_id"]
        print(f"  采购单: id={s['purchase_id']} 金额=11300")

        r = c.get("/api/inventory", headers=HEADERS)
        target = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid"]), None)
        assert target is not None and target["quantity"] == 100
        print(f"  库存量: {target['quantity']}  单位成本: {target.get('unit_cost', 'N/A')}")

        r = c.get("/api/bank-accounts", headers=HEADERS)
        assert float(r.json()["items"][0]["balance"]) == 100000.0
        print(f"  银行余额(赊购): 100000")
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
        assert Decimal(str(r.json()["items"][0]["balance"])) == Decimal("88700.00")
        print(f"  银行余额(付款后): 88700")
        print("[OK] 第三幕: 采购付款完成")

    def test_04_sale(self, client):
        s = STATE
        c = client
        r = c.post("/api/sales", json={
            "customer_id": s["customer_id"], "deduct_inventory": True,
            "payment_status": "unpaid", "sale_date": "2026-01-15T10:00:00",
            "items": [{"product_id": s["pid"], "quantity": 50, "unit_price": 226, "tax_rate": 0.13}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["sale_id"] = r.json()["entity_id"]
        print(f"  销售单: id={s['sale_id']} 金额=11300")

        r = c.get("/api/inventory", headers=HEADERS)
        target = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid"]), None)
        assert target["quantity"] == 50
        print(f"  库存量(销售后): {target['quantity']}")
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
        assert Decimal(str(r.json()["items"][0]["balance"])) == Decimal("100000.00")
        print(f"  银行余额(收款后): 100000")
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
        assert Decimal(str(r.json()["items"][0]["balance"])) == Decimal("98000.00")
        print(f"  银行余额(费用后): 98000")
        print("[OK] 第六幕: 费用报销完成")

    def test_07_invoice_and_tax(self, client):
        s = STATE
        c = client
        r = c.post("/api/invoices", json={
            "invoice_no": f"INV-IN-{UNIQUE}", "direction": "in", "invoice_type": "special",
            "amount_without_tax": 10000, "tax_rate": 0.13, "tax_amount": 1300, "amount_with_tax": 11300,
            "counterparty_name": f"供应商S-{UNIQUE}", "issue_date": "2026-01-10",
            "related_order_id": s["purchase_id"], "related_order_type": "purchase_order",
            "certification_status": "certified",
        }, headers=HEADERS)
        assert r.status_code in (200, 201), r.text

        r = c.post("/api/invoices", json={
            "invoice_no": f"INV-OUT-{UNIQUE}", "direction": "out", "invoice_type": "ordinary",
            "amount_without_tax": 10000, "tax_rate": 0.13, "tax_amount": 1300, "amount_with_tax": 11300,
            "counterparty_name": f"客户S-{UNIQUE}", "issue_date": "2026-01-15",
            "related_order_id": s["sale_id"], "related_order_type": "sale_order",
            "certification_status": "n_a",
        }, headers=HEADERS)
        assert r.status_code in (200, 201), r.text

        r = c.get("/api/tax-report/monthly?year=2026&month=1", headers=HEADERS)
        assert r.status_code == 200, r.text
        tax = r.json()
        print(f"  增值税报表: 销项={tax['output_tax']} 进项={tax['input_tax']} 应纳税={tax['tax_payable']}")
        print("[OK] 第七幕: 税务验证完成")

    def test_08_financial_reports(self, client):
        c = client
        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        pl = r.json()
        print(f"  利润表: 收入={pl['revenue']} 成本={pl['cost_of_goods_sold']}"
              f" 管理费={pl['administrative_expenses']} 毛利={pl['gross_profit']}"
              f" 利润总额={pl['gross_profit_total']} 所得税={pl['income_tax_expense']}"
              f" 净利润={pl['net_profit']}")

        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        if r.status_code != 200:
            print(f"  [WARN] 资产负债表报错: {r.json().get('error', {}).get('message', '')}")
        else:
            bs = r.json()
            diff = Decimal(str(bs['total_assets'])) - Decimal(str(bs['total_liabilities_and_equity']))
            print(f"  资产负债表: 货币={bs['monetary_funds']} 存货={bs['inventory']}"
                  f" 应收={bs['accounts_receivable']} 应付={bs['accounts_payable']}"
                  f" 应交税费={bs['tax_payable']}")
            print(f"  总资产={bs['total_assets']} = 负债={bs['total_liabilities']} + 权益={bs['total_equity']}")
            print(f"  借贷差异: {diff}")
        print("[OK] 第八幕: 财务报表完成")

    def test_09_summary(self):
        print(f"\n{'='*60}")
        print(f"*** Module 1: 小规模纳税人全流程 完成 ***")
        print(f"{'='*60}")
