"""P1 会计恒等式测试：资产 = 负债 + 权益"""

import sys, os, pytest, tempfile, uuid
from decimal import Decimal
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import get_db, Base, init_db
import database

# ── 每个测试文件使用独立的临时数据库 ──
TEST_DB = os.path.join(tempfile.gettempdir(), f"test_acct_{uuid.uuid4().hex[:8]}.db")
TEST_DB_URL = f"sqlite:///{TEST_DB}"
_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setattr(database, '_engine', _engine)
    monkeypatch.setattr(database, 'SessionLocal', _SessionLocal)
    Base.metadata.create_all(bind=_engine)
    init_db()

    from factories import ensure_default_account
    _db = _SessionLocal()
    try:
        ensure_default_account(_db)
    finally:
        _db.close()

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


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID)}
TODAY = "2026-06-24"


class TestAccountingEquation:
    """会计恒等式：资产 = 负债 + 权益"""

    def _bs(self, client):
        resp = client.get(f"/api/financial-reports/balance-sheet?date={TODAY}", headers=HEADERS)
        assert resp.status_code == 200, resp.text
        return resp.json()

    def test_opening_balance_balanced(self, client):
        """期初余额：现金 50000 = 实收资本 50000"""
        resp = client.post("/api/opening-balances", json={
            "date": "2026-06-01", "cash_balance": 50000, "paid_in_capital": 50000,
        }, headers=HEADERS)
        assert resp.status_code == 200

        bs = self._bs(client)
        assert bs["total_assets"] == bs["total_liabilities_and_equity"]

    def test_purchase_keeps_balanced(self, client):
        """采购入库后仍平衡：库存↑ + 应付↑"""
        client.post("/api/opening-balances", json={
            "date": "2026-06-01", "cash_balance": 50000, "paid_in_capital": 50000,
        }, headers=HEADERS)

        # 创建商品
        resp = client.post("/api/products", json={
            "name": "测试商品", "sku": "ACCT-001",
            "purchase_price": 10, "sale_price": 20,
        }, headers=HEADERS)
        pid = resp.json()["entity_id"]

        # 创建采购单（发票驱动：小规模纳税人 tax_rate=0, tax_amount=0, amount_with_tax=不含税合计）
        # 不含税合计 = 10 * 10 = 100
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-IN-PUR-{pid}",
            "direction": "in",
            "invoice_type": "ordinary",
            "amount_with_tax": "100.00",
            "tax_rate": "0",
            "tax_amount": "0.00",
            "counterparty_name": "测试供应商",
            "seller_name": "测试供应商",
            "buyer_name": "本公司",
            "issue_date": TODAY,
            "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 10, "unit_price": "10.00", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200, resp.text

        bs = self._bs(client)
        assert bs["total_assets"] == bs["total_liabilities_and_equity"]

    def test_sale_keeps_balanced(self, client):
        """销售出库后仍平衡：库存↓ + 收入↑"""
        client.post("/api/opening-balances", json={
            "date": "2026-06-01", "cash_balance": 50000, "paid_in_capital": 50000,
        }, headers=HEADERS)

        resp = client.post("/api/products", json={
            "name": "测试商品", "sku": "ACCT-002",
            "purchase_price": 10, "sale_price": 20,
        }, headers=HEADERS)
        pid = resp.json()["entity_id"]

        # 采购入库（发票驱动：小规模纳税人 tax_rate=0, tax_amount=0, amount_with_tax=不含税合计）
        # 不含税合计 = 20 * 10 = 200
        client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-IN-SALE-{pid}",
            "direction": "in",
            "invoice_type": "ordinary",
            "amount_with_tax": "200.00",
            "tax_rate": "0",
            "tax_amount": "0.00",
            "counterparty_name": "测试供应商",
            "seller_name": "测试供应商",
            "buyer_name": "本公司",
            "issue_date": TODAY,
            "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 20, "unit_price": "10.00", "tax_rate": "0"}],
        }, headers=HEADERS)

        # 销售出库（发票驱动：小规模纳税人 tax_rate=0, tax_amount=0, amount_with_tax=不含税合计）
        # 不含税合计 = 5 * 20 = 100
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-OUT-SALE-{pid}",
            "direction": "out",
            "invoice_type": "ordinary",
            "amount_with_tax": "100.00",
            "tax_rate": "0",
            "tax_amount": "0.00",
            "counterparty_name": "测试客户",
            "seller_name": "本公司",
            "buyer_name": "测试客户",
            "issue_date": "2026-06-24",
            "sale_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 5, "unit_price": "20.00", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code == 200, resp.text

        bs = self._bs(client)
        assert bs["total_assets"] == bs["total_liabilities_and_equity"]

    def test_expense_keeps_balanced(self, client):
        """费用记录后仍平衡"""
        client.post("/api/opening-balances", json={
            "date": "2026-06-01", "cash_balance": 50000, "paid_in_capital": 50000,
        }, headers=HEADERS)

        resp = client.post("/api/expenses", json={
            "expense_date": "2026-06-24",
            "category": "办公用品",
            "amount": 500,
            "payment_method": "company",
        }, headers=HEADERS)
        assert resp.status_code == 200

        bs = self._bs(client)
        assert bs["total_assets"] == bs["total_liabilities_and_equity"]

    def test_multi_transaction_balanced(self, client):
        """多笔交易后仍平衡"""
        client.post("/api/opening-balances", json={
            "date": "2026-06-01", "cash_balance": 50000, "paid_in_capital": 50000,
        }, headers=HEADERS)

        # 商品 x 2
        r1 = client.post("/api/products", json={
            "name": "商品A", "sku": "A-001", "purchase_price": 10, "sale_price": 20,
        }, headers=HEADERS)
        r2 = client.post("/api/products", json={
            "name": "商品B", "sku": "B-001", "purchase_price": 50, "sale_price": 100,
        }, headers=HEADERS)
        pid1, pid2 = r1.json()["entity_id"], r2.json()["entity_id"]

        # 采购两批（发票驱动：小规模纳税人 tax_rate=0, tax_amount=0, amount_with_tax=不含税合计）
        # 采购1: 10 * 10 = 100
        client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-IN-MULTI1-{pid1}",
            "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": "100.00", "tax_rate": "0", "tax_amount": "0.00",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": TODAY, "purchase_order_action": "auto_create",
            "items": [{"product_id": pid1, "quantity": 10, "unit_price": "10.00", "tax_rate": "0"}],
        }, headers=HEADERS)
        # 采购2: 5 * 50 = 250
        client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-IN-MULTI2-{pid2}",
            "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": "250.00", "tax_rate": "0", "tax_amount": "0.00",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": TODAY, "purchase_order_action": "auto_create",
            "items": [{"product_id": pid2, "quantity": 5, "unit_price": "50.00", "tax_rate": "0"}],
        }, headers=HEADERS)

        # 销售（发票驱动：小规模纳税人 tax_rate=0, tax_amount=0, amount_with_tax=不含税合计）
        # 销售: 3 * 20 = 60
        client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-OUT-MULTI-{pid1}",
            "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "60.00", "tax_rate": "0", "tax_amount": "0.00",
            "counterparty_name": "测试客户", "seller_name": "本公司", "buyer_name": "测试客户",
            "issue_date": "2026-06-24", "sale_order_action": "auto_create",
            "items": [{"product_id": pid1, "quantity": 3, "unit_price": "20.00", "tax_rate": "0"}],
        }, headers=HEADERS)

        # 费用
        client.post("/api/expenses", json={
            "expense_date": "2026-06-24", "category": "办公用品",
            "amount": 200, "payment_method": "company",
        }, headers=HEADERS)

        bs = self._bs(client)
        assert bs["total_assets"] == bs["total_liabilities_and_equity"]
