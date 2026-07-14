"""集成测试公共 fixture

所有集成测试统一使用独立临时 SQLite 数据库，绝不触碰生产数据库 backend/inventory.db。

关键设计：在模块加载时创建临时库并 monkeypatch database 模块，
确保所有后续 `from database import SessionLocal` 导入拿到的都是临时库版本。
"""
import os
import sys
import uuid
import atexit
import tempfile

# ═══ 确保 backend 在 sys.path 中 ═══
_BACKEND = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database
from database import Base, get_db, init_db

# ═══ 模块加载时：创建临时库 + monkeypatch database 模块 ═══
_TEMP_DB_PATH = os.path.join(tempfile.gettempdir(), f"test_integration_{uuid.uuid4().hex}.db")
_temp_engine = create_engine(f"sqlite:///{_TEMP_DB_PATH}", connect_args={"check_same_thread": False})
_TempSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_temp_engine)

database._engine = _temp_engine
database.SessionLocal = _TempSessionLocal

Base.metadata.create_all(bind=_temp_engine)
init_db()

# 测试结束后清理临时库文件
def _cleanup_temp_db():
    try:
        os.unlink(_TEMP_DB_PATH)
    except OSError:
        pass

atexit.register(_cleanup_temp_db)

# ═══ fixtures ═══
import pytest
from fastapi.testclient import TestClient
from main import app
from factories import ensure_default_account


@pytest.fixture(scope="class", autouse=True)
def _reset_db():
    """每个测试类前：清空所有表数据，重新初始化默认账本

    使用 class scope 允许同一类内的方法共享数据（如 test_01 创建 → test_02 查询）。
    不同类/独立函数各得独立 DB。
    """
    # 删除 + 重建所有表（相当于完整的数据库重置）
    Base.metadata.drop_all(bind=_temp_engine)
    Base.metadata.create_all(bind=_temp_engine)
    init_db()

    # 每次函数都创建默认账本
    db = database.SessionLocal()
    try:
        ensure_default_account(db)
    finally:
        db.close()

    # 每次函数重新覆盖依赖注入
    def _get_db():
        db = database.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = _get_db

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def db():
    """返回当前测试的隔离数据库 session"""
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c
