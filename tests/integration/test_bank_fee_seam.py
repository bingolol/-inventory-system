"""post_bank_fee_journal seam 集成测试"""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from database import Base
import models, models_finance
from models_finance import AccountMove, AccountMoveLine, LedgerAccount


@pytest.fixture
def db():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=e)
    s = sessionmaker(bind=e)()
    yield s
    s.close()


def _setup(db):
    """创建 account + ledger + ledger_accounts，返回 account_id"""
    a = models.Account(name="测试账本", code=f"BF{uuid.uuid4().hex[:4]}", taxpayer_type_l3="small_scale")
    db.add(a)
    db.flush()
    from finance_integration import get_or_create_ledger_id
    lid = get_or_create_ledger_id(db, a.id)
    return a.id, lid


def _codes_by_line(db, move_id):
    """返回 {account_code: AccountMoveLine} map"""
    lines = db.query(AccountMoveLine).filter(
        AccountMoveLine.move_id == move_id
    ).all()
    result = {}
    for ln in lines:
        la = db.query(LedgerAccount).filter(
            LedgerAccount.id == ln.ledger_account_id
        ).first()
        result[la.code] = ln
    return result


class TestPostBankFeeJournal:
    def test_bank_fee_creates_account_move(self, db):
        """手续费出账: post_bank_fee_journal 生成 dr 6603 / cr 1002"""
        aid, _ = _setup(db)
        from finance_integration import post_bank_fee_journal

        move = post_bank_fee_journal(
            db, aid, Decimal("100"), "out", "2026-07-01",
            "test_fee", 42,
        )

        assert move is not None
        assert move.move_type == "bank_fee_entry"
        codes = _codes_by_line(db, move.id)
        assert "6603" in codes
        assert codes["6603"].debit_l2 == Decimal("100")
        assert codes["6603"].credit_l2 == Decimal("0")
        assert "1002" in codes
        assert codes["1002"].credit_l2 == Decimal("100")
        assert codes["1002"].debit_l2 == Decimal("0")

    def test_bank_interest_creates_account_move(self, db):
        """利息入账: post_bank_fee_journal 生成 dr 1002 / cr 6603"""
        aid, _ = _setup(db)
        from finance_integration import post_bank_fee_journal

        move = post_bank_fee_journal(
            db, aid, Decimal("50"), "in", "2026-07-01",
            "test_interest", 43,
        )

        codes = _codes_by_line(db, move.id)
        assert "1002" in codes
        assert codes["1002"].debit_l2 == Decimal("50")
        assert "6603" in codes
        assert codes["6603"].credit_l2 == Decimal("50")

    def test_idempotent_same_source(self, db):
        """相同 source_model + source_id 返回同一凭证"""
        aid, _ = _setup(db)
        from finance_integration import post_bank_fee_journal

        m1 = post_bank_fee_journal(
            db, aid, Decimal("200"), "out", "2026-07-01",
            "test_idem", 99,
        )
        m2 = post_bank_fee_journal(
            db, aid, Decimal("999"), "out", "2026-07-02",
            "test_idem", 99,
        )
        assert m1.id == m2.id

    def test_invalid_direction_raises(self, db):
        """非法的 direction 抛 BusinessError"""
        aid, _ = _setup(db)
        from finance_integration import post_bank_fee_journal
        from errors import BusinessError

        with pytest.raises(BusinessError):
            post_bank_fee_journal(
                db, aid, Decimal("100"), "invalid", "2026-07-01",
                "test_invalid", 1,
            )
