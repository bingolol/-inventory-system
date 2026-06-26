"""单元测试公共 fixture — 共享测试数据库"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base


@pytest.fixture
def db():
    """提供内存 SQLite session，测试后自动关闭"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
