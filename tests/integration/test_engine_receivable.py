"""ReceivableEngine 集成测试"""
import pytest
from datetime import date as date_obj
from decimal import Decimal
from models_finance import (
    Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine,
    AccountPartialReconcile,
)
from accounting_engine import AccountingError
from engine_receivable import ReceivableEngine


import uuid

@pytest.fixture
def engine():
    from sqlalchemy import create_engine
    return create_engine("sqlite:///:memory:")

@pytest.fixture
def db(engine):
    from sqlalchemy.orm import sessionmaker
    from database import Base
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def ledger(db):
    suffix = uuid.uuid4().hex[:8]
    l = Ledger(name="测试账本", type="company", code=f"rec_{suffix}")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def accounts(db, ledger):
    seed = [
        ("1122", "应收账款", "asset_receivable"),
        ("2202", "应付账款", "liability_payable"),
    ]
    result = {}
    for code, name, acct_type in seed:
        a = LedgerAccount(
            ledger_id=ledger.id, code=code, name=name,
            account_type=acct_type, is_leaf=True,
        )
        db.add(a)
        db.flush()
        result[code] = a
    db.commit()
    return result


def make_move(db, ledger, day):
    """创建指定日期的凭证（仅日期不同）"""
    m = AccountMove(
        ledger_id=ledger.id,
        move_type="test",
        date=date_obj(2026, 6, day),
        state="posted",
    )
    db.add(m)
    db.flush()
    return m


def make_line(db, move, account_id, debit=Decimal("0"), credit=Decimal("0"),
              partner_id=None, partner_type=None):
    """创建分录行（自动设置 amount_residual）"""
    residual = debit or credit
    line = AccountMoveLine(
        move_id=move.id,
        ledger_account_id=account_id,
        debit=debit,
        credit=credit,
        partner_id=partner_id,
        partner_type=partner_type,
        amount_residual=residual,
    )
    db.add(line)
    db.flush()
    return line


class TestReconcile:
    """核销"""

    def test_residual_decreases(self, db, ledger, accounts):
        engine = ReceivableEngine(db)
        move = make_move(db, ledger, 15)
        line_a = make_line(db, move, accounts["1122"].id, debit=Decimal("500"),
                          partner_id=1, partner_type="customer")
        line_b = make_line(db, move, accounts["1122"].id, credit=Decimal("300"),
                          partner_id=1, partner_type="customer")

        engine.reconcile(ledger.id, line_a.id, line_b.id, Decimal("300"))
        db.commit()

        db.refresh(line_a)
        db.refresh(line_b)
        assert line_a.amount_residual == Decimal("200")
        assert line_b.amount_residual == Decimal("0")

    def test_reconciled_flag(self, db, ledger, accounts):
        engine = ReceivableEngine(db)
        move = make_move(db, ledger, 15)
        line_a = make_line(db, move, accounts["1122"].id, debit=Decimal("500"),
                          partner_id=1, partner_type="customer")
        line_b = make_line(db, move, accounts["1122"].id, credit=Decimal("500"),
                          partner_id=1, partner_type="customer")

        engine.reconcile(ledger.id, line_a.id, line_b.id, Decimal("500"))
        db.commit()

        db.refresh(line_a)
        db.refresh(line_b)
        assert line_a.reconciled is True
        assert line_b.reconciled is True

    def test_partial_reconcile_created(self, db, ledger, accounts):
        engine = ReceivableEngine(db)
        move = make_move(db, ledger, 15)
        line_a = make_line(db, move, accounts["1122"].id, debit=Decimal("500"),
                          partner_id=1, partner_type="customer")
        line_b = make_line(db, move, accounts["1122"].id, credit=Decimal("300"),
                          partner_id=1, partner_type="customer")

        engine.reconcile(ledger.id, line_a.id, line_b.id, Decimal("300"))

        rec = db.query(AccountPartialReconcile).first()
        assert rec is not None
        assert rec.debit_move_id == line_a.id
        assert rec.credit_move_id == line_b.id
        assert rec.amount == Decimal("300")
        assert rec.ledger_id == ledger.id

    def test_cross_ledger_blocked(self, db, ledger, accounts):
        """跨账本核销应报错"""
        other = Ledger(name="其他账本", type="company", code="other_rec")
        db.add(other)
        db.commit()

        engine = ReceivableEngine(db)
        move = make_move(db, ledger, 15)
        # line_a 属于 ledger
        line_a = make_line(db, move, accounts["1122"].id, debit=Decimal("100"),
                          partner_id=1, partner_type="customer")

        with pytest.raises(AccountingError) as exc:
            engine.reconcile(other.id, line_a.id, 99999, Decimal("50"))
        assert exc.value.code == "LINE_NOT_FOUND"


