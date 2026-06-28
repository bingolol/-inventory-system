"""双保险安全方案 - 中间件集成测试"""

import pytest
from fastapi.testclient import TestClient
from database import set_maintenance_mode


@pytest.fixture(scope="module")
def client():
    from main import app
    with TestClient(app) as c:
        yield c


_ACCOUNT_CODE = "sec-mw-test"

@pytest.fixture(scope="module")
def account_id(client):
    """创建测试账本（模块级，复用一次）"""
    from database import SessionLocal
    from models import Account
    db = SessionLocal()
    existing = db.query(Account).filter(Account.code == _ACCOUNT_CODE).first()
    db.close()
    if existing:
        return existing.id
    resp = client.post("/api/accounts", json={
        "name": "sec-mw-test", "type": "company",
        "code": _ACCOUNT_CODE, "taxpayer_type": "small_scale",
    }, headers={"X-Operator": "user"})
    assert resp.status_code == 200
    return resp.json()["id"]


class TestGatewayIntegration:
    """2.1~2.2 Gateway + WritePermission 中间件联动"""

    @pytest.fixture(autouse=True)
    def no_maintenance(self):
        set_maintenance_mode(False)

    def test_get_read_only_ok(self, client):
        """GET 不需要令牌，正常放行"""
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_post_user_allowed(self, client, account_id):
        """X-Operator: user → 网关放行 → 中间件给令牌 → 可写"""
        resp = client.post("/api/products", json={
            "name": "user-prod", "purchase_price": 10, "sale_price": 20, "unit": "个",
        }, headers={"X-Operator": "user", "X-Account-ID": str(account_id)})
        assert resp.status_code == 200

    def test_post_no_operator_blocked(self, client, account_id):
        """无 X-Operator → 网关 403，到不了中间件"""
        resp = client.post("/api/products", json={
            "name": "noop-prod", "purchase_price": 10, "sale_price": 20, "unit": "个",
        }, headers={"X-Account-ID": str(account_id)})
        assert resp.status_code == 403

    def test_post_ai_whitelisted_allowed(self, client, account_id):
        """X-Operator: ai + 白名单端点 → 可写"""
        resp = client.post("/api/products", json={
            "name": "ai-prod", "purchase_price": 10, "sale_price": 20, "unit": "个",
        }, headers={"X-Operator": "ai", "X-Account-ID": str(account_id)})
        assert resp.status_code == 200

    def test_post_ai_not_whitelisted_blocked(self, client, account_id):
        """X-Operator: ai + 非白名单端点(bank-accounts) → 403"""
        resp = client.post("/api/bank-accounts", json={
            "name": "blocked-test", "account_type": "checking", "opening_balance": 0,
        }, headers={"X-Operator": "ai", "X-Account-ID": str(account_id)})
        assert resp.status_code == 403


class TestBootstrap:
    """3.2 bootstrap API 初始化账本"""

    @pytest.fixture(autouse=True)
    def no_maintenance(self):
        set_maintenance_mode(False)

    def test_bootstrap_init_creates_account(self, client):
        """首次 init 创建账本 + 科目 + 用户"""
        from database import SessionLocal, set_maintenance_mode
        from models import Account, User
        set_maintenance_mode(True)
        db = SessionLocal()
        db.query(User).delete()
        db.query(Account).delete()
        db.commit()
        db.close()
        set_maintenance_mode(False)

        resp = client.post("/api/bootstrap/init")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["account_id"] > 0

    def test_bootstrap_init_idempotent(self, client):
        """重复 init 返回 already"""
        resp = client.post("/api/bootstrap/init")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "already"
