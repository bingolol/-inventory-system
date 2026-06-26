"""只读中间件：阻止直接修改/删除关键历史数据，强制使用替代业务流程。

禁用规则：
  PUT/DELETE /api/opening-balances/*      → 403 期初余额创建后不可直接修改
  DELETE     /api/invoices/*              → 403 发票通过 reverse 红冲
  DELETE     /api/fixed-assets/*          → 403 固定资产通过 dispose 处置
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
