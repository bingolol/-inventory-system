"""AI 接口网关 — 规范接口白名单 + 403 硬拦截

约束 AI Agent 只能调用"规范接口"，杜绝过度开发带来的多入口混乱：
  - 同一业务能力的增/改/删，对 AI 只暴露 1 个规范端点（如发票创建只走 /quick）。
  - 变体端点（已被合并的 /with-fixed-asset 等）对 AI 不再可调用。

拦截规则（仅对 X-Operator: ai 生效，前端 user 请求全部放行）：
  - GET / HEAD：查询全部放行
  - 写操作（POST/PUT/DELETE/PATCH）：命中白名单 → 放行；否则 → 403 + ai_instruction 指明规范替代

白名单 AI_CAPABILITIES 是"唯一真相源"，同时驱动：
  - 本中间件的放行判断
  - GET /api/_ai/capabilities 发现接口的返回内容

设计参考 confirm_middleware.py 的 ASGI 中间件模式。
"""

import re
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("inventory")


# ── 规范接口表（唯一真相源）──────────────────────────────

@dataclass
class Capability:
    """一个对 AI 开放的规范写接口"""
    method: str
    path: str                      # 可含 {id} 占位符，匹配时按段比对
    desc: str
    canonical: bool = True         # 是否为该能力的规范入口（False 表示仅记录，不放行）
    replaces: list[str] = field(default_factory=list)  # 该接口取代的旧/变体端点
    params_hint: str = ""          # 入参提示（字段说明）


# 路径按段规范化：{xxx} 占位符统一匹配任意单段
def _compile(path: str) -> re.Pattern:
    # 将 /{id} 形式的段转为正则 \d+（路径参数都是 int id）
    segs = []
    for seg in path.strip("/").split("/"):
        if seg.startswith("{") and seg.endswith("}"):
            segs.append(r"[^/]+")
        else:
            segs.append(re.escape(seg))
    return re.compile(r"^/" + "/".join(segs) + r"/?$")


# ── AI 规范写接口白名单 ─────────────────────────────────
# 原则：每个实体的增/改/删对 AI 只暴露 1 个规范入口。
# 新能力优先作为现有规范端点的可选字段（如 fixed_asset 嵌套对象），而非新增并行端点。
AI_CAPABILITIES: list[Capability] = [
    # ── 商品 / 合作伙伴 ──
    Capability("POST",   "/api/products",            "创建商品", params_hint="name,sku,unit,purchase_price,sale_price"),
    Capability("PUT",    "/api/products/{id}",       "更新商品", params_hint="可部分更新"),
    Capability("POST",   "/api/suppliers",           "创建供应商"),
    Capability("POST",   "/api/customers",           "创建客户"),
    Capability("PUT",    "/api/suppliers/{id}",      "更新供应商"),
    Capability("PUT",    "/api/customers/{id}",      "更新客户"),
    # ── 采购 / 销售 ──
    Capability("POST",   "/api/purchases",           "创建采购单（自动入库）", params_hint="supplier_id,items[]"),
    Capability("PUT",    "/api/purchases/{id}",      "更新采购单（含付款状态）"),
    Capability("POST",   "/api/sales",               "创建销售单（自动扣库存）", params_hint="customer_id,items[],deduct_inventory"),
    Capability("PUT",    "/api/sales/{id}",          "更新销售单（含付款状态）"),
    # ── 发票（创建对 AI 只走 /quick，变体已合并）──
    Capability(
        "POST", "/api/invoices/quick", "AI 快捷录发票（规范入口，支持 fixed_asset 嵌套对象）",
        replaces=["POST /api/invoices", "POST /api/invoices/with-fixed-asset"],
        params_hint="invoice_no,direction,invoices_type,amount_with_tax,tax_rate,counterparty_name,issue_date; 可选 fixed_asset{}",
    ),
    Capability("PUT",    "/api/invoices/{id}",       "更新发票（字段级 patch）"),
    Capability("POST",   "/api/invoices/{id}/certify", "认证进项专票"),
    # ── 库存 ──
    Capability("PUT",    "/api/inventory/{product_id}", "调整库存"),
    # ── 费用 / 财务 ──
    Capability("POST",   "/api/expenses",            "创建费用"),
    Capability("PUT",    "/api/expenses/{id}",       "更新费用"),
    Capability("POST",   "/api/opening-balances",    "创建期初余额"),
    Capability("POST",   "/api/cash-flows/transactions", "创建现金流水"),
    Capability("POST",   "/api/fixed-assets",        "创建固定资产（独立入账）"),
    Capability("PUT",    "/api/fixed-assets/{id}",   "更新固定资产"),
    # ── 个人流水 ──
    Capability("POST",   "/api/personal",            "创建个人流水记录"),
    Capability("PUT",    "/api/personal/{tx_id}",    "更新个人流水记录"),
    # ── 付款 / 收款 ──
    Capability("POST",   "/api/payments",            "创建付款"),
    Capability("POST",   "/api/receipts",            "创建收款"),
    # ── 备份 ──
    Capability("POST",   "/api/backup/hot",          "热备份"),
    # ── 删除类（危险操作，放行后由 ConfirmMiddleware 二次确认）──
    Capability("DELETE", "/api/products/{id}",       "删除商品"),
    Capability("DELETE", "/api/suppliers/{id}",      "删除供应商"),
    Capability("DELETE", "/api/customers/{id}",      "删除客户"),
    Capability("DELETE", "/api/purchases/{id}",      "删除采购单"),
    Capability("DELETE", "/api/sales/{id}",          "删除销售单"),
    Capability("DELETE", "/api/invoices/{id}",       "删除发票"),
    Capability("DELETE", "/api/expenses/{id}",       "删除费用"),
    Capability("DELETE", "/api/personal/{tx_id}",    "删除个人流水记录"),
]


