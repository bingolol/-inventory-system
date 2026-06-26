"""AccountingError 全局处理器集成测试(TDD - 接线层)

验证 main.py 注册了 AccountingError handler 后,真实路由抛出的
AccountingError 冒泡到 app 时返回结构化 4xx(而非 500 丢引导字段)。

触发路径:GET /api/accounting/vat?taxpayer_type=xxx(非法值)
  - 修复缺口3后,该路由不再用 except Exception 吞错,AccountingError 冒泡
  - 修复缺口1后,main.py 的 handler 捕获并转结构化响应
"""
import pytest


@pytest.mark.integration
class TestAccountingErrorWiring:
    """AccountingError 经 main.py handler 返回结构化响应(缺口1+3修复验证)"""

    def test_invalid_taxpayer_not_500(self, client):
        """非法纳税人类型 → 不应返回 500(证明 handler 已接线)"""
        r = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=xxx",
                       headers={"X-Account-ID": "1"})
        assert r.status_code != 500, "AccountingError 被吞成 500,handler 未接线或 check 路由仍吞错"

    def test_invalid_taxpayer_returns_422(self, client):
        """参数非法类应映射到 422"""
        r = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=xxx",
                       headers={"X-Account-ID": "1"})
        assert r.status_code == 422

    def test_invalid_taxpayer_returns_structured_code(self, client):
        """响应体含 error.code == VAT_TAXPAYER_TYPE_INVALID"""
        r = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=xxx",
                       headers={"X-Account-ID": "1"})
        assert r.json()["error"]["code"] == "VAT_TAXPAYER_TYPE_INVALID"

    def test_invalid_taxpayer_preserves_ai_instruction(self, client):
        """响应体含 ai_instruction,带 STOP_RETRYING 引导"""
        r = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=xxx",
                       headers={"X-Account-ID": "1"})
        assert "STOP_RETRYING" in r.json()["error"]["ai_instruction"]

    def test_valid_request_still_works(self, client):
        """回归:合法请求仍返回 valid:true(修复未破坏正常路径)"""
        r = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=general",
                       headers={"X-Account-ID": "1"})
        assert r.status_code == 200
        assert r.json()["valid"] is True
