"""固定资产发票复合接口测试 - TDD 循环

Behavior 1: 发票含税金额 = 资产原值（强一致）
Behavior 2: 发票金额三件套自动计算且平衡
Behavior 3: 事务回滚：资产创建失败 → 发票也撤销
Behavior 4: 发票号码重复 → 整体拒绝
Behavior 5: 返回值包含发票和资产完整信息
Behavior 6: 更新发票金额 → 资产原值自动同步
Behavior 7: 删除发票 → 关联资产自动删除
Behavior 8: 更新资产原值 → 发票金额自动同步
Behavior 9: 删除资产 → 关联发票清空
Behavior 10: 发票金额计算使用 AccountingEngine
"""

import sys
import os
import pytest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import uuid

from main import app
from database import get_db, Base
import database
import models
from helpers import get_entity_id
from accounting_engine import AccountingEngine


# 测试数据库（文件 SQLite，唯一路径）
TEST_DB_FILE = os.path.join(tempfile.gettempdir(), f"test_invoice_asset_{uuid.uuid4().hex[:8]}.db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# 保存原始生产数据库 URL（用于隔离验证）
ORIGINAL_PROD_DB_URL = str(database.get_engine().url)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    """每个测试前重建数据库，并完全隔离生产数据库"""
    # 覆盖 database 模块的全局变量，确保完全隔离
    # _engine 是私有全局，get_engine() 读取它；SessionLocal 是 session 工厂
    monkeypatch.setattr(database, '_engine', test_engine)
    monkeypatch.setattr(database, 'SessionLocal', TestingSessionLocal)

    # 创建表
    Base.metadata.create_all(bind=test_engine)

    # 覆盖 FastAPI 依赖
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    # 清理
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


# ── 隔离验证测试 ──

def test_database_isolation():
    """验证测试数据库与生产数据库完全隔离"""
    # 测试 engine 应该指向临时数据库
    test_url = str(test_engine.url)
    assert "test_invoice_asset_" in test_url, f"测试 engine 未指向测试数据库: {test_url}"

    # 生产 engine URL 应该指向原始数据库
    assert "test_invoice_asset_" not in ORIGINAL_PROD_DB_URL, f"生产 engine 被污染: {ORIGINAL_PROD_DB_URL}"

    # 两者应该不同
    assert test_url != ORIGINAL_PROD_DB_URL, "测试数据库与生产数据库路径相同"


@pytest.fixture(autouse=True)
def disable_readonly_middleware(monkeypatch):
    from middleware.readonly_middleware import ReadonlyMiddleware
    async def fake_dispatch(self, request, call_next):
        return await call_next(request)
    monkeypatch.setattr(ReadonlyMiddleware, 'dispatch', fake_dispatch)


@pytest.fixture
def client():
    """测试客户端"""
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


# ── 辅助函数 ──

def _create_product(client):
    resp = client.post("/api/products", json={
        "name": "测试商品", "sku": "TEST-SKU", "category": "测试",
        "unit": "个", "purchase_price": 100, "sale_price": 200,
    }, headers={"X-Account-ID": "1"})
    assert resp.status_code == 200
    return get_entity_id(resp.json())


# ── Behavior 1: 发票含税金额 = 资产原值（Critical）──

def test_invoice_amount_equals_asset_original_value(client):
    """发票含税金额必须等于固定资产原值，由代码强保证"""
    pid = _create_product(client)
    response = client.post("/api/invoices/quick", json={
        "invoice_no": "FA-INV-001",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商A",
        "seller_name": "供应商A",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-001",
            "asset_name": "测试设备",
            "useful_life": 60,
            "start_date": "2026-06-19"
        }
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()["data"]

    invoice_amount = Decimal(data["amount_with_tax"])
    asset_value = Decimal(data["fixed_asset"]["original_value"])

    assert invoice_amount == asset_value == Decimal("11300.00"), \
        f"发票金额 {invoice_amount} != 资产原值 {asset_value}"


# ── Behavior 2: 发票金额三件套自动计算且平衡（Critical）──

def test_invoice_amounts_auto_calculated_and_balanced(client):
    """只传含税金额和税率，系统自动计算不含税金额和税额，且三者平衡"""
    pid = _create_product(client)
    response = client.post("/api/invoices/quick", json={
        "invoice_no": "FA-INV-002",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 22600,
        "counterparty_name": "供应商B",
        "seller_name": "供应商B",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-002",
            "asset_name": "测试设备B",
            "useful_life": 120,
            "start_date": "2026-06-19"
        }
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    inv = response.json()["data"]

    amount_without_tax = Decimal(inv["amount_without_tax"])
    tax_amount = Decimal(inv["tax_amount"])
    amount_with_tax = Decimal(inv["amount_with_tax"])

    assert amount_without_tax == Decimal("20000.00"), f"不含税金额错误: {amount_without_tax}"
    assert tax_amount == Decimal("2600.00"), f"税额错误: {tax_amount}"

    assert amount_without_tax + tax_amount == amount_with_tax, \
        f"金额不平衡: {amount_without_tax} + {tax_amount} != {amount_with_tax}"


# ── Behavior 3: 事务回滚 — 资产创建失败 → 发票也撤销（High）──

def test_rollback_on_duplicate_invoice(client):
    """发票号码重复时，整个事务回滚，发票和资产都不创建"""
    pid = _create_product(client)
    body1 = {
        "invoice_no": "FA-INV-ROLLBACK",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商C",
        "seller_name": "供应商C",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-ROLLBACK",
            "asset_name": "设备C",
            "useful_life": 60,
            "start_date": "2026-06-19"
        }
    }
    response1 = client.post("/api/invoices/quick", json=body1, headers={"X-Account-ID": "1"})
    assert response1.status_code == 200

    body2 = {
        "invoice_no": "FA-INV-ROLLBACK",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 5650,
        "counterparty_name": "供应商D",
        "seller_name": "供应商D",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-ROLLBACK-2",
            "asset_name": "设备D",
            "useful_life": 36,
            "start_date": "2026-06-19"
        }
    }
    response2 = client.post("/api/invoices/quick", json=body2, headers={"X-Account-ID": "1"})
    assert response2.status_code == 409

    invoice_list = client.get("/api/invoices", headers={"X-Account-ID": "1"})
    assert invoice_list.status_code == 200
    invoices = invoice_list.json()["items"]
    assert any(inv["invoice_no"] == "FA-INV-ROLLBACK" for inv in invoices)

    asset_list = client.get("/api/fixed-assets", headers={"X-Account-ID": "1"})
    assert asset_list.status_code == 200
    assets = asset_list.json()["items"]
    assert not any(a["asset_code"] == "FA-ROLLBACK-2" for a in assets)


# ── Behavior 4: 发票号码重复 → 整体拒绝（Medium）──

def test_duplicate_invoice_number_returns_structured_error(client):
    """发票号码重复时返回结构化错误，包含错误码和AI指令"""
    pid = _create_product(client)
    client.post("/api/invoices/quick", json={
        "invoice_no": "FA-INV-DUP",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商E",
        "seller_name": "供应商E",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-DUP",
            "asset_name": "设备E",
            "useful_life": 60,
            "start_date": "2026-06-19"
        }
    }, headers={"X-Account-ID": "1"})

    response = client.post("/api/invoices/quick", json={
        "invoice_no": "FA-INV-DUP",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 5650,
        "counterparty_name": "供应商F",
        "seller_name": "供应商F",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-DUP-2",
            "asset_name": "设备F",
            "useful_life": 36,
            "start_date": "2026-06-19"
        }
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INVOICE_DUPLICATE_NUMBER"
    assert "FA-INV-DUP" in error["message"]
    assert "STOP_RETRYING" in error["ai_instruction"]


# ── Behavior 5: 返回值包含发票和资产完整信息（Medium）──

def test_response_contains_complete_invoice_and_asset_info(client):
    """返回值包含发票和资产的完整信息，包括关联ID"""
    pid = _create_product(client)
    response = client.post("/api/invoices/quick", json={
        "invoice_no": "FA-INV-COMPLETE",
        "direction": "in",
        "invoice_type": "special",
        "tax_rate": 0.09,
        "amount_with_tax": 10900,
        "counterparty_name": "供应商G",
        "seller_name": "供应商G",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "notes": "测试完整信息",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-COMPLETE",
            "asset_name": "完整设备",
            "category": "机器设备",
            "salvage_rate": 0.10,
            "useful_life": 120,
            "depreciation_method": "双倍余额递减法",
            "start_date": "2026-07-01",
            "asset_status": "在用"
        }
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()["data"]

    inv = data
    assert inv["invoice_no"] == "FA-INV-COMPLETE"
    assert inv["direction"] == "in"
    assert inv["invoice_type"] == "special"
    assert inv["tax_rate"] == 0.09
    assert inv["amount_without_tax"] == 10000.0
    assert inv["tax_amount"] == 900.0
    assert inv["amount_with_tax"] == 10900.0
    assert inv["counterparty_name"] == "供应商G"
    assert inv["notes"] == "测试完整信息"
    assert inv["related_order_type"] == "fixed_asset"
    assert inv["related_order_id"] is not None

    asset = data["fixed_asset"]
    assert asset["asset_code"] == "FA-COMPLETE"
    assert asset["name"] == "完整设备"
    assert asset["original_value"] == "10900.00"
    assert asset["start_date"] == "2026-07-01"

    assert inv["related_order_id"] == asset["id"]


# ═══════════════════════════════════════════════════════════
# Behavior 6-9: 更新/删除联动
# ═══════════════════════════════════════════════════════════

# ── Behavior 6: 更新发票金额 → 资产原值自动同步（High）──

def test_update_invoice_amount_syncs_asset(client):
    pid = _create_product(client)
    body = {
        "invoice_no": "FA-INV-UPD",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商H",
        "seller_name": "供应商H",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-UPD",
            "asset_name": "待更新设备",
            "useful_life": 60,
            "start_date": "2026-06-19"
        }
    }
    create_resp = client.post("/api/invoices/quick", json=body, headers={"X-Account-ID": "1"})
    assert create_resp.status_code == 200
    cr_data = create_resp.json()["data"]
    asset_id = cr_data["fixed_asset"]["id"]

    update_resp = client.put(f"/api/fixed-assets/{asset_id}/with-invoice", json={
        "original_value": 22600
    }, headers={"X-Account-ID": "1"})
    assert update_resp.status_code == 200

    inv = update_resp.json()["invoice"]
    assert inv["amount_with_tax"] == 22600.0
    assert inv["amount_without_tax"] == 20000.0
    assert inv["tax_amount"] == 2600.0

    asset = update_resp.json()["asset"]
    assert asset["original_value"] == 22600.0


# ── Behavior 7: 删除发票 → 关联资产自动删除（High）──

def test_delete_invoice_cascades_to_asset(client):
    """删除发票时，关联的固定资产自动删除"""
    pid = _create_product(client)
    body = {
        "invoice_no": "FA-INV-DEL",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商I",
        "seller_name": "供应商I",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-DEL",
            "asset_name": "待删除设备",
            "useful_life": 60,
            "start_date": "2026-06-19"
        }
    }
    create_resp = client.post("/api/invoices/quick", json=body, headers={"X-Account-ID": "1"})
    assert create_resp.status_code == 200
    cr_data = create_resp.json()["data"]
    invoice_id = get_entity_id(create_resp.json())
    asset_id = cr_data["fixed_asset"]["id"]

    delete_resp = client.delete(f"/api/invoices/{invoice_id}", headers={"X-Account-ID": "1"})
    assert delete_resp.status_code == 200

    invoice_list = client.get("/api/invoices", headers={"X-Account-ID": "1"})
    assert invoice_list.status_code == 200
    invoices = invoice_list.json()["items"]
    assert not any(inv["id"] == invoice_id for inv in invoices)

    asset_list = client.get("/api/fixed-assets", headers={"X-Account-ID": "1"})
    assert asset_list.status_code == 200
    assets = asset_list.json()["items"]
    assert any(a["id"] == asset_id for a in assets)


