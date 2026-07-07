"""财务查询 API 集成测试"""
import time
import pytest
from decimal import Decimal

from test_helpers import ensure_test_product
from helpers import get_entity_id, make_headers
from factories import api_create_customer, api_create_supplier

HEADERS = make_headers()


def _get_cid(client, tag):
    return api_create_customer(client, HEADERS)[0]


def _get_sid(client, tag):
    return api_create_supplier(client, HEADERS)[0]


def _create_sale(client, pid: int, cid: int) -> dict:
    resp = client.post("/api/sales", json={
        "customer_id": cid,
        "deduct_inventory": True,
        "payment_status": "unpaid",
        "sale_date": "2026-06-15T10:00:00",
        "items": [{"product_id": pid, "quantity": 2, "unit_price": 100, "tax_rate": 0.01}],
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建销售失败: {resp.text}"
    return resp.json()


class TestAccountChart:
    """科目表 API"""

    def test_returns_all_phase1_accounts(self, client):
        resp = client.get("/api/finance/accounts/chart", headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json()["items"]
        codes = {it["code"] for it in items}

        for code in ("1001", "1002", "1122", "1405", "2202",
                     "222101", "222102", "6001", "6401",
                     "6601", "6602", "6603"):
            assert code in codes, f"缺少科目 {code}"

    def test_leaf_account_has_balance_zero(self, client):
        resp = client.get("/api/finance/accounts/chart", headers=HEADERS)
        items = resp.json()["items"]
        cash = next(it for it in items if it["code"] == "1001")
        assert cash["is_leaf"] is True
        assert float(cash["balance"]) == 0

    def test_non_leaf_not_returned(self, client):
        resp = client.get("/api/finance/accounts/chart", headers=HEADERS)
        items = resp.json()["items"]
        assert all(it["is_leaf"] for it in items)


class TestJournalMoves:
    """凭证查询 API"""

    def test_moves_list_after_sale(self, client):
        pid = ensure_test_product(1)
        cid = _get_cid(client, "JM1")
        _create_sale(client, pid, cid)

        resp = client.get("/api/finance/journal/moves", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        sale_moves = [m for m in data["items"] if m["move_type"] == "sale_order"]
        assert len(sale_moves) >= 1

    def test_filter_by_move_type(self, client):
        resp = client.get("/api/finance/journal/moves",
                          params={"move_type": "sale_order"},
                          headers=HEADERS)
        assert resp.status_code == 200
        for m in resp.json()["items"]:
            assert m["move_type"] == "sale_order"

    def test_filter_by_date(self, client):
        resp = client.get("/api/finance/journal/moves",
                          params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
                          headers=HEADERS)
        assert resp.status_code == 200

    def test_pagination(self, client):
        resp = client.get("/api/finance/journal/moves",
                          params={"skip": 0, "limit": 5},
                          headers=HEADERS)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 5

    def test_move_detail_has_lines_with_account_codes(self, client):
        resp = client.get("/api/finance/journal/moves",
                          params={"move_type": "sale_order", "limit": 1},
                          headers=HEADERS)
        if resp.json()["total"] == 0:
            pytest.skip("No sale moves to test detail")
        move_id = resp.json()["items"][0]["id"]

        resp = client.get(f"/api/finance/journal/moves/{move_id}", headers=HEADERS)
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == move_id
        assert len(detail["lines"]) >= 2

        codes = {ln["account_code"] for ln in detail["lines"]}
        assert "1122" in codes, "缺少应收账款科目"
        assert "6001" in codes or "222101" in codes


class TestTrialBalance:
    """试算平衡表 API"""

    def test_balanced_after_sale(self, client):
        pid = ensure_test_product(1)
        cid = _get_cid(client, "TB1")
        _create_sale(client, pid, cid)

        resp = client.get("/api/finance/reports/trial-balance",
                          params={"date": "2026-12-31"},
                          headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "rows" in data
        assert "total_debit" in data
        assert "total_credit" in data
        assert data["balanced"] is True, \
            f"试算不平衡: 借={data['total_debit']}, 贷={data['total_credit']}"

    def test_total_debit_equals_total_credit(self, client):
        resp = client.get("/api/finance/reports/trial-balance",
                          params={"date": "2026-12-31"},
                          headers=HEADERS)
        data = resp.json()
        assert data["total_debit"] == data["total_credit"]


class TestPartnerReceivable:
    """往来余额 + 账龄 API"""

    def test_customer_balance_and_aging(self, client):
        pid = ensure_test_product(1)
        cid = _get_cid(client, "PR1")
        _create_sale(client, pid, cid)

        resp = client.get(f"/api/finance/receivable/partner/{cid}",
                          params={"partner_type": "customer"},
                          headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["partner_id"] == cid
        assert data["partner_type"] == "customer"
        assert float(data["balance"]) != 0
        for bucket in ("0-30", "31-60", "61-90", "90+"):
            assert bucket in data["aging"]

    def test_supplier_balance_and_aging(self, client):
        pid = ensure_test_product(1)
        sid = _get_sid(client, "SP1")

        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "payment_method": "company",
            "purchase_date": "2026-06-10T10:00:00",
            "items": [{"product_id": pid, "quantity": 5, "unit_price": 50, "tax_rate": 0.13}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建采购失败: {resp.text}"

        resp = client.get(f"/api/finance/receivable/partner/{sid}",
                          params={"partner_type": "supplier"},
                          headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["partner_type"] == "supplier"
        for bucket in ("0-30", "31-60", "61-90", "90+"):
            assert bucket in data["aging"]
