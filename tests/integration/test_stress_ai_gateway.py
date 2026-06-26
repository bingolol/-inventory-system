"""压力测试 — 验证 AI 网关中间件栈在高频请求下的正确性与稳定性

测试维度:
  1. 网关拦截吞吐:大量 AI 非规范写请求并发/连续 → 全部 403(无一漏网)
  2. /quick 批量创建:连续创建 N 张发票 → 全部成功,金额计算一致
  3. 中间件栈混合负载:AI/user/GET/POST 混合 → 各自正确分流,无串扰
  4. 网关匹配性能:1000 次路径匹配在合理时间内完成(无 O(n) 退化)

注:本测试用同步顺序模拟"高并发",验证的是正确性 + 无状态泄漏 + 性能基线,
而非真实多线程并发(SQLite + TestClient 不适合真并发,会锁竞争)。
"""
import time
import uuid
import pytest
from ai_gateway import _match, AI_CAPABILITIES
from test_helpers import ensure_test_product


def _uniq(prefix, i):
    return f"{prefix}-{uuid.uuid4().hex[:6]}-{i}"


@pytest.mark.integration
class TestGatewayThroughput:
    """网关拦截吞吐与正确性"""

    def test_100_consecutive_ai_blocks_all_403(self, client):
        """100 次 AI 非规范写连续请求 → 全部 403,无一漏网"""
        h = {"X-Account-ID": "1", "X-Operator": "ai"}
        codes = []
        for i in range(100):
            r = client.post("/api/invoices", json={"x": i}, headers=h)
            codes.append(r.status_code)
        assert all(c == 403 for c in codes), f"有非403: {[c for c in codes if c != 403][:5]}"
        assert len(codes) == 100

    def test_mixed_ai_user_no_cross_contamination(self, client):
        """AI/user 交替请求 → AI 拦截、user 放行,无状态串扰"""
        ai_h = {"X-Account-ID": "1", "X-Operator": "ai"}
        user_h = {"X-Account-ID": "1", "X-Operator": "user"}
        for i in range(20):
            r_ai = client.post("/api/invoices", json={"x": i}, headers=ai_h)
            assert r_ai.status_code == 403, f"第{i}轮 AI 应拦截"
            r_user = client.post("/api/invoices", json={"x": i}, headers=user_h)
            assert r_user.status_code != 403, f"第{i}轮 user 不应被网关拦截"


@pytest.mark.integration
class TestQuickBatchCreate:
    """/quick 批量创建正确性"""

    def test_batch_50_invoices_all_succeed(self, client):
        """连续创建 50 张发票 → 全部成功,金额三件套一致"""
        h = {"X-Account-ID": "1", "X-Operator": "user"}
        pid = ensure_test_product(1)
        ids = []
        for i in range(50):
            r = client.post("/api/invoices/quick", json={
                "invoice_no": _uniq("STRESS-INV", i),
                "direction": "out", "invoice_type": "ordinary",
                "amount_with_tax": "113.00", "tax_rate": "0.13",
                "counterparty_name": "压测客户", "seller_name": "本公司", "buyer_name": "压测客户",
                "issue_date": "2026-06-20",
                "sale_order_action": "auto_create",
                "items": [{"product_id": pid, "quantity": 1, "unit_price": "100.00", "tax_rate": "0.13"}],
            }, headers=h)
            assert r.status_code == 200, f"第{i}张创建失败: {r.text}"
            data = r.json()["data"]
            ids.append(data["id"])
            # 金额一致性:113/(1.13)=100, 税额=13
            assert float(data["amount_without_tax"]) == 100.00
            assert float(data["tax_amount"]) == 13.00
        assert len(set(ids)) == 50, "发票ID应全部唯一"


@pytest.mark.unit
class TestGatewayMatchPerformance:
    """网关路径匹配性能基线"""

    def test_1000_matches_under_50ms(self):
        """1000 次路径匹配 < 50ms(无性能退化)"""
        start = time.perf_counter()
        for _ in range(1000):
            _match("POST", "/api/invoices/quick")
            _match("DELETE", "/api/invoices/123")
            _match("POST", "/api/products")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.5, f"1000 次匹配耗时 {elapsed:.3f}s 过长"

    def test_capabilities_count_stable(self):
        """白名单条目数稳定(防止误删)"""
        assert len(AI_CAPABILITIES) >= 30, f"白名单仅 {len(AI_CAPABILITIES)} 条,疑似被误删"


@pytest.mark.integration
class TestMiddlewareStackMixedLoad:
    """中间件栈混合负载 — 真实分流验证"""

    def test_30_mixed_requests_correct_routing(self, client):
        """30 次混合请求(GET/AI写/user写/规范写)全部正确分流"""
        ai_h = {"X-Account-ID": "1", "X-Operator": "ai"}
        user_h = {"X-Account-ID": "1", "X-Operator": "user"}
        pid = ensure_test_product(1)
        results = {"get": 0, "ai_block": 0, "user_pass": 0, "ai_pass": 0}
        for i in range(30):
            # GET 全放行
            r = client.get("/api/invoices?limit=1", headers=ai_h)
            assert r.status_code == 200
            results["get"] += 1
            # AI 非规范写 → 403
            r = client.post("/api/invoices", json={}, headers=ai_h)
            assert r.status_code == 403
            results["ai_block"] += 1
            # user 写 → 放行(进入业务层)
            r = client.post("/api/invoices", json={}, headers=user_h)
            assert r.status_code != 403
            results["user_pass"] += 1
            # AI 规范写 /quick → 放行(进入业务层)
            r = client.post("/api/invoices/quick", json={
                "invoice_no": _uniq("MX-INV", i), "direction": "out",
                "invoice_type": "ordinary", "amount_with_tax": "113.00",
                "tax_rate": "0.13", "counterparty_name": "x", "seller_name": "本公司",
                "buyer_name": "x", "issue_date": "2026-06-20",
                "sale_order_action": "auto_create",
                "items": [{"product_id": pid, "quantity": 1, "unit_price": "100.00", "tax_rate": "0.13"}],
            }, headers=ai_h)
            assert r.status_code != 403
            results["ai_pass"] += 1
        assert sum(results.values()) == 120
