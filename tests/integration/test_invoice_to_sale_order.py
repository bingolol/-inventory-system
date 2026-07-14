"""集成测试：销项发票录入时自动生成销售单

验证：
  1. 销项发票(direction='out')带items创建 → 自动生成销售单，双向关联
  2. 自动生成的销售单 total_price = 发票 amount_with_tax（价税合计）
  3. 自动生成的销售单 tax_amount = 发票 tax_amount（增值税额）
  4. 发票 items 同步到销售单 SaleItem
  5. 缺 items / seller_name / buyer_name → 拒绝创建(422)
  6. 进项发票(direction='in')创建 → 不生成销售单
"""
import uuid
import pytest
from datetime import datetime
from decimal import Decimal
from database import SessionLocal
from models import Invoice, SaleOrder
from test_helpers import ensure_test_product
from helpers import get_account_id


_INV_COUNTER = 0

def _next_inv_no():
    """生成唯一发票号（进程内计数器 + uuid，避免共享 DB 冲突）"""
    global _INV_COUNTER
    _INV_COUNTER += 1
    return f"INV-OUT-{uuid.uuid4().hex[:8]}-{_INV_COUNTER}"


def _base_out_invoice_payload():
    """销项发票基础payload（带items、销方、买方）"""
    pid = ensure_test_product()
    return {
        "invoice_no": _next_inv_no(),
        "direction": "out",
        "invoice_type": "ordinary",
        "amount_with_tax": "1030.00",
        "tax_rate": "0.03",
        "tax_amount": "30.00",
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
        aid = get_account_id()
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
        aid = get_account_id()
        payload = _base_out_invoice_payload()
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text

        db = SessionLocal()
        try:
            invoice = db.query(Invoice).filter(Invoice.invoice_no == payload["invoice_no"]).first()
            sale_order = db.query(SaleOrder).filter(SaleOrder.id == invoice.related_order_id).first()
            # total_price = 价税合计
            assert Decimal(str(sale_order.total_price_l1)) == Decimal("1030.00")
            # tax_amount = 发票税额
            assert Decimal(str(sale_order.tax_amount_l1)) == Decimal("30.00")
        finally:
            db.close()

    def test_out_invoice_items_synced_to_sale_order(self, client):
        """Behavior 4: 发票items同步到销售单SaleItem"""
        aid = get_account_id()
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
            assert item.quantity_l1 == 10
            # 发票商品明细也已保存
            assert len(invoice.items) == 1
            assert invoice.items[0].product_id == payload["items"][0]["product_id"]
        finally:
            db.close()

    def test_out_invoice_missing_items_rejected(self, client):
        """Behavior 5a: 缺items → 拒绝创建(422)"""
        aid = get_account_id()
        payload = _base_out_invoice_payload()
        del payload["items"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"缺items应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_missing_seller_name_rejected(self, client):
        """Behavior 5b: 缺seller_name → 拒绝创建(422)"""
        aid = get_account_id()
        payload = _base_out_invoice_payload()
        del payload["seller_name"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"缺seller_name应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_missing_buyer_name_rejected(self, client):
        """Behavior 5c: 缺buyer_name → 拒绝创建(422)"""
        aid = get_account_id()
        payload = _base_out_invoice_payload()
        del payload["buyer_name"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"缺buyer_name应返回422, 实际{r.status_code}: {r.text}"

    def test_in_invoice_no_sale_order(self, client):
        """Behavior 6: 进项发票创建 → 自动生成采购单（不生成销售单）"""
        aid = get_account_id()
        pid = ensure_test_product()
        payload = _base_out_invoice_payload()
        payload["direction"] = "in"
        payload["invoice_no"] = _next_inv_no().replace("OUT", "IN")
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
        aid = get_account_id()
        pid = ensure_test_product()
        # 先通过发票驱动自动生成一个销售单（POST /api/sales 已停用）
        first_payload = _base_out_invoice_payload()
        r_first = client.post("/api/invoices/quick", json=first_payload,
                              headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r_first.status_code == 200, r_first.text
        existing_sale_id = r_first.json()["data"]["related_order_id"]
        assert existing_sale_id is not None

        # 录入第二张发票关联到该销售单
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
        aid = get_account_id()
        payload = _base_out_invoice_payload()
        del payload["sale_order_action"]
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"缺sale_order_action应返回422, 实际{r.status_code}: {r.text}"

    def test_out_invoice_link_existing_missing_related_order_id_rejected(self, client):
        """Behavior 9: sale_order_action=link_existing 但缺related_order_id → 拒绝(422)"""
        aid = get_account_id()
        payload = _base_out_invoice_payload()
        payload["sale_order_action"] = "link_existing"
        # 不传 related_order_id
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 422, f"link_existing缺related_order_id应返回422, 实际{r.status_code}: {r.text}"
