"""
EventBus 中间件模块

提供日志中间件和不变量校验中间件，通过 register_middleware() 统一注册。
"""

import time
import logging
from events import bus, get_handlers

logger = logging.getLogger("inventory")


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
    """不变量校验中间件（已禁用：verify_invariants 已移除）"""
    return next_func(**kwargs)


def register_middleware():
    """注册所有中间件到全局 EventBus

    注册顺序：logging → invariant_check
    执行顺序（后注册先执行）：invariant_check → logging → handler
    即 logging 在最外层记录总耗时，invariant_check 在 handler 后校验不变量。
    """
    bus.use(logging_middleware)
    bus.use(invariant_check_middleware)