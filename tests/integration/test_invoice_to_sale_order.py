"""集成测试：销项发票录入时自动生成销售单

验证：
  1. 销项发票(direction='out')带items创建 → 自动生成销售单，双向关联
  2. 自动生成的销售单 total_price = 发票 amount_with_tax（价税合计）
  3. 自动生成的销售单 tax_amount = 发票 tax_amount（增值税额）
  4. 发票 items 同步到销售单 SaleItem
  5. 缺 items / seller_name / buyer_name → 拒绝创建(422)
  6. 进项发票(direction='in')创建 → 不生成销售单
"""
import pytest
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, init_db
from models import Invoice, SaleOrder, Account, Product, Inventory
from test_helpers import ensure_test_product


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _account_id():
    db = SessionLocal()
    try:
        acc = db.query(Account).first()
        return acc.id if acc else 1
    finally:
        db.close()


def _uniq(prefix):
    return f"{prefix}-{datetime.now().strftime('%H%M%S%f')}"


def _get_product_id():
    """获取测试商品ID（委托给 conftest.ensure_test_product）"""
    return ensure_test_product()


def _base_out_invoice_payload():
    """销项发票基础payload（带items、销方、买方）"""
    pid = _get_product_id()
    return {
        "invoice_no": _uniq("INV-OUT"),
        "direction": "out",
        "invoice_type": "ordinary",
        "amount_with_tax": "1030.00",
        "tax_rate": "0.03",
        "counterparty_name": "测试买方公司",
        "seller_name": "本公司",
        "buyer_name": "测试买方公司",
        "issue_date": "2026-06-15",
        "items": [
            {
                "product_id": pid,
                "quantity": 10,
                "unit_price": "100.00",
                "tax_rate": "0.03"
            }
        ],
        "sale_order_action": "auto_create"
    }


@pytest.mark.integration
class TestInvoiceAutoGenerateSaleOrder:
    """销项发票录入时自动生成销售单"""

    def test_out_invoice_creates_sale_order(self, client):
        """Behavior 1: 销项发票带items创建 → 自动生成销售单，双向关联"""
        aid = _account_id()
        payload = _base_out_invoice_payload()
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        # 发票关联到销售单
        assert data["related_order_type"] == "sale_order"
        assert data["related_order_id"] is not None

        # DB验证：销售单存在
        db = SessionLocal()
        try:
            invoice = db.query(Invoice).filter(Invoice.invoice_no == payload["invoice_no"]).first()
            assert invoice is not None
            assert invoice.related_order_type == "sale_order"
            sale_order = db.query(SaleOrder).filter(SaleOrder.id == invoice.related_order_id).first()
            assert sale_order is not None
        finally:
            db.close()

    def test_out_invoice_sale_order_amounts_match(self, client):
        """Behavior 2+3: 销售单total_price=发票价税合计，tax_amount=发票税额"""
        aid = _account_id()
        payload = _base_out_invoice_payload()
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text

        db = SessionLocal()
        try:
            invoice = db.query(Invoice).filter(Invoice.invoice_no == payload["invoice_no"]).first()
            sale_order = db.query(SaleOrder).filter(SaleOrder.id == invoice.related_order_id).first()
            # total_price = 价税合计
            assert Decimal(str(sale_order.total_price)) == Decimal("1030.00")
            # tax_amount = 发票税额
            assert Decimal(str(sale_order.tax_amount)) == Decimal("30.00")
        finally:
            db.close()

    def test_out_invoice_items_synced_to_sale_order(self, client):
        """Behavior 4: 发票items同步到销售单SaleItem"""
        aid = _account_id()
        payload = _base_out_invoice_payload()
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text

        db = SessionLocal()
        try:
            invoice = db.query(Invoice).filter(Invoice.invoice_no == payload["invoice_no"]).first()
            sale_order = db.query(SaleOrder).filter(SaleOrder.id == invoice.related_order_id).first()
            # 销售单有1个商品行
            assert len(sale_order.items) == 1
            item = sale_order.items[0]
            assert item.product_id == payload["items"][0]["product_id"]
            assert item.quantity == 10
            # 发票商品明细也已保存
            assert len(invoice.items) == 1
            assert invoice.items[0].product_id == payload["items"][0]["product_id"]
        finally:
            db.close()

    def test_out_invoice_missing_items_rejected(self, client):
        """Behavior 5a: 缺items → 拒绝创建(422)"""
        aid = _account_id()
        payload = _base_out_invoice_payload()
        del payload["items"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"缺items应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_missing_seller_name_rejected(self, client):
        """Behavior 5b: 缺seller_name → 拒绝创建(422)"""
        aid = _account_id()
        payload = _base_out_invoice_payload()
        del payload["seller_name"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"缺seller_name应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_missing_buyer_name_rejected(self, client):
        """Behavior 5c: 缺buyer_name → 拒绝创建(422)"""
        aid = _account_id()
        payload = _base_out_invoice_payload()
        del payload["buyer_name"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"缺buyer_name应返回422, 实际{r.status_code}: {r.text}"

    def test_in_invoice_no_sale_order(self, client):
        """Behavior 6: 进项发票创建 → 自动生成采购单（不生成销售单）"""
        aid = _account_id()
        pid = _get_product_id()
        payload = _base_out_invoice_payload()
        payload["direction"] = "in"
        payload["invoice_no"] = _uniq("INV-IN")
        payload["seller_name"] = "测试供应商"
        payload["buyer_name"] = "本公司"
        payload["purchase_order_action"] = "auto_create"
        del payload["sale_order_action"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        # 进项发票不生成销售单，而是生成采购单
        assert data["related_order_type"] == "purchase_order"
        assert data["related_order_id"] is not None

    def test_out_invoice_link_existing_no_new_sale_order(self, client):
        """Behavior 7: 销项发票 sale_order_action=link_existing + related_order_id → 关联已有销售单，不生成新销售单"""
        aid = _account_id()
        pid = _get_product_id()
        # 先手动建一个销售单
        r_sale = client.post("/api/sales", json={
            "customer_id": None,
            "deduct_inventory": True,
            "payment_status": "unpaid",
            "sale_date": "2026-06-10",
            "items": [{"product_id": pid, "quantity": 5, "unit_price": "100.00", "tax_rate": "0.03"}],
        }, headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r_sale.status_code in (200, 201), r_sale.text
        existing_sale_id = r_sale.json().get("data", {}).get("id") or r_sale.json().get("id")

        # 录入发票关联到该销售单
        payload = _base_out_invoice_payload()
        payload["sale_order_action"] = "link_existing"
        payload["related_order_id"] = existing_sale_id
        payload["related_order_type"] = "sale_order"
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        # 关联到已有销售单，不生成新销售单
        assert data["related_order_type"] == "sale_order"
        assert data["related_order_id"] == existing_sale_id

    def test_out_invoice_missing_sale_order_action_rejected(self, client):
        """Behavior 8: 销项发票缺sale_order_action → 拒绝创建(422)"""
        aid = _account_id()
        payload = _base_out_invoice_payload()
        del payload["sale_order_action"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"缺sale_order_action应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_link_existing_missing_related_order_id_rejected(self, client):
        """Behavior 9: sale_order_action=link_existing 但缺related_order_id → 拒绝(422)"""
        aid = _account_id()
        payload = _base_out_invoice_payload()
        payload["sale_order_action"] = "link_existing"
        # 不传 related_order_id
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"link_existing缺related_order_id应返回422, 实际{r.status_code}: {r.text}"
