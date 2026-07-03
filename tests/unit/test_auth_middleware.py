"""TDD: Auth 中间件 — 从 Bearer token 解析用户"""
import hashlib
import time
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import models
from routers.auth import _generate_salt, _hash_password, _make_token_pair, get_user_from_token


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_user_and_token(session, username="admin"):
    """创建用户及其有效 access token，返回 (user, raw_token)。"""
    account = models.Account(name="默认账本", code="default")
    session.add(account)
    session.flush()

    salt = _generate_salt()
    user = models.User(
        username=username,
        password_hash=_hash_password("admin", salt),
        password_salt=salt,
        account_id=account.id,
        is_active=True,
    )
    session.add(user)
    session.flush()

    access_raw, access_hash, refresh_raw, refresh_hash = _make_token_pair()
    token = models.UserToken(
        user_id=user.id,
        access_token_hash=access_hash,
        refresh_token_hash=refresh_hash,
        access_expires_at=datetime.now() + timedelta(hours=2),
        refresh_expires_at=datetime.now() + timedelta(days=7),
    )
    session.add(token)
    session.commit()
    return user, access_raw


class TestAuthMiddleware:
    """验证 get_user_from_token 从 Bearer token 解析用户"""

    def test_valid_token_extracts_user(self, db):
        user, token = _make_user_and_token(db)
        result = get_user_from_token(token, db)
        assert result is not None
        assert result.username == user.username
        assert result.id == user.id

    def test_invalid_token_returns_none(self, db):
        assert get_user_from_token("invalid-token", db) is None

    def test_expired_token_returns_none(self, db):
        user, token = _make_user_and_token(db)
        # 将所有 token 改为已过期
        for row in db.query(models.UserToken).all():
            row.access_expires_at = datetime.now() - timedelta(seconds=1)
        db.commit()
        assert get_user_from_token(token, db) is None

    def test_disabled_user_returns_none(self, db):
        user, token = _make_user_and_token(db)
        user.is_active = False
        db.commit()
        assert get_user_from_token(token, db) is None
