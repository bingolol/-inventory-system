"""集成测试：固定资产 CRUD API"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, init_db


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _get_account_id():
    from models import Account
    db = SessionLocal()
    try:
        acc = db.query(Account).first()
        return acc.id if acc else 1
    finally:
        db.close()


def _unique_code(prefix="FA-TEST"):
    """生成唯一资产编码，避免重复运行冲突"""
    from datetime import datetime
    return f"{prefix}-{datetime.now().strftime('%H%M%S%f')}"


@pytest.mark.integration
class TestFixedAssetsAPI:
    """固定资产 CRUD API 集成测试"""

    def test_create_fixed_asset(self, client):
        """POST /api/fixed-assets → 创建固定资产"""
        account_id = _get_account_id()
        payload = {
            "asset_code": _unique_code(),
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
        account_id = _get_account_id()
        r = client.get("/api/fixed-assets", headers={"X-Account-ID": str(account_id)})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    def test_update_fixed_asset(self, client):
        """PUT /api/fixed-assets/{id} → 更新"""
        account_id = _get_account_id()
        # 先创建
        payload = {
            "asset_code": _unique_code("FA-UPD"),
            "name": "更新前设备",
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
        # 更新
        r2 = client.put(f"/api/fixed-assets/{asset_id}", json={"name": "更新后设备", "status": "停用"},
                        headers={"X-Account-ID": str(account_id)})
        assert r2.status_code == 200
        assert r2.json()["name"] == "更新后设备"
        assert r2.json()["status"] == "停用"

    def test_delete_fixed_asset(self, client):
        """DELETE /api/fixed-assets/{id} → 删除"""
        account_id = _get_account_id()
        # 先创建
        payload = {
            "asset_code": _unique_code("FA-DEL"),
            "name": "待删除设备",
            "category": "电子设备",
            "original_value": "3000.00",
            "salvage_rate": "0.05",
            "useful_life": 24,
            "depreciation_method": "年限平均法",
            "start_date": "2026-01-01",
            "status": "在用"
        }
        r = client.post("/api/fixed-assets", json=payload, headers={"X-Account-ID": str(account_id)})
        assert r.status_code == 200, r.text
        asset_id = r.json()["id"]
        # 删除
        r2 = client.delete(f"/api/fixed-assets/{asset_id}", headers={"X-Account-ID": str(account_id)})
        assert r2.status_code == 200

    def test_get_nonexistent_returns_404(self, client):
        """PUT 不存在的 ID → 404"""
        account_id = _get_account_id()
        r = client.put("/api/fixed-assets/999999", json={"name": "不存在"},
                       headers={"X-Account-ID": str(account_id)})
        assert r.status_code == 404
