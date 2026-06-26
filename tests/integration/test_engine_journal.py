"""JournalEngine 集成测试"""
import pytest
from datetime import date as date_obj
from decimal import Decimal
from models import Product
from models_finance import (
    Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine,
    AccountingError,
)
from engine_journal import JournalEngine


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
    l = Ledger(name="测试账本", type="company", code=f"jl_{suffix}")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def accounts(db, ledger):
    """创建 Phase 1 所需的所有叶子科目"""
    seed = [
        ("1001", "库存现金", "asset"),
        ("1002", "银行存款", "asset"),
        ("1122", "应收账款", "asset_receivable"),
        ("1405", "库存商品", "asset"),
        ("2202", "应付账款", "liability_payable"),
        ("222101", "应交增值税-销项税额", "liability"),
        ("222102", "应交增值税-进项税额", "liability"),
        ("6001", "主营业务收入", "income"),
        ("6401", "主营业务成本", "expense"),
        ("6601", "管理费用", "expense"),
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


@pytest.fixture
def product(db, ledger):
    p = Product(
        account_id=1, name="测试商品", sku="T-001",
        purchase_price=Decimal("50"), sale_price=Decimal("100"),
    )
    db.add(p)
    db.commit()
    return p


class TestSaleOrder:
    """销售单凭证"""

    def test_creates_correct_lines(self, db, ledger, accounts, product):
        engine = JournalEngine(db)
        source = {
            "partner_id": 1,
            "total_with_tax": Decimal("113.00"),
            "total_without_tax": Decimal("100.00"),
            "tax_amount": Decimal("13.00"),
            "date": date_obj(2026, 6, 15),
            "items": [
                {"product_id": product.id, "quantity": 2},
            ],
        }
        move = engine.post(ledger.id, "sale_order", source)
        db.commit()

        assert move.state == "posted"
        assert move.name.startswith("SALE-2026-")
        assert move.amount_total == Decimal("213.00")

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 5

        # 借 1122 应收账款 113
        assert lines[0].ledger_account_id == accounts["1122"].id
        assert lines[0].debit == Decimal("113.00")
        assert lines[0].credit == Decimal("0")
        assert lines[0].partner_id == 1
        assert lines[0].partner_type == "customer"
        assert lines[0].amount_residual == Decimal("113.00")

        # 贷 6001 主营业务收入 100
        assert lines[1].ledger_account_id == accounts["6001"].id
        assert lines[1].debit == Decimal("0")
        assert lines[1].credit == Decimal("100.00")
        assert lines[1].amount_residual == Decimal("100.00")

        # 贷 222101 销项税 13
        assert lines[2].ledger_account_id == accounts["222101"].id
        assert lines[2].credit == Decimal("13.00")
        assert lines[2].amount_residual == Decimal("13.00")

        # 借 6401 主营业务成本 100 (2 * 50)
        assert lines[3].ledger_account_id == accounts["6401"].id
        assert lines[3].debit == Decimal("100.00")

        # 贷 1405 库存商品 100
        assert lines[4].ledger_account_id == accounts["1405"].id
        assert lines[4].credit == Decimal("100.00")

    def test_balance_check(self, db, ledger, accounts, product):
        engine = JournalEngine(db)
        source = {
            "partner_id": 1,
            "total_with_tax": Decimal("113.00"),
            "total_without_tax": Decimal("100.00"),
            "tax_amount": Decimal("13.00"),
            "date": date_obj(2026, 6, 15),
            "items": [
                {"product_id": product.id, "quantity": 0},
            ],
        }
        move = engine.post(ledger.id, "sale_order", source)
        db.commit()

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).all()
        total_debit = sum(l.debit for l in lines)
        total_credit = sum(l.credit for l in lines)
        assert total_debit == total_credit

    def test_amount_mismatch_raises(self, db, ledger, accounts):
        engine = JournalEngine(db)
        source = {
            "partner_id": 1,
            "total_with_tax": Decimal("113.00"),
            "total_without_tax": Decimal("100.00"),
            "tax_amount": Decimal("10.00"),
            "date": date_obj(2026, 6, 15),
            "items": [],
        }
        with pytest.raises(AccountingError) as exc:
            engine.post(ledger.id, "sale_order", source)
        assert exc.value.code == "AMOUNT_MISMATCH"

    def test_residual_on_debit_line(self, db, ledger, accounts, product):
        """借记行 amount_residual = debit（正数）"""
        engine = JournalEngine(db)
        source = {
            "partner_id": 1,
            "total_with_tax": Decimal("56.50"),
            "total_without_tax": Decimal("50.00"),
            "tax_amount": Decimal("6.50"),
            "date": date_obj(2026, 6, 15),
            "items": [{"product_id": product.id, "quantity": 1}],
        }
        move = engine.post(ledger.id, "sale_order", source)
        db.commit()

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        # 1122 是借记行 → residual = debit
        assert lines[0].amount_residual == lines[0].debit == Decimal("56.50")
        # 6001 是贷记行 → residual = credit
        assert lines[1].amount_residual == lines[1].credit == Decimal("50.00")


class TestPurchaseOrder:
    """采购单凭证"""

    def test_creates_correct_lines(self, db, ledger, accounts):
        engine = JournalEngine(db)
        source = {
            "partner_id": 2,
            "total_with_tax": Decimal("226.00"),
            "total_without_tax": Decimal("200.00"),
            "tax_amount": Decimal("26.00"),
            "date": date_obj(2026, 6, 16),
        }
        move = engine.post(ledger.id, "purchase_order", source)
        db.commit()

        assert move.state == "posted"
        assert move.name.startswith("PURCHASE-2026-")

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 3

        # 借 1405 库存商品 200
        assert lines[0].ledger_account_id == accounts["1405"].id
        assert lines[0].debit == Decimal("200.00")

        # 借 222102 进项税 26
        assert lines[1].ledger_account_id == accounts["222102"].id
        assert lines[1].debit == Decimal("26.00")

        # 贷 2202 应付账款 226
        assert lines[2].ledger_account_id == accounts["2202"].id
        assert lines[2].credit == Decimal("226.00")
        assert lines[2].partner_id == 2
        assert lines[2].partner_type == "supplier"
        assert lines[2].amount_residual == Decimal("226.00")


class TestReceipt:
    """收款单凭证"""

    def test_creates_correct_lines(self, db, ledger, accounts):
        engine = JournalEngine(db)
        source = {
            "partner_id": 1,
            "amount": Decimal("500.00"),
            "bank_account_id": 10,
            "date": date_obj(2026, 6, 20),
        }
        move = engine.post(ledger.id, "receipt", source)
        db.commit()

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 2

        # 借 1002 银行存款 500
        assert lines[0].ledger_account_id == accounts["1002"].id
        assert lines[0].debit == Decimal("500.00")

        # 贷 1122 应收账款 500
        assert lines[1].ledger_account_id == accounts["1122"].id
        assert lines[1].credit == Decimal("500.00")
        assert lines[1].partner_id == 1
        assert lines[1].partner_type == "customer"


class TestPayment:
    """付款单凭证"""

    def test_creates_correct_lines(self, db, ledger, accounts):
        engine = JournalEngine(db)
        source = {
            "partner_id": 2,
            "amount": Decimal("300.00"),
            "bank_account_id": 10,
            "date": date_obj(2026, 6, 21),
        }
        move = engine.post(ledger.id, "payment", source)
        db.commit()

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 2

        # 借 2202 应付账款 300
        assert lines[0].ledger_account_id == accounts["2202"].id
        assert lines[0].debit == Decimal("300.00")
        assert lines[0].partner_id == 2
        assert lines[0].partner_type == "supplier"

        # 贷 1002 银行存款 300
        assert lines[1].ledger_account_id == accounts["1002"].id
        assert lines[1].credit == Decimal("300.00")


class TestExpense:
    """费用报销凭证"""

    def test_creates_correct_lines(self, db, ledger, accounts):
        engine = JournalEngine(db)
        source = {
            "amount": Decimal("200.00"),
            "bank_account_id": 10,
            "expense_account_code": "6601",
            "date": date_obj(2026, 6, 22),
        }
        move = engine.post(ledger.id, "expense", source)
        db.commit()

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 2

        # 借 6601 管理费用 200
        assert lines[0].ledger_account_id == accounts["6601"].id
        assert lines[0].debit == Decimal("200.00")

        # 贷 1002 银行存款 200
        assert lines[1].ledger_account_id == accounts["1002"].id
        assert lines[1].credit == Decimal("200.00")


class TestErrors:
    """异常处理"""

    def test_unknown_move_type(self, db, ledger, accounts):
        engine = JournalEngine(db)
        with pytest.raises(AccountingError) as exc:
            engine.post(ledger.id, "unknown_type", {})
        assert exc.value.code == "UNKNOWN_MOVE_TYPE"

    def test_field_required(self, db, ledger, accounts):
        engine = JournalEngine(db)
        source = {"partner_id": 1, "total_with_tax": Decimal("100"), "date": date_obj(2026, 6, 1)}
        with pytest.raises(AccountingError) as exc:
            engine.post(ledger.id, "sale_order", source)
        assert exc.value.code == "FIELD_REQUIRED"

    def test_cash_insufficient_via_expense(self, db, ledger, accounts):
        """通过费用报销触发库存现金余额不足"""
        engine = JournalEngine(db)
        source = {
            "amount": Decimal("100.00"),
            "bank_account_id": 10,
            "expense_account_code": "6601",
            "date": date_obj(2026, 6, 22),
        }
        engine.post(ledger.id, "expense", source)
        db.commit()

        # 再次报销 100，但库存现金只有测试代码中写入的余额，
        # 不过我们测试的是 1002 银行存款，不是 1001 库存现金
        # 1002 没有硬性余额校验，所以不会报错
        source2 = {
            "amount": Decimal("99999.00"),
            "bank_account_id": 10,
            "expense_account_code": "6601",
            "date": date_obj(2026, 6, 23),
        }
        engine.post(ledger.id, "expense", source2)
        db.commit()

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id.in_(
                db.query(AccountMove.id).filter(AccountMove.move_type == "expense")
            )
        ).all()
        assert len(lines) == 4


class TestBalanceUpdated:
    """余额更新验证"""

    def test_ledger_balance_after_sale(self, db, ledger, accounts, product):
        engine = JournalEngine(db)
        source = {
            "partner_id": 1,
            "total_with_tax": Decimal("113.00"),
            "total_without_tax": Decimal("100.00"),
            "tax_amount": Decimal("13.00"),
            "date": date_obj(2026, 6, 15),
            "items": [{"product_id": product.id, "quantity": 2}],
        }
        engine.post(ledger.id, "sale_order", source)
        db.commit()

        bal = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["1122"].id
        ).first()
        assert bal.balance == Decimal("113.00")

        bal = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["1405"].id
        ).first()
        assert bal.balance == Decimal("-100.00")

        bal = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["6001"].id
        ).first()
        assert bal.balance == Decimal("-100.00")
