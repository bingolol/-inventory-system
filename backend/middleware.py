"""
EventBus 中间件模块

提供日志中间件和不变量校验中间件，通过 register_middleware() 统一注册。
"""

import time
import logging
from events import bus, get_handlers
from utils import verify_invariants

logger = logging.getLogger("inventory")

# 写操作事件前缀列表（不变量校验仅对写操作触发）
_WRITE_PREFIXES = (
    "purchase_order.", "sale_order.", "inventory.",
    "project.", "payment.", "income.", "cost.",
)


def _is_write_event(event: str) -> bool:
    """判断事件是否为写操作事件"""
    return any(event.startswith(prefix) for prefix in _WRITE_PREFIXES)


def logging_middleware(next_func, **kwargs):
    """日志中间件：记录事件名、处理器数量、耗时"""
    event = kwargs.get("_event", "")
    handlers = get_handlers(event) if event else []
    handler_count = len(handlers)

    t0 = time.perf_counter()
    try:
        result = next_func(**kwargs)
    finally:
        elapsed = (time.perf_counter() - t0) * 1000
        logger.info(
            "[EventBus] %s | handlers=%d | %.1fms",
            event, handler_count, elapsed,
        )
    return result


def invariant_check_middleware(next_func, **kwargs):
    """不变量校验中间件：写操作事件后自动调用 verify_invariants()"""
    result = next_func(**kwargs)

    event = kwargs.get("_event", "")
    if _is_write_event(event):
        db = kwargs.get("db")
        account_id = kwargs.get("account_id")
        if db is not None:
            try:
                inv_result = verify_invariants(db, account_id)
                if not inv_result["ok"]:
                    logger.warning(
                        "[Invariant] %s 违规 %d 项: %s",
                        event, inv_result["violation_count"],
                        inv_result["violations"][:3],
                    )
            except Exception as e:
                logger.error("[Invariant] 校验异常: %s", e)
    return result


def register_middleware():
    """注册所有中间件到全局 EventBus

    注册顺序：logging → invariant_check
    执行顺序（后注册先执行）：invariant_check → logging → handler
    即 logging 在最外层记录总耗时，invariant_check 在 handler 后校验不变量。
    """
    bus.use(logging_middleware)
    bus.use(invariant_check_middleware)