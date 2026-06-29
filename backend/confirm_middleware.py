"""
危险操作确认中间件

拦截 AI 发出的 DELETE 和特定 PUT 请求，生成确认 token，
返回 202 Accepted，等待用户在前端确认后才真正执行。

触发条件：
  - 请求头 X-Operator == "ai"
  - 请求方法为 DELETE，或 PUT 且路径匹配危险操作白名单

流程：
  1. AI 发起 DELETE/PUT → 中间件拦截 → 存储请求 → 返回 202 + confirm_token
  2. 前端轮询 /api/confirm/pending → 获取待确认列表 → 弹出确认对话框
  3. 用户点确认 → POST /api/confirm/{token} → 中间件重放原始请求 → 返回实际结果
  4. 用户点取消 → DELETE /api/confirm/{token} → 丢弃请求 → 返回 200
"""

import json
import time
import uuid
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger("inventory")


@contextmanager
def _bypass_write_guard():
    """临时放行 ORM/SQL/DDL 写拦截

    ConfirmStore 在以下场景必须直接写 SQL：
      1. 模块导入时建表（_init_db，DDL）—— 还在 WritePermissionMiddleware 之外
      2. AIGatewayMiddleware 调用 put() 暂存待确认请求 —— 还在 WritePermissionMiddleware 之外
      3. confirm 路由调用 remove/cleanup_expired

    DDL（CREATE TABLE）只能由 maintenance_mode 绕过（contextvar 无效），
    因此统一使用 set_maintenance_mode。操作均为单条短 SQL，影响窗口极小。
    """
    from database import set_maintenance_mode
    set_maintenance_mode(True)
    try:
        yield
    finally:
        set_maintenance_mode(False)

# ── 配置 ──────────────────────────────────────────────

# Token 有效期（秒）
TOKEN_TTL = 300

# 需要确认的 PUT 路径白名单（子串匹配）
# 只拦截状态变更等不可逆操作，普通编辑不需要确认
DANGEROUS_PUT_PATTERNS = (
    "/cancel",        # 取消订单
    "/void",          # 作废
    "/confirm",       # 确认（可能导致后续联动不可逆）
)

# 需要确认的 POST 路径子串（红冲/冲销/取消等不可逆操作）
DANGEROUS_POST_PATTERNS = (
    "/reverse",       # 红冲/冲销
    "/cancel",        # 取消订单（冲红凭证+回退库存）
    "/dispose",       # 固定资产处置
)

# 不需要确认的路径（精确前缀匹配，优先级高于白名单）
# 例如备份接口的 DELETE 不需要确认
SKIP_PATH_PREFIXES = (
    "/api/confirm",   # 确认 API 本身不拦截
    "/api/upload",    # 图片上传/删除不拦截
    "/api/backup",    # 备份接口不拦截
    "/api/health",    # 健康检查不拦截
    "/api/enums",     # 枚举查询不拦截
    "/api/accounts",  # 账本管理暂不拦截（低风险）
)


# ── 待确认请求存储 ────────────────────────────────────

