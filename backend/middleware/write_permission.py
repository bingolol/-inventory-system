from starlette.types import ASGIApp, Scope, Receive, Send
from database import _request_write_perm

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class WritePermissionMiddleware:
    """给已放行的写请求设 SecureSession 令牌（AIGatewayMiddleware 在外层做 X-Operator 校验）"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if scope["method"] in WRITE_METHODS:
            token = _request_write_perm.set(True)
            try:
                await self.app(scope, receive, send)
            finally:
                _request_write_perm.reset(token)
        else:
            await self.app(scope, receive, send)
