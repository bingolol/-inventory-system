"""集成测试：固定资产 CRUD API"""
import pytest
from decimal import Decimal
from helpers import get_account_id, uniq


@pytest.mark.integration
class TestFixedAssetsAPI:
    """固定资产 CRUD API 集成测试"""

    def test_create_fixed_asset(self, client):
        """POST /api/fixed-assets → 创建固定资产"""
        account_id = get_account_id()
        payload = {
            "asset_code": uniq("FA-TEST"),
            "name": "测试设备",
            "category": "电子设备",
            "original_value": "10000.00",
            "salvage_rate": "0.05",
            "useful_life": 60,
            "depreciation_method": "年限平均法",
            "start_date": "2026-01-01",
            "accumulated_depreciation": "0.00",
            "status": "在用"
        }
        r = client.post("/api/fixed-assets", json=payload, headers={"X-Account-ID": str(account_id)})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] > 0
        assert data["name"] == "测试设备"

    def test_list_fixed_assets(self, client):
        """GET /api/fixed-assets → 列表"""
        account_id = get_account_id()
        r = client.get("/api/fixed-assets", headers={"X-Account-ID": str(account_id)})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_dispose_fixed_asset(self, client):
        """POST /api/fixed-assets/{id}/dispose → 资产处置（替代 PUT/DELETE）"""
        account_id = get_account_id()
        # 先创建
        payload = {
            "asset_code": uniq("FA-UPD"),
            "name": "处置测试设备",
            "category": "电子设备",
            "original_value": "5000.00",
            "salvage_rate": "0.05",
            "useful_life": 36,
            "depreciation_method": "年限平均法",
            "start_date": "2026-01-01",
            "status": "在用"
        }
        r = client.post("/api/fixed-assets", json=payload, headers={"X-Account-ID": str(account_id)})
        assert r.status_code == 200, r.text
        asset_id = r.json()["id"]
        # 处置
        r2 = client.post(f"/api/fixed-assets/{asset_id}/dispose?reason=报废测试",
                         headers={"X-Account-ID": str(account_id)})
        assert r2.status_code == 200, r2.text
        assert r2.json()["data"]["status"] == "报废"

    def test_dispose_nonexistent_returns_404(self, client):
        """POST /api/fixed-assets/{id}/dispose 不存在的 ID → 404"""
        account_id = get_account_id()
        r = client.post("/api/fixed-assets/999999/dispose",
                        headers={"X-Account-ID": str(account_id)})
        assert r.status_code == 404

    def test_readonly_middleware_blocks_delete(self, client):
        """ReadonlyMiddleware 阻止 DELETE 固定资产"""
        account_id = get_account_id()
        r = client.delete("/api/fixed-assets/1",
                          headers={"X-Account-ID": str(account_id)})
        assert r.status_code == 403
