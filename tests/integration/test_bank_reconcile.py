"""银行对账 TDD 完整套件"""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from datetime import datetime, date, timedelta
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models, models_finance, models_bank
from models_finance import LedgerAccount, AccountMove, AccountMoveLine, LedgerAccountBalance

@pytest.fixture
def db():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=e)
    s = sessionmaker(bind=e)(); yield s; s.close()

def _acc(db):
    a = models.Account(name="T", code=f"BR{uuid.uuid4().hex[:4]}", taxpayer_type_l3="general")
    db.add(a); db.flush()
    from finance_integration import get_or_create_ledger_id
    get_or_create_ledger_id(db, a.id)
    return a
def _bank(db, aid):
    b = models.BankAccount(account_id=aid, bank_name="X", account_number="6222", balance_l4=0)
    db.add(b); db.flush(); return b
def _tx(db, baid, aid, amt, dr, dt, lid=None):
    tx = models.BankTransaction(bank_account_id=baid, account_id=aid, amount_l2=amt,
        transaction_type="inflow" if dr=="in" else "outflow", transaction_date_l1=dt,
        description=f"t{amt}", balance_after_l4=amt if dr=="in" else 0)
    db.add(tx); db.flush()
    ba = db.query(models.BankAccount).filter(models.BankAccount.id==baid, models.BankAccount.account_id==aid).first()
    if ba: ba.balance_l4 += (Decimal(str(amt)) if dr=="in" else -Decimal(str(amt)))
    if lid:
        ac = db.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid, LedgerAccount.code=="1002").first()
        if ac:
            m = AccountMove(ledger_id=lid, move_type="bank", date_l1=dt, state="posted")
            db.add(m); db.flush()
            deb = Decimal(str(amt)) if dr=="in" else 0
            cre = 0 if dr=="in" else Decimal(str(amt))
            db.add(AccountMoveLine(move_id=m.id, ledger_account_id=ac.id, debit_l2=deb, credit_l2=cre, amount_residual_l2=deb or cre))
            bal = db.query(LedgerAccountBalance).filter(LedgerAccountBalance.ledger_account_id==ac.id).first()
            if bal: bal.balance_l4 += (deb - cre); bal.debit_total_l4 += deb; bal.credit_total_l4 += cre
    db.flush(); return tx


class TestBankEngine:
    def test_seed_creates_items(self, db):
        acc=_acc(db);bank=_bank(db,acc.id)
        from finance_integration import get_or_create_ledger_id;lid=get_or_create_ledger_id(db,acc.id)
        _tx(db,bank.id,acc.id,1000,"in",datetime(2024,12,31,23,59,59),lid);db.commit()
        from engine_bank_reconcile import BankReconcileEngine
        e=BankReconcileEngine(db,acc.id,bank.id,"2025-01")
        rec=e.create_reconciliation([
            {"item_type":"book_paid_not_bank","amount":500,"direction":"out","source_dates":["2024-12-28"],"notes":"支票"},
            {"item_type":"bank_received_not_book","amount":200,"direction":"in","source_dates":["2024-12-30"],"notes":"利息"},
        ])
        assert rec.period=="2025-01" and rec.book_balance_l4==Decimal("1000")
        items=db.query(models_bank.ReconciliationItem).filter(models_bank.ReconciliationItem.reconciliation_id==rec.id).all()
        assert len(items)==2

    def test_1to1_match(self, db):
        acc=_acc(db);bank=_bank(db,acc.id)
        from finance_integration import get_or_create_ledger_id;lid=get_or_create_ledger_id(db,acc.id)
        _tx(db,bank.id,acc.id,1000,"in",datetime(2024,12,31,23,59,59),lid);db.commit()
        d1,d2=date(2025,1,5),date(2025,1,8)
        _tx(db,bank.id,acc.id,500,"in",d1,lid);_tx(db,bank.id,acc.id,200,"out",d2,lid);db.commit()
        stmt=models_bank.BankStatement(bank_account_id=bank.id,account_id=acc.id,
            period_start=date(2025,1,1),period_end=date(2025,1,31),opening_balance_l1=1000,closing_balance_l1=1300)
        db.add(stmt);db.flush()
        db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=d1,amount_l1=500))
        db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=d2,amount_l1=-200))
        db.commit()
        from engine_bank_reconcile import BankReconcileEngine
        e=BankReconcileEngine(db,acc.id,bank.id,"2025-01")
        e.create_reconciliation([]);e.run_matching()
        lines=db.query(models_bank.BankStatementLine).filter(models_bank.BankStatementLine.statement_id==stmt.id).all()
        for l in lines: assert l.matched_tx_ids is not None

    def test_combo_n1(self, db):
        acc=_acc(db);bank=_bank(db,acc.id)
        from finance_integration import get_or_create_ledger_id;lid=get_or_create_ledger_id(db,acc.id)
        _tx(db,bank.id,acc.id,1000,"in",datetime(2024,12,31,23,59,59),lid);db.commit()
        _tx(db,bank.id,acc.id,100,"in",date(2025,1,1),lid)
        _tx(db,bank.id,acc.id,200,"in",date(2025,1,5),lid)
        _tx(db,bank.id,acc.id,300,"in",date(2025,1,8),lid);db.commit()
        stmt=models_bank.BankStatement(bank_account_id=bank.id,account_id=acc.id,
            period_start=date(2025,1,1),period_end=date(2025,1,31),opening_balance_l1=1000,closing_balance_l1=1600)
        db.add(stmt);db.flush()
        db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=date(2025,1,10),amount_l1=600))
        db.commit()
        from engine_bank_reconcile import BankReconcileEngine
        e=BankReconcileEngine(db,acc.id,bank.id,"2025-01")
        e.create_reconciliation([]);e.run_matching()
        line=db.query(models_bank.BankStatementLine).first()
        assert line.matched_tx_ids is not None and len(line.matched_tx_ids)==3

    def test_confirm(self, db):
        acc=_acc(db);bank=_bank(db,acc.id)
        from finance_integration import get_or_create_ledger_id;lid=get_or_create_ledger_id(db,acc.id)
        _tx(db,bank.id,acc.id,5000,"in",datetime(2024,12,31,23,59,59),lid)
        _tx(db,bank.id,acc.id,500,"in",date(2025,1,5),lid);db.commit()
        stmt=models_bank.BankStatement(bank_account_id=bank.id,account_id=acc.id,
            period_start=date(2025,1,1),period_end=date(2025,1,31),opening_balance_l1=5000,closing_balance_l1=5500)
        db.add(stmt);db.flush()
        db.add(models_bank.BankStatementLine(statement_id=stmt.id,transaction_date_l1=date(2025,1,5),amount_l1=500))
        db.commit()
        from engine_bank_reconcile import BankReconcileEngine
        e=BankReconcileEngine(db,acc.id,bank.id,"2025-01")
        rec=e.create_reconciliation([]);e.run_matching()
        assert rec.balanced
        e.confirm(rec.id,"admin")
        db.refresh(rec);assert rec.status=="confirmed"


