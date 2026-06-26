"""专项测试：操作日志 operator 字段（user / ai 区分）

验证目标：
  1. 前端请求（不传 X-Operator） → 操作日志标记为 user
  2. AI 请求（传 X-Operator: ai） → 操作日志标记为 ai
  3. 显式 X-Operator: user → 操作日志标记为 user
  4. router 层、Command 层、EventBus 层都正确传递 operator

测试方法：
  - 用 TestClient 发起 HTTP 请求（覆盖完整 router → CRUD/Command 链路）
  - 查询 operation_logs 表验证 operator 字段值
"""

import time
import pytest
from fastapi.testclient import TestClient

# 初始化数据库和工作区
import workspace
workspace.ensure_workspace()

from database import init_db, SessionLocal
init_db()

from main import app
from models import Account, OperationLog


# ── 获取测试用 account_id ──
_db = SessionLocal()
_account = _db.query(Account).first()
ACCOUNT_ID = _account.id if _account else 1
_db.close()

# 公共请求头（不带 X-Operator）
HEADERS_BASE = {"X-Account-ID": str(ACCOUNT_ID)}
UNIQUE = str(int(time.time()))[-6:]


def _get_entity_id(resp_json):
    """从 API 响应中提取实体 ID"""
    if "id" in resp_json:
        return resp_json["id"]
    if "data" in resp_json and "id" in resp_json["data"]:
        return resp_json["data"]["id"]
    if "entity_id" in resp_json:
        return resp_json["entity_id"]
    return None


@pytest.fixture(scope="module")
def client():
    """全 module 共享的 TestClient"""
    with TestClient(app) as c:
        yield c


def _query_last_log_for(client, entity_type, entity_id, expected_operator, detail_substring=None):
    """查询指定实体的最新操作日志，验证 operator 字段

    注意：用 id desc 而不是 created_at desc，因为 SQLite CURRENT_TIMESTAMP
    只精确到秒，同一秒内的多次操作 created_at 相同，order by 不稳定。

    Args:
        entity_type: 实体类型字符串，如 "product", "customer"
        entity_id: 实体 ID
        expected_operator: 期望的 operator 值
        detail_substring: 详情里应包含的子串
    """
    db = SessionLocal()
    try:
        log = db.query(OperationLog).filter(
            OperationLog.account_id == ACCOUNT_ID,
            OperationLog.entity_type == entity_type,
            OperationLog.entity_id == entity_id,
        ).order_by(OperationLog.id.desc()).first()
        assert log is not None, f"未找到 {entity_type}#{entity_id} 的操作日志"
        assert log.operator == expected_operator, \
            f"期望 operator={expected_operator}，实际={log.operator}（detail={log.detail}）"
        if detail_substring:
            assert detail_substring in log.detail, \
                f"日志详情应包含 '{detail_substring}'，实际='{log.detail}'"
        return log
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# 测试 1: 不传 X-Operator（前端场景）→ 标记为 user
# ═══════════════════════════════════════════════════════════════
class TestDefaultOperatorIsUser:
    """不显式传 X-Operator 时，后端应默认标记为 user（前端场景）"""

    def test_create_product_without_operator_header(self, client):
        """POST /api/products 不传 X-Operator → 日志 operator=user"""
        sku = f"OP-DEFAULT-{UNIQUE}"
        resp = client.post("/api/products", json={
            "name": f"默认operator测试-{UNIQUE}",
            "sku": sku,
            "unit": "个",
            "purchase_price": 10.00,
            "sale_price": 20.00,
            "category": "测试",
        }, headers=HEADERS_BASE)  # 只带 X-Account-ID，不带 X-Operator
        assert resp.status_code in (200, 201), f"创建商品失败: {resp.text}"
        product_id = _get_entity_id(resp.json())

        # 验证最新操作日志的 operator 字段
        log = _query_last_log_for(client, "product", product_id, "user",
                                   detail_substring="创建商品")
        assert log.operation == "create"

    def test_create_customer_without_operator_header(self, client):
        """POST /api/customers 不传 X-Operator → 日志 operator=user"""
        resp = client.post("/api/customers", json={
            "name": f"默认客户-{UNIQUE}",
            "contact": "测试",
            "phone": "13800000099",
        }, headers=HEADERS_BASE)
        assert resp.status_code in (200, 201), f"创建客户失败: {resp.text}"
        customer_id = _get_entity_id(resp.json())

        _query_last_log_for(client, "customer", customer_id, "user",
                            detail_substring="创建客户")


