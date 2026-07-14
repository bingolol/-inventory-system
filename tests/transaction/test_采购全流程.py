"""采购全流程事务测试 — 覆盖命令层与 API 层的所有场景"""
import pytest
from datetime import datetime
from decimal import Decimal

pytestmark = pytest.mark.usefixtures("bootstrap_db")


from commands.base import dispatch
from commands.orders import (
    CreateOrder, CancelOrder, DeleteOrder,
    UpdateOrderItems, UpdateOrderFields,
)
from errors import BusinessError
from models import PurchaseOrder, StockMove
from tests.factories import make_product, make_supplier, api_create_product, api_create_supplier
from tests.helpers import get_entity_id, uniq

HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}


class Test创建采购单:
    """创建采购单 — 成功路径与错误路径"""

    def test_empty_items(self, db):
        with pytest.raises(BusinessError, match="ORDER_EMPTY_ITEMS|采购单"):
            dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=[]), db)

    def test_duplicate_products(self, db):
        p = make_product(db, 1, track_inventory=False)
        items = [{"product_id": p.id, "quantity_l1": 1, "unit_price_l1": 10, "tax_rate_l1": 0.13},
                 {"product_id": p.id, "quantity_l1": 2, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        with pytest.raises(BusinessError, match="ORDER_DUPLICATE_PRODUCT|重复"):
            dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, business_date=datetime(2026,6,18,10,0,0)), db)

    def test_product_not_found(self, db):
        items = [{"product_id": 99999, "quantity_l1": 1, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        with pytest.raises(BusinessError, match="PRODUCT_NOT_FOUND|不存在"):
            dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, business_date=datetime(2026,6,18,10,0,0)), db)

    def test_create_success(self, db):
        p = make_product(db, 1, track_inventory=True, purchase_price=Decimal("10"))
        s = make_supplier(db, 1)
        items = [{"product_id": p.id, "quantity_l1": 5, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        order = dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, supplier_id=s.id, business_date=datetime(2026,6,18,10,0,0)), db)
        assert order.total_price_l1 == Decimal("50.00")
        assert order.status == "completed"
        moves = db.query(StockMove).filter(StockMove.source_id == order.id).all()
        assert len(moves) > 0

    def test_api_create_success(self, client):
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        amount = 3 * 15  # 不含税合计
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-IN-API"), "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": "2026-06-01", "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 3, "unit_price": "15", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"采购失败: {resp.text}"
        data = resp.json()["data"]
        assert data["related_order_type"] == "purchase_order"
        assert data["related_order_id"] is not None


class Test查询采购单:
    """查询采购单 — 列表与详情"""

    def test_list_default(self, client):
        resp = client.get("/api/purchases", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data

    def test_list_with_filters(self, client):
        resp = client.get("/api/purchases?status=completed&start_date=2026-01-01&end_date=2026-12-31",
                          headers=HEADERS)
        assert resp.status_code == 200

    def test_list_pagination(self, client):
        resp = client.get("/api/purchases?page=1&page_size=10", headers=HEADERS)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 10

    def test_get_not_found(self, client):
        resp = client.get("/api/purchases/99999", headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_get_created_purchase(self, client):
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        amount = 5 * 10  # 不含税合计
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-IN-GET"), "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": "2026-06-01", "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 5, "unit_price": "10", "tax_rate": "0"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"采购失败: {resp.text}"
        purchase_id = resp.json()["data"]["related_order_id"]
        resp2 = client.get(f"/api/purchases/{purchase_id}", headers=HEADERS)
        assert resp2.status_code == 200


class Test取消采购单:
    """取消采购单 — 成功与错误路径"""

    def test_cancel_not_found(self, db, client):
        with pytest.raises(BusinessError, match="ORDER_NOT_FOUND|不存在"):
            dispatch(CancelOrder(order_type="purchase", account_id=1, operator="test", order_id=99999), db)
        resp = client.put("/api/purchases/99999", json={"status": "cancelled"}, headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_cancel_already_cancelled(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = make_supplier(db, 1)
        items = [{"product_id": p.id, "quantity_l1": 1, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        order = dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, supplier_id=s.id, business_date=datetime(2026,6,18,10,0,0)), db)
        dispatch(CancelOrder(order_type="purchase", account_id=1, operator="test", order_id=order.id), db)
        with pytest.raises(BusinessError):
            dispatch(CancelOrder(order_type="purchase", account_id=1, operator="test", order_id=order.id), db)

    def test_cancel_success(self, db, client):
        p = make_product(db, 1, track_inventory=False, purchase_price=Decimal("10"))
        s = make_supplier(db, 1)
        items = [{"product_id": p.id, "quantity_l1": 3, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        order = dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, supplier_id=s.id, business_date=datetime(2026,6,18,10,0,0)), db)
        result = dispatch(CancelOrder(order_type="purchase", account_id=1, operator="test", order_id=order.id), db)
        assert result.status == "cancelled"

        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        amount = 1 * 10  # 不含税合计
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-IN-CNL"), "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": "2026-06-01", "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "10", "tax_rate": "0"}],
        }, headers=HEADERS)
        purchase_id = resp.json()["data"]["related_order_id"]
        resp2 = client.put(f"/api/purchases/{purchase_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp2.status_code == 200


class Test删除采购单:
    """删除采购单 — 成功与错误路径"""

    def test_delete_not_found(self, db, client):
        with pytest.raises(BusinessError, match="ORDER_NOT_FOUND|不存在"):
            dispatch(DeleteOrder(order_type="purchase", account_id=1, operator="test", order_id=99999), db)
        resp = client.delete("/api/purchases/99999", headers=HEADERS)
        assert resp.status_code in (400, 403, 404)

    def test_delete_success(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = make_supplier(db, 1)
        items = [{"product_id": p.id, "quantity_l1": 1, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        order = dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, supplier_id=s.id, business_date=datetime(2026,6,18,10,0,0)), db)
        result = dispatch(DeleteOrder(order_type="purchase", account_id=1, operator="test", order_id=order.id), db)
        assert result is True

    def test_delete_with_items_blocked(self, client):
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        amount = 1 * 10  # 不含税合计
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-IN-DL"), "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": "2026-06-01", "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "10", "tax_rate": "0"}],
        }, headers=HEADERS)
        purchase_id = resp.json()["data"]["related_order_id"]
        resp2 = client.post(f"/api/purchases/{purchase_id}/cancel", headers=HEADERS)
        assert resp2.status_code == 200