class TestBankAPI:

    def setup_method(self):
        import tempfile, models_bank
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); self._tmp.close()
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from database import Base, get_db, _request_write_perm
        e = create_engine(f"sqlite:///{self._tmp.name}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=e)
        TS = sessionmaker(bind=e, autocommit=False, autoflush=False)
        _request_write_perm.set(True)
        def _o():
            s = TS()
            try: yield s
            finally: s.close()
        from account_dep import get_account_id
        from main import app
        app.dependency_overrides[get_db] = _o
        async def _fake_aid(): return 1
        app.dependency_overrides[get_account_id] = _fake_aid
        from fastapi.testclient import TestClient
        self.client = TestClient(app)
        self.TS = TS

    def teardown_method(self):
        try: import os; os.unlink(self._tmp.name)
        except: pass

    def test_statement_import(self):
        s = self.TS()
        acc = models.Account(name="X", code=f"A{uuid.uuid4().hex[:4]}", taxpayer_type_l3="general")
        s.add(acc); s.flush(); aid = acc.id
        from finance_integration import get_or_create_ledger_id; get_or_create_ledger_id(s, aid)
        ba = models.BankAccount(account_id=aid, bank_name="X", account_number="6222", balance_l4=0)
        s.add(ba); s.flush()
        s.commit(); s.close()
        h = {"X-Account-ID": "1", "X-Operator": "user"}
        r = self.client.post("/api/bank/statement", headers=h, json={
            "period_start": "2025-01-01", "period_end": "2025-01-31",
            "opening_balance": 3000, "closing_balance": 3500,
            "lines": [{"transaction_date": "2025-01-05", "amount": 500, "description": "收款"}],
        })
        assert r.status_code == 200, r.text
        assert r.json()["id"] == 1


class TestMonthEndGuard:
    """RED-9: 调节表未确认 → 月结被拒绝"""

    def test_blocks_if_unconfirmed(self, db):
        acc = _acc(db); bank = _bank(db, acc.id)
        from finance_integration import get_or_create_ledger_id; lid = get_or_create_ledger_id(db, acc.id)
        _tx(db, bank.id, acc.id, 1000, "in", datetime(2024, 12, 31, 23, 59, 59), lid)

        # 创建未确认调节表
        stmt = models_bank.BankStatement(bank_account_id=bank.id, account_id=acc.id,
            period_start=date(2025, 1, 1), period_end=date(2025, 1, 31), opening_balance_l1=1000, closing_balance_l1=1000)
        db.add(stmt); db.flush()
        from engine_bank_reconcile import BankReconcileEngine
        e = BankReconcileEngine(db, acc.id, bank.id, "2025-01")
        rec = e.create_reconciliation([])
        # status = "draft" (unconfirmed)
        db.commit()

        # 月结应被拒绝
        from commands.month_end import MonthEndClose, MonthEndCloseHandler
        from errors import BusinessError
        cmd = MonthEndClose(account_id=acc.id, period="2025-01")
        with pytest.raises(BusinessError) as exc:
            MonthEndCloseHandler().handle(cmd, db)
        assert "银行对账未完成" in exc.value.message
