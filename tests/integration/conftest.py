"""集成测试公共 fixture"""
import pytest
from fastapi.testclient import TestClient
from database import SessionLocal, set_maintenance_mode, init_db


@pytest.fixture(autouse=True)
def ensure_account():
    """确保 Account(id=1) 和 Ledger/LedgerAccount 存在（集成测试使用真实 DB 时需要）"""
    set_maintenance_mode(True)
    try:
        init_db()
        # init_db 会在 finally 中关闭维护模式，恢复以保证后续 ORM 写入被放行
        set_maintenance_mode(True)
        from models import Account
        from models_finance import Ledger, LedgerAccount, LedgerAccountBalance
        from finance_integration import CHART_OF_ACCOUNTS
        db = SessionLocal()
        try:
            acc = db.query(Account).filter(Account.id == 1).first()
            if not acc:
                acc = Account(id=1, name="测试账本", code="test", type="company", taxpayer_type_l3="small_scale")
                db.add(acc)
                db.flush()
            ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
            if not ledger:
                ledger = Ledger(code=acc.code, name=acc.name, type=acc.type or "company", taxpayer_type_l3=acc.taxpayer_type_l3 or "small_scale")
                db.add(ledger)
                db.flush()
                for code, name, atype in CHART_OF_ACCOUNTS:
                    la = LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True, is_active=True)
                    db.add(la)
                    db.flush()
                    db.add(LedgerAccountBalance(ledger_account_id=la.id, balance_l4=0, debit_total_l4=0, credit_total_l4=0))
            db.commit()
        except Exception:
            import traceback, logging
            logging.getLogger("inventory").error(f"ensure_account fixture failed: {traceback.format_exc()}")
            raise
        finally:
            db.close()
    finally:
        set_maintenance_mode(False)


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
