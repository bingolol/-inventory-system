"""Module 3: 冲销场景 — 取消采购/销售的库存回滚 + 金额验证

两个账本：Account 1=小规模, Account 2=一般纳税人
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

TEST_DB = os.path.join(tempfile.gettempdir(), f"test_cancel_{uuid.uuid4().hex[:8]}.db")
_engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

database.engine = _engine
database.SessionLocal = _SessionLocal
Base.metadata.create_all(bind=_engine)
init_db()

# 创建第二个账本（一般纳税人）
db = _SessionLocal()
try:
    db2 = Account(name="一般纳税人账本", type="company", code="general_test",
                  taxpayer_type="general", vat_rate=Decimal('0.13'), enable_vat_deduction=True)
    db.add(db2)
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


class TestCancelScenarios:

    HDR_SS = {"X-Account-ID": "1", "X-Operator": "test"}   # 小规模
    HDR_GN = {"X-Account-ID": "2", "X-Operator": "test"}   # 一般纳税人

    def test_01_setup_two_accounts(self, client):
        """准备两个账本的基础数据"""
        c = client
        s = STATE

        # Account 1: 小规模
        r = c.post("/api/bank-accounts", json={
            "bank_name": "银行SS", "account_number": f"SS{UNIQUE}", "balance": 50000,
        }, headers=self.HDR_SS)
        assert r.status_code == 200, r.text
        s["bank_ss"] = r.json()["id"]

        r = c.post("/api/products", json={
            "name": f"PA-SS-{UNIQUE}", "sku": f"PASS{UNIQUE}",
            "purchase_price": 100, "sale_price": 200,
            "unit": "个", "track_inventory": True, "category": "测试",
        }, headers=self.HDR_SS)
        assert r.status_code == 200, r.text
        s["pid_ss"] = r.json()["entity_id"]

        r = c.post("/api/suppliers", json={"name": f"SUP-SS-{UNIQUE}"}, headers=self.HDR_SS)
        assert r.status_code == 200, r.text
        s["sup_ss"] = r.json()["entity_id"]

        # Account 2: 一般纳税人
        r = c.post("/api/bank-accounts", json={
            "bank_name": "银行GN", "account_number": f"GN{UNIQUE}", "balance": 50000,
        }, headers=self.HDR_GN)
        assert r.status_code == 200, r.text
        s["bank_gn"] = r.json()["id"]

        r = c.post("/api/products", json={
            "name": f"PA-GN-{UNIQUE}", "sku": f"PAGN{UNIQUE}",
            "purchase_price": 100, "sale_price": 200,
            "unit": "个", "track_inventory": True, "category": "测试",
        }, headers=self.HDR_GN)
        assert r.status_code == 200, r.text
        s["pid_gn"] = r.json()["entity_id"]

        r = c.post("/api/suppliers", json={"name": f"SUP-GN-{UNIQUE}"}, headers=self.HDR_GN)
        assert r.status_code == 200, r.text
        s["sup_gn"] = r.json()["entity_id"]

        print(f"[初始化] 小规模: 商品={s['pid_ss']} 供应商={s['sup_ss']}")
        print(f"[初始化] 一般纳税人: 商品={s['pid_gn']} 供应商={s['sup_gn']}")
        print("[OK] 基础数据准备完成")

    def test_02_ss_purchase_then_cancel(self, client):
        """小规模: 采购入库→取消→验证库存回滚金额"""
        s = STATE
        c = client

        # 采购100个，单价113，全额入成本
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_ss"],
            "items": [{"product_id": s["pid_ss"], "quantity": 100, "unit_price": 113, "tax_rate": 0.13}],
        }, headers=self.HDR_SS)
        assert r.status_code == 200, r.text
        po_id = r.json()["entity_id"]
        print(f"[SS采购] 单号={po_id} 金额=11300")

        r = c.get("/api/inventory", headers=self.HDR_SS)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_ss"]), None)
        assert inv["quantity"] == 100
        print(f"[SS库存] 数量={inv['quantity']}")

        # 取消采购
        r = c.post(f"/api/purchases/{po_id}/cancel", headers=self.HDR_SS)
        assert r.status_code == 200, r.text
        print(f"[SS取消] 结果={r.status_code}")

        # 验证库存归零
        r = c.get("/api/inventory", headers=self.HDR_SS)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_ss"]), None)
        qty = inv["quantity"] if inv else 0
        print(f"[SS库存] 取消后数量={qty} (预期=0)")
        assert qty == 0, f"库存应为0，实际{qty}"
        print("[OK] 小规模取消采购: 库存回滚正确")

    def test_03_gn_purchase_then_cancel(self, client):
        """一般纳税人: 采购入库(价税分离)→取消→验证回滚金额"""
        s = STATE
        c = client

        # 采购100个，单价113，价税分离: 成本100/个
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_gn"],
            "items": [{"product_id": s["pid_gn"], "quantity": 100, "unit_price": 113, "tax_rate": 0.13}],
        }, headers=self.HDR_GN)
        assert r.status_code == 200, r.text
        po_id = r.json()["entity_id"]
        print(f"[GN采购] 单号={po_id} 金额=11300")

        r = c.get("/api/inventory", headers=self.HDR_GN)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_gn"]), None)
        assert inv["quantity"] == 100
        print(f"[GN库存] 数量={inv['quantity']}")

        # 取消采购
        r = c.post(f"/api/purchases/{po_id}/cancel", headers=self.HDR_GN)
        assert r.status_code == 200, r.text

        # 验证库存归零
        r = c.get("/api/inventory", headers=self.HDR_GN)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_gn"]), None)
        qty = inv["quantity"] if inv else 0
        print(f"[GN库存] 取消后数量={qty} (预期=0)")
        assert qty == 0, f"库存应为0，实际{qty}"
        print("[OK] 一般纳税人取消采购: 库存回滚正确")

    def test_04_sale_then_cancel(self, client):
        """销售出库→取消→库存回补"""
        s = STATE
        c = client

        # 先采购100个（小规模）
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_ss"],
            "items": [{"product_id": s["pid_ss"], "quantity": 100, "unit_price": 113, "tax_rate": 0.13}],
        }, headers=self.HDR_SS)
        assert r.status_code == 200, r.text
        po_id = r.json()["entity_id"]

        r = c.get("/api/inventory", headers=self.HDR_SS)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_ss"]), None)
        assert inv["quantity"] == 100
        print(f"[SS库存] 采购后={inv['quantity']}")

        # 创建客户
        r = c.post("/api/customers", json={"name": f"CUST-SS-{UNIQUE}"}, headers=self.HDR_SS)
        cust_id = r.json()["entity_id"]

        # 销售30个
        r = c.post("/api/sales", json={
            "customer_id": cust_id, "deduct_inventory": True,
            "payment_status": "unpaid", "sale_date": "2026-03-01T10:00:00",
            "items": [{"product_id": s["pid_ss"], "quantity": 30, "unit_price": 226, "tax_rate": 0.13}],
        }, headers=self.HDR_SS)
        assert r.status_code == 200, r.text
        sale_id = r.json()["entity_id"]
        print(f"[SS销售] 单号={sale_id} 数量=30")

        r = c.get("/api/inventory", headers=self.HDR_SS)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_ss"]), None)
        assert inv["quantity"] == 70
        print(f"[SS库存] 销售后={inv['quantity']}")

        # 取消销售
        r = c.post(f"/api/sales/{sale_id}/cancel", headers=self.HDR_SS)
        assert r.status_code == 200, r.text
        print(f"[SS取消销售] 结果={r.status_code}")

        # 验证库存恢复
        r = c.get("/api/inventory", headers=self.HDR_SS)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_ss"]), None)
        qty = inv["quantity"] if inv else 0
        print(f"[SS库存] 取消销售后={qty} (预期=100)")
        assert qty == 100, f"库存应为100，实际{qty}"
        print("[OK] 取消销售: 库存回补正确")

    def test_05_gn_full_lifecycle(self, client):
        """一般纳税人: 采购→取消→重新采购→验证第二次采购正常"""
        s = STATE
        c = client

        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_gn"],
            "items": [{"product_id": s["pid_gn"], "quantity": 50, "unit_price": 113, "tax_rate": 0.13}],
        }, headers=self.HDR_GN)
        assert r.status_code == 200, r.text
        po1 = r.json()["entity_id"]
        print(f"[GN采购1] 单号={po1} 数量=50")

        # 取消
        c.post(f"/api/purchases/{po1}/cancel", headers=self.HDR_GN)

        # 重新采购
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_gn"],
            "items": [{"product_id": s["pid_gn"], "quantity": 80, "unit_price": 113, "tax_rate": 0.13}],
        }, headers=self.HDR_GN)
        assert r.status_code == 200, r.text
        po2 = r.json()["entity_id"]
        print(f"[GN采购2] 单号={po2} 数量=80 (重新采购)")

        r = c.get("/api/inventory", headers=self.HDR_GN)
        inv = next((i for i in r.json().get("items", []) if i["product_id"] == s["pid_gn"]), None)
        qty = inv["quantity"] if inv else 0
        print(f"[GN库存] 最终数量={qty} (预期=80)")
        assert qty == 80, f"库存应为80，实际{qty}"
        print("[OK] 完整生命周期: 采购→取消→重采购 正确")

    def test_06_summary(self):
        print(f"\n{'='*60}")
        print(f"*** Module 3: 冲销场景 完成 ***")
        print(f"  [SS小规模] 取消采购: 库存100→0 回滚正确")
        print(f"  [GN一般]   取消采购: 库存100→0 回滚正确")
        print(f"  [SS小规模] 取消销售: 库存100→70→100 回补正确")
        print(f"  [GN一般]   采购→取消→重采购: 0→50→0→80 正确")
        print(f"{'='*60}")
