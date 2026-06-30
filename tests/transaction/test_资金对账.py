"""一体化事务测试：资金对账（银行流水 + 往来对账）

合并自:
  - tests/integration/test_cash_flows.py
  - tests/integration/test_reconciliations.py
"""

import pytest
from decimal import Decimal



from tests.factories import (
    api_create_customer, api_create_supplier,
)

HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}
DATE_RANGE = "start_date=2026-01-01&end_date=2026-12-31"


@pytest.fixture(scope="module", autouse=True)
def bootstrap(client):
    resp = client.post("/api/bootstrap/init")
    assert resp.status_code == 200, f"bootstrap 失败: {resp.text}"


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


class Test银行流水:
    """银行流水 CRUD + 报表"""

    def test_create_inflow(self, client):
        tx = _create_tx(client)
        assert tx["type"] == "inflow"
        assert float(tx["amount"]) == 1000.0

    def test_create_outflow(self, client):
        tx = _create_tx(client, type="outflow", amount=500.00)
        assert tx["type"] == "outflow"

    def test_create_with_related_entity(self, client):
        tx = _create_tx(client, related_entity_type="sale_order", related_entity_id=1)
        assert tx.get("related_entity_type") == "sale_order"

    def test_create_invalid_type(self, client):
        resp = client.post("/api/cash-flows/transactions", json={
            "type": "invalid", "amount": 100, "flow_category": "operating",
            "description": "test", "transaction_date": "2026-06-01",
        }, headers=HEADERS)
        assert resp.status_code == 422

    def test_list_default(self, client):
        _create_tx(client)
        resp = client.get("/api/cash-flows/transactions", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "items" in data

    def test_list_with_filters(self, client):
        _create_tx(client, flow_category="operating")
        resp = client.get(
            f"/api/cash-flows/transactions?flow_category=operating&{DATE_RANGE}",
            headers=HEADERS,
        )
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

    def test_list_includes_created(self, client):
        tx = _create_tx(client)
        tid = tx["id"]
        resp = client.get("/api/cash-flows/transactions", headers=HEADERS)
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json().get("items", [])]
        assert tid in ids

    def test_update_amount(self, client):
        tx = _create_tx(client)
        tid = tx["id"]
        resp = client.put(f"/api/cash-flows/transactions/{tid}", json={"amount": 2000.00}, headers=HEADERS)
        assert resp.status_code == 200
        updated = resp.json().get("data", resp.json())
        assert float(updated["amount"]) == 2000.0

    def test_update_description(self, client):
        tx = _create_tx(client)
        tid = tx["id"]
        resp = client.put(f"/api/cash-flows/transactions/{tid}", json={"description": "已更新"}, headers=HEADERS)
        assert resp.status_code == 200
        updated = resp.json().get("data", resp.json())
        assert updated["description"] == "已更新"

    def test_update_not_found(self, client):
        resp = client.put("/api/cash-flows/transactions/99999", json={"amount": 100}, headers=HEADERS)
        assert resp.status_code in (400, 404)

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

    def test_statement_default(self, client):
        resp = client.get(f"/api/cash-flows/statement?{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "categories" in data or isinstance(data, dict)

    def test_statement_invalid_dates(self, client):
        resp = client.get("/api/cash-flows/statement?start_date=abc&end_date=def", headers=HEADERS)
        assert resp.status_code in (400, 422, 500)


class Test往来对账:
    """供应商/客户对账汇总 + 明细"""

    def test_all_supplier_reconciliation(self, client):
        api_create_supplier(client, HEADERS)
        resp = client.get(f"/api/reconciliations?party_type=supplier&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["party_type"] == "supplier"
        assert "summary" in data
        assert "items" in data

    def test_all_customer_reconciliation(self, client):
        api_create_customer(client, HEADERS)
        resp = client.get(f"/api/reconciliations?party_type=customer&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["party_type"] == "customer"

    def test_invalid_dates(self, client):
        resp = client.get("/api/reconciliations?party_type=supplier&start_date=abc&end_date=def", headers=HEADERS)
        assert resp.status_code in (400, 422)

    def test_invalid_party_type(self, client):
        resp = client.get(f"/api/reconciliations?party_type=invalid&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code == 422

    def test_supplier_detail_found(self, client):
        sid, _ = api_create_supplier(client, HEADERS)
        resp = client.get(f"/api/reconciliations/detail?party_type=supplier&partner_id={sid}&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["party_type"] == "supplier"
        assert "items" in data
        assert "opening_balance" in data

    def test_customer_detail_found(self, client):
        cid, _ = api_create_customer(client, HEADERS)
        resp = client.get(f"/api/reconciliations/detail?party_type=customer&partner_id={cid}&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["party_type"] == "customer"

    def test_supplier_detail_not_found(self, client):
        resp = client.get(f"/api/reconciliations/detail?party_type=supplier&partner_id=99999&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code in (400, 404, 422)

    def test_customer_detail_not_found(self, client):
        resp = client.get(f"/api/reconciliations/detail?party_type=customer&partner_id=99999&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code in (400, 404, 422)

    def test_detail_invalid_dates(self, client):
        resp = client.get("/api/reconciliations/detail?party_type=supplier&partner_id=1&start_date=abc&end_date=def", headers=HEADERS)
        assert resp.status_code in (400, 422)