# ── Behavior 8: 更新资产原值 → 发票金额自动同步（Medium）──

def test_update_asset_syncs_invoice_amount(client):
    """更新资产原值时，关联发票的含税金额自动同步"""
    pid = _create_product(client)
    body = {
        "invoice_no": "FA-INV-SYNC",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商J",
        "seller_name": "供应商J",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-SYNC",
            "asset_name": "同步设备",
            "useful_life": 60,
            "start_date": "2026-06-19"
        }
    }
    create_resp = client.post("/api/invoices/quick", json=body, headers={"X-Account-ID": "1"})
    assert create_resp.status_code == 200
    cr_data = create_resp.json()["data"]
    asset_id = cr_data["fixed_asset"]["id"]

    update_resp = client.put(f"/api/fixed-assets/{asset_id}/with-invoice", json={
        "original_value": 22600
    }, headers={"X-Account-ID": "1"})
    assert update_resp.status_code == 200

    asset = update_resp.json()["asset"]
    assert asset["original_value"] == 22600.0

    inv = update_resp.json()["invoice"]
    assert inv["amount_with_tax"] == 22600.0
    assert inv["amount_without_tax"] == 20000.0
    assert inv["tax_amount"] == 2600.0


# ── Behavior 9: 删除资产 → 关联发票清空（Low）──