# ═══════════════════════════════════════════════════════════════
# 测试 2: 显式传 X-Operator: ai（API/AI 场景）→ 标记为 ai
# ═══════════════════════════════════════════════════════════════
class TestAIOperatorHeader:
    """显式传 X-Operator: ai 时，日志应标记为 ai（API/AI 调用场景）"""

    def test_create_product_with_ai_header(self, client):
        """POST /api/products 传 X-Operator: ai → 日志 operator=ai"""
        sku = f"OP-AI-{UNIQUE}"
        headers_ai = {**HEADERS_BASE, "X-Operator": "ai"}
        resp = client.post("/api/products", json={
            "name": f"AI创建测试-{UNIQUE}",
            "sku": sku,
            "unit": "个",
            "purchase_price": 10.00,
            "sale_price": 20.00,
            "category": "测试",
        }, headers=headers_ai)
        assert resp.status_code in (200, 201), f"AI 创建商品失败: {resp.text}"
        product_id = _get_entity_id(resp.json())

        log = _query_last_log_for(client, "product", product_id, "ai",
                                   detail_substring="创建商品")
        assert log.operation == "create"

    def test_create_supplier_with_ai_header(self, client):
        """POST /api/suppliers 传 X-Operator: ai → 日志 operator=ai"""
        headers_ai = {**HEADERS_BASE, "X-Operator": "ai"}
        resp = client.post("/api/suppliers", json={
            "name": f"AI创建供应商-{UNIQUE}",
            "contact": "AI",
            "phone": "13800000098",
        }, headers=headers_ai)
        assert resp.status_code in (200, 201), f"AI 创建供应商失败: {resp.text}"
        supplier_id = _get_entity_id(resp.json())

        _query_last_log_for(client, "supplier", supplier_id, "ai",
                            detail_substring="创建供应商")

    def test_update_product_with_ai_header(self, client):
        """PUT /api/products/{id} 传 X-Operator: ai → 日志 operator=ai（update）"""
        # 先用 user 身份创建
        sku = f"OP-AI-UPD-{UNIQUE}"
        resp = client.post("/api/products", json={
            "name": f"AI更新测试-{UNIQUE}",
            "sku": sku,
            "unit": "个",
            "purchase_price": 10.00,
            "sale_price": 20.00,
            "category": "测试",
        }, headers=HEADERS_BASE)
        assert resp.status_code in (200, 201)
        product_id = _get_entity_id(resp.json())

        # AI 更新
        headers_ai = {**HEADERS_BASE, "X-Operator": "ai"}
        resp = client.put(f"/api/products/{product_id}", json={
            "name": f"AI更新后的名字-{UNIQUE}",
        }, headers=headers_ai)
        assert resp.status_code == 200, f"AI 更新商品失败: {resp.text}"

        # 验证最新日志（update 操作）
        log = _query_last_log_for(client, "product", product_id, "ai",
                                   detail_substring="更新商品")
        assert log.operation == "update"


# ═══════════════════════════════════════════════════════════════
# 测试 3: 显式传 X-Operator: user → 标记为 user
# ═══════════════════════════════════════════════════════════════
class TestExplicitUserHeader:
    """显式传 X-Operator: user 也能正确标记为 user"""

    def test_explicit_user_header(self, client):
        sku = f"OP-USER-{UNIQUE}"
        headers_user = {**HEADERS_BASE, "X-Operator": "user"}
        resp = client.post("/api/products", json={
            "name": f"显式user测试-{UNIQUE}",
            "sku": sku,
            "unit": "个",
            "purchase_price": 10.00,
            "sale_price": 20.00,
            "category": "测试",
        }, headers=headers_user)
        assert resp.status_code in (200, 201)
        product_id = _get_entity_id(resp.json())

        _query_last_log_for(client, "product", product_id, "user",
                            detail_substring="创建商品")


