"""Golden Tests 共享配置

- 在 conftest.py 中统一处理 sys.path.insert（消除 AP-1 反模式）
- 提供 client fixture（消除 AP-2 反模式）
- 暴露 helpers 模块中的公共辅助函数
"""
import sys
import os

# ═══ AP-1 修复：仅在此处做一次 sys.path.insert ═══
_BACKEND = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

_GOLDEN = os.path.dirname(os.path.abspath(__file__))
if _GOLDEN not in sys.path:
    sys.path.insert(0, _GOLDEN)

import pytest
from fastapi.testclient import TestClient
from main import app
from database import get_db, Base, init_db
import database
from factories import ensure_default_account
from models import Account
from golden_helpers import make_engine

# ═══ 共享 client fixture ═══
@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


def make_setup(taxpayer_type="general", enable_vat_deduction=True):
    """工厂函数：生成 setup fixture，支持不同纳税人类型

    用法（在测试类中）::

        @pytest.fixture(autouse=True)
        def setup(self, monkeypatch):
            yield from make_setup("general", True)(self, monkeypatch)

    或直接::

        setup = pytest.fixture(autouse=True)(
            lambda self, monkeypatch: make_setup("small_scale", False)(self, monkeypatch)
        )
    """
    def _setup(self, monkeypatch):
        _engine, _SessionLocal = make_engine()
        monkeypatch.setattr(database, '_engine', _engine)
        monkeypatch.setattr(database, 'SessionLocal', _SessionLocal)
        Base.metadata.create_all(bind=_engine)
        init_db()

        db = _SessionLocal()
        try:
            ensure_default_account(db)
            acc = db.query(Account).first()
            if acc:
                acc.taxpayer_type_l3 = taxpayer_type
                acc.enable_vat_deduction = enable_vat_deduction
                db.commit()
        finally:
            db.close()

        def _get_db():
            db = _SessionLocal()
            try:
                yield db
            finally:
                db.close()
        app.dependency_overrides[get_db] = _get_db
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    return _setup
