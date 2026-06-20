"""flow_category 测试 — BankTransaction 现金流量分类

测试：
- BankTransaction 新增 flow_category 字段
- 付款/收款默认 flow_category=operating
- 现金流量表按 flow_category 分类
"""
import pytest
from decimal import Decimal
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
import models
from enums import FlowCategory


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def seed_data(db):
    """创建测试基础数据"""
    account = models.Account(id=1, name="测试账本", type="company", code="test", taxpayer_type="small_scale")
    db.add(account)

    bank_account = models.BankAccount(id=1, account_id=1, bank_name="测试银行", account_number="123456", balance=Decimal("10000"))
    db.add(bank_account)

    db.flush()
    return {"account_id": 1, "bank_account_id": 1}


class TestBankTransactionFlowCategory:
    def test_model_has_flow_category_field(self, db, seed_data):
        """BankTransaction 模型有 flow_category 字段"""
        tx = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="inflow", amount=Decimal("1000"),
            balance_after=Decimal("11000"),
            transaction_date=datetime.now(),
            flow_category=FlowCategory.OPERATING,
        )
        db.add(tx)
        db.flush()
        assert tx.flow_category == "operating"

    def test_default_flow_category_is_operating(self, db, seed_data):
        """默认 flow_category 为 operating"""
        tx = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="inflow", amount=Decimal("1000"),
            balance_after=Decimal("11000"),
            transaction_date=datetime.now(),
        )
        db.add(tx)
        db.flush()
        assert tx.flow_category == "operating"

    def test_can_set_investing_category(self, db, seed_data):
        """可以设置为 investing"""
        tx = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="outflow", amount=Decimal("5000"),
            balance_after=Decimal("5000"),
            transaction_date=datetime.now(),
            flow_category=FlowCategory.INVESTING,
        )
        db.add(tx)
        db.flush()
        assert tx.flow_category == "investing"

    def test_can_set_financing_category(self, db, seed_data):
        """可以设置为 financing"""
        tx = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="inflow", amount=Decimal("50000"),
            balance_after=Decimal("60000"),
            transaction_date=datetime.now(),
            flow_category=FlowCategory.FINANCING,
        )
        db.add(tx)
        db.flush()
        assert tx.flow_category == "financing"


class TestCashFlowStatementClassification:
    def test_operating_transactions_classified_correctly(self, db, seed_data):
        """经营活动流水正确分类"""
        from crud.finance import generate_cash_flow_statement

        # 经营流入
        tx1 = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="inflow", amount=Decimal("1000"),
            balance_after=Decimal("11000"),
            transaction_date=datetime(2026, 1, 15),
            flow_category=FlowCategory.OPERATING,
        )
        db.add(tx1)
        db.flush()

        result = generate_cash_flow_statement(db, 1, "2026-01-01", "2026-01-31")
        assert result["operating_activities"]["inflows"] == Decimal("1000.00")

    def test_investing_transactions_classified_correctly(self, db, seed_data):
        """投资活动流水正确分类"""
        from crud.finance import generate_cash_flow_statement

        # 投资流出（购买设备）
        tx = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="outflow", amount=Decimal("5000"),
            balance_after=Decimal("5000"),
            transaction_date=datetime(2026, 1, 15),
            flow_category=FlowCategory.INVESTING,
        )
        db.add(tx)
        db.flush()

        result = generate_cash_flow_statement(db, 1, "2026-01-01", "2026-01-31")
        assert result["investing_activities"]["outflows"] == Decimal("5000.00")
        assert result["operating_activities"]["outflows"] == Decimal("0.00")

    def test_financing_transactions_classified_correctly(self, db, seed_data):
        """筹资活动流水正确分类"""
        from crud.finance import generate_cash_flow_statement

        # 筹资流入（银行贷款）
        tx = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="inflow", amount=Decimal("50000"),
            balance_after=Decimal("60000"),
            transaction_date=datetime(2026, 1, 15),
            flow_category=FlowCategory.FINANCING,
        )
        db.add(tx)
        db.flush()

        result = generate_cash_flow_statement(db, 1, "2026-01-01", "2026-01-31")
        assert result["financing_activities"]["inflows"] == Decimal("50000.00")
        assert result["operating_activities"]["inflows"] == Decimal("0.00")

    def test_mixed_categories(self, db, seed_data):
        """混合分类正确"""
        from crud.finance import generate_cash_flow_statement

        # 经营流入
        tx1 = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="inflow", amount=Decimal("1000"),
            balance_after=Decimal("11000"),
            transaction_date=datetime(2026, 1, 15),
            flow_category=FlowCategory.OPERATING,
        )
        # 投资流出
        tx2 = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="outflow", amount=Decimal("5000"),
            balance_after=Decimal("6000"),
            transaction_date=datetime(2026, 1, 20),
            flow_category=FlowCategory.INVESTING,
        )
        # 筹资流入
        tx3 = models.BankTransaction(
            account_id=1, bank_account_id=1,
            transaction_type="inflow", amount=Decimal("50000"),
            balance_after=Decimal("56000"),
            transaction_date=datetime(2026, 1, 25),
            flow_category=FlowCategory.FINANCING,
        )
        db.add_all([tx1, tx2, tx3])
        db.flush()

        result = generate_cash_flow_statement(db, 1, "2026-01-01", "2026-01-31")
        assert result["operating_activities"]["inflows"] == Decimal("1000.00")
        assert result["investing_activities"]["outflows"] == Decimal("5000.00")
        assert result["financing_activities"]["inflows"] == Decimal("50000.00")
