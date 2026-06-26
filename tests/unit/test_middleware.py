"""P0 合规性测试：只读中间件阻止直接修改关键历史数据"""

import pytest

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
HEADERS = {"X-Account-ID": "1", "X-Operator": "test"}


class TestReadonlyMiddleware:
    """只读中间件 — 禁止直接修改数据库"""

    def test_forbid_put_opening_balance(self):
        """PUT /api/opening-balances/{id} → 403"""
        resp = client.put("/api/opening-balances/1", json={"cash_balance": 999}, headers=HEADERS)
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "READONLY_DATA"
        assert "期初余额" in body["error"]["message"]

    def test_forbid_delete_opening_balance(self):
        """DELETE /api/opening-balances/{id} → 403"""
        resp = client.delete("/api/opening-balances/1", headers=HEADERS)
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "READONLY_DATA"
        assert "期初余额" in body["error"]["message"]

    def test_forbid_delete_invoice(self):
        """DELETE /api/invoices/{id} → 403"""
        resp = client.delete("/api/invoices/1", headers=HEADERS)
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "READONLY_DATA"
        assert "发票" in body["error"]["message"]

    def test_forbid_delete_fixed_asset(self):
        """DELETE /api/fixed-assets/{id} → 403"""
        resp = client.delete("/api/fixed-assets/1", headers=HEADERS)
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "READONLY_DATA"
        assert "固定资产" in body["error"]["message"]

    def test_allow_normal_routes(self):
        """非只读路由不受影响 → 通过"""
        resp = client.get("/api/health", headers=HEADERS)
        assert resp.status_code == 200

    def test_middleware_returns_path_and_method(self):
        """中间件返回被拦截的路径和方法"""
        resp = client.put("/api/opening-balances/999", json={"cash_balance": 0}, headers=HEADERS)
        body = resp.json()
        assert body["error"]["data"]["path"] == "/api/opening-balances/999"
        assert body["error"]["data"]["method"] == "PUT"
