import contextvars
import re
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.sql.dml import Update, Delete, Insert
from errors import BusinessError, ErrorCode

from workspace import get_db_path as _get_db_path

# ── 全局状态 ──
_request_write_perm = contextvars.ContextVar('_request_write_perm', default=False)
_maintenance_mode = False


def _is_write_permitted() -> bool:
    return _maintenance_mode or _request_write_perm.get()


def set_maintenance_mode(val: bool):
    global _maintenance_mode
    _maintenance_mode = val


# ── Engine 私有化 ──
DB_PATH = _get_db_path()
DATABASE_URL = f"sqlite:///{DB_PATH}"

_DDL_KEYWORDS = {"drop", "alter", "create", "truncate"}
_DML_KEYWORDS = {"insert", "update", "delete", "replace"}


def _guard_text_dml(stmt_str: str, first_word: str):
    """非 ORM 写操作拦截（覆盖 text() CTE 绕过）"""
    if not _is_write_permitted():
        if first_word in _DML_KEYWORDS:
            raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                                message="禁止直接写数据库，请调用合规 API")
        for kw in _DML_KEYWORDS:
            if re.search(rf'\b{kw}\b', stmt_str):
                # 放行 SELECT ... FOR UPDATE（行锁，非 DML）
                if kw == "update" and re.search(r'\bfor\s+update\b', stmt_str):
                    continue
                raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                                    message="禁止直接写数据库（CTE 内 DML 被拦截）")


def _guard_execute(conn, clauseelement, multiparams, params, execution_options):
    if _maintenance_mode:
        return

    stmt_str = str(clauseelement).lower()
    first_word = stmt_str.strip().split()[0] if stmt_str.strip() else ""

    # DDL 红线（首单词检测，防表名含关键字误杀）
    if first_word in _DDL_KEYWORDS:
        raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                            message="禁止执行结构变更(DDL)")

    # ORM-level DML
    if isinstance(clauseelement, (Update, Delete, Insert)):
        if not _is_write_permitted():
            raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                                message="禁止直接写数据库，请调用合规 API")
        return

    # Raw SQL DML（text()、TextClause 等全靠字符串检测）
    _guard_text_dml(stmt_str, first_word)


def _make_engine(db_url: str):
    e = create_engine(db_url, connect_args={"check_same_thread": False})
    event.listen(e, 'before_execute', _guard_execute)
    return e


_engine = _make_engine(DATABASE_URL)


def get_db_url() -> str:
    return str(_engine.url)


def configure_engine(db_url: str):
    global _engine, SessionLocal
    _engine = _make_engine(db_url)
    SessionLocal = sessionmaker(class_=SecureSession, bind=_engine)


# ── SecureSession ──
class SecureSession(Session):
    pass


SessionLocal = sessionmaker(class_=SecureSession, bind=_engine)


@event.listens_for(SecureSession, 'before_flush')
def _guard_flush(session, context, instances):
    if _is_write_permitted():
        return
    if session.new or session.dirty or session.deleted:
        raise BusinessError(code=ErrorCode.SECURITY_VIOLATION,
                            message="ORM 操作被拦截：请通过 API 操作")


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models
    import models_finance
    Base.metadata.create_all(bind=_engine)
