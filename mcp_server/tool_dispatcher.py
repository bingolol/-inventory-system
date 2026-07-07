"""Tool dispatcher — 桥接 MCP tool 调用与 backend commands 层

职责:
1. 创建数据库 Session
2. 设置写权限 contextvar (与 WritePermissionMiddleware 等价)
3. 强制 operator='ai' 写入审计日志
4. 调用 commands.dispatch 执行业务命令
5. commit / rollback + 关闭 Session
6. BusinessError 透传为 MCP error, 不吞异常

铁律:
- 写操作只走 commands 层, 禁止 server 直接 UPDATE 真相源表
- operator 必须为 'ai' 以便审计追溯
- 异常不吞, 全部透传给 agent
"""
from typing import Any

from database import SessionLocal, _request_write_perm
from commands.base import dispatch
from commands import base as commands_base
from errors import BusinessError


def execute_command(cmd_cls, **kwargs) -> Any:
    """同步执行 Command 并返回结果。

    自动注入 account_id (从 account_context) 和 operator='ai'。
    kwargs 中若显式传 account_id / operator 则覆盖默认值。

    :param cmd_cls: Command 子类 (如 CreateOrder)
    :param kwargs: Command 字段值
    :return: handler.handle() 返回值
    :raises BusinessError: 业务校验失败时透传
    :raises Exception: 其他异常透传
    """
    from .account_context import require_account_id

    account_id = kwargs.pop("account_id", None) or require_account_id()
    operator = kwargs.pop("operator", "ai")

    cmd = cmd_cls(account_id=account_id, operator=operator, **kwargs)

    db = SessionLocal()
    # commit 后默认会 expire 所有 ORM 对象属性, 导致序列化时 __dict__ 为空
    # (agent 拿不到新建对象的 id)。这里关闭 expire_on_commit, 反正 db 在
    # finally 里 close, 不会泄漏。
    db.expire_on_commit = False
    token = _request_write_perm.set(True)
    try:
        result = dispatch(cmd, db)
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        _request_write_perm.reset(token)
        db.close()


def run_readonly(fn, *args, **kwargs) -> Any:
    """执行只读函数 (查询类), 不开写权限。

    :param fn: 接收 db 作为第一个参数的函数
    """
    from .account_context import require_account_id

    account_id = kwargs.pop("account_id", None) or require_account_id()
    db = SessionLocal()
    try:
        return fn(db, account_id, *args, **kwargs)
    finally:
        db.close()


def format_business_error(err: BusinessError) -> dict:
    """将 BusinessError 格式化为 MCP error 返回结构。"""
    return {
        "code": err.code.value if hasattr(err.code, "value") else str(err.code),
        "message": getattr(err, "message", str(err)),
        "data": getattr(err, "data", None),
        "ai_instruction": getattr(err, "ai_instruction", None),
    }
