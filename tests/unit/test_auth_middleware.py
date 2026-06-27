"""TDD: Auth 中间件 — 从 Bearer token 解析用户"""
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models
from routers.auth import _hash_password, _generate_token, _tokens


# 手动生成一个 token（依赖 _hash_password，不依赖 DB）
def make_token(username="admin"):
    pw_hash = _hash_password("admin")
    # 直接调用 _generate_token（它不依赖 DB）
    return _generate_token(username)


class TestAuthMiddleware:
    """验证 auth 中间件从 Bearer token 解析用户"""

    @pytest.fixture(autouse=True)
    def clear_tokens(self):
        _tokens.clear()

    def test_valid_token_extracts_user(self):
        token = make_token("admin")
        # 验证 token 在缓存中
        from routers.auth import validate_token
        result = validate_token(token)
        assert result is not None
        assert result[0] == "admin"

    def test_invalid_token_returns_none(self):
        from routers.auth import validate_token
        assert validate_token("invalid-token") is None

    def test_expired_token_returns_none(self):
        from routers.auth import validate_token, _tokens
        import time
        token = make_token("admin")
        # 模拟过期
        for username, data in _tokens.items():
            data["expiry"] = time.time() - 1
        assert validate_token(token) is None
