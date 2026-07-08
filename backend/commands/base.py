"""Command 基类 + Dispatcher — 命令模式基础设施

所有业务命令继承 Command，对应 Handler 继承 CommandHandler，
通过 @register 装饰器注册，dispatch 查表执行。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Type

from errors import BusinessError, ErrorCode

# 全局注册表：Command 类型 → Handler 类型
_registry: Dict[Type["Command"], Type["CommandHandler"]] = {}


@dataclass
class Command(ABC):
    """命令基类（dataclass + ABC）

    子类必须用 @dataclass 装饰，新增字段须有默认值
    （dataclass 继承约束：基类无默认值字段之后不能再出现无默认值字段）。
    """

    account_id: int
    operator: str = "user"


class CommandHandler(ABC):
    """处理器基类"""

    @abstractmethod
    def handle(self, cmd: Command, db: Any) -> Any:
        """执行命令，返回结果"""
        ...


def register(cmd_type: Type[Command]):
    """类装饰器：将 Handler 注册到全局注册表

    用法::

        @register(MyCommand)
        class MyHandler(CommandHandler):
            def handle(self, cmd, db): ...
    """

    def decorator(handler_cls: Type[CommandHandler]) -> Type[CommandHandler]:
        if cmd_type in _registry:
            raise BusinessError(
                code=ErrorCode.DUPLICATE_ENTRY,
                data={"details": f"Command {cmd_type.__name__} already registered to {_registry[cmd_type].__name__}"}
            )
        _registry[cmd_type] = handler_cls
        return handler_cls

    return decorator


def dispatch(cmd: Command, db: Any) -> Any:
    """查找已注册的 Handler 并执行 handle()"""
    cmd_type = type(cmd)
    handler_cls = _registry.get(cmd_type)
    if handler_cls is None:
        raise KeyError(
            f"No handler registered for command type: {cmd_type.__name__}"
        )
    # 设置审计上下文（供 SQLAlchemy 事件监听器使用）
    from utils.audit import set_audit_context
    set_audit_context(db, account_id=cmd.account_id, operator=cmd.operator)
    return handler_cls().handle(cmd, db)


def get_registered_commands() -> Dict[Type[Command], Type[CommandHandler]]:
    """返回注册表浅拷贝（调试用）"""
    return dict(_registry)


def dispatch_safe(cmd: Command, db: Any, error_msg: str = "") -> Any:
    """执行 dispatch 并用 BusinessError 包装 ValueError

    消除 16 个路由中重复的 try/except ValueError 包装器。
    """
    try:
        return dispatch(cmd, db)
    except ValueError as e:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=error_msg or str(e),
        )