def test_delete_asset_clears_invoice_link(client):
    """删除资产时，关联发票的 related_order_id 和 related_order_type 清空"""
    pid = _create_product(client)
    body = {
        "invoice_no": "FA-INV-CLEAR",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商K",
        "seller_name": "供应商K",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-CLEAR",
            "asset_name": "待清空设备",
            "useful_life": 60,
            "start_date": "2026-06-19"
        }
    }
    create_resp = client.post("/api/invoices/quick", json=body, headers={"X-Account-ID": "1"})
    assert create_resp.status_code == 200
    cr_data = create_resp.json()["data"]
    invoice_id = get_entity_id(create_resp.json())
    asset_id = cr_data["fixed_asset"]["id"]

    delete_resp = client.delete(f"/api/fixed-assets/{asset_id}", headers={"X-Account-ID": "1"})
    assert delete_resp.status_code == 200

    invoice_resp = client.get(f"/api/invoices", headers={"X-Account-ID": "1"})
    assert invoice_resp.status_code == 200
    invoices = invoice_resp.json()["items"]
    inv = next((i for i in invoices if i["id"] == invoice_id), None)
    assert inv is not None
    assert inv["related_order_id"] is None
    assert inv["related_order_type"] is None


# ═══════════════════════════════════════════════════════════
# Behavior 10: 发票金额计算使用 AccountingEngine
# ═══════════════════════════════════════════════════════════

def test_invoice_calculation_uses_accounting_engine(client):
    """验证发票金额计算使用 AccountingEngine，结果与直接调用一致"""
    pid = _create_product(client)
    engine = AccountingEngine()

    expected = engine.calculate_invoice_amounts(
        amount_with_tax=Decimal('11300'),
        tax_rate=Decimal('0.13')
    )

    response = client.post("/api/invoices/quick", json={
        "invoice_no": "FA-INV-ENGINE",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商L",
        "seller_name": "供应商L",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100}],
        "purchase_order_action": "auto_create",
        "fixed_asset": {
            "asset_code": "FA-ENGINE",
            "asset_name": "引擎测试设备",
            "useful_life": 60,
            "start_date": "2026-06-19"
        }
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    inv = response.json()["data"]

    assert Decimal(str(inv["amount_without_tax"])) == expected.amount_without_tax
    assert Decimal(str(inv["tax_amount"])) == expected.tax_amount
    assert Decimal(str(inv["amount_with_tax"])) == expected.amount_with_tax
