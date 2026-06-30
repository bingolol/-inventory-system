"""集成测试：采购单 API (routers/purchases.py)"""
import pytest
from helpers import get_account_id
from factories import api_create_product, api_create_supplier

HEADERS = {"X-Account-ID": "1", "X-Operator": "test"}


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
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "items": [{"product_id": pid, "quantity": 5, "unit_price": 10}],
            "purchase_date": "2026-06-01",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        purchase_id = resp.json().get("entity_id") or resp.json().get("id")
        resp2 = client.get(f"/api/purchases/{purchase_id}", headers=HEADERS)
        assert resp2.status_code == 200


class TestCreatePurchase:
    def test_create_success(self, client):
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "items": [{"product_id": pid, "quantity": 3, "unit_price": 15}],
            "notes": "测试采购单",
            "purchase_date": "2026-06-01",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "entity_id" in data or "id" in data


class TestUpdatePurchase:
    def test_update_status_to_cancelled(self, client):
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "items": [{"product_id": pid, "quantity": 2, "unit_price": 10}],
            "purchase_date": "2026-06-01",
        }, headers=HEADERS)
        purchase_id = resp.json().get("entity_id") or resp.json().get("id")
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
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 10}],
            "purchase_date": "2026-06-01",
        }, headers=HEADERS)
        purchase_id = resp.json().get("entity_id") or resp.json().get("id")
        resp2 = client.post(f"/api/purchases/{purchase_id}/cancel", headers=HEADERS)
        assert resp2.status_code == 200


class TestDeletePurchase:
    def test_delete_not_found(self, client):
        resp = client.delete("/api/purchases/99999", headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_delete_with_items_blocked(self, client):
        sid, _ = api_create_supplier(client, HEADERS)
        pid, _ = api_create_product(client, HEADERS)
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 10}],
            "purchase_date": "2026-06-01",
        }, headers=HEADERS)
        purchase_id = resp.json().get("entity_id") or resp.json().get("id")
        resp2 = client.delete(f"/api/purchases/{purchase_id}", headers=HEADERS)
        assert resp2.status_code in (400, 409, 422, 500)
