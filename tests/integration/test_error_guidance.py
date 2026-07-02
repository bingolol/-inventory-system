"""错误引导和 OperationResult 一致性测试

验证：
1. 所有写操作返回 OperationResult 格式
2. 所有错误返回 ai_instruction
3. 更新/删除操作返回 OperationResult
"""

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


# 测试数据库
TEST_DB_FILE = os.path.join(tempfile.gettempdir(), f"test_error_guidance_{uuid.uuid4().hex[:8]}.db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    """每个测试前重建数据库"""
    monkeypatch.setattr(database, '_engine', test_engine)
    monkeypatch.setattr(database, 'SessionLocal', TestingSessionLocal)
    Base.metadata.create_all(bind=test_engine)

    from factories import ensure_default_account
    _db = TestingSessionLocal()
    try:
        ensure_default_account(_db)
    finally:
        _db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


# ═══════════════════════════════════════════════════════════
# 测试 1: 发票创建失败时返回 ai_instruction
# ═══════════════════════════════════════════════════════════

def test_invoice_duplicate_returns_ai_instruction(client):
    """发票号码重复时，返回结构化错误包含 ai_instruction"""
    # 第一次创建
    client.post("/api/invoices", json={
        "invoice_no": "INV-DUP-001",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_without_tax": 10000,
        "tax_amount": 1300,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商A",
        "issue_date": "2026-06-19"
    }, headers={"X-Account-ID": "1"})

    # 第二次创建（重复发票号）
    response = client.post("/api/invoices", json={
        "invoice_no": "INV-DUP-001",  # 重复
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_without_tax": 5000,
        "tax_amount": 650,
        "amount_with_tax": 5650,
        "counterparty_name": "供应商B",
        "issue_date": "2026-06-20"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 409
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVOICE_DUPLICATE_NUMBER"
    assert "ai_instruction" in data["error"]
    assert "STOP_RETRYING" in data["error"]["ai_instruction"]


# ═══════════════════════════════════════════════════════════
# 测试 2: 发票创建成功返回 OperationResult
# ═══════════════════════════════════════════════════════════

def test_invoice_create_returns_operation_result(client):
    """发票创建成功时，返回 OperationResult 格式"""
    response = client.post("/api/invoices", json={
        "invoice_no": "INV-OR-001",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_without_tax": 10000,
        "tax_amount": 1300,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商A",
        "issue_date": "2026-06-19"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == "create"
    assert data["entity_type"] == "invoice"
    assert "ai_hint" in data


# ═══════════════════════════════════════════════════════════
# 测试 3: 发票更新返回 OperationResult
# ═══════════════════════════════════════════════════════════

def test_invoice_update_returns_operation_result(client):
    """发票更新时，返回 OperationResult 格式"""
    # 先创建
    create_resp = client.post("/api/invoices", json={
        "invoice_no": "INV-UPD-001",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_without_tax": 10000,
        "tax_amount": 1300,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商A",
        "issue_date": "2026-06-19"
    }, headers={"X-Account-ID": "1"})
    invoice_id = create_resp.json()["data"]["id"]

    # 更新
    response = client.put(f"/api/invoices/{invoice_id}", json={
        "notes": "更新备注"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == "update"
    assert data["entity_type"] == "invoice"


# ═══════════════════════════════════════════════════════════
# 测试 4: 发票删除被只读中间件阻止，返回错误引导
# ═══════════════════════════════════════════════════════════

def test_invoice_delete_blocked_by_readonly_middleware(client):
    """发票DELETE被只读中间件拦截，返回403和ai_instruction引导使用红冲"""
    # 先创建
    create_resp = client.post("/api/invoices", json={
        "invoice_no": "INV-DEL-001",
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_without_tax": 10000,
        "tax_amount": 1300,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商A",
        "issue_date": "2026-06-19"
    }, headers={"X-Account-ID": "1"})
    invoice_id = create_resp.json()["data"]["id"]

    # 删除（被只读中间件拦截）
    response = client.delete(f"/api/invoices/{invoice_id}", headers={"X-Account-ID": "1"})

    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "READONLY_DATA"
    assert "reverse" in data["error"]["message"]
    assert "ai_instruction" in data["error"]
    assert "STOP_RETRYING" in data["error"]["ai_instruction"]
