"""集成测试：采购单 API (routers/purchases.py)"""
import uuid
import pytest
from decimal import Decimal
from helpers import get_account_id, get_entity_id, extract_data
from factories import api_create_product, api_create_supplier

from helpers import make_headers

HEADERS = make_headers()


_PUR_INV_COUNTER = 0


def _next_purchase_inv_no():
    """生成唯一进项发票号（进程内计数器 + uuid，避免冲突）"""
    global _PUR_INV_COUNTER
    _PUR_INV_COUNTER += 1
    return f"INV-IN-{uuid.uuid4().hex[:8]}-{_PUR_INV_COUNTER}"


def _create_purchase_via_invoice(client, headers, supplier_name, product_id,
                                 qty, unit_price, tax_rate, business_date="2026-06-01"):
    """通过 POST /api/invoices/quick (direction=in, purchase_order_action=auto_create)
    创建发票驱动自动生成采购单，返回采购单 ID。

    unit_price 视为不含税单价，据此计算 tax_amount / amount_with_tax。
    """
    unit_price_d = Decimal(str(unit_price))
    tax_rate_d = Decimal(str(tax_rate))
    amount_without_tax = (unit_price_d * qty).quantize(Decimal("0.01"))
    tax_amount = (amount_without_tax * tax_rate_d).quantize(Decimal("0.01"))
    amount_with_tax = (amount_without_tax + tax_amount).quantize(Decimal("0.01"))

    resp = client.post("/api/invoices/quick", json={
        "invoice_no": _next_purchase_inv_no(),
        "direction": "in",
        "invoice_type": "ordinary",
        "amount_with_tax": str(amount_with_tax),
        "tax_amount": str(tax_amount),
        "tax_rate": str(tax_rate_d),
        "counterparty_name": supplier_name,
        "seller_name": supplier_name,
        "buyer_name": "本公司",
        "issue_date": business_date,
        "items": [{"product_id": product_id, "quantity": qty,
                   "unit_price": str(unit_price_d), "tax_rate": str(tax_rate_d)}],
        "purchase_order_action": "auto_create",
    }, headers=headers)
    assert resp.status_code in (200, 201), f"通过发票创建采购单失败: {resp.text}"
    data = extract_data(resp.json())
    purchase_id = data.get("related_order_id")
    assert purchase_id is not None, f"发票未生成采购单: {resp.text}"
    return purchase_id, resp.json()


def _supplier_name(sjson):
    """从 api_create_supplier 返回的响应中提取供应商名称"""
    data = extract_data(sjson)
    return data.get("name") if isinstance(data, dict) else "测试供应商"


class TestListPurchases:
    def test_list_default(self, client):
        resp = client.get("/api/purchases", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data

    def test_list_with_filters(self, client):
        resp = client.get("/api/purchases?status=completed&start_date=2026-01-01&end_date=2026-12-31", headers=HEADERS)
        assert resp.status_code == 200

    def test_list_pagination(self, client):
        resp = client.get("/api/purchases?page=1&page_size=10", headers=HEADERS)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 10


class TestGetPurchase:
    def test_get_not_found(self, client):
        resp = client.get("/api/purchases/99999", headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_get_created_purchase(self, client):
        sid, sjson = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        purchase_id, _ = _create_purchase_via_invoice(
            client, HEADERS, _supplier_name(sjson), pid, qty=5, unit_price=10, tax_rate=0.13)
        resp2 = client.get(f"/api/purchases/{purchase_id}", headers=HEADERS)
        assert resp2.status_code == 200


class TestCreatePurchase:
    def test_create_success(self, client):
        sid, sjson = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        _, resp_json = _create_purchase_via_invoice(
            client, HEADERS, _supplier_name(sjson), pid, qty=3, unit_price=15, tax_rate=0.13)
        data = resp_json
        assert get_entity_id(data) is not None


class TestUpdatePurchase:
    def test_update_status_to_cancelled(self, client):
        sid, sjson = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        purchase_id, _ = _create_purchase_via_invoice(
            client, HEADERS, _supplier_name(sjson), pid, qty=2, unit_price=10, tax_rate=0.13)
        resp2 = client.put(f"/api/purchases/{purchase_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp2.status_code == 200

    def test_update_not_found(self, client):
        resp = client.put("/api/purchases/99999", json={"notes": "测试"}, headers=HEADERS)
        assert resp.status_code in (400, 404)


class TestCancelPurchase:
    def test_cancel_not_found(self, client):
        resp = client.post("/api/purchases/99999/cancel", headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_cancel_success(self, client):
        sid, sjson = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        purchase_id, _ = _create_purchase_via_invoice(
            client, HEADERS, _supplier_name(sjson), pid, qty=1, unit_price=10, tax_rate=0.13)
        resp2 = client.post(f"/api/purchases/{purchase_id}/cancel", headers=HEADERS)
        assert resp2.status_code == 200


class TestDeletePurchase:
    def test_delete_not_found(self, client):
        resp = client.delete("/api/purchases/99999", headers=HEADERS)
        assert resp.status_code == 403

    def test_delete_with_items_blocked(self, client):
        sid, sjson = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        purchase_id, _ = _create_purchase_via_invoice(
            client, HEADERS, _supplier_name(sjson), pid, qty=1, unit_price=10, tax_rate=0.13)
        resp2 = client.delete(f"/api/purchases/{purchase_id}", headers=HEADERS)
        assert resp2.status_code == 403
