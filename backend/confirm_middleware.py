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
from typing import Optional

logger = logging.getLogger("inventory")

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
    """内存存储待确认请求，单进程内有效"""

    def __init__(self):
        self._pending: dict[str, dict] = {}

    def put(self, token: str, entry: dict):
        self._pending[token] = entry

    def get(self, token: str) -> Optional[dict]:
        entry = self._pending.get(token)
        if entry is None:
            return None
        # 检查是否过期
        if time.time() - entry["created_at"] > TOKEN_TTL:
            self.remove(token)
            return None
        return entry

    def remove(self, token: str):
        self._pending.pop(token, None)

    def list_pending(self) -> list[dict]:
        """返回所有未过期的待确认请求"""
        now = time.time()
        expired = [t for t, e in self._pending.items() if now - e["created_at"] > TOKEN_TTL]
        for t in expired:
            del self._pending[t]
        return [
            {
                "confirm_token": token,
                "method": e["method"],
                "path": e["path"],
                "summary": e.get("summary", ""),
                "created_at": e["created_at"],
                "expires_at": e["created_at"] + TOKEN_TTL,
            }
            for token, e in self._pending.items()
        ]


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
    }
    resource_cn = resource_map.get(resource, resource)

    if method == "DELETE":
        res_id = parts[2] if len(parts) > 2 else "?"
        return f"删除 {resource_cn} #{res_id}"
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