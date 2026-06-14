"""
EventBus v2 — 事件总线模块

支持优先级排序、条件过滤、中间件链的线程安全事件总线。
提供同步 emit() 和异步 emit_async() 双版本，分别用于脚本场景和 FastAPI 路由。
"""

import threading
import asyncio
from dataclasses import dataclass
from typing import Callable, Optional, Any, Dict, List


@dataclass
class HandlerEntry:
    """事件处理器条目"""
    name: str                               # handler 名称（去重/调试）
    handler: Callable                       # 实际处理函数
    priority: int = 0                       # 优先级，数字越小越先执行
    condition: Optional[Callable] = None    # 条件过滤函数，接收 emit 的 kwargs


class EventBus:
    """线程安全的事件总线"""

    def __init__(self):
        self._handlers: Dict[str, List[HandlerEntry]] = {}
        self._middleware: List[Callable] = []
        self._lock = threading.Lock()

    # ── 注册 ──────────────────────────────────────────────

    def on(self, event: str, priority: int = 0,
           condition: Optional[Callable] = None, name: Optional[str] = None):
        """装饰器：注册事件处理器

        用法::
            @bus.on('order.created', priority=10)
            def handle_order(**kwargs): ...
        """
        def decorator(func: Callable) -> Callable:
            entry = HandlerEntry(
                name=name or func.__name__,
                handler=func,
                priority=priority,
                condition=condition,
            )
            with self._lock:
                if event not in self._handlers:
                    self._handlers[event] = []
                self._handlers[event].append(entry)
                # 按 priority 升序排序（数字小先执行）
                self._handlers[event].sort(key=lambda e: e.priority)
            return func
        return decorator

    # ── 触发 ──────────────────────────────────────────────

    def emit(self, event: str, **kwargs) -> List[Any]:
        """同步触发事件，返回所有 handler 的返回值列表"""
        kwargs['_event'] = event
        results = []
        for entry in self._get_matching_handlers(event, **kwargs):
            result = self._run_middleware(entry.handler, len(self._middleware) - 1, **kwargs)
            results.append(result)
        return results

    async def emit_async(self, event: str, **kwargs) -> List[Any]:
        """异步触发事件，支持 async handler，用于 FastAPI 路由"""
        kwargs['_event'] = event
        results = []
        for entry in self._get_matching_handlers(event, **kwargs):
            result = await self._run_middleware_async(
                entry.handler, len(self._middleware) - 1, **kwargs
            )
            results.append(result)
        return results

    # ── 中间件 ────────────────────────────────────────────

    def use(self, middleware: Callable) -> None:
        """注册中间件。中间件签名: (next_func, **kwargs) -> result"""
        with self._lock:
            self._middleware.append(middleware)

    # ── 查询 ──────────────────────────────────────────────

    def get_handlers(self, event: str) -> List[HandlerEntry]:
        """返回某事件的所有已注册 handler（副本）"""
        with self._lock:
            return list(self._handlers.get(event, []))

    # ── 内部方法 ──────────────────────────────────────────

    def _get_matching_handlers(self, event: str, **kwargs) -> List[HandlerEntry]:
        """获取匹配 condition 的事件处理器列表"""
        with self._lock:
            entries = list(self._handlers.get(event, []))
        return [
            e for e in entries
            if e.condition is None or e.condition(**kwargs)
        ]

    def _run_middleware(self, handler: Callable, index: int, **kwargs) -> Any:
        """递归执行中间件链（同步版）"""
        if index < 0:
            return handler(**kwargs)
        mw = self._middleware[index]
        next_func = lambda **kw: self._run_middleware(handler, index - 1, **kw)
        return mw(next_func, **kwargs)

    async def _run_middleware_async(self, handler: Callable, index: int, **kwargs) -> Any:
        """递归执行中间件链（异步版）"""
        if index < 0:
            result = handler(**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        mw = self._middleware[index]
        next_func = lambda **kw: self._run_middleware_async(handler, index - 1, **kw)
        result = mw(next_func, **kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        return result


# ── 全局单例 ──────────────────────────────────────────────

bus = EventBus()


# ── 便捷函数 ──────────────────────────────────────────────

def on(event: str, priority: int = 0,
       condition: Optional[Callable] = None, name: Optional[str] = None):
    """便捷函数：注册事件处理器（委托到全局 bus）"""
    return bus.on(event, priority=priority, condition=condition, name=name)


def emit(event: str, **kwargs) -> List[Any]:
    """便捷函数：同步触发事件（委托到全局 bus）"""
    return bus.emit(event, **kwargs)


def use(middleware: Callable) -> None:
    """便捷函数：注册中间件（委托到全局 bus）"""
    return bus.use(middleware)


def get_handlers(event: str) -> List[HandlerEntry]:
    """便捷函数：查询事件 handler（委托到全局 bus）"""
    return bus.get_handlers(event)