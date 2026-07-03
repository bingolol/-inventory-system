"""Unit of Work — 统一事务边界上下文管理器

所有业务写操作必须在 unit_of_work(db) 内执行，保证单一 commit 点。
CRUD 函数只做 db.flush()，不调 commit()/rollback()。
"""

from contextlib import contextmanager
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger("inventory")


@contextmanager
def unit_of_work(db: Session):
    """写操作上下文：with 块内所有操作原子生效，全部成功或全部回滚

    规则：
    1. CRUD 函数只做 db.flush()，不调 commit()/rollback()
    2. log_op() 也只做 flush()，日志与业务数据在同一事务中
    3. HTTPException 在 uow 内抛出也会触发 rollback
    4. db.refresh() 需要在 uow 块外执行（commit 后才能 refresh）
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise


@contextmanager
def read_only(db: Session):
    """只读操作上下文：自动关闭 session，不 commit"""
    try:
        yield db
    finally:
        db.close()