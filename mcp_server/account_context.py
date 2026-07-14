"""账本上下文管理 — MCP server 全局会话状态

MCP server 在单个进程内服务一个端侧 agent, agent 可能跨多轮对话操作多个账本。
本模块维护"当前账本 ID", 所有 tool 调用时自动注入, 避免 agent 每次都传 account_id。

初始化策略:
- 启动时从环境变量 MCP_ACCOUNT_ID 读取 (可选)
- 未设置时取数据库第一个公司账本作为默认
- agent 可通过 set_current_account tool 切换
"""
import os
import threading

from database import SessionLocal
import models


_lock = threading.Lock()
_current_account_id: int = 0


def init_default_account() -> int:
    """启动时初始化默认账本。优先用环境变量, 否则取第一个公司账本。"""
    global _current_account_id

    env_id = os.environ.get("MCP_ACCOUNT_ID")
    if env_id:
        try:
            with _lock:
                _current_account_id = int(env_id)
            return _current_account_id
        except ValueError:
            pass

    db = SessionLocal()
    try:
        account = db.query(models.Account).order_by(models.Account.id.asc()).first()
        if account:
            with _lock:
                _current_account_id = account.id
        return _current_account_id
    finally:
        db.close()


def get_current_account_id() -> int:
    """获取当前账本 ID。若为 0 表示尚未初始化。"""
    with _lock:
        return _current_account_id


def set_current_account_id(account_id: int) -> None:
    """切换当前账本。"""
    global _current_account_id
    with _lock:
        _current_account_id = account_id


def require_account_id() -> int:
    """获取当前账本 ID, 若为 0 则抛错 (供 tool 调用前置校验)。"""
    aid = get_current_account_id()
    if not aid:
        raise RuntimeError(
            "未设置当前账本。请先调用 set_current_account 工具选择账本, "
            "或在启动时设置 MCP_ACCOUNT_ID 环境变量。"
        )
    return aid


def list_all_accounts(db) -> list:
    """列出所有账本 (供 agent 选择)。"""
    accounts = db.query(models.Account).order_by(models.Account.id.asc()).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "code": a.code,
            "type": a.type,
            "taxpayer_type": getattr(a, "taxpayer_type_l3", None),
        }
        for a in accounts
    ]
