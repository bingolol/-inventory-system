"""不变量测试共享基础设施 — 每个文件独立 temp DB"""
import pytest
import os
import uuid
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db


@pytest.fixture(scope="function")
def db():
    import models  # noqa: F401
    import models_finance  # noqa: F401
    db_path = os.path.join(tempfile.gettempdir(), f"inv_{uuid.uuid4().hex[:12]}.db")
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


@pytest.fixture(scope="function")
def bootstrap_db(db):
    """建账本+总账+标准科目（一般纳税人）"""
    from models import Account
    if db.query(Account).filter(Account.id == 1).first():
        return
<<<<<<< Updated upstream
    account = Account(name="不变量测试账本", type="company", code="invariants", taxpayer_type="general")
=======
    account = Account(name="不变量测试账本", type="company", code="invariants", taxpayer_type_l3="general")
>>>>>>> Stashed changes
    db.add(account)
    db.flush()
    from finance_integration import get_or_create_ledger_id
    ledger_id = get_or_create_ledger_id(db, account.id)
    # get_or_create_ledger_id 已自动建好标准科目（1001/1002/1405/2202/222102 等）
    db.commit()