class ConfirmStore:
    """SQLite 持久化存储待确认请求

    进程重启或 uvicorn --reload 重启 worker 后 token 不丢失。
    多 worker 也能共享同一份数据。
    """

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """创建 pending_confirms 表（幂等）"""
        from database import _engine
        from sqlalchemy import text
        with _bypass_write_guard(), _engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS pending_confirms ("
                "  token VARCHAR(32) PRIMARY KEY,"
                "  method VARCHAR(10) NOT NULL,"
                "  path VARCHAR(500) NOT NULL,"
                "  summary VARCHAR(500) DEFAULT '',"
                "  body BLOB,"
                "  query_string BLOB,"
                "  headers JSON,"
                "  created_at REAL NOT NULL"
                ")"
            ))
            conn.commit()

    def put(self, token: str, entry: dict):
        from database import _engine
        from sqlalchemy import text
        with _bypass_write_guard(), _engine.connect() as conn:
            # 先删除可能存在的同 token 旧记录（幂等）
            conn.execute(text("DELETE FROM pending_confirms WHERE token = :t"), {"t": token})
            conn.execute(text(
                "INSERT INTO pending_confirms "
                "(token, method, path, summary, body, query_string, headers, created_at) "
                "VALUES (:token, :method, :path, :summary, :body, :qs, :headers, :ca)"
            ), {
                "token": token,
                "method": entry["method"],
                "path": entry["path"],
                "summary": entry.get("summary", ""),
                "body": entry.get("body", b""),
                "qs": entry.get("query_string", b""),
                "headers": json.dumps([
                    [k.decode("latin-1") if isinstance(k, bytes) else k,
                     v.decode("latin-1") if isinstance(v, bytes) else v]
                    for k, v in entry.get("headers", [])
                ]),
                "ca": entry["created_at"],
            })
            conn.commit()

    def get(self, token: str) -> Optional[dict]:
        from database import _engine
        from sqlalchemy import text
        with _engine.connect() as conn:
            row = conn.execute(text(
                "SELECT method, path, summary, body, query_string, headers, created_at "
                "FROM pending_confirms WHERE token = :t"
            ), {"t": token}).fetchone()
            if row is None:
                return None
            # 检查是否过期
            if time.time() - row[6] > TOKEN_TTL:
                self.remove(token)
                return None
            # 还原 headers 格式：[(bytes, bytes), ...]
            headers_raw = json.loads(row[5]) if row[5] else []
            headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers_raw]
            return {
                "method": row[0],
                "path": row[1],
                "summary": row[2],
                "body": row[3] if row[3] else b"",
                "query_string": row[4] if row[4] else b"",
                "headers": headers,
                "created_at": row[6],
            }

    def remove(self, token: str):
        from database import _engine
        from sqlalchemy import text
        with _bypass_write_guard(), _engine.connect() as conn:
            conn.execute(text("DELETE FROM pending_confirms WHERE token = :t"), {"t": token})
            conn.commit()

    def list_pending(self) -> list[dict]:
        """返回所有未过期的待确认请求"""
        now = time.time()
        from database import _engine
        from sqlalchemy import text
        with _bypass_write_guard(), _engine.connect() as conn:
            # 先清理过期
            conn.execute(text(
                "DELETE FROM pending_confirms WHERE :now - created_at > :ttl"
            ), {"now": now, "ttl": TOKEN_TTL})
            conn.commit()
            rows = conn.execute(text(
                "SELECT token, method, path, summary, created_at "
                "FROM pending_confirms ORDER BY created_at ASC"
            )).fetchall()
            return [
                {
                    "confirm_token": r[0],
                    "method": r[1],
                    "path": r[2],
                    "summary": r[3],
                    "created_at": r[4],
                    "expires_at": r[4] + TOKEN_TTL,
                }
                for r in rows
            ]

    def cleanup_expired(self):
        """启动时清理过期 token"""
        from database import _engine
        from sqlalchemy import text
        now = time.time()
        with _bypass_write_guard(), _engine.connect() as conn:
            result = conn.execute(text(
                "DELETE FROM pending_confirms WHERE :now - created_at > :ttl"
            ), {"now": now, "ttl": TOKEN_TTL})
            conn.commit()
            if result.rowcount > 0:
                logger.info("[ConfirmStore] 启动时清理了 %d 个过期 token", result.rowcount)


# 全局单例
confirm_store = ConfirmStore()


# ── 工具函数 ──────────────────────────────────────────

def _should_confirm(method: str, path: str, operator: str) -> bool:
    """判断请求是否需要确认"""
    # 只拦截 AI 操作
    if operator != "ai":
        return False

    # 跳过无需确认的路径
    for prefix in SKIP_PATH_PREFIXES:
        if path.startswith(prefix):
            return False

    # DELETE 一律拦截
    if method == "DELETE":
        return True

    # PUT 只拦截危险操作
    if method == "PUT":
        for pattern in DANGEROUS_PUT_PATTERNS:
            if pattern in path:
                return True

    # POST 只拦截红冲/冲销等不可逆操作
    if method == "POST":
        for pattern in DANGEROUS_POST_PATTERNS:
            if pattern in path:
                return True

    return False


