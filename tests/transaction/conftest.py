"""事务测试共享基础设施 — 每个文件独立 temp DB"""
import pytest
import os
import uuid
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db


@pytest.fixture(scope="module")
def db():
    # 先导入所有模型以注册到 Base.metadata
    import models  # noqa: F401
    import models_finance  # noqa: F401
    db_path = os.path.join(tempfile.gettempdir(), f"tx_{uuid.uuid4().hex[:12]}.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="module")
def bootstrap_db(db):
    """Ensure Account+Ledger exist for all tests in module"""
    from models import Account
    if db.query(Account).filter(Account.id == 1).first():
        return
    account = Account(name="测试账本", type="company", code="company", taxpayer_type_l3="small_scale")
    db.add(account)
    db.flush()
    from finance_integration import get_or_create_ledger_id
    get_or_create_ledger_id(db, account.id)
    db.commit()


@pytest.fixture(scope="module")
def client(db):
    from main import app
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c
    app.dependency_overrides.clear()
