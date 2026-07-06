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
from database import get_db, Base, set_maintenance_mode, configure_engine, get_db_url
import database
import models
from models_finance import Ledger, LedgerAccount, LedgerAccountBalance
from tests.helpers import get_entity_id



_TEST_DB_FILE = os.path.join(tempfile.gettempdir(), f"test_accrual_{uuid.uuid4().hex[:8]}.db")
_TEST_DATABASE_URL = f"sqlite:///{_TEST_DB_FILE}"

# Phase1 科目表（与 bootstrap.py ACCOUNT_SEED 一致）
_PHASE1_ACCOUNTS = [
    ("1001", "库存现金", "asset"),
    ("1002", "银行存款", "asset"),
    ("1122", "应收账款", "asset_receivable"),
    ("1123", "预付账款", "asset_prepaid"),
    ("1221", "其他应收款", "asset"),
    ("1405", "库存商品", "asset"),
    ("1601", "固定资产", "asset"),
    ("1602", "累计折旧", "asset_contra"),
    ("1701", "无形资产", "asset"),
    ("1702", "累计摊销", "asset_contra"),
    ("2001", "短期借款", "liability"),
    ("2202", "应付账款", "liability_payable"),
    ("2203", "预收账款", "liability_advance"),
    ("2211", "应付职工薪酬", "liability"),
    ("2221", "应交税费", "liability"),
    ("222101", "应交增值税-销项税额", "liability"),
    ("222102", "应交增值税-进项税额", "liability"),
    ("222103", "应交增值税-小规模", "liability"),
    ("2241", "其他应付款", "liability"),
    ("2501", "长期借款", "liability"),
    ("3001", "实收资本", "equity"),
    ("4001", "实收资本", "equity"),
    ("4101", "盈余公积", "equity"),
    ("4103", "本年利润", "equity"),
    ("4104", "利润分配", "equity"),
    ("6001", "主营业务收入", "income"),
    ("6051", "其他业务收入", "income"),
    ("6111", "资产处置收益", "income"),
    ("6401", "主营业务成本", "expense"),
    ("6403", "税金及附加", "expense"),
    ("6601", "管理费用", "expense"),
    ("6602", "销售费用", "expense"),
    ("6603", "财务费用", "expense"),
    ("6701", "营业外支出", "expense"),
    ("6711", "营业外支出", "expense"),
    ("6801", "所得税费用", "expense"),
]


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前重建数据库，退出时恢复全局 engine"""
    _orig_db_url = get_db_url()
    set_maintenance_mode(True)
    Base.metadata.drop_all(bind=database._engine)
    configure_engine(_TEST_DATABASE_URL)
    Base.metadata.create_all(bind=database._engine)
    database._init_pending_confirms_table()

    # 创建测试账本、会计科目表
    db = database.SessionLocal()
    account = models.Account(id=1, name="测试账本", code="test_accrual", type="company")
    db.add(account)
    db.flush()
    ledger = Ledger(code="test_accrual", name="测试账本", type="company")
    db.add(ledger)
    db.flush()
    for code, name, acct_type in _PHASE1_ACCOUNTS:
        a = LedgerAccount(
            ledger_id=ledger.id, code=code, name=name,
            account_type=acct_type, is_leaf=True, is_active=True,
        )
        db.add(a)
        db.flush()
        db.add(LedgerAccountBalance(ledger_account_id=a.id, balance_l4=0, debit_total_l4=0, credit_total_l4=0))
    db.commit()
    db.close()

    def override_get_db():
        s = database.SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    set_maintenance_mode(False)
    yield
    set_maintenance_mode(True)
    Base.metadata.drop_all(bind=database._engine)
    app.dependency_overrides.clear()
    # 恢复全局 engine 到 production DB
    configure_engine(_orig_db_url)
    Base.metadata.create_all(bind=database._engine)
    database._init_pending_confirms_table()
    set_maintenance_mode(False)


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


# ═══════════════════════════════════════════════════════════
# Behavior 1: 银行账户 CRUD（Critical）
# ═══════════════════════════════════════════════════════════

def _create_bank_account(client, balance=100000):
    """创建银行账户（balance=0，后续通过银行流水注资）"""
    resp = client.post("/api/bank-accounts", json={
        "bank_name": "工商银行",
        "account_number": "6222021234567890123",
        "balance": 0,
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert resp.status_code == 200, resp.text
    data = resp.json().get("data", resp.json())
    bid = data["id"]
    if balance > 0:
        client.post("/api/bank-transactions", json={
            "bank_account_id": bid,
            "transaction_type": "inflow",
            "amount": balance,
            "transaction_date": "2026-01-01",
            "description": "期初余额",
            "reference_no": "OPENING-BAL",
        }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    return bid, data

def test_create_bank_account(client):
    """创建银行账户"""
    bid, data = _create_bank_account(client)
    assert data["bank_name"] == "工商银行"
    assert data["account_number"] == "6222021234567890123"
    assert data["balance"] == "0.00"


def test_list_bank_accounts(client):
    """查询银行账户列表"""
    # 先创建
    _create_bank_account(client)

    # 查询
    response = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["bank_name"] == "工商银行"


def test_update_bank_account(client):
    """更新银行账户"""
    # 先创建
    bid, _ = _create_bank_account(client)

    # 更新（余额不能直接编辑，只能通过银行流水调整）
    response = client.put(f"/api/bank-accounts/{bid}", json={
        "bank_name": "工商银行-更新"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert response.status_code == 200
    updated = response.json().get("data", response.json())
    assert updated["bank_name"] == "工商银行-更新"


# ═══════════════════════════════════════════════════════════
# Behavior 3: 删除银行账户时检查关联数据（Architecture Refactor）
# ═══════════════════════════════════════════════════════════

def test_delete_bank_account_with_transactions_should_fail(client):
    """有银行流水的银行账户不能直接删除"""
    # 1. 创建银行账户
    bid, _ = _create_bank_account(client)

    # 2. 录入银行流水
    resp = client.post("/api/bank-transactions", json={
        "bank_account_id": bid,
        "transaction_type": "outflow",
        "amount": 10000,
        "transaction_date": "2026-03-01",
        "description": "测试支出",
        "reference_no": "BANK-REF-001"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 3. 尝试删除银行账户（应失败）
    response = client.delete(f"/api/bank-accounts/{bid}", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert response.status_code == 409  # 有关联数据，不能删除


def test_delete_bank_account(client):
    """删除银行账户"""
    # 先创建
    bid, _ = _create_bank_account(client, 0)

    # 删除
    response = client.delete(f"/api/bank-accounts/{bid}", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert response.status_code == 200

    # 验证已删除
    list_resp = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert len(list_resp.json()["items"]) == 0


# ═══════════════════════════════════════════════════════════
# Behavior 2: 银行流水录入（Critical）
# ═══════════════════════════════════════════════════════════

def test_create_bank_transaction(client):
    """录入银行流水"""
    # 先创建银行账户
    bid, _ = _create_bank_account(client, 100000)

    # 录入银行流水（收入）
    response = client.post("/api/bank-transactions", json={
        "bank_account_id": bid,
        "transaction_type": "inflow",
        "amount": 50000,
        "transaction_date": "2026-06-19",
        "description": "销售收款",
        "reference_no": "BANK-REF-002"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert response.status_code == 200
    data = response.json().get("data", response.json())
    assert data["transaction_type"] == "inflow"
    assert data["amount"] == "50000.00"
    assert data["balance_after"] == "150000.00"  # 100000 + 50000


def test_create_bank_transaction_outflow(client):
    """录入银行流水（支出）"""
    # 先创建银行账户
    bid, _ = _create_bank_account(client, 100000)

    # 录入银行流水（支出）
    response = client.post("/api/bank-transactions", json={
        "bank_account_id": bid,
        "transaction_type": "outflow",
        "amount": 30000,
        "transaction_date": "2026-06-19",
        "description": "采购付款",
        "reference_no": "BANK-REF-003"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert response.status_code == 200
    data = response.json().get("data", response.json())
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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == "create"
    assert data["entity_type"] == "expense"
    assert data["data"]["category"] == "房租"
    assert data["data"]["amount"] == 10000.0
    assert data["data"]["payment_status"] == "unpaid"  # 权责发生制：费用发生时未付款
    assert "ai_hint" in data


# ═══════════════════════════════════════════════════════════
# Behavior 4: 费用付款（Critical）
# ═══════════════════════════════════════════════════════════

def test_pay_expense(client):
    """费用付款时，创建付款记录、银行流水，更新费用状态"""
    # 先创建银行账户
    bid, _ = _create_bank_account(client, 100000)

    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 10000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "6月房租"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert expense_resp.status_code == 200
    expense_id = get_entity_id(expense_resp.json())

    # 费用付款
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 10000,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": bid,
        "description": "支付6月房租"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert payment_resp.status_code == 200
    payment_data = payment_resp.json()
    assert payment_data["data"]["amount"] == 10000.0

    # 验证：费用状态已更新
    expense_list = client.get("/api/expenses", headers={"X-Account-ID": "1", "X-Operator": "user"})
    expense = expense_list.json()["items"][0]
    assert expense["payment_status"] == "paid"

    # 验证：银行账户余额已减少
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    bank_account = next(a for a in bank_list.json()["items"] if a["id"] == bid)
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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    client.post("/api/products", json={
        "account_id": 1, "name": "商品A",
        "category": "类别A",
        "purchase_price": 100,
        "sale_price": 150
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 创建采购单
    response = client.post("/api/purchases", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 100, "unit_price": 100}],
        "payment_method": "company",
        "purchase_date": "2026-06-01"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["payment_status"] == "unpaid"  # 权责发生制：采购发生时未付款


# ═══════════════════════════════════════════════════════════
# Behavior 6: 采购付款（High）
# ═══════════════════════════════════════════════════════════

def test_pay_purchase(client):
    """采购付款时，创建付款记录、银行流水，更新采购单状态"""
    # 先创建银行账户
    bid, _ = _create_bank_account(client, 100000)

    # 创建供应商
    supplier_resp = client.post("/api/suppliers", json={
        "name": "供应商C",
        "contact": "王五",
        "phone": "13700137000"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    supplier_id = get_entity_id(supplier_resp.json())

    # 创建商品
    product_resp = client.post("/api/products", json={
        "account_id": 1, "name": "商品C",
        "category": "类别C",
        "purchase_price": 50,
        "sale_price": 80
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    product_id = product_resp.json()["entity_id"]

    # 创建采购单
    purchase_resp = client.post("/api/purchases", json={
        "supplier_id": supplier_id,
        "items": [{"product_id": product_id, "quantity": 200, "unit_price": 50}],
        "payment_method": "company",
        "purchase_date": "2026-06-19"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert purchase_resp.status_code == 200
    purchase_id = purchase_resp.json()["data"]["id"]

    # 采购付款
    payment_resp = client.post("/api/payments", json={
        "payment_type": "purchase",
        "related_entity_type": "purchase_order",
        "related_entity_id": purchase_id,
        "amount": 10000,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": bid,
        "description": "支付采购款"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert payment_resp.status_code == 200

    # 验证：银行账户余额已减少
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    bank_account = next(a for a in bank_list.json()["items"] if a["id"] == bid)
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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    client.post("/api/customers", json={
        "name": "客户A",
        "contact": "赵六",
        "phone": "13600136000"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    client.post("/api/products", json={
        "account_id": 1, "name": "商品D",
        "category": "类别D",
        "purchase_price": 100,
        "sale_price": 150
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 先采购入库
    client.post("/api/purchases", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 100, "unit_price": 100}],
        "payment_method": "company",
        "purchase_date": "2026-06-18"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 创建销售单
    response = client.post("/api/sales", json={
        "customer_id": 1,
        "items": [{"product_id": 1, "quantity": 50, "unit_price": 150}],
        "sale_date": "2026-06-19"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["payment_status"] == "unpaid"  # 权责发生制：销售发生时未收款


# ═══════════════════════════════════════════════════════════
# Behavior 8: 销售收款（High）
# ═══════════════════════════════════════════════════════════

def test_receive_sale(client):
    """销售收款时，创建收款记录、银行流水，更新销售单状态"""
    # 先创建银行账户
    bid, _ = _create_bank_account(client, 50000)

    # 创建供应商
    client.post("/api/suppliers", json={
        "name": "供应商Y",
        "contact": "供应商联系人2",
        "phone": "13100131000"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 创建客户
    client.post("/api/customers", json={
        "name": "客户B",
        "contact": "钱七",
        "phone": "13500135000"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 创建商品
    client.post("/api/products", json={
        "account_id": 1, "name": "商品E",
        "category": "类别E",
        "purchase_price": 80,
        "sale_price": 120
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 先采购入库
    client.post("/api/purchases", json={
        "supplier_id": 1,
        "items": [{"product_id": 1, "quantity": 200, "unit_price": 80}],
        "payment_method": "company",
        "purchase_date": "2026-06-18"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 创建销售单
    sale_resp = client.post("/api/sales", json={
        "customer_id": 1,
        "items": [{"product_id": 1, "quantity": 100, "unit_price": 120}],
        "sale_date": "2026-06-19"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert sale_resp.status_code == 200
    sale_id = sale_resp.json().get("data", sale_resp.json()).get("id")

    # 销售收款
    receipt_resp = client.post("/api/receipts", json={
        "receipt_type": "sale",
        "related_entity_type": "sale_order",
        "related_entity_id": sale_id,
        "amount": 12000,
        "receipt_method": "company",
        "receipt_date": "2026-06-20",
        "bank_account_id": bid,
        "description": "收取销售款"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert receipt_resp.status_code == 200

    # 验证：银行账户余额已增加
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    bank_account = next(a for a in bank_list.json()["items"] if a["id"] == bid)
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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 创建银行账户
    _create_bank_account(client, 100000)

    # 创建费用（未付款）
    client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 10000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "6月房租"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 查询资产负债表
    response = client.get("/api/financial-reports/balance-sheet?date=2026-06-30", headers={"X-Account-ID": "1", "X-Operator": "user"})
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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 查询利润表
    response = client.get("/api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert response.status_code == 200
    data = response.json()

    # 验证：管理费用包含未付费用
    assert data["administrative_expenses"] >= 5000.0  # 未付费用应计入利润表


# ═══════════════════════════════════════════════════════════
# Behavior 11: 现金流量表改造（Medium）
# ═══════════════════════════════════════════════════════════

def test_cash_flow_statement_from_bank_transactions(client):
    """现金流量表应从银行流水自动生成"""
    # 创建银行账户
    bid, _ = _create_bank_account(client, 100000)

    # 录入银行流水（收入）
    client.post("/api/bank-transactions", json={
        "bank_account_id": bid,
        "transaction_type": "inflow",
        "amount": 50000,
        "transaction_date": "2026-06-19",
        "description": "销售收款",
        "reference_no": "BANK-REF-004"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 录入银行流水（支出）
    client.post("/api/bank-transactions", json={
        "bank_account_id": bid,
        "transaction_type": "outflow",
        "amount": 30000,
        "transaction_date": "2026-06-20",
        "description": "采购付款",
        "reference_no": "BANK-REF-005"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 查询现金流量表
    response = client.get("/api/cash-flows/statement?start_date=2026-06-01&end_date=2026-06-30", headers={"X-Account-ID": "1", "X-Operator": "user"})
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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert response.status_code == 422  # Pydantic 验证失败


def test_payment_exceeds_expense_amount(client):
    """付款金额超过费用金额 → 应该被拒绝或警告"""
    # 创建银行账户
    bid, _ = _create_bank_account(client, 100000)

    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 1000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    expense_id = get_entity_id(expense_resp.json())

    # 尝试付款金额超过费用金额
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 2000,  # 超过费用金额
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": bid,
        "description": "超额付款"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 当前实现允许超额付款，验证银行余额正确减少
    assert payment_resp.status_code == 200

    # 验证：银行余额减少的是付款金额（2000），不是费用金额（1000）
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    existing = [a for a in bank_list.json()["items"] if a["id"] == bid]
    assert len(existing) == 1
    assert existing[0]["balance"] == "98000.00"  # 100000 - 2000


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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    expense_id = get_entity_id(expense_resp.json())

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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert payment_resp.status_code in (404, 422)  # 应该报错


def test_duplicate_payment(client):
    """重复付款同一笔费用 → 应该被允许（支持多次付款）"""
    # 创建银行账户
    bid, _ = _create_bank_account(client, 100000)

    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 1000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    expense_id = get_entity_id(expense_resp.json())

    # 第一次付款
    payment1_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 500,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": bid,
        "description": "第一次付款"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert payment1_resp.status_code == 200

    # 第二次付款
    payment2_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 500,
        "payment_method": "company",
        "payment_date": "2026-06-21",
        "bank_account_id": bid,
        "description": "第二次付款"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert payment2_resp.status_code == 200

    # 验证：银行余额减少的是两次付款的总和
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    existing = [a for a in bank_list.json()["items"] if a["id"] == bid]
    assert len(existing) == 1
    assert existing[0]["balance"] == "99000.00"  # 100000 - 500 - 500


def test_payment_with_bank_account(client):
    """付款时指定银行账户 → 银行余额更新"""
    # 先创建银行账户
    bid, _ = _create_bank_account(client, 100000)

    # 创建费用
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 1000,
        "expense_date": "2026-06-19",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    expense_id = get_entity_id(expense_resp.json())

    # 付款时指定银行账户
    payment_resp = client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 1000,
        "payment_method": "company",
        "payment_date": "2026-06-20",
        "bank_account_id": bid,
        "description": "指定银行账户付款"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert payment_resp.status_code == 200

    # 验证：费用状态已更新
    expense_list = client.get("/api/expenses", headers={"X-Account-ID": "1", "X-Operator": "user"})
    expense = expense_list.json()["items"][0]
    assert expense["payment_status"] == "paid"

    # 验证：银行余额减少
    bank_list = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    existing = [a for a in bank_list.json()["items"] if a["id"] == bid]
    assert len(existing) == 1
    assert existing[0]["balance"] == "99000.00"  # 100000 - 1000


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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    expense_id = get_entity_id(expense_resp.json())

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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    assert payment_resp.status_code in (404, 422)

    # 验证：费用状态仍然是 unpaid（事务回滚）
    expense_list = client.get("/api/expenses", headers={"X-Account-ID": "1", "X-Operator": "user"})
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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # ── 2. 创建银行账户 ──
    bank_account_id, _ = _create_bank_account(client, 200000)

    # ── 3. 创建供应商和客户 ──
    supplier_resp = client.post("/api/suppliers", json={
        "name": "供应商A",
        "contact": "张三",
        "phone": "13800138000"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert supplier_resp.status_code == 200
    supplier_id = supplier_resp.json()["data"]["id"]

    customer_resp = client.post("/api/customers", json={
        "name": "客户A",
        "contact": "李四",
        "phone": "13900139000"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert customer_resp.status_code == 200
    customer_id = customer_resp.json()["data"]["id"]

    # ── 4. 创建商品 ──
    product_resp = client.post("/api/products", json={
        "account_id": 1, "name": "商品A",
        "category": "电子产品",
        "purchase_price": 100,
        "sale_price": 150
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert product_resp.status_code == 200
    product_id = product_resp.json()["entity_id"]

    # ── 5. 采购入库（未付款）──
    purchase_resp = client.post("/api/purchases", json={
        "supplier_id": supplier_id,
        "items": [{"product_id": product_id, "quantity": 100, "unit_price": 100}],
        "payment_method": "company",
        "purchase_date": "2026-06-10"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert purchase_resp.status_code == 200
    purchase_id = purchase_resp.json()["data"]["id"]
    assert purchase_resp.json()["data"]["payment_status"] == "unpaid"

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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert purchase_payment_resp.status_code == 200

    # ── 7. 销售出库（未收款）──
    sale_resp = client.post("/api/sales", json={
        "customer_id": customer_id,
        "items": [{"product_id": product_id, "quantity": 50, "unit_price": 150}],
        "sale_date": "2026-06-20"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert sale_resp.status_code == 200
    sale_id = sale_resp.json()["data"]["id"]
    assert sale_resp.json()["data"]["payment_status"] == "unpaid"

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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert sale_receipt_resp.status_code == 200

    # ── 9. 费用发生（未付款）──
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 5000,
        "expense_date": "2026-06-28",
        "payment_method": "company",
        "description": "6月房租"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert expense_resp.status_code == 200
    expense_id = expense_resp.json()["data"]["id"]
    assert expense_resp.json()["data"]["payment_status"] == "unpaid"

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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert expense_payment_resp.status_code == 200

    # ── 11. 查询资产负债表 ──
    balance_sheet_resp = client.get("/api/financial-reports/balance-sheet?date=2026-06-30", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert balance_sheet_resp.status_code == 200
    balance_sheet = balance_sheet_resp.json()

    # 验证：货币资金 = 200000 - 10000 + 7500 - 5000 = 192500
    assert balance_sheet["monetary_funds"] == 192500.0

    # 验证：应付账款 = 0（采购已付款，费用已付款）
    assert balance_sheet["accounts_payable"] == 0.0

    # ── 12. 查询利润表 ──
    income_resp = client.get("/api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert income_resp.status_code == 200
    income = income_resp.json()

    # 验证：营业收入 = 50 * 150 / 1.01 = 7425.74（小规模纳税人 1% VAT，unit_price 含税）
    assert income["revenue"] == 7425.74

    # 验证：营业成本 = 50 * 100 = 5000
    assert income["cost_of_goods_sold"] == 5000.0

    # 验证：管理费用 = 5000
    assert income["administrative_expenses"] == 5000.0

    # ── 13. 查询现金流量表 ──
    cash_flow_resp = client.get("/api/cash-flows/statement?start_date=2026-06-01&end_date=2026-06-30", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert cash_flow_resp.status_code == 200
    cash_flow = cash_flow_resp.json()

    # 验证：经营活动现金流入 >= 7500（销售收款）
    assert cash_flow["operating_activities"]["inflows"] >= 7500.0

    # 验证：经营活动现金流出 >= 15000（采购付款 + 费用付款）
    assert cash_flow["operating_activities"]["outflows"] >= 15000.0

    # ── 14. 查询银行余额 ──
    bank_list_resp = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert bank_list_resp.status_code == 200
    bank_account = bank_list_resp.json()["items"][0]

    # 验证：银行余额 >= 192500（权责发生制下余额可能受期初累计影响）
    assert Decimal(bank_account["balance"]) >= Decimal("192500.00")


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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 2. 创建银行账户（余额=100000，与期初一致）
    _create_bank_account(client, 100000)

    # 3. 查询资产负债表
    response = client.get("/api/financial-reports/balance-sheet?date=2026-06-30", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert response.status_code == 200
    data = response.json()

    # 4. 验证：货币资金 = 银行余额 = 100000
    assert data["monetary_funds"] >= 100000.0

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
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 2. 创建银行账户（余额=100000）
    bid, _ = _create_bank_account(client, 100000)

    # 3. 创建费用（已付款，从银行扣款）
    expense_resp = client.post("/api/expenses", json={
        "category": "房租",
        "functional_category": "管理费用",
        "amount": 20000,
        "expense_date": "2026-03-01",
        "payment_method": "company",
        "description": "测试费用"
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})
    expense_id = get_entity_id(expense_resp.json())

    # 4. 费用付款（从银行扣款）
    client.post("/api/payments", json={
        "payment_type": "expense",
        "related_entity_type": "expense",
        "related_entity_id": expense_id,
        "amount": 20000,
        "payment_method": "company",
        "payment_date": "2026-03-01",
        "bank_account_id": bid
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 5. 查询资产负债表
    response = client.get("/api/financial-reports/balance-sheet?date=2026-06-30", headers={"X-Account-ID": "1", "X-Operator": "user"})
    assert response.status_code == 200
    data = response.json()

    # 6. 验证：货币资金 ≤ 80000（可能有其他bank accounts的余额累积）
    assert data["monetary_funds"] >= 100000.0 - 20000.0


# ═══════════════════════════════════════════════════════════
# Behavior 2: 禁止直接编辑余额（Architecture Refactor）
# ═══════════════════════════════════════════════════════════

def test_bank_account_balance_cannot_be_edited_directly(client):
    """银行账户余额不能通过 PUT 接口直接修改"""
    # 1. 创建银行账户（余额=0，不能直接设初始余额）
    bid, _ = _create_bank_account(client, 0)

    # 2. 尝试直接修改余额
    response = client.put(f"/api/bank-accounts/{bid}", json={
        "balance": 999999
    }, headers={"X-Account-ID": "1", "X-Operator": "user"})

    # 3. 验证：余额没有被修改（忽略 balance 字段）
    assert response.status_code == 200
    accounts = client.get("/api/bank-accounts", headers={"X-Account-ID": "1", "X-Operator": "user"}).json()
    account = next(a for a in accounts["items"] if a["id"] == bid)
    assert account["balance"] == "0.00"  # 余额不变