def _generate_token() -> str:
    return uuid.uuid4().hex[:16]


def _make_summary(method: str, path: str, body: Optional[bytes]) -> str:
    """生成人类可读的操作摘要"""
    # 从路径提取资源类型和ID
    parts = path.strip("/").split("/")
    resource = parts[1] if len(parts) > 1 else "未知"
    resource_map = {
        "products": "商品", "suppliers": "供应商", "customers": "客户",
        "purchases": "采购单", "sales": "销售单", "inventory": "库存",
        "invoices": "发票", "expenses": "费用",
        "income-tax-report": "企业所得税报表", "opening-balances": "期初余额",
        "financial-reports": "财务报表", "cash-flows": "现金流量",
        "reconciliations": "对账记录",
        "bank": "银行", "transaction": "银行交易",
        "receipts": "收款", "payments": "付款",
    }
    resource_cn = resource_map.get(resource, resource)

    if method == "DELETE":
        res_id = parts[2] if len(parts) > 2 else "?"
        return f"删除 {resource_cn} #{res_id}"
    elif method == "POST" and "/reverse" in path:
        res_id = parts[-2] if len(parts) >= 2 else "?"
        return f"红冲 {resource_cn} #{res_id}"
    elif method == "POST" and "/cancel" in path:
        res_id = parts[-2] if len(parts) >= 2 else "?"
        return f"取消 {resource_cn} #{res_id}"
    elif method == "POST" and "/dispose" in path:
        res_id = parts[-2] if len(parts) >= 2 else "?"
        return f"处置 {resource_cn} #{res_id}"
    elif method == "PUT":
        res_id = parts[2] if len(parts) > 2 else "?"
        if "/cancel" in path:
            return f"取消 {resource_cn} #{res_id}"
        if "/void" in path:
            return f"作废 {resource_cn} #{res_id}"
        if "/confirm" in path:
            return f"确认 {resource_cn} #{res_id}"
        return f"修改 {resource_cn} #{res_id}"
    return f"{method} {path}"


# ── ASGI 中间件 ───────────────────────────────────────

class ConfirmMiddleware:
    """ASGI 中间件：拦截 AI 危险操作，生成确认 token

    注册方式（在 main.py 中，CORS 之后）：
        app.add_middleware(ConfirmMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope.get("path", "")
        headers_raw = scope.get("headers", [])

        # 解析 headers
        headers = {}
        for key, val in headers_raw:
            headers[key.decode("latin-1").lower()] = val.decode("latin-1")

        operator = headers.get("x-operator", "user")

        # 判断是否需要确认
        if not _should_confirm(method, path, operator):
            await self.app(scope, receive, send)
            return

        # 读取请求体
        body_parts = []
        while True:
            message = await receive()
            body_parts.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        body = b"".join(body_parts)

        # 生成确认 token 并存储
        token = _generate_token()
        entry = {
            "method": method,
            "path": path,
            "headers": headers_raw,
            "body": body,
            "query_string": scope.get("query_string", b""),
            "summary": _make_summary(method, path, body),
            "created_at": time.time(),
        }
        confirm_store.put(token, entry)

        logger.info("[Confirm] AI危险操作已拦截: %s %s → token=%s", method, path, token)

        # 返回 202 Accepted + 确认信息
        response_body = json.dumps({
            "confirm_token": token,
            "message": f"操作需要确认: {entry['summary']}",
            "summary": entry["summary"],
            "method": method,
            "path": path,
            "expires_at": entry["created_at"] + TOKEN_TTL,
            "detail": "此操作由AI发起，需要用户在前端确认后方可执行。"
        }, ensure_ascii=False).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": 202,
            "headers": [
                [b"content-type", b"application/json; charset=utf-8"],
                [b"content-length", str(len(response_body)).encode()],
                [b"x-confirm-token", token.encode()],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": response_body,
        })