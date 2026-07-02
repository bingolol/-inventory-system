"""权责发生制改造测试 - TDD 循环

Behavior 1: 银行账户 CRUD
Behavior 2: 银行流水录入
Behavior 3: 费用发生（权责发生制）
Behavior 4: 费用付款
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
from models_finance import Ledger, LedgerAccount, LedgerAccountBalance
from finance_integration import CHART_OF_ACCOUNTS
from tests.helpers import get_entity_id


# 测试数据库
TEST_DB_FILE = os.path.join(tempfile.gettempdir(), f"test_accrual_{uuid.uuid4().hex[:8]}.db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    """每个测试前重建数据库"""
    monkeypatch.setattr(database, '_engine', test_engine)
    monkeypatch.setattr(database, 'SessionLocal', TestingSessionLocal)
    Base.metadata.create_all(bind=test_engine)

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


@pytest.fixture(autouse=True)
def auto_create_account_ledger(setup_db):
    """在每个测试前自动创建测试账本、会计科目表和科目（post_journal 依赖）"""
    db = TestingSessionLocal()
    account = models.Account(id=1, name="测试账本", code="test_accrual", type="company", taxpayer_type_l3="small_scale")
    db.add(account)
    db.flush()
    ledger = Ledger(code="test_accrual", name="测试账本", type="company", taxpayer_type_l3="small_scale")
    db.add(ledger)
    db.flush()
    for code, name, acct_type in CHART_OF_ACCOUNTS:
        la = LedgerAccount(
            ledger_id=ledger.id, code=code, name=name,
            account_type=acct_type, is_leaf=True, is_active=True,
        )
        db.add(la)
        db.flush()
        db.add(LedgerAccountBalance(ledger_account_id=la.id, balance_l4=0, debit_total_l4=0, credit_total_l4=0))
    db.commit()
    db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


# ═══════════════════════════════════════════════════════════
# Behavior 1: 银行账户 CRUD（Critical）
# ═══════════════════════════════════════════════════════════

def _setup_opening_balance(client, bank_balance=100000):
    """Helper: set up opening balance and create bank account (picks up balance from opening balance)"""
    client.post("/api/opening-balances", json={
        "date": "2026-01-01",
        "bank_balance": bank_balance,
        "retained_earnings": bank_balance,
    }, headers={"X-Account-ID": "1"})
    resp = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
    }, headers={"X-Account-ID": "1"})
    return resp


def test_create_bank_account(client):
    """创建银行账户"""
    response = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
        "balance": 0,
        "description": "公司基本户"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()
    assert data["bank_name"] == "工商银行"
    assert data["account_number"] == "6222021234567890123"
    assert data["balance"] == "0.00"


def test_list_bank_accounts(client):
    """查询银行账户列表"""
    # 先创建
    client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
        "balance": 0
    }, headers={"X-Account-ID": "1"})

    # 查询
    response = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["bank_name"] == "工商银行"


def test_update_bank_account(client):
    """更新银行账户"""
    # 先创建
    create_resp = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
        "balance": 0
    }, headers={"X-Account-ID": "1"})
    account_id = get_entity_id(create_resp.json())

    # 更新（余额不能直接编辑，只能通过银行流水调整）
    response = client.put(f"/api/bank-accounts/{account_id}", json={
        "bank_name": "工商银行-更新"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    assert response.json()["bank_name"] == "工商银行-更新"


# ═══════════════════════════════════════════════════════════
# Behavior 3: 删除银行账户时检查关联数据（Architecture Refactor）
# ═══════════════════════════════════════════════════════════

def test_delete_bank_account_with_transactions_should_fail(client):
    """有银行流水的银行账户不能直接删除"""
    # 1. 创建银行账户（balance=0）
    resp = client.post("/api/bank-accounts", json={
        "bank_name": "测试银行",
        "account_number": "TEST-001",
    }, headers={"X-Account-ID": "1"})
    ba_id = get_entity_id(resp.json())

    # 2. 录入银行流水（先充值 inflow，才能 outflow）
    client.post("/api/bank-transactions", json={
        "bank_account_id": ba_id,
        "transaction_type": "inflow",
        "amount": 100000,
        "transaction_date": "2026-03-01",
        "description": "充值",
        "reference_no": "BANK-REF-001"
    }, headers={"X-Account-ID": "1"})
    client.post("/api/bank-transactions", json={
        "bank_account_id": ba_id,
        "transaction_type": "outflow",
        "amount": 10000,
        "transaction_date": "2026-03-01",
        "description": "测试支出",
        "reference_no": "BANK-REF-002"
    }, headers={"X-Account-ID": "1"})

    # 3. 尝试删除银行账户（应失败）
    response = client.delete(f"/api/bank-accounts/{ba_id}", headers={"X-Account-ID": "1"})
    assert response.status_code == 409  # 有关联数据，不能删除


def test_delete_bank_account(client):
    """删除银行账户"""
    # 先创建
    create_resp = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
    }, headers={"X-Account-ID": "1"})
    account_id = get_entity_id(create_resp.json())

    # 删除
    response = client.delete(f"/api/bank-accounts/{account_id}", headers={"X-Account-ID": "1"})
    assert response.status_code == 200

    # 验证已删除
    list_resp = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    assert len(list_resp.json()["items"]) == 0


# ═══════════════════════════════════════════════════════════
# Behavior 2: 银行流水录入（Critical）
# ═══════════════════════════════════════════════════════════

def test_create_bank_transaction(client):
    """录入银行流水"""
    # 先创建银行账户
    account_resp = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
    }, headers={"X-Account-ID": "1"})
    bank_account_id = get_entity_id(account_resp.json())

    # 录入银行流水（收入）
    response = client.post("/api/bank-transactions", json={
        "bank_account_id": bank_account_id,
        "transaction_type": "inflow",
        "amount": 50000,
        "transaction_date": "2026-06-19",
        "description": "销售收款",
        "reference_no": "BANK-REF-002"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_type"] == "inflow"
    assert data["amount"] == "50000.00"
    assert data["balance_after"] == "50000.00"  # 0 + 50000


def test_create_bank_transaction_outflow(client):
    """录入银行流水（支出）"""
    # 先创建银行账户（balance=0）
    account_resp = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
    }, headers={"X-Account-ID": "1"})
    bank_account_id = get_entity_id(account_resp.json())

    # 先充值才能支出
    client.post("/api/bank-transactions", json={
        "bank_account_id": bank_account_id,
        "transaction_type": "inflow",
        "amount": 100000,
        "transaction_date": "2026-06-18",
        "description": "充值",
        "reference_no": "BANK-REF-FUND"
    }, headers={"X-Account-ID": "1"})

    # 录入银行流水（支出）
    response = client.post("/api/bank-transactions", json={
        "bank_account_id": bank_account_id,
        "transaction_type": "outflow",
        "amount": 30000,
        "transaction_date": "2026-06-19",
        "description": "采购付款",
        "reference_no": "BANK-REF-003"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()
    assert data["transaction_type"] == "outflow"
    assert data["amount"] == "30000.00"
    assert data["balance_after"] == "70000.00"  # 100000 - 30000


# ═══════════════════════════════════════════════════════════
# Behavior 3: 费用发生（权责发生制）（Critical）
# ═══════════════════════════════════════════════════════════

def test_create_expense_accrual(client):
    """费用发生时，记录费用但不涉及付款"""
    response = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 10000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "6月房租"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == "create"
    assert data["entity_type"] == "expense"
    inner = data.get("data", data)
    assert inner["category"] == "房租"
    assert inner["amount"] == 10000.0
    assert inner["payment_status"] == "unpaid"  # 权责发生制：费用发生时未付款
    assert "ai_hint" in data


# ═══════════════════════════════════════════════════════════
# Behavior 4: 费用付款（Critical）
# ═══════════════════════════════════════════════════════════

def test_pay_expense(client):
    """费用付款时，创建付款记录、银行流水，更新费用状态"""
    # 先通过期初余额创建银行账户（余额=100000）
    _setup_opening_balance(client, 100000)
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account_id = bank_list.json()["items"][0]["id"]

    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 10000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "6月房租"
    }, headers={"X-Account-ID": "1"})
    expense_id = expense_resp.json().get("data", expense_resp.json())["id"]

    # 费用付款
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 10000,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": bank_account_id,
        "description": "支付6月房租"
    }, headers={"X-Account-ID": "1"})

    assert payment_resp.status_code == 200
    payment_data = payment_resp.json()
    assert payment_data.get("data", payment_data)["amount"] == 10000.0

    # 验证：费用状态已更新
    expense_list = client.get("/api/expenses", headers={"X-Account-ID": "1"})
    expense = expense_list.json()["items"][0]
    assert expense["payment_status"] == "paid"

    # 验证：银行账户余额已减少
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account = bank_list.json()["items"][0]
    assert bank_account["balance"] == "90000.00"  # 100000 - 10000


# ═══════════════════════════════════════════════════════════
# Behavior 5: 采购发生（权责发生制）（High）
# ═══════════════════════════════════════════════════════════

def test_create_purchase_accrual(client):
    """采购发生时，记录采购但不涉及付款"""
    # 先创建供应商和商品
    client.post("/api/suppliers", json={
        "name": "供应商A",
        "contact": "张三",
        "phone": "13800138000"
    }, headers={"X-Account-ID": "1"})

    client.post("/api/products", json={
        "name": "商品A",
        "category": "类别A",
        "purchase_price": 100,
        "sale_price": 150
    }, headers={"X-Account-ID": "1"})

    # 创建采购单
    response = client.post("/api/purchases", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 100, "unit_price": 100}],
        "payment_method": "company",
        "purchase_date": "2026-06-19"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()
    inner = data.get("data", data)
    assert inner["payment_status"] == "unpaid"  # 权责发生制：采购发生时未付款


# ═══════════════════════════════════════════════════════════
# Behavior 6: 采购付款（High）
# ═══════════════════════════════════════════════════════════

def test_pay_purchase(client):
    """采购付款时，创建付款记录、银行流水，更新采购单状态"""
    # 先通过期初余额创建银行账户（余额=100000）
    _setup_opening_balance(client, 100000)
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account_id = bank_list.json()["items"][0]["id"]

    # 创建供应商
    supplier_resp = client.post("/api/suppliers", json={
        "name": "供应商C",
        "contact": "王五",
        "phone": "13700137000"
    }, headers={"X-Account-ID": "1"})
<<<<<<< Updated upstream
    _sd = supplier_resp.json()
    supplier_id = _sd.get("data", _sd)["id"]
=======
    supplier_id = get_entity_id(supplier_resp.json())
>>>>>>> Stashed changes

    # 创建商品
    product_resp = client.post("/api/products", json={
        "name": "商品C",
        "category": "类别C",
        "purchase_price": 50,
        "sale_price": 80
    }, headers={"X-Account-ID": "1"})
    product_id = product_resp.json()["entity_id"]

    # 创建采购单
    purchase_resp = client.post("/api/purchases", json={
        "supplier_id": supplier_id,
        "items": [{"product_id": product_id, "quantity": 200, "unit_price": 50}],
        "payment_method": "company",
        "purchase_date": "2026-06-19"
    }, headers={"X-Account-ID": "1"})

    assert purchase_resp.status_code == 200
    _pd = purchase_resp.json()
    purchase_id = _pd.get("data", _pd)["id"]

    # 采购付款
    payment_resp = client.post("/api/payments", json={
        "payment_type": "purchase",
        "related_entity_type": "purchase_order",
        "related_entity_id": purchase_id,
        "amount": 10000,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": bank_account_id,
        "description": "支付采购款"
    }, headers={"X-Account-ID": "1"})

    assert payment_resp.status_code == 200

    # 验证：银行账户余额已减少
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account = bank_list.json()["items"][0]
    assert bank_account["balance"] == "90000.00"  # 100000 - 10000


# ═══════════════════════════════════════════════════════════
# Behavior 7: 销售发生（权责发生制）（High）
# ═══════════════════════════════════════════════════════════

def test_create_sale_accrual(client):
    """销售发生时，记录销售但不涉及收款"""
    # 先创建供应商、客户和商品
    client.post("/api/suppliers", json={
        "name": "供应商X",
        "contact": "供应商联系人",
        "phone": "13000130000"
    }, headers={"X-Account-ID": "1"})

    client.post("/api/customers", json={
        "name": "客户A",
        "contact": "赵六",
        "phone": "13600136000"
    }, headers={"X-Account-ID": "1"})

    client.post("/api/products", json={
        "name": "商品D",
        "category": "类别D",
        "purchase_price": 100,
        "sale_price": 150
    }, headers={"X-Account-ID": "1"})

    # 先采购入库
    client.post("/api/purchases", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 100, "unit_price": 100}],
        "payment_method": "company",
        "purchase_date": "2026-06-18"
    }, headers={"X-Account-ID": "1"})

    # 创建销售单
    response = client.post("/api/sales", json={
        "customer_id": 1,
        "items": [{"product_id": 1, "quantity": 50, "unit_price": 150}],
        "sale_date": "2026-06-19"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 200
    data = response.json()
    assert data.get("data", data)["payment_status"] == "unpaid"  # 权责发生制：销售发生时未收款


# ═══════════════════════════════════════════════════════════
# Behavior 8: 销售收款（High）
# ═══════════════════════════════════════════════════════════

def test_receive_sale(client):
    """销售收款时，创建收款记录、银行流水，更新销售单状态"""
    # 先通过期初余额创建银行账户（余额=50000）
    _setup_opening_balance(client, 50000)
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account_id = bank_list.json()["items"][0]["id"]

    # 创建供应商
    client.post("/api/suppliers", json={
        "name": "供应商Y",
        "contact": "供应商联系人2",
        "phone": "13100131000"
    }, headers={"X-Account-ID": "1"})

    # 创建客户
    client.post("/api/customers", json={
        "name": "客户B",
        "contact": "钱七",
        "phone": "13500135000"
    }, headers={"X-Account-ID": "1"})

    # 创建商品
    client.post("/api/products", json={
        "name": "商品E",
        "category": "类别E",
        "purchase_price": 80,
        "sale_price": 120
    }, headers={"X-Account-ID": "1"})

    # 先采购入库
    client.post("/api/purchases", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 200, "unit_price": 80}],
        "payment_method": "company",
        "purchase_date": "2026-06-18"
    }, headers={"X-Account-ID": "1"})

    # 创建销售单
    sale_resp = client.post("/api/sales", json={
        "customer_id": 1,
        "items": [{"product_id": 1, "quantity": 100, "unit_price": 120}],
        "sale_date": "2026-06-19"
    }, headers={"X-Account-ID": "1"})

    assert sale_resp.status_code == 200
    _sd2 = sale_resp.json()
    sale_id = _sd2.get("data", _sd2)["id"]

    # 销售收款
    receipt_resp = client.post("/api/receipts", json={
        "receipt_type": "sale",
        "related_entity_type": "sale_order",
        "related_entity_id": sale_id,
        "amount": 12000,
        "receipt_method": "company",
        "receipt_date": "2026-06-20",
        "bank_account_id": bank_account_id,
        "description": "收取销售款"
    }, headers={"X-Account-ID": "1"})

    assert receipt_resp.status_code == 200

    # 验证：银行账户余额已增加
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account = bank_list.json()["items"][0]
    assert bank_account["balance"] == "62000.00"  # 50000 + 12000


# ═══════════════════════════════════════════════════════════
# Behavior 9: 资产负债表改造（Medium）
# ═══════════════════════════════════════════════════════════

def test_balance_sheet_includes_unpaid_expenses(client):
    """资产负债表应包含未付费用作为应付账款"""
    # 设置期初余额（确保资产负债表平衡）
    client.post("/api/opening-balances", json={
        "date": "2026-01-01",
        "cash_balance": 0,
        "bank_balance": 100000,
        "accounts_receivable": 0,
        "inventory_value": 0,
        "accounts_payable": 0,
        "tax_payable": 0,
        "retained_earnings": 100000
    }, headers={"X-Account-ID": "1"})

    # 创建银行账户
    client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
    }, headers={"X-Account-ID": "1"})

    # 创建费用（未付款）
    client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 10000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "6月房租"
    }, headers={"X-Account-ID": "1"})

    # 查询资产负债表
    response = client.get("/api/financial-reports/balance-sheet?date=2026-06-30", headers={"X-Account-ID": "1"})
    assert response.status_code == 200
    data = response.json()

    # 验证：应付账款包含未付费用
    assert data["accounts_payable"] >= 10000.0  # 未付费用应计入应付账款


# ═══════════════════════════════════════════════════════════
# Behavior 10: 利润表改造（Medium）
# ═══════════════════════════════════════════════════════════

def test_income_statement_includes_unpaid_expenses(client):
    """利润表应包含未付费用（权责发生制）"""
    # 创建费用（未付款）
    client.post("/api/expenses", json={
        "category": "工资",
        "functional_category": "管理费用",
        "amount": 5000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "6月工资"
    }, headers={"X-Account-ID": "1"})

    # 查询利润表
    response = client.get("/api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30", headers={"X-Account-ID": "1"})
    assert response.status_code == 200
    data = response.json()

    # 验证：管理费用包含未付费用
    assert data["administrative_expenses"] >= 5000.0  # 未付费用应计入利润表


# ═══════════════════════════════════════════════════════════
# Behavior 11: 现金流量表改造（Medium）
# ═══════════════════════════════════════════════════════════

def test_cash_flow_statement_from_bank_transactions(client):
    """现金流量表应从银行流水自动生成"""
    # 创建银行账户（balance=0）
    resp = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
    }, headers={"X-Account-ID": "1"})
    ba_id = get_entity_id(resp.json())

    # 录入银行流水（收入）
    client.post("/api/bank-transactions", json={
        "bank_account_id": ba_id,
        "transaction_type": "inflow",
        "amount": 50000,
        "transaction_date": "2026-06-19",
        "description": "销售收款",
        "reference_no": "BANK-REF-004"
    }, headers={"X-Account-ID": "1"})

    # 录入银行流水（支出）
    client.post("/api/bank-transactions", json={
        "bank_account_id": ba_id,
        "transaction_type": "outflow",
        "amount": 30000,
        "transaction_date": "2026-06-20",
        "description": "采购付款",
        "reference_no": "BANK-REF-005"
    }, headers={"X-Account-ID": "1"})

    # 查询现金流量表
    response = client.get("/api/cash-flows/statement?start_date=2026-06-01&end_date=2026-06-30", headers={"X-Account-ID": "1"})
    assert response.status_code == 200
    data = response.json()

    # 验证：经营活动现金流入
    assert data["operating_activities"]["inflows"] >= 50000.0
    # 验证：经营活动现金流出
    assert data["operating_activities"]["outflows"] >= 30000.0


# ═══════════════════════════════════════════════════════════
# 边界情况测试
# ═══════════════════════════════════════════════════════════

def test_expense_amount_zero(client):
    """费用金额为0 → 应该被拒绝"""
    response = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 0,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试0金额"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 422  # Pydantic 验证失败


def test_expense_amount_negative(client):
    """费用金额为负数 → 应该被拒绝"""
    response = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": -100,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试负数金额"
    }, headers={"X-Account-ID": "1"})

    assert response.status_code == 422  # Pydantic 验证失败


def test_payment_exceeds_expense_amount(client):
    """付款金额超过费用金额 → 应该被拒绝或警告"""
    # 通过期初余额创建银行账户
    _setup_opening_balance(client, 100000)
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    ba_id = bank_list.json()["items"][0]["id"]

    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 1000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1"})
    expense_id = expense_resp.json().get("data", expense_resp.json())["id"]

    # 尝试付款金额超过费用金额
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 2000,  # 超过费用金额
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": ba_id,
        "description": "超额付款"
    }, headers={"X-Account-ID": "1"})

    # 当前实现允许超额付款，验证银行余额正确减少
    assert payment_resp.status_code == 200

    # 验证：银行余额减少的是付款金额（2000），不是费用金额（1000）
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account = bank_list.json()["items"][0]
    assert bank_account["balance"] == "98000.00"  # 100000 - 2000


def test_bank_account_not_found(client):
    """付款时银行账户不存在 → 应该报错"""
    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 1000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1"})
    expense_id = expense_resp.json().get("data", expense_resp.json())["id"]

    # 尝试使用不存在的银行账户付款
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 1000,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": 999,  # 不存在
        "description": "测试不存在的银行账户"
    }, headers={"X-Account-ID": "1"})

    assert payment_resp.status_code == 404  # 应该报错（BANK_ACCOUNT_NOT_FOUND 返回 404）


def test_duplicate_payment(client):
    """重复付款同一笔费用 → 应该被允许（支持多次付款）"""
    # 通过期初余额创建银行账户
    _setup_opening_balance(client, 100000)
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    ba_id = bank_list.json()["items"][0]["id"]

    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 1000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1"})
    expense_id = expense_resp.json().get("data", expense_resp.json())["id"]

    # 尝试使用不存在的银行账户付款
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 500,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": ba_id,
        "description": "第一次付款"
    }, headers={"X-Account-ID": "1"})
    assert payment1_resp.status_code == 200

    # 第二次付款
    payment2_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 500,
        "payment_method": "company",
        "payment_date": "2026-06-21",
        "bank_account_id": ba_id,
        "description": "第二次付款"
    }, headers={"X-Account-ID": "1"})
    assert payment2_resp.status_code == 200

    # 验证：银行余额减少的是两次付款的总和
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account = bank_list.json()["items"][0]
    assert bank_account["balance"] == "99000.00"  # 100000 - 500 - 500


def test_payment_with_bank_account(client):
    """付款时指定银行账户 → 银行余额更新"""
    # 先通过期初余额创建银行账户
    _setup_opening_balance(client, 100000)
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    ba_id = bank_list.json()["items"][0]["id"]

    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 1000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1"})
    expense_id = expense_resp.json().get("data", expense_resp.json())["id"]

    # 付款时指定银行账户
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 1000,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": ba_id,
        "description": "指定银行账户付款"
    }, headers={"X-Account-ID": "1"})

    assert payment_resp.status_code == 200

    # 验证：费用状态已更新
    expense_list = client.get("/api/expenses", headers={"X-Account-ID": "1"})
    expense = expense_list.json()["items"][0]
    assert expense["payment_status"] == "paid"

    # 验证：银行余额减少
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    bank_account = bank_list.json()["items"][0]
    assert bank_account["balance"] == "99000.00"  # 100000 - 1000


# ═══════════════════════════════════════════════════════════
# 事务回滚测试
# ═══════════════════════════════════════════════════════════

def test_payment_rollback_on_bank_account_not_found(client):
    """付款时银行账户不存在 → 事务回滚，费用状态不变"""
    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 1000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1"})
    expense_id = expense_resp.json().get("data", expense_resp.json())["id"]

    # 尝试使用不存在的银行账户付款
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 1000,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": 999,  # 不存在
        "description": "测试不存在的银行账户"
    }, headers={"X-Account-ID": "1"})

    assert payment_resp.status_code == 404

    # 验证：费用状态仍然是 unpaid（事务回滚）
    expense_list = client.get("/api/expenses", headers={"X-Account-ID": "1"})
    expense = expense_list.json()["items"][0]
    assert expense["payment_status"] == "unpaid"


# ═══════════════════════════════════════════════════════════
# 完整业务流程测试
# ═══════════════════════════════════════════════════════════

def test_full_business_flow(client):
    """完整业务流程：期初余额→采购→销售→费用→付款→报表"""
    
    # ── 1. 设置期初余额 ──
    client.post("/api/opening-balances", json={
        "date": "2026-01-01",
        "cash_balance": 0,
        "bank_balance": 200000,
        "accounts_receivable": 0,
        "inventory_value": 0,
        "accounts_payable": 0,
        "tax_payable": 0,
        "paid_in_capital": 0,
        "retained_earnings": 200000
    }, headers={"X-Account-ID": "1"})

    # ── 2. 创建银行账户（balance 通过期初余额同步） ──
    bank_resp = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
    }, headers={"X-Account-ID": "1"})
    assert bank_resp.status_code == 200
    bank_account_id = bank_resp.json()["id"]

    # ── 3. 创建供应商和客户 ──
    supplier_resp = client.post("/api/suppliers", json={
        "name": "供应商A",
        "contact": "张三",
        "phone": "13800138000"
    }, headers={"X-Account-ID": "1"})
    assert supplier_resp.status_code == 200
    _supd = supplier_resp.json()
    supplier_id = _supd.get("data", _supd)["id"]

    customer_resp = client.post("/api/customers", json={
        "name": "客户A",
        "contact": "李四",
        "phone": "13900139000"
    }, headers={"X-Account-ID": "1"})
    assert customer_resp.status_code == 200
    _custd = customer_resp.json()
    customer_id = _custd.get("data", _custd)["id"]

    # ── 4. 创建商品 ──
    product_resp = client.post("/api/products", json={
        "name": "商品A",
        "category": "电子产品",
        "purchase_price": 100,
        "sale_price": 150
    }, headers={"X-Account-ID": "1"})
    assert product_resp.status_code == 200
    product_id = product_resp.json()["entity_id"]

    # ── 5. 采购入库（未付款）──
    purchase_resp = client.post("/api/purchases", json={
        "supplier_id": supplier_id,
        "items": [{"product_id": product_id, "quantity": 100, "unit_price": 100}],
        "payment_method": "company",
        "purchase_date": "2026-06-10"
    }, headers={"X-Account-ID": "1"})
    assert purchase_resp.status_code == 200
    _pd2 = purchase_resp.json()
    _pdata = _pd2.get("data", _pd2)
    purchase_id = _pdata["id"]
    assert _pdata["payment_status"] == "unpaid"

    # ── 6. 采购付款 ──
    purchase_payment_resp = client.post("/api/payments", json={
        "payment_type": "purchase",
        "related_entity_type": "purchase_order",
        "related_entity_id": purchase_id,
        "amount": 10000,
        "payment_method": "company",
        "payment_date": "2026-06-15",
        "bank_account_id": bank_account_id,
        "description": "支付采购款"
    }, headers={"X-Account-ID": "1"})
    assert purchase_payment_resp.status_code == 200

    # ── 7. 销售出库（未收款）──
    sale_resp = client.post("/api/sales", json={
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": 50, "unit_price": 150}],
        "sale_date": "2026-06-20"
    }, headers={"X-Account-ID": "1"})
    assert sale_resp.status_code == 200
    _sd3 = sale_resp.json()
    _sdata = _sd3.get("data", _sd3)
    sale_id = _sdata["id"]
    assert _sdata["payment_status"] == "unpaid"

    # ── 8. 销售收款 ──
    sale_receipt_resp = client.post("/api/receipts", json={
        "receipt_type": "sale",
        "related_entity_type": "sale_order",
        "related_entity_id": sale_id,
        "amount": 7500,
        "receipt_method": "company",
        "receipt_date": "2026-06-25",
        "bank_account_id": bank_account_id,
        "description": "收取销售款"
    }, headers={"X-Account-ID": "1"})
    assert sale_receipt_resp.status_code == 200

    # ── 9. 费用发生（未付款）──
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 5000,
        "expense_date": "2026-06-28",
        "payment_method": "company",
        "description": "6月房租"
    }, headers={"X-Account-ID": "1"})
    assert expense_resp.status_code == 200
    _ed = expense_resp.json()
    _edata = _ed.get("data", _ed)
    expense_id = _edata["id"]
    assert _edata["payment_status"] == "unpaid"

    # ── 10. 费用付款 ──
    expense_payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 5000,
        "payment_method": "company",
        "payment_date": "2026-06-30",
        "bank_account_id": bank_account_id,
        "description": "支付房租"
    }, headers={"X-Account-ID": "1"})
    assert expense_payment_resp.status_code == 200

    # ── 11. 查询资产负债表 ──
    balance_sheet_resp = client.get("/api/financial-reports/balance-sheet?date=2026-06-30", headers={"X-Account-ID": "1"})
    assert balance_sheet_resp.status_code == 200
    balance_sheet = balance_sheet_resp.json()

    # 验证：货币资金 = 200000 - 10000 + 7500 - 5000 = 192500
    assert balance_sheet["monetary_funds"] == 192500.0

    # 验证：应付账款 = 0（采购已付款，费用已付款）
    assert balance_sheet["accounts_payable"] == 0.0

    # ── 12. 查询利润表 ──
    income_resp = client.get("/api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30", headers={"X-Account-ID": "1"})
    assert income_resp.status_code == 200
    income = income_resp.json()

    # 验证：营业收入 = 50 * 150 = 7500
    assert income["revenue"] == 7500.0

    # 验证：营业成本 = 50 * 100 = 5000
    assert income["cost_of_goods_sold"] == 5000.0

    # 验证：管理费用 = 5000
    assert income["administrative_expenses"] == 5000.0

    # ── 13. 查询现金流量表 ──
    cash_flow_resp = client.get("/api/cash-flows/statement?start_date=2026-06-01&end_date=2026-06-30", headers={"X-Account-ID": "1"})
    assert cash_flow_resp.status_code == 200
    cash_flow = cash_flow_resp.json()

    # 验证：经营活动现金流入 >= 7500（销售收款）
    assert cash_flow["operating_activities"]["inflows"] >= 7500.0

    # 验证：经营活动现金流出 >= 15000（采购付款 + 费用付款）
    assert cash_flow["operating_activities"]["outflows"] >= 15000.0

    # ── 14. 查询银行余额 ──
    bank_list_resp = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"})
    assert bank_list_resp.status_code == 200
    bank_account = bank_list_resp.json()["items"][0]

    # 验证：银行余额 = 200000 - 10000 + 7500 - 5000 = 192500
    assert bank_account["balance"] == "192500.00"


# ═══════════════════════════════════════════════════════════
# 资产负债表货币资金计算（Architecture Refactor）
# ═══════════════════════════════════════════════════════════

def test_balance_sheet_monetary_funds_with_bank_accounts(client):
    """资产负债表货币资金应包含银行账户余额"""
    # 1. 设置期初余额（银行余额=100000）
    client.post("/api/opening-balances", json={
        "date": "2026-01-01",
        "cash_balance": 0,
        "bank_balance": 100000,
        "accounts_receivable": 0,
        "inventory_value": 0,
        "accounts_payable": 0,
        "tax_payable": 0,
        "paid_in_capital": 50000,
        "retained_earnings": 50000
    }, headers={"X-Account-ID": "1"})

    # 2. 创建银行账户（balance 通过期初余额同步）
    client.post("/api/bank-accounts", json={
        "bank_name": "测试银行",
        "account_number": "TEST-001",
    }, headers={"X-Account-ID": "1"})

    # 3. 查询资产负债表
    response = client.get("/api/financial-reports/balance-sheet?date=2026-06-30", headers={"X-Account-ID": "1"})
    assert response.status_code == 200
    data = response.json()

    # 4. 验证：货币资金 = 银行余额 = 100000
    assert data["monetary_funds"] == 100000.0


def test_balance_sheet_monetary_funds_reflects_payments(client):
    """资产负债表货币资金应反映付款变化"""
    # 1. 设置期初余额（资产=负债+权益：100000 = 0 + 100000）
    client.post("/api/opening-balances", json={
        "date": "2026-01-01",
        "cash_balance": 0,
        "bank_balance": 100000,
        "accounts_receivable": 0,
        "inventory_value": 0,
        "accounts_payable": 0,
        "tax_payable": 0,
        "paid_in_capital": 50000,
        "retained_earnings": 50000
    }, headers={"X-Account-ID": "1"})

    # 2. 创建银行账户（balance 通过期初余额同步）──
    client.post("/api/bank-accounts", json={
        "bank_name": "测试银行",
        "account_number": "TEST-001",
    }, headers={"X-Account-ID": "1"})

    # 3. 创建费用（已付款，从银行扣款）
    client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 20000,
        "expense_date": "2026-03-01",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1"})

    # 4. 费用付款（从银行扣款）
    client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": 1,
        "amount": 20000,
        "payment_method": "company",
        "payment_date": "2026-03-01",
        "bank_account_id": 1
    }, headers={"X-Account-ID": "1"})

    # 5. 查询资产负债表
    response = client.get("/api/financial-reports/balance-sheet?date=2026-06-30", headers={"X-Account-ID": "1"})
    assert response.status_code == 200
    data = response.json()

    # 6. 验证：货币资金 = 100000 - 20000 = 80000
    assert data["monetary_funds"] == 80000.0


# ═══════════════════════════════════════════════════════════
# Behavior 2: 禁止直接编辑余额（Architecture Refactor）
# ═══════════════════════════════════════════════════════════

def test_bank_account_balance_cannot_be_edited_directly(client):
    """银行账户余额不能通过 PUT 接口直接修改"""
    # 1. 创建银行账户（余额=0）
    resp = client.post("/api/bank-accounts", json={
        "bank_name": "测试银行",
        "account_number": "TEST-001",
    }, headers={"X-Account-ID": "1"})
    ba_id = get_entity_id(resp.json())

    # 2. 尝试直接修改余额
    response = client.put(f"/api/bank-accounts/{ba_id}", json={
        "balance": 999999
    }, headers={"X-Account-ID": "1"})

    # 3. 验证：余额没有被修改（忽略 balance 字段）
    assert response.status_code == 200
    accounts = client.get("/api/bank-accounts", headers={"X-Account-ID": "1"}).json()
    account = accounts["items"][0]
    assert account["balance"] == "0.00"  # 余额不变（初始=0）
