"""AI 网关中间件单元测试 — 验证白名单拦截行为

通过最小 ASGI 内层 app + AIGatewayMiddleware 包装，用 TestClient 验证
"AI 写操作命中非规范接口 → 403；前端/GET 全放行"的核心行为。
不依赖数据库，纯单元测试。
"""
import json
import pytest
from fastapi.testclient import TestClient

from ai_gateway import AIGatewayMiddleware


# ── 最小 ASGI 内层 app：收到请求返回 200 + 标记，证明"未被网关拦截" ──
async def _ok_app(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return
    if scope["type"] != "http":
        return
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [[b"content-type", b"application/json"]],
    })
    await send({
        "type": "http.response.body",
        "body": b'{"reached":"inner"}',
    })


@pytest.fixture
def client():
    """仅包装 AIGatewayMiddleware 的 TestClient（无 DB、无其他中间件）"""
    with TestClient(AIGatewayMiddleware(_ok_app)) as c:
        yield c


AI = {"X-Operator": "ai"}
USER = {"X-Operator": "user"}


@pytest.mark.unit
class TestAIGatewayAllows:
    """放行场景：前端请求、GET、规范写接口应全部到达内层 app"""

    def test_user_write_not_blocked(self, client):
        """前端(user)写非规范接口 → 放行（中间件只约束 AI）"""
        r = client.post("/api/invoices", json={"x": 1}, headers=USER)
        assert r.status_code == 200
        assert r.json()["reached"] == "inner"

    def test_no_operator_header_treated_as_user(self, client):
        """无 X-Operator 头 → 视为前端 user，放行"""
        r = client.post("/api/invoices/with-fixed-asset", json={"x": 1})
        assert r.status_code == 200
        assert r.json()["reached"] == "inner"

    def test_ai_get_not_blocked(self, client):
        """AI 的 GET 请求 → 查询全部放行"""
        r = client.get("/api/invoices", headers=AI)
        assert r.status_code == 200
        assert r.json()["reached"] == "inner"

    def test_ai_post_canonical_quick(self, client):
        """AI POST /api/invoices/quick（规范入口）→ 放行"""
        r = client.post("/api/invoices/quick", json={"x": 1}, headers=AI)
        assert r.status_code == 200
        assert r.json()["reached"] == "inner"

    def test_ai_delete_canonical(self, client):
        """AI DELETE /api/invoices/{id}（白名单）→ 放行"""
        r = client.delete("/api/invoices/123", headers=AI)
        assert r.status_code == 200
        assert r.json()["reached"] == "inner"

    def test_ai_post_products_canonical(self, client):
        """AI POST /api/products（白名单）→ 放行"""
        r = client.post("/api/products", json={"x": 1}, headers=AI)
        assert r.status_code == 200

    def test_ai_infrastructure_path_skipped(self, client):
        """AI POST /api/accounts（基础设施白名单前缀）→ 放行"""
        r = client.post("/api/accounts", json={"x": 1}, headers=AI)
        assert r.status_code == 200
        assert r.json()["reached"] == "inner"


@pytest.mark.unit
class TestAIGatewayBlocks:
    """拦截场景：AI 命中非规范写接口 → 403 + ai_instruction 指明替代"""

    def test_ai_post_base_invoice_blocked(self, client):
        """AI POST /api/invoices（非规范，应走 /quick）→ 403"""
        r = client.post("/api/invoices", json={"x": 1}, headers=AI)
        assert r.status_code == 403
        body = r.json()
        assert body["error"]["code"] == "ENDPOINT_NOT_ALLOWED_FOR_AI"
        assert "STOP_RETRYING" in body["error"]["ai_instruction"]

    def test_blocked_suggests_quick_for_invoices(self, client):
        """发票变体被拦截时，ai_instruction 应指明 /quick 规范替代"""
        r = client.post("/api/invoices", json={"x": 1}, headers=AI)
        suggestion = r.json()["error"]["ai_instruction"]
        assert "/api/invoices/quick" in suggestion

    def test_ai_post_with_fixed_asset_variant_blocked(self, client):
        """AI POST /api/invoices/with-fixed-asset（已删变体）→ 403（网关先于路由拦截）"""
        r = client.post("/api/invoices/with-fixed-asset", json={"x": 1}, headers=AI)
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "ENDPOINT_NOT_ALLOWED_FOR_AI"

    def test_ai_put_with_fixed_asset_variant_blocked(self, client):
        """AI PUT /api/invoices/{id}/with-fixed-asset（已删变体）→ 403"""
        r = client.put("/api/invoices/1/with-fixed-asset", json={"x": 1}, headers=AI)
        assert r.status_code == 403

    def test_ai_delete_with_fixed_asset_variant_blocked(self, client):
        """AI DELETE /api/invoices/{id}/with-fixed-asset（已删变体）→ 403"""
        r = client.delete("/api/invoices/1/with-fixed-asset", headers=AI)
        assert r.status_code == 403

    def test_ai_post_upload_not_whitelisted(self, client):
        """AI POST /api/invoices/upload（移出白名单，AI 应走 /quick）→ 403"""
        r = client.post("/api/invoices/upload", json={"x": 1}, headers=AI)
        assert r.status_code == 403

    def test_ai_unknown_write_blocked(self, client):
        """AI POST 不存在的写接口 → 403（网关先于 404 路由）"""
        r = client.post("/api/invoices/some-unknown-variant", json={"x": 1}, headers=AI)
        assert r.status_code == 403

    def test_blocked_response_shape(self, client):
        """403 响应体结构含 data.suggested_endpoint"""
        r = client.post("/api/invoices", json={"x": 1}, headers=AI)
        data = r.json()["error"]["data"]
        assert data["method"] == "POST"
        assert data["path"] == "/api/invoices"
        assert "suggested_endpoint" in data