# 预编译所有规范路径正则
_COMPILED = [(c, _compile(c.path)) for c in AI_CAPABILITIES]

# 永远放行的路径前缀（基础设施接口，AI 与前端共用）
_SKIP_PREFIXES = (
    "/api/_ai",        # 能力发现接口本身
    "/api/confirm",    # 确认流程接口
    "/api/health",
    "/api/enums",
    "/api/accounts",
)

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def _match(method: str, path: str) -> Optional[Capability]:
    """在白名单中查找匹配的 Capability，未命中返回 None"""
    for cap, pat in _COMPILED:
        if cap.method == method and pat.match(path):
            return cap
    return None


def _suggest(method: str, path: str) -> Optional[str]:
    """对被拦截的写请求，给出应使用的规范端点提示"""
    # /api/invoices 变体 → 统一指向 /quick
    if path.startswith("/api/invoices"):
        return "POST /api/invoices/quick（发票创建/带固定资产入账请用 quick + fixed_asset 字段）"
    # 通用：找同前缀的规范写接口
    prefix = "/" + path.strip("/").split("/")[1] if path.strip("/") else ""
    full_prefix = "/api/" + prefix
    candidates = [f"{c.method} {c.path}" for c in AI_CAPABILITIES if c.path.startswith(full_prefix)]
    if candidates:
        return "可用规范接口：" + "；".join(sorted(set(candidates)))
    return None


def _send_json(send, status: int, payload: dict):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    async def _go():
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json; charset=utf-8"],
                [b"content-length", str(len(body)).encode()],
            ],
        })
        await send({"type": "http.response.body", "body": body})
    return _go()


class AIGatewayMiddleware:
    """ASGI 中间件：对 X-Operator: ai 的写操作做白名单校验，非规范接口返回 403。

    注册（main.py，CORS 之后、ConfirmMiddleware 之前）：
        app.add_middleware(AIGatewayMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        path = scope.get("path", "")

        # 非写操作一律放行（查询不约束）
        if method not in WRITE_METHODS:
            await self.app(scope, receive, send)
            return

        # 基础设施接口放行
        if path.startswith(_SKIP_PREFIXES):
            await self.app(scope, receive, send)
            return

        # 识别调用者：只有 AI 才走网关校验
        operator = "user"
        for key, val in scope.get("headers", []):
            if key.decode("latin-1").lower() == "x-operator":
                operator = val.decode("latin-1")
                break

        if operator != "ai":
            await self.app(scope, receive, send)
            return

        # AI 写操作：校验白名单
        cap = _match(method, path)
        if cap is not None and cap.canonical:
            await self.app(scope, receive, send)
            return

        # 命中非规范写接口 → 403
        suggestion = _suggest(method, path)
        ai_instruction = (
            f"STOP_RETRYING. AI 不允许调用 {method} {path}。"
            + (suggestion + "。" if suggestion else "请调用 GET /api/_ai/capabilities 查看可用规范接口。")
        )
        logger.info("[AIGateway] 拦截 AI 非规范写接口: %s %s", method, path)
        payload = {
            "error": {
                "code": "ENDPOINT_NOT_ALLOWED_FOR_AI",
                "message": f"AI 不允许调用此接口: {method} {path}",
                "action": "none",
                "action_data": {},
                "data": {"method": method, "path": path, "suggested_endpoint": suggestion},
                "ai_instruction": ai_instruction,
            }
        }
        await _send_json(send, 403, payload)
