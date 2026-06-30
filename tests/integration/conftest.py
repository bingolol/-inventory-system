"""集成测试公共 fixture"""
import pytest
from fastapi.testclient import TestClient
from database import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client():
    from main import app
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c
