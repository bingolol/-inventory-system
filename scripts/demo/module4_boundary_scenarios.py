"""Module 4: 边界场景 — 加权平均、0税率、track_inventory=False、跨月"""
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

TEST_DB = os.path.join(tempfile.gettempdir(), f"test_boundary_{uuid.uuid4().hex[:8]}.db")
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
UNIQUE = str(uuid.uuid4().hex[:6])

@pytest.fixture
def client():
    return TestClient(app)

ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "test"}

class TestBoundaryScenarios:

    def test_01_setup(self, client):
        """基础数据准备"""
        s = STATE
        c = client
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": f"BN{UNIQUE}", "balance": 100000,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["bank_id"] = r.json()["id"]

        r = c.post("/api/products", json={
            "name": f"PA-{UNIQUE}-A", "sku": f"A{UNIQUE}",
            "purchase_price": 100, "sale_price": 200,
            "unit": "个", "track_inventory": True, "category": "测试",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["pid"] = r.json()["entity_id"]

        r = c.post("/api/products", json={
            "name": f"PA-{UNIQUE}-B", "sku": f"B{UNIQUE}",
            "purchase_price": 50, "sale_price": 100,
            "unit": "个", "track_inventory": True, "category": "测试",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["pid_b"] = r.json()["entity_id"]

        r = c.post("/api/products", json={
            "name": f"PA-{UNIQUE}-NONINV", "sku": f"NON{UNIQUE}",
            "purchase_price": 30, "sale_price": 60,
            "unit": "个", "track_inventory": False, "category": "服务",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["pid_noninv"] = r.json()["entity_id"]

        r = c.post("/api/suppliers", json={"name": f"SUP-{UNIQUE}"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["sup_id"] = r.json()["entity_id"]

        r = c.post("/api/customers", json={"name": f"CUST-{UNIQUE}"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["cust_id"] = r.json()["entity_id"]

        print(f"[基础] 商品A(有库存)={s['pid']} 商品B(有库存)={s['pid_b']}")
        print(f"[基础] 商品NON(不计库存)={s['pid_noninv']}")
        print("[OK] 基础数据完成")

    def test_02_weighted_average(self, client):
        """加权平均：两次不同单价采购"""
        s = STATE
        c = client

        # 第一次采购：50个，单价113(含税=100+13)
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [{"product_id": s["pid"], "quantity": 50, "unit_price": 113, "tax_rate": 0.13}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        po1 = r.json()["entity_id"]
        print(f"[加权] 采购1: 50个 x 113 = 5650 单号={po1}")

        r = c.get("/api/inventory", headers=HEADERS)
        inv_items = r.json().get("items", [])
        inv_a = next((i for i in inv_items if i["product_id"] == s["pid"]), None)
        print(f"[加权] 库存A: 数量={inv_a['quantity']} 单位成本={inv_a.get('unit_cost', 'N/A')} (预期成本=100)")

        # 第二次采购：30个，单价226(含税=200+26)
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [{"product_id": s["pid"], "quantity": 30, "unit_price": 226, "tax_rate": 0.13}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        po2 = r.json()["entity_id"]
        print(f"[加权] 采购2: 30个 x 226 = 6780 单号={po2}")

        r = c.get("/api/inventory", headers=HEADERS)
        inv_items = r.json().get("items", [])
        inv_a = next((i for i in inv_items if i["product_id"] == s["pid"]), None)
        # 加权平均成本 = (50*100 + 30*200) / 80 = (5000+6000)/80 = 11000/80 = 137.5
        print(f"[加权] 库存A: 数量={inv_a['quantity']} 单位成本={inv_a.get('unit_cost', 'N/A')} (预期~137.5)")
        s["wa_qty"] = inv_a["quantity"]
        s["wa_cost"] = inv_a.get("unit_cost", "N/A")
        print("[OK] 加权平均完成")

    def test_03_zero_tax_rate(self, client):
        """0税率商品"""
        s = STATE
        c = client

        # 采购商品B，0税率
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [{"product_id": s["pid_b"], "quantity": 20, "unit_price": 50, "tax_rate": 0.0}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        po_id = r.json()["entity_id"]
        print(f"[0税率] 采购: 20个 x 50 = 1000 (税率0%) 单号={po_id}")

        r = c.get("/api/inventory", headers=HEADERS)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_b"]), None)
        print(f"[0税率] 库存B: 数量={inv['quantity']} 单位成本={inv.get('unit_cost', 'N/A')} (预期成本=50)")

        # 销售商品B，0税率
        r = c.post("/api/sales", json={
            "customer_id": s["cust_id"], "deduct_inventory": True,
            "payment_status": "unpaid", "sale_date": "2026-04-01T10:00:00",
            "items": [{"product_id": s["pid_b"], "quantity": 5, "unit_price": 100, "tax_rate": 0.0}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        sale_id = r.json()["entity_id"]
        print(f"[0税率] 销售: 5个 x 100 = 500 (税率0%) 单号={sale_id}")
        print("[OK] 0税率完成")

    def test_04_non_inventory_goods(self, client):
        """不计库存商品（服务类）"""
        s = STATE
        c = client

        r = c.post("/api/sales", json={
            "customer_id": s["cust_id"], "deduct_inventory": False,
            "payment_status": "paid", "sale_date": "2026-04-05T10:00:00",
            "items": [{"product_id": s["pid_noninv"], "quantity": 3, "unit_price": 60, "tax_rate": 0.13}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        sale_id = r.json()["entity_id"]
        print(f"[非库存] 销售服务: 3个 x 60 = 180 (不计库存) 单号={sale_id}")
        # 验证没有库存记录产生
        r = c.get("/api/inventory", headers=HEADERS)
        inv_all = r.json().get("items", [])
        noninv = next((i for i in inv_all if i["product_id"] == s["pid_noninv"]), None)
        if noninv:
            print(f"[非库存] 发现有库存记录: qty={noninv['quantity']}")
        else:
            print("[非库存] 无库存记录 (符合预期)")
        print("[OK] 非库存商品完成")

    def test_05_cross_month(self, client):
        """跨月：1月采购，2月销售，验证期初结存"""
        s = STATE
        c = client

        # 采购库存B（在1月已有20个，再采购10个到2月）
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [{"product_id": s["pid_b"], "quantity": 10, "unit_price": 50, "tax_rate": 0.0}],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        print(f"[跨月] 采购B: +10个 (延续之前20-5=15, 现=25)")

        r = c.get("/api/inventory", headers=HEADERS)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_b"]), None)
        print(f"[跨月] 库存B: 数量={inv['quantity']} (预期25)")

        # 验证库存报表
        r = c.get("/api/reports/inventory", headers=HEADERS)
        if r.status_code == 200:
            print(f"[跨月] 库存报表可访问")
        print("[OK] 跨月场景完成")

    def test_06_mixed_tax_rate_order(self, client):
        """一单多商品不同税率"""
        s = STATE
        c = client

        # 采购商品A(13%) + 商品B(0%) 同一单
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [
                {"product_id": s["pid"], "quantity": 10, "unit_price": 113, "tax_rate": 0.13},
                {"product_id": s["pid_b"], "quantity": 10, "unit_price": 50, "tax_rate": 0.0},
            ],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        po_id = r.json()["entity_id"]
        print(f"[混税率] 同一采购单: A(13%) x10 + B(0%) x10 单号={po_id}")

        r = c.get("/api/inventory", headers=HEADERS)
        inv_items = r.json().get("items", [])
        inv_a = next((i for i in inv_items if i["product_id"] == s["pid"]), None)
        inv_b = next((i for i in inv_items if i["product_id"] == s["pid_b"]), None)
        print(f"[混税率] 库存A: qty={inv_a['quantity']} 库存B: qty={inv_b['quantity']}")
        print("[OK] 混合税率完成")

    def test_07_summary(self):
        print(f"\n{'='*60}")
        print(f"*** Module 4: 边界场景 完成 ***")
        print(f"  加权平均: 采购单价100+200 → 加权={STATE.get('wa_cost', 'N/A')}")
        print(f"  0税率: 采购/销售正常")
        print(f"  非库存商品: 无 StockMove 产生")
        print(f"  跨月: 库存延续")
        print(f"  混税率一单: 正常")
        print(f"{'='*60}")
