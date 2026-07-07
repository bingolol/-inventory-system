"""税务申报声明 集成测试 — TDD tracer bullet"""

import pytest
from decimal import Decimal
from helpers import get_entity_id, make_headers

HEADERS = make_headers("user")


class TestVATDeclaration:
    """VAT 申报声明"""

    def test_declare_vat_creates_snapshot(self, client):
        """提交 VAT 申报 → 锁定快照，返回 vat_payable"""
        resp = client.post("/api/tax/declare?force=true", json={
            "period": "2026-Q2",
            "taxpayer_type": "small_scale",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"提交 VAT 申报失败: {resp.text}"
        data = resp.json()
        assert data["ok"] is True
        assert "data" in data
        assert data["data"]["period"] == "2026-Q2"
        assert isinstance(data["data"]["vat_payable"], float)

    def test_declare_duplicate_period_fails(self, client):
        """同一期间重复提交 VAT 申报 → 409"""
        resp = client.post("/api/tax/declare", json={
            "period": "2026-Q2",
            "taxpayer_type": "small_scale",
        }, headers=HEADERS)
        assert resp.status_code == 409

    def test_pending_declarations_returns_list(self, client):
        """查询待申报期间 → 返回列表"""
        resp = client.get("/api/tax/pending-declarations", headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 1, "待申报列表不应为空"

    def test_list_declarations_contains_q2(self, client):
        """查询已申报列表 → 包含 Q2"""
        resp = client.get("/api/tax/declarations", headers=HEADERS)
        assert resp.status_code == 200
        decls = resp.json()
        periods = [d["period"] for d in decls]
        assert "2026-Q2" in periods


class TestSurchargeDeclaration:
    """附加税申报声明"""

    def test_surcharge_needs_vat_declaration_first(self, client):
        """未提交 VAT 就录附加税 → 报错"""
        resp = client.post("/api/tax/surcharge-declaration", json={
            "period": "2026-Q3",
            "urban_construction_tax": 15.89,
            "education_surcharge": 6.81,
            "local_education_surcharge": 4.54,
        }, headers=HEADERS)
        assert resp.status_code == 422, f"应报错但没有: {resp.text}"
        assert "VAT 尚未申报" in resp.text

    def test_declare_surcharge_success(self, client):
        """提交 VAT 后录入附加税 → 成功过账"""
        resp = client.post("/api/tax/surcharge-declaration", json={
            "period": "2026-Q2",
            "urban_construction_tax": 15.89,
            "education_surcharge": 6.81,
            "local_education_surcharge": 4.54,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"录入附加税失败: {resp.text}"
        data = resp.json()
        assert data["ok"] is True
        assert data["data"]["period"] == "2026-Q2"
        assert data["data"]["total"] == pytest.approx(15.89 + 6.81 + 4.54, 0.01)
        assert data["data"]["posted"] in ("new", "no_change"), f"expected new or no_change, got {data['data']['posted']}"

    def test_pending_shows_surcharge_declared(self, client):
        """录入附加税后，待办状态验证"""
        resp = client.get("/api/tax/pending-declarations", headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json()
        q2 = next((it for it in items if it["period"] == "2026-Q2"), None)
        if q2 is None:
            pytest.skip("2026-Q2 not in pending list (may be completed)")
        assert q2["surcharge_declared"] is True
        assert q2["status"] == "surcharge_declared"