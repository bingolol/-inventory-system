"""集成测试：对账管理 (routers/reconciliations.py)"""
import pytest
from decimal import Decimal
from database import SessionLocal
from helpers import get_account_id, make_headers
from factories import api_create_customer, api_create_supplier, api_create_product

HEADERS = make_headers()
DATE_RANGE = "start_date=2026-01-01&end_date=2026-12-31"


class TestAllReconciliations:
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


class TestReconciliationDetail:
    def test_supplier_detail_not_found(self, client):
        resp = client.get(f"/api/reconciliations/detail?party_type=supplier&partner_id=99999&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code in (400, 404, 422)

    def test_customer_detail_not_found(self, client):
        resp = client.get(f"/api/reconciliations/detail?party_type=customer&partner_id=99999&{DATE_RANGE}", headers=HEADERS)
        assert resp.status_code in (400, 404, 422)

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

    def test_detail_invalid_dates(self, client):
        resp = client.get("/api/reconciliations/detail?party_type=supplier&partner_id=1&start_date=abc&end_date=def", headers=HEADERS)
        assert resp.status_code in (400, 422)