class TestGetPartnerBalance:
    """客户/供应商余额实时聚合"""

    def test_customer_balance(self, db, ledger, accounts):
        engine = ReceivableEngine(db)
        move = make_move(db, ledger, 15)

        make_line(db, move, accounts["1122"].id, debit=Decimal("500"),
                 partner_id=1, partner_type="customer")
        make_line(db, move, accounts["1122"].id, credit=Decimal("200"),
                 partner_id=1, partner_type="customer")

        bal = engine.get_partner_balance(1, "customer")
        assert bal == Decimal("300")

    def test_supplier_balance(self, db, ledger, accounts):
        engine = ReceivableEngine(db)
        move = make_move(db, ledger, 15)

        make_line(db, move, accounts["2202"].id, debit=Decimal("100"),
                 partner_id=2, partner_type="supplier")
        make_line(db, move, accounts["2202"].id, credit=Decimal("500"),
                 partner_id=2, partner_type="supplier")

        bal = engine.get_partner_balance(2, "supplier")
        assert bal == Decimal("-400")

    def test_filter_by_account_type(self, db, ledger, accounts):
        engine = ReceivableEngine(db)
        move = make_move(db, ledger, 15)

        make_line(db, move, accounts["1122"].id, debit=Decimal("500"),
                 partner_id=1, partner_type="customer")
        make_line(db, move, accounts["2202"].id, debit=Decimal("300"),
                 partner_id=1, partner_type="customer")

        bal = engine.get_partner_balance(1, "customer", account_type="asset_receivable")
        assert bal == Decimal("500")

    def test_as_of_filter(self, db, ledger, accounts):
        engine = ReceivableEngine(db)
        move_early = make_move(db, ledger, 1)
        move_late = make_move(db, ledger, 20)

        make_line(db, move_early, accounts["1122"].id, debit=Decimal("500"),
                 partner_id=1, partner_type="customer")
        make_line(db, move_late, accounts["1122"].id, debit=Decimal("300"),
                 partner_id=1, partner_type="customer")

        bal = engine.get_partner_balance(1, "customer", as_of="2026-06-15")
        assert bal == Decimal("500")


class TestAgingReport:
    """账龄分析"""

    def test_basic_buckets(self, db, ledger, accounts):
        """as_of=2026-06-23, thresholds: d30=May24 d60=Apr24 d90=Mar25
        - Jun15 >= May24 → 0-30
        - May15: <May24, >=Apr24 → 31-60
        - Apr1:  <Apr24, >=Mar25 → 61-90
        - Mar1:  <Mar25          → 90+
        """
        engine = ReceivableEngine(db)

        dates_amounts = [
            (date_obj(2026, 6, 15), 500),
            (date_obj(2026, 6, 15), 200),   # 合计 700 → 0-30
            (date_obj(2026, 5, 15), 300),    # → 31-60
            (date_obj(2026, 4, 1),  400),    # → 61-90
            (date_obj(2026, 3, 1),  100),    # → 90+
        ]

        for d, amt in dates_amounts:
            m = AccountMove(
                ledger_id=ledger.id, move_type="test",
                date=d, state="posted",
            )
            db.add(m)
            db.flush()
            make_line(db, m, accounts["1122"].id, debit=Decimal(str(amt)),
                     partner_id=1, partner_type="customer")

        aging = engine.get_aging_report(1, "customer", as_of_date="2026-06-23")
        assert aging["0-30"] == Decimal("700")
        assert aging["31-60"] == Decimal("300")
        assert aging["61-90"] == Decimal("400")
        assert aging["90+"] == Decimal("100")

    def test_reconciled_lines_excluded(self, db, ledger, accounts):
        engine = ReceivableEngine(db)

        m1 = AccountMove(
            ledger_id=ledger.id, move_type="test",
            date=date_obj(2026, 6, 15), state="posted",
        )
        db.add(m1)
        db.flush()

        line_200 = make_line(db, m1, accounts["1122"].id, debit=Decimal("200"),
                            partner_id=1, partner_type="customer")
        make_line(db, m1, accounts["1122"].id, debit=Decimal("300"),
                 partner_id=1, partner_type="customer")

        # 核销 200 那条
        m2 = AccountMove(
            ledger_id=ledger.id, move_type="test",
            date=date_obj(2026, 6, 20), state="posted",
        )
        db.add(m2)
        db.flush()
        credit_line = make_line(db, m2, accounts["1122"].id, credit=Decimal("200"),
                               partner_id=1, partner_type="customer")
        engine.reconcile(ledger.id, line_200.id, credit_line.id, Decimal("200"))

        aging = engine.get_aging_report(1, "customer", as_of_date="2026-06-23")
        # 200 那条已核销,不应计入; 300 未核销应计入
        assert aging["0-30"] == Decimal("300")
        assert aging["31-60"] == Decimal("0")

    def test_all_buckets_present(self, db, ledger, accounts):
        """即使无数据,4个bucket都应返回0"""
        engine = ReceivableEngine(db)
        aging = engine.get_aging_report(999, "customer", as_of_date="2026-06-23")
        assert aging == {"0-30": Decimal("0"), "31-60": Decimal("0"),
                         "61-90": Decimal("0"), "90+": Decimal("0")}
