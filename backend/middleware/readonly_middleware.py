"""只读中间件：阻止直接修改/删除关键历史数据，强制使用替代业务流程。

禁用规则：
  PUT/DELETE /api/opening-balances/*      → 403 期初余额创建后不可直接修改
  DELETE     /api/invoices/*              → 403 发票通过 reverse 红冲
  DELETE     /api/fixed-assets/*          → 403 固定资产通过 dispose 处置
  DELETE     /api/expenses/*              → 403 费用通过 reverse 红冲（冲红总账凭证）
  DELETE     /api/cash-flows/transactions/* → 403 现金流水通过 reverse 红冲
  DELETE     /api/sales/*                 → 403 销售单通过 POST /{id}/cancel 取消
  DELETE     /api/purchases/*             → 403 采购单通过 POST /{id}/cancel 取消
  DELETE     /api/personal-advances/*     → 403 个人垫付单通过 reverse 红冲
"""

import re
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

BLOCKED_PUT_DELETE = [
    (re.compile(r"^/api/opening-balances/\d+$"), "期初余额已锁定，请通过 POST /api/opening-balances 创建新期初"),
]

BLOCKED_DELETE = [
    (re.compile(r"^/api/invoices/\d+$"), "发票已锁定，请通过 POST /api/invoices/{id}/reverse 红冲"),
    (re.compile(r"^/api/fixed-assets/\d+$"), "固定资产已锁定，请通过 POST /api/fixed-assets/{id}/dispose 处置"),
    (re.compile(r"^/api/expenses/\d+$"), "费用已过账，请通过 POST /api/expenses/{id}/reverse 红冲（冲红总账凭证+保留审计轨迹）"),
    (re.compile(r"^/api/cash-flows/transactions/\d+$"), "现金流水已过账，请通过 POST /api/cash-flows/transactions/{id}/reverse 红冲"),
    (re.compile(r"^/api/sales/\d+$"), "销售单已锁定，请通过 POST /api/sales/{id}/cancel 取消（保留审计轨迹+冲红凭证库存）"),
    (re.compile(r"^/api/purchases/\d+$"), "采购单已锁定，请通过 POST /api/purchases/{id}/cancel 取消（保留审计轨迹+冲红凭证库存）"),
    (re.compile(r"^/api/personal-advances/\d+$"), "个人垫付单已过账，请通过 POST /api/personal-advances/{id}/reverse 红冲（冲红总账凭证+保留审计轨迹）"),
    (re.compile(r"^/api/personal-advances/\d+/repayments/\d+$"), "偿还记录已过账，请通过 POST /api/personal-advances/{id}/repayments/{rid}/reverse 红冲"),
]


class ReadonlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        for pattern, msg in BLOCKED_PUT_DELETE:
            if request.method in ("PUT", "DELETE") and pattern.match(request.url.path):
                return JSONResponse(status_code=403, content={
                    "error": {
                        "code": "READONLY_DATA",
                        "message": msg,
                        "action": "user_input",
                        "action_data": {},
                        "data": {"path": request.url.path, "method": request.method},
                        "ai_instruction": f"STOP_RETRYING. {msg}",
                    }
                })
        for pattern, msg in BLOCKED_DELETE:
            if request.method == "DELETE" and pattern.match(request.url.path):
                return JSONResponse(status_code=403, content={
                    "error": {
                        "code": "READONLY_DATA",
                        "message": msg,
                        "action": "user_input",
                        "action_data": {},
                        "data": {"path": request.url.path, "method": request.method},
                        "ai_instruction": f"STOP_RETRYING. {msg}",
                    }
                })
        return await call_next(request)