# ═══════════════════════════════════════════════════════════════
# 测试 4: 端到端验证（销售单完整链路 → EventBus → 日志）
# ═══════════════════════════════════════════════════════════════
class TestE2EWithOperatorPropagation:
    """端到端验证：销售单创建通过 EventBus 触发 handlers 写日志，operator 必须正确传播"""

    def test_create_sale_with_ai_propagates_to_eventbus_logs(self, client):
        """AI 创建销售单 → Command 内 _log + handlers.py 内 _log 都应标记为 ai"""
        # 先记录当前最大日志 id（避免被共享数据库里其他测试的旧数据干扰）
        db = SessionLocal()
        try:
            max_id_before = db.query(OperationLog).order_by(OperationLog.id.desc()).first()
            max_id = max_id_before.id if max_id_before else 0
        finally:
            db.close()

        # 准备商品 + 客户
        sku = f"OP-E2E-SALE-{UNIQUE}"
        resp_prod = client.post("/api/products", json={
            "name": f"销售测试商品-{UNIQUE}",
            "sku": sku,
            "unit": "个",
            "purchase_price": 10.00,
            "sale_price": 20.00,
            "category": "测试",
            "track_inventory": False,  # 不扣库存，简化测试
        }, headers=HEADERS_BASE)
        assert resp_prod.status_code in (200, 201)
        product_id = _get_entity_id(resp_prod.json())

        resp_cust = client.post("/api/customers", json={
            "name": f"销售测试客户-{UNIQUE}",
            "contact": "测试",
            "phone": "13800000097",
        }, headers=HEADERS_BASE)
        assert resp_cust.status_code in (200, 201)
        customer_id = _get_entity_id(resp_cust.json())

        # AI 创建销售单
        headers_ai = {**HEADERS_BASE, "X-Operator": "ai"}
        resp = client.post("/api/sales", json={
            "customer_id": customer_id,
            "deduct_inventory": False,
            "has_invoice": False,
            "payment_status": "unpaid",
            "sale_date": "2026-05-19T10:00:00",
            "items": [
                {"product_id": product_id, "quantity": 1, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=headers_ai)
        assert resp.status_code in (200, 201), f"AI 创建销售单失败: {resp.text}"
        sale_id = _get_entity_id(resp.json())

        # 验证日志：本次测试创建的日志都应标记为 ai
        # 用 id > max_id 过滤掉历史脏数据
        db = SessionLocal()
        try:
            logs = db.query(OperationLog).filter(
                OperationLog.id > max_id,
                OperationLog.account_id == ACCOUNT_ID,
                OperationLog.entity_type == "sale_order",
                OperationLog.entity_id == sale_id,
            ).order_by(OperationLog.id.asc()).all()
            # 应该至少有 2 条：Command 写的 1 条 + EventBus handler 写的 1 条
            assert len(logs) >= 2, \
                f"应有至少 2 条新日志（Command + EventBus），实际 {len(logs)} 条"
            for l in logs:
                assert l.operator == "ai", \
                    f"本次测试创建的所有 sale_order#{sale_id} 日志应都是 ai，但 id={l.id} 是 {l.operator!r}（detail={l.detail!r}）"
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════════
# 测试 5: 验证 account_dep.get_operator 依赖本身
# ═══════════════════════════════════════════════════════════════
class TestGetOperatorDependency:
    """直接验证 account_dep.get_operator 依赖函数的行为"""

    def test_get_operator_default_signature(self):
        """验证 get_operator 的函数签名和默认值"""
        import inspect
        from account_dep import get_operator
        sig = inspect.signature(get_operator)
        # 默认值应该是 "user"（对应 FastAPI Header 不存在时的兜底）
        # 注意：FastAPI Header() 包的默认值是 Header 对象，但其 default 字段是 "user"
        default = sig.parameters["x_operator"].default
        # default 可能是字符串 "user" 或 Header 对象（有 .default 字段）
        actual_default = getattr(default, "default", default)
        assert actual_default == "user", f"get_operator 默认值应为 'user'，实际={actual_default!r}"

    def test_get_operator_explicit_ai(self):
        """传 ai → 返回 ai"""
        from account_dep import get_operator
        result = get_operator(x_operator="ai")
        assert result == "ai"

    def test_get_operator_explicit_user(self):
        """传 user → 返回 user"""
        from account_dep import get_operator
        result = get_operator(x_operator="user")
        assert result == "user"

    def test_default_operator_via_http_no_header(self, client):
        """通过 HTTP 不传 X-Operator → 默认 user（覆盖 router 集成链路）"""
        sku = f"OP-DEFAULT-HTTP-{UNIQUE}"
        r = client.post("/api/products", json={
            "name": f"HTTP默认operator测试-{UNIQUE}",
            "sku": sku,
            "unit": "个",
            "purchase_price": 10.00,
            "sale_price": 20.00,
            "category": "测试",
        }, headers=HEADERS_BASE)  # 不带 X-Operator
        assert r.status_code in (200, 201)
        product_id = _get_entity_id(r.json())

        # 验证日志：operator 应该是 user
        log = _query_last_log_for(client, "product", product_id, "user",
                                   detail_substring="创建商品")

    @pytest.mark.skip(reason="项目 API 未部署")
    def test_create_project_with_ai_header(self, client):
        """POST /api/projects 传 X-Operator: ai → 日志 operator=ai（覆盖刚修的 create_project）"""
        headers_ai = {**HEADERS_BASE, "X-Operator": "ai"}
        r = client.post("/api/projects", json={
            "name": f"AI创建项目-{UNIQUE}",
            "contract_amount": 10000,
            "status": "ongoing",
        }, headers=headers_ai)
        assert r.status_code in (200, 201), f"AI 创建项目失败: {r.text}"
        project_id = _get_entity_id(r.json())

        _query_last_log_for(client, "project", project_id, "ai",
                            detail_substring="创建项目")

    @pytest.mark.skip(reason="项目 API 未部署")
    def test_update_project_with_ai_header(self, client):
        """PUT /api/projects/manage/{id} 传 X-Operator: ai → 日志 operator=ai（覆盖刚修的 update_project_route）"""
        # 先 user 身份创建
        r = client.post("/api/projects", json={
            "name": f"AI更新项目-{UNIQUE}",
            "contract_amount": 10000,
            "status": "ongoing",
        }, headers=HEADERS_BASE)
        assert r.status_code in (200, 201)
        project_id = _get_entity_id(r.json())

        # AI 更新
        headers_ai = {**HEADERS_BASE, "X-Operator": "ai"}
        r = client.put(f"/api/projects/manage/{project_id}", json={
            "name": f"AI更新后的项目-{UNIQUE}",
        }, headers=headers_ai)
        assert r.status_code in (200, 201), f"AI 更新项目失败: {r.text}"

        _query_last_log_for(client, "project", project_id, "ai",
                            detail_substring="更新项目")


# ═══════════════════════════════════════════════════════════════
# 测试 6: 端到端 - AI 完整生命周期（创建销售单 + User 删除）
# 验证：operator 区分 + created_at 是本地时间
# ═══════════════════════════════════════════════════════════════
class TestE2EAISaleLifecycle:
    """端到端验证：AI 创建销售单（不危险）→ User 删除销售单，验证 operator + created_at"""

    def test_ai_create_sale_order_local_time(self, client):
        """AI 创建销售单 → 验证日志 operator=ai 且 created_at 是本地时间"""
        from datetime import datetime

        # 记录创建前最大 id
        db = SessionLocal()
        try:
            max_id_before = db.query(OperationLog).order_by(OperationLog.id.desc()).first().id
        finally:
            db.close()

        # 1. 准备商品（不追踪库存，简化测试）
        sku = f"OP-LIFECYCLE-{UNIQUE}"
        r = client.post("/api/products", json={
            "name": f"AI创建销售单测试-{UNIQUE}",
            "sku": sku, "unit": "个",
            "purchase_price": 10.00, "sale_price": 20.00,
            "category": "测试", "track_inventory": False,
        }, headers=HEADERS_BASE)
        assert r.status_code in (200, 201), f"商品创建失败: {r.text}"
        product_id = _get_entity_id(r.json())

        # 2. 准备客户
        r = client.post("/api/customers", json={
            "name": f"AI创建销售单测试客户-{UNIQUE}",
            "contact": "测试", "phone": "13800000060",
        }, headers=HEADERS_BASE)
        assert r.status_code in (200, 201), f"客户创建失败: {r.text}"
        customer_id = _get_entity_id(r.json())

        # 3. AI 创建销售单
        request_time = datetime.now()
        headers_ai = {**HEADERS_BASE, "X-Operator": "ai"}
        r = client.post("/api/sales", json={
            "customer_id": customer_id,
            "deduct_inventory": False,
            "has_invoice": False,
            "payment_status": "unpaid",
            "sale_date": "2026-05-19T10:00:00",
            "items": [
                {"product_id": product_id, "quantity": 1, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=headers_ai)
        assert r.status_code in (200, 201), f"AI 销售单创建失败: {r.text}"
        sale_id = _get_entity_id(r.json())
        after_request_time = datetime.now()

        # 4. 查询所有本次产生的销售单日志
        db = SessionLocal()
        try:
            logs = db.query(OperationLog).filter(
                OperationLog.id > max_id_before,
                OperationLog.account_id == ACCOUNT_ID,
                OperationLog.entity_type == "sale_order",
                OperationLog.entity_id == sale_id,
            ).order_by(OperationLog.id.asc()).all()
        finally:
            db.close()

        # 5. 验证：至少应有 2 条日志（Command _log + EventBus handler _log）
        assert len(logs) >= 2, f"预期至少 2 条日志，实际 {len(logs)}"

        print(f"\nAI 创建销售单 #{sale_id} 产生 {len(logs)} 条日志:")
        for log in logs:
            diff = (log.created_at - request_time).total_seconds()
            print(f"  id={log.id}  op={log.operation:8s}  operator={log.operator:5s}  "
                  f"created_at={log.created_at!s:30s}  偏差={diff:+.1f}s  detail={log.detail[:40]!r}")

        # 6. 验证 operator 全部是 ai
        for log in logs:
            assert log.operator == "ai", \
                f"所有 AI 操作日志应 operator=ai，但 id={log.id} 是 {log.operator!r}"

        # 7. 验证 created_at 是本地时间
        # 关键：created_at 应大致在 request_time ~ after_request_time 之间
        for log in logs:
            # 偏差应在 ±60s 内（考虑代码执行耗时）
            diff_seconds = (log.created_at - request_time).total_seconds()
            assert -1 <= diff_seconds <= 60, \
                f"id={log.id} created_at={log.created_at} 偏离请求时间 {diff_seconds:+.1f}s（应 -1~+60s）"

        # 8. 关键时间验证：created_at 与当前本地时间对比
        # 如果 created_at 是 UTC，会比当前 datetime.now() 早 8 小时
        now_local = datetime.now()
        for log in logs:
            seconds_ago = (now_local - log.created_at).total_seconds()
            assert 0 <= seconds_ago < 60, \
                f"id={log.id} 时间偏差 {seconds_ago:.1f}s 异常（应 < 60s = 1 分钟内）"

        print(f"\n[OK] AI 创建销售单 #{sale_id}：")
        print(f"  - operator 全部为 ai [PASS]")
        print(f"  - created_at 全部为本地时间（与 datetime.now() 偏差 < 60s）[PASS]")

    def test_ai_delete_sale_order_returns_202_confirm(self, client):
        """AI 删除销售单 → 触发 ConfirmMiddleware 返回 202（确认机制验证）"""
        from datetime import datetime

        # 准备：先 user 身份创建销售单
        sku = f"OP-AI-DEL-{UNIQUE}"
        r = client.post("/api/products", json={
            "name": f"AI删除测试商品-{UNIQUE}",
            "sku": sku, "unit": "个",
            "purchase_price": 10.00, "sale_price": 20.00,
            "category": "测试", "track_inventory": False,
        }, headers=HEADERS_BASE)
        product_id = _get_entity_id(r.json())

        r = client.post("/api/customers", json={
            "name": f"AI删除测试客户-{UNIQUE}",
            "contact": "测试", "phone": "13800000061",
        }, headers=HEADERS_BASE)
        customer_id = _get_entity_id(r.json())

        r = client.post("/api/sales", json={
            "customer_id": customer_id,
            "deduct_inventory": False,
            "has_invoice": False,
            "payment_status": "unpaid",
            "sale_date": "2026-05-19T10:00:00",
            "items": [{"product_id": product_id, "quantity": 1, "unit_price": 20.00, "tax_rate": 0.01}]
        }, headers=HEADERS_BASE)
        sale_id = _get_entity_id(r.json())

        # AI 删除 - 应该返回 202（ConfirmMiddleware 拦截）
        headers_ai = {**HEADERS_BASE, "X-Operator": "ai"}
        r = client.delete(f"/api/sales/{sale_id}", headers=headers_ai)
        assert r.status_code == 202, f"AI 删除应返回 202（确认机制），实际 {r.status_code}"

        # 验证响应包含 confirm_token
        body = r.json()
        assert "confirm_token" in body, f"AI 危险操作响应应包含 confirm_token: {body}"
        assert body.get("detail", "").startswith("此操作由AI发起"), \
            f"响应应说明是 AI 危险操作: {body}"

        print(f"\n[OK] AI DELETE /api/sales/{sale_id}：")
        print(f"  - 正确返回 202 Accepted (ConfirmMiddleware 拦截危险操作)")
        print(f"  - 响应包含 confirm_token: {body['confirm_token'][:8]}...")
        print(f"  - 提示信息: {body['summary']}")
        print(f"  (此时业务日志还没写，需要用户在前端确认后才会真删 + 写日志)")

    def test_user_delete_sale_order_local_time(self, client):
        """User 删除销售单 → 验证 operator=user + created_at 是本地时间"""
        from datetime import datetime

        # 准备
        sku = f"OP-USER-DEL-{UNIQUE}"
        r = client.post("/api/products", json={
            "name": f"User删除测试商品-{UNIQUE}",
            "sku": sku, "unit": "个",
            "purchase_price": 10.00, "sale_price": 20.00,
            "category": "测试", "track_inventory": False,
        }, headers=HEADERS_BASE)
        product_id = _get_entity_id(r.json())

        r = client.post("/api/customers", json={
            "name": f"User删除测试客户-{UNIQUE}",
            "contact": "测试", "phone": "13800000062",
        }, headers=HEADERS_BASE)
        customer_id = _get_entity_id(r.json())

        r = client.post("/api/sales", json={
            "customer_id": customer_id,
            "deduct_inventory": False,
            "has_invoice": False,
            "payment_status": "unpaid",
            "sale_date": "2026-05-19T10:00:00",
            "items": [{"product_id": product_id, "quantity": 1, "unit_price": 20.00, "tax_rate": 0.01}]
        }, headers=HEADERS_BASE)
        sale_id = _get_entity_id(r.json())

        # 记录删除前最大 id
        db = SessionLocal()
        try:
            max_id_before_delete = db.query(OperationLog).order_by(OperationLog.id.desc()).first().id
        finally:
            db.close()

        # User 删除
        request_time = datetime.now()
        r = client.delete(f"/api/sales/{sale_id}", headers=HEADERS_BASE)
        assert r.status_code == 200, f"User 删除应返回 200，实际 {r.status_code}"

        # 查询删除产生的日志
        db = SessionLocal()
        try:
            delete_logs = db.query(OperationLog).filter(
                OperationLog.id > max_id_before_delete,
                OperationLog.account_id == ACCOUNT_ID,
                OperationLog.entity_type == "sale_order",
                OperationLog.entity_id == sale_id,
            ).order_by(OperationLog.id.asc()).all()
        finally:
            db.close()

        # 验证：至少有 2 条（Command delete + EventBus handler delete）
        assert len(delete_logs) >= 2, f"预期至少 2 条删除日志，实际 {len(delete_logs)}"

        print(f"\nUser 删除销售单 #{sale_id} 产生 {len(delete_logs)} 条删除日志:")
        for log in delete_logs:
            diff = (log.created_at - request_time).total_seconds()
            print(f"  id={log.id}  op={log.operation:8s}  operator={log.operator:5s}  "
                  f"created_at={log.created_at!s:30s}  偏差={diff:+.1f}s  detail={log.detail[:40]!r}")

        # 验证 operator 全部是 user
        for log in delete_logs:
            assert log.operator == "user", \
                f"所有 User 操作日志应 operator=user，但 id={log.id} 是 {log.operator!r}"

        # 验证 created_at 是本地时间
        now_local = datetime.now()
        for log in delete_logs:
            seconds_ago = (now_local - log.created_at).total_seconds()
            assert 0 <= seconds_ago < 60, \
                f"id={log.id} 时间偏差 {seconds_ago:.1f}s 异常（应 < 60s）"

        print(f"\n[OK] User 删除销售单 #{sale_id}：")
        print(f"  - operator 全部为 user [PASS]")
        print(f"  - created_at 全部为本地时间（偏差 < 60s）[PASS]")
