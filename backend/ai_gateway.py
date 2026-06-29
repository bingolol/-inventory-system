import contextvars

_gateway_authorized = contextvars.ContextVar('_gateway_authorized', default=False)

"""AI 接口网关 — 规范接口白名单 + 403 硬拦截

约束 AI Agent 只能调用"规范接口"，杜绝过度开发带来的多入口混乱：
  - 同一业务能力的增/改/删，对 AI 只暴露 1 个规范端点（如发票创建只走 /quick）。
  - 变体端点（已被合并的 /with-fixed-asset 等）对 AI 不再可调用。

拦截规则：
  - GET / HEAD：查询全部放行
  - 写操作（POST/PUT/DELETE/PATCH）：
    · 无 X-Operator 头 → 403（curl 直调直接拒绝）
    · X-Operator: user → 全部放行（前端正常操作）
    · X-Operator: ai → 白名单校验：命中放行（带 state_after 包装）；否则 403

设计意图：前端在 get_operator() 依赖注入中自动设 X-Operator: user，
脚本/curl 不设头直接 403；AI Agent 设 ai 走白名单。

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
import models

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
    Capability("POST",   "/api/purchases/{id}/cancel", "取消采购单（冲红凭证+回退库存，保留审计轨迹）"),
    Capability("POST",   "/api/sales",               "创建销售单（自动扣库存）", params_hint="customer_id,items[],deduct_inventory"),
    Capability("PUT",    "/api/sales/{id}",          "更新销售单（含付款状态）"),
    Capability("POST",   "/api/sales/{id}/cancel",   "取消销售单（冲红凭证+回退库存，保留审计轨迹）"),
    # ── 发票（创建对 AI 只走 /quick，变体已合并）──
    Capability(
        "POST", "/api/invoices/quick", "AI 快捷录发票（规范入口，支持 fixed_asset 嵌套对象）",
        replaces=["POST /api/invoices", "POST /api/invoices/with-fixed-asset"],
        params_hint="invoice_no,direction,invoice_type,amount_with_tax,tax_rate,counterparty_name,seller_name,buyer_name,issue_date,items[]; 可选 fixed_asset{},sale_order_action,purchase_order_action,related_order_id",
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
    Capability("POST",   "/api/fixed-assets/{id}/depreciate", "计提单个资产折旧"),
    Capability("POST",   "/api/fixed-assets/batch-depreciate", "批量计提折旧"),
    Capability("POST",   "/api/fixed-assets/{id}/dispose", "处置固定资产"),
    # ── 个人流水 ──
    Capability("POST",   "/api/personal",            "创建个人流水记录"),
    Capability("PUT",    "/api/personal/{tx_id}",    "更新个人流水记录"),
    # ── 付款 / 收款 ──
    Capability("POST",   "/api/payments",            "创建付款"),
    Capability("POST",   "/api/receipts",            "创建收款"),
    Capability("POST",   "/api/receipts/{id}/reverse", "红冲收款"),
    Capability("POST",   "/api/payments/{id}/reverse", "红冲付款"),
    # ── 冲红（危险操作，放行后由 ConfirmMiddleware 二次确认）──
    Capability("POST",   "/api/invoices/{id}/reverse", "发票红冲（红字发票+级联冲红凭证库存）"),
    Capability("POST",   "/api/expenses/{id}/reverse", "费用冲红（冲红总账凭证）"),
    Capability("POST",   "/api/cash-flows/transactions/{id}/reverse", "现金流水冲红"),
    # ── 银行管理 ──
    Capability("POST",   "/api/bank-accounts",       "创建银行账户", params_hint="bank_name,account_number"),
    # ── 月末结账 ──
    Capability("POST",   "/api/finance/month-close", "月末结账（自动算税+生成凭证）", params_hint="period:YYYY-MM"),
    # ── 银行对账 ──
    Capability("POST",   "/api/bank/statement",      "导入银行对账单"),
    Capability("POST",   "/api/bank/reconcile",      "执行银行对账", params_hint="period:YYYY-MM"),
    Capability("POST",   "/api/bank/reconciliation/{id}/match", "强制匹配未达项"),
    Capability("POST",   "/api/bank/reconciliation/{id}/generate-entry", "生成手续费/利息凭证"),
    Capability("POST",   "/api/bank/reconciliation/{id}/confirm", "确认调节表"),
    Capability("POST",   "/api/bank/entry",         "录入银行利息收入/手续费"),
    Capability("POST",   "/api/bank/transaction/{id}/reverse", "红冲银行交易"),
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
    "/api/bootstrap",  # 首次初始化
    "/api/confirm",    # 确认流程接口
    "/api/health",
    "/api/enums",
    "/api/accounts",
    "/api/auth",       # 登录认证（不设 X-Operator）
)

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

# HTTP 方法 → 操作类型
_METHOD_TO_OPERATION = {
    "POST": "created",
    "PUT": "updated",
    "DELETE": "deleted",
    "PATCH": "updated",
}


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


def _build_snapshot(inner: dict) -> dict:
    """解析 OperationResult，查数据库构建当前状态快照"""
    entity_type = inner.get("entity_type") if isinstance(inner, dict) else None
    entity_id = inner.get("entity_id")
    if not entity_type or not entity_id:
        return {}

    from database import SessionLocal
    db = SessionLocal()
    try:
        snapshot = {}

        if entity_type in ("sale_order", "purchase_order"):
            # 查订单详情
            if entity_type == "sale_order":
                order = db.query(models.SaleOrder).filter(models.SaleOrder.id == entity_id).first()
            else:
                order = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == entity_id).first()
            if order:
                snapshot["order"] = {
                    "id": order.id,
                    "order_no": getattr(order, "order_no", ""),
                    "total_price": float(order.total_price) if order.total_price else 0,
                    "status": order.status,
                }

            # 查本次操作涉及的库存（从 response data 找 product_id）
            data = inner.get("data", {}) if isinstance(inner, dict) else {}
            items = data.get("items", []) if isinstance(data, dict) else []
            product_ids = []
            if items and isinstance(items, list):
                product_ids = [it.get("product_id") for it in items if isinstance(it, dict)]
            if product_ids:
                inventory = []
                for pid in product_ids:
                    inv = db.query(models.Inventory).filter(
                        models.Inventory.product_id == pid,
                    ).first()
                    product = db.query(models.Product).filter(models.Product.id == pid).first()
                    if inv is not None:
                        inventory.append({
                            "product_id": pid,
                            "product_name": product.name if product else f"商品{pid}",
                            "remaining": inv.quantity,
                        })
                if inventory:
                    snapshot["inventory"] = inventory

        elif entity_type == "product":
            inv = db.query(models.Inventory).filter(
                models.Inventory.product_id == entity_id,
            ).first()
            if inv is not None:
                snapshot["inventory"] = [{
                    "product_id": entity_id,
                    "remaining": inv.quantity,
                }]

        return snapshot
    finally:
        db.close()


class AIGatewayMiddleware:
    """ASGI 中间件：校验写操作 + 白名单端点响应统一包装。

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
            _gateway_authorized.set(True)
            await self.app(scope, receive, send)
            return

        # 基础设施接口放行
        if path.startswith(_SKIP_PREFIXES):
            _gateway_authorized.set(True)
            await self.app(scope, receive, send)
            return

        # 识别调用者
        operator = ""
        for key, val in scope.get("headers", []):
            if key.decode("latin-1").lower() == "x-operator":
                operator = val.decode("latin-1")
                break

        # user（前端正常操作）→ 全部放行
        if operator == "user":
            _gateway_authorized.set(True)
            await self.app(scope, receive, send)
            return

        # 无 X-Operator → 403（curl 直调拦截）
        if not operator:
            logger.info("[AIGateway] 拦截无头写请求: %s %s", method, path)
            await _send_json(send, 403, {
                "error": {
                    "code": "ENDPOINT_NOT_ALLOWED_FOR_AI",
                    "message": f"写操作需要 X-Operator 头：user（前端）或 ai（白名单）：{method} {path}",
                    "action": "none",
                    "action_data": {},
                    "data": {"method": method, "path": path},
                    "ai_instruction": "STOP_RETRYING. 写操作必须带 X-Operator 头。前端页面自动带 user，AI Agent 应设 ai。",
                }
            })
            return

        # ai / 其他 → 白名单校验
        cap = _match(method, path)
        if cap is not None and cap.canonical:
            _gateway_authorized.set(True)
            captured = {"status": None, "headers": [], "body": bytearray()}

            async def wrapped_send(event):
                if event["type"] == "http.response.start":
                    captured["status"] = event["status"]
                    captured["headers"] = event.get("headers", [])
                elif event["type"] == "http.response.body":
                    captured["body"].extend(event.get("body", b""))
                    if not event.get("more_body", False):
                        wrapped = self._wrap_ai_response(method, captured)
                        await send({
                            "type": "http.response.start",
                            "status": captured["status"],
                            "headers": [[b"content-type", b"application/json; charset=utf-8"]],
                        })
                        await send({"type": "http.response.body", "body": wrapped})
                else:
                    await send(event)

            await self.app(scope, receive, wrapped_send)
            return

        # 非白名单写接口 → 403
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

    @staticmethod
    def _wrap_ai_response(method: str, captured: dict) -> bytes:
        """将白名单端点的 200 响应包装为 AI 统一格式"""
        raw_body = bytes(captured["body"])
        operation = _METHOD_TO_OPERATION.get(method, "unknown")
        try:
            inner = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return raw_body

        if not isinstance(inner, dict):
            return raw_body

        # handler 可用 _idempotent / _state_after 显式标记
        idempotent = inner.pop("_idempotent", False)
        state_after = inner.pop("_state_after", {})

        # OperationResult 格式：提取 changes → state_after（inventory / cash / payable 等）
        if not state_after and "changes" in inner and isinstance(inner["changes"], dict):
            state_after = inner.pop("changes")

        # 补充系统真实快照（查数据库）
        snapshot = _build_snapshot(inner)
        if snapshot:
            state_after.update(snapshot)

        wrapped = {
            "ok": captured["status"] == 200,
            "entity": inner,
            "operation": operation,
            "idempotent": idempotent,
            "state_after": state_after,
        }
        return json.dumps(wrapped, ensure_ascii=False, default=str).encode("utf-8")
