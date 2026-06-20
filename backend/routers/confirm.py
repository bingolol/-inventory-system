"""
确认操作路由

提供三个 API 供前端管理待确认请求：
- GET  /api/confirm/pending       → 获取所有待确认请求列表
- POST /api/confirm/{token}       → 确认执行（重放原始请求，返回实际结果）
- DELETE /api/confirm/{token}     → 取消（丢弃请求）
- GET  /api/confirm/{token}/status → 查询单个请求状态
"""

import json
import logging
from fastapi import APIRouter, Request
from confirm_middleware import confirm_store
from errors import BusinessError, ErrorCode

logger = logging.getLogger("inventory")
router = APIRouter()


@router.get("/pending")
def list_pending():
    """获取所有待确认请求列表"""
    return {"pending": confirm_store.list_pending()}


@router.get("/{token}/status")
def get_status(token: str):
    """查询单个确认请求状态"""
    entry = confirm_store.get(token)
    if entry is None:
        return {"status": "not_found", "detail": "确认令牌不存在或已过期"}
    return {
        "status": "pending",
        "confirm_token": token,
        "method": entry["method"],
        "path": entry["path"],
        "summary": entry.get("summary", ""),
        "created_at": entry["created_at"],
        "expires_at": entry["created_at"] + confirm_store._pending.get(token, {}).get("ttl", 300) if token in confirm_store._pending else entry["created_at"] + 300,
    }


@router.delete("/{token}")
def cancel_confirm(token: str):
    """取消待确认请求（用户拒绝执行）"""
    entry = confirm_store.get(token)
    if entry is None:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "确认令牌", "order_id": 0})

    summary = entry.get("summary", "")
    confirm_store.remove(token)
    logger.info("[Confirm] 用户已取消: %s (token=%s)", summary, token)
    return {"message": f"已取消: {summary}", "status": "cancelled"}


@router.post("/{token}")
async def confirm_execute(token: str, request: Request):
    """确认执行：重放原始请求并返回实际结果

    通过 httpx 将原始请求转发回本服务，绕过中间件再次拦截。
    """
    entry = confirm_store.get(token)
    if entry is None:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "确认令牌", "order_id": 0})

    # 先从存储中移除，防止重复确认
    summary = entry.get("summary", "")
    confirm_store.remove(token)
    logger.info("[Confirm] 用户已确认: %s (token=%s)，正在执行...", summary, token)

    # 重放请求：使用 httpx 发送回本地服务，带 X-Operator: user 绕过确认中间件
    try:
        import httpx
        method = entry["method"]
        path = entry["path"]
        body = entry.get("body", b"")
        query_string = entry.get("query_string", b"")
        original_headers = entry.get("headers", [])

        # 构建请求 URL
        # 从请求对象获取当前服务的 host:port
        host = request.headers.get("host", "localhost:8000")
        scheme = "http"
        url = f"{scheme}://{host}{path}"
        if query_string:
            url += f"?{query_string.decode('latin-1')}"

        # 构建请求头：保留原始头，但将 X-Operator 改为 user 避免再次拦截
        headers = {}
        for key, val in original_headers:
            key_str = key.decode("latin-1")
            val_str = val.decode("latin-1")
            if key_str.lower() == "x-operator":
                headers["X-Operator"] = "confirmed-by-user"
            elif key_str.lower() in ("host", "content-length", "transfer-encoding"):
                continue  # httpx 会自动设置
            else:
                headers[key_str] = val_str

        # 发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                content=body,
                headers=headers,
            )

        logger.info("[Confirm] 执行完成: %s → status=%d", summary, response.status_code)

        # 返回与原始请求相同的状态码和内容
        from fastapi.responses import Response
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json"),
        )

    except ImportError:
        logger.error("[Confirm] httpx 未安装，无法重放请求")
        raise BusinessError(code=ErrorCode.INTERNAL_ERROR, message="服务器缺少 httpx 依赖，无法执行确认操作")
    except Exception as e:
        logger.error("[Confirm] 重放请求失败: %s", e)
        raise BusinessError(code=ErrorCode.INTERNAL_ERROR, message=f"执行确认操作失败: {e}")