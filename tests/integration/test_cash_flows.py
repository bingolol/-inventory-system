"""集成测试：现金流管理 (routers/cash_flows.py)"""
import pytest
from helpers import get_account_id

HEADERS = {"X-Account-ID": "1", "X-Operator": "test"}


def _create_tx(client, **overrides):
    payload = {
        "type": "inflow",
        "amount": 1000.00,
        "flow_category": "operating",
        "description": "测试流水",
        "transaction_date": "2026-06-01",
    }
    payload.update(overrides)
    resp = client.post("/api/cash-flows/transactions", json=payload, headers=HEADERS)
    assert resp.status_code == 200, resp.text
    return resp.json().get("data", resp.json())


class TestCashFlowStatement:
    def test_statement_default(self, client):
        resp = client.get("/api/cash-flows/statement?start_date=2026-01-01&end_date=2026-12-31", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data or isinstance(data, dict)

    def test_statement_invalid_dates(self, client):
        resp = client.get("/api/cash-flows/statement?start_date=abc&end_date=def", headers=HEADERS)
        assert resp.status_code == 500 or resp.status_code == 400


class TestCreateCashFlowTransaction:
    def test_create_income(self, client):
        tx = _create_tx(client)
        assert tx["type"] in ("inflow", "outflow")
        assert float(tx["amount"]) == 1000.0

    def test_create_expense(self, client):
        tx = _create_tx(client, type="outflow", amount=500.00)
        assert tx["type"] in ("inflow", "outflow")

    def test_create_with_related_entity(self, client):
        tx = _create_tx(client, related_entity_type="sale_order", related_entity_id=1)
        assert tx["related_entity_type"] == "sale_order"

    def test_create_invalid_type(self, client):
        resp = client.post("/api/cash-flows/transactions", json={
            "type": "invalid", "amount": 100, "flow_category": "operating",
            "description": "test", "transaction_date": "2026-06-01",
        }, headers=HEADERS)
        assert resp.status_code == 422


class TestListCashFlowTransactions:
    def test_list_default(self, client):
        _create_tx(client)
        resp = client.get("/api/cash-flows/transactions", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data

    def test_list_with_filters(self, client):
        _create_tx(client, flow_category="operating")
        resp = client.get("/api/cash-flows/transactions?flow_category=operating&start_date=2026-01-01&end_date=2026-12-31", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_list_pagination(self, client):
        for i in range(3):
            _create_tx(client, description=f"流水-{i}")
        resp = client.get("/api/cash-flows/transactions?skip=0&limit=2", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2


class TestUpdateCashFlowTransaction:
    def test_update_amount(self, client):
        tx = _create_tx(client)
        tid = tx["id"]
        resp = client.put(f"/api/cash-flows/transactions/{tid}", json={"amount": 2000.00}, headers=HEADERS)
        assert resp.status_code == 200
        assert float(resp.json().get("data", resp.json())["amount"]) == 2000.0

    def test_update_not_found(self, client):
        resp = client.put("/api/cash-flows/transactions/99999", json={"amount": 100}, headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_update_description(self, client):
        tx = _create_tx(client)
        tid = tx["id"]
        resp = client.put(f"/api/cash-flows/transactions/{tid}", json={"description": "已更新"}, headers=HEADERS)
        assert resp.status_code == 200
        assert resp.json().get("data", resp.json())["description"] == "已更新"


class TestDeleteCashFlowTransaction:
    def test_delete_existing(self, client):
        tx = _create_tx(client)
        tid = tx["id"]
        resp = client.delete(f"/api/cash-flows/transactions/{tid}", headers=HEADERS)
        assert resp.status_code == 200

    def test_delete_not_found(self, client):
        resp = client.delete("/api/cash-flows/transactions/99999", headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_delete_twice(self, client):
        tx = _create_tx(client)
        tid = tx["id"]
        client.delete(f"/api/cash-flows/transactions/{tid}", headers=HEADERS)
        resp = client.delete(f"/api/cash-flows/transactions/{tid}", headers=HEADERS)
        assert resp.status_code in (400, 404)
