"""集成测试公共 fixture — 需要 DB 连接"""
import pytest
from database import SessionLocal, init_db


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """确保数据库初始化"""
    init_db()


@pytest.fixture
def db():
    """提供数据库 session，测试后自动关闭"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()