"""TDD: 登录认证 — 绕过 HTTP，直接测试 login 函数"""
import hashlib
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models
from routers.auth import login, _hash_password
from schemas.user import LoginRequest


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add(models.Account(id=1, name="公司账本", type="company", code="company"))
    session.flush()
    session.add(models.User(
        username="admin",
        password_hash=_hash_password("admin"),
        account_id=1, is_active=True,
    ))
    session.commit()
    return session


class TestLogin:
    def test_wrong_password_returns_401(self, db_session):
        with pytest.raises(Exception) as exc:
            login(LoginRequest(username="admin", password="wrong"), db=db_session)
        assert "401" in str(exc.value) or "用户名或密码错误" in str(exc.value)

    def test_correct_password_returns_token(self, db_session):
        result = login(LoginRequest(username="admin", password="admin"), db=db_session)
        assert result.token
        assert result.username == "admin"
        assert result.account_id == 1