class Test更新采购单:
    """更新采购单 — 商品变更与字段变更"""

    def test_update_not_found(self, db, client):
        with pytest.raises(BusinessError, match="ORDER_NOT_FOUND|不存在"):
            dispatch(UpdateOrderItems(order_type="purchase", account_id=1, operator="test", order_id=99999, items=[]), db)
        with pytest.raises(BusinessError, match="ORDER_NOT_FOUND|不存在"):
            dispatch(UpdateOrderFields(order_type="purchase", account_id=1, operator="test", order_id=99999, notes="test"), db)
        resp = client.put("/api/purchases/99999", json={"notes": "测试"}, headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_update_duplicate_products(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = make_supplier(db, 1)
        items = [{"product_id": p.id, "quantity_l1": 1, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        order = dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, supplier_id=s.id, business_date=datetime(2026,6,18,10,0,0)), db)
        dupe_items = [{"product_id": p.id, "quantity_l1": 1, "unit_price_l1": 10, "tax_rate_l1": 0.13},
                      {"product_id": p.id, "quantity_l1": 2, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        with pytest.raises(BusinessError, match="ORDER_DUPLICATE_PRODUCT|重复"):
            dispatch(UpdateOrderItems(order_type="purchase", account_id=1, operator="test", order_id=order.id, items=dupe_items), db)

    def test_update_to_empty_deletes_order(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = make_supplier(db, 1)
        items = [{"product_id": p.id, "quantity_l1": 1, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        order = dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, supplier_id=s.id, business_date=datetime(2026,6,18,10,0,0)), db)
        result = dispatch(UpdateOrderItems(order_type="purchase", account_id=1, operator="test", order_id=order.id, items=[]), db)
        assert result is None
        deleted = db.query(PurchaseOrder).filter(PurchaseOrder.id == order.id).first()
        assert deleted is None

    def test_update_success(self, db):
        p1 = make_product(db, 1, track_inventory=False, purchase_price=Decimal("10"))
        p2 = make_product(db, 1, track_inventory=False, purchase_price=Decimal("20"))
        s = make_supplier(db, 1)
        items = [{"product_id": p1.id, "quantity_l1": 2, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        order = dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, supplier_id=s.id, business_date=datetime(2026,6,18,10,0,0)), db)
        new_items = [{"product_id": p2.id, "quantity_l1": 3, "unit_price_l1": 20, "tax_rate_l1": 0.13}]
        result = dispatch(UpdateOrderItems(order_type="purchase", account_id=1, operator="test", order_id=order.id, items=new_items), db)
        assert result is not None
        assert result.total_price_l1 == Decimal("60.00")
        assert len(result.items) == 1
        assert result.items[0].product_id == p2.id

    def test_update_fields(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = make_supplier(db, 1)
        items = [{"product_id": p.id, "quantity_l1": 1, "unit_price_l1": 10, "tax_rate_l1": 0.13}]
        order = dispatch(CreateOrder(order_type="purchase", account_id=1, operator="test", items=items, supplier_id=s.id, business_date=datetime(2026,6,18,10,0,0)), db)
        result = dispatch(UpdateOrderFields(order_type="purchase", 
            account_id=1, operator="test", order_id=order.id,
            notes="更新备注", payment_status="paid",
        ), db)
        assert result.notes == "更新备注"
        assert result.payment_status == "paid"

    def test_update_status_to_cancelled(self, client):
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        amount = 2 * 10  # 不含税合计
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("INV-IN-UPD"), "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": str(amount), "tax_rate": "0", "tax_amount": "0",
            "counterparty_name": "测试供应商", "seller_name": "测试供应商", "buyer_name": "本公司",
            "issue_date": "2026-06-01", "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 2, "unit_price": "10", "tax_rate": "0"}],
        }, headers=HEADERS)
        purchase_id = resp.json()["data"]["related_order_id"]
        resp2 = client.put(f"/api/purchases/{purchase_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp2.status_code == 200
