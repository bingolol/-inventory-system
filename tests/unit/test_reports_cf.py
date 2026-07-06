"""P5: CF 定义测试"""
import pytest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Account, BankAccount, BankTransaction
from models_finance import Ledger, LedgerAccount, LedgerAccountBalance
from crud.finance._snapshot import LedgerSnapshot

BANK_CHART = [
    ("1001", "库存现金", "asset"), ("1002", "银行存款", "asset"),
    ("3001", "实收资本", "equity"),
    ("6001", "主营业务收入", "income"), ("6601", "管理费用", "expense"),
    ("222103", "应交增值税-小规模", "liability"),
]


@pytest.fixture
def cf_test_db():
    engine = sa_create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    acc = Account(id=1, name="CF测试", code="cf_test", type="company",
                  taxpayer_type_l3="small_scale")
    db.add(acc); db.flush()
    ledger = Ledger(code=acc.code, name=acc.name, type=acc.type,
                    taxpayer_type_l3=acc.taxpayer_type_l3)
    db.add(ledger); db.flush()

    la = {}
    for ccode, cname, ctype in BANK_CHART:
        x = LedgerAccount(ledger_id=ledger.id, code=ccode, name=cname,
                          account_type=ctype, is_leaf=True, is_active=True)
        db.add(x); db.flush()
        db.add(LedgerAccountBalance(ledger_account_id=x.id, balance_l4=0))
        la[ccode] = x
    db.flush()

    # 银行账户
    ba = BankAccount(account_id=1, bank_name="测试银行",
                     account_number="123456", balance_l4=Decimal("0"))
    db.add(ba); db.flush()

    # 销售收款（CF01 = 销售商品收到现金）
    tx1 = BankTransaction(
        account_id=1, bank_account_id=ba.id,
        transaction_type="inflow", amount_l2=Decimal("11300"),
        transaction_date_l1=datetime(2025, 3, 15),
        balance_after_l4=Decimal("11300"),
        related_entity_type="sale_order", related_entity_id=1,
        description="销售收款",
    )
    # 费用支付（CF06 = 支付其他经营现金）
    tx2 = BankTransaction(
        account_id=1, bank_account_id=ba.id,
        transaction_type="outflow", amount_l2=Decimal("2000"),
        transaction_date_l1=datetime(2025, 3, 20),
        balance_after_l4=Decimal("9300"),
        related_entity_type="expense", related_entity_id=1,
        description="支付办公费",
    )
    db.add_all([tx1, tx2])
    db.commit()
    return db, la


def test_cf_self_consistent(cf_test_db):
    """CF 内部一致性：net_cash_flow == net_operating + net_investing + net_financing"""
    db, la = cf_test_db

    from reports.engine import ReportEngine
    from reports.definitions.cash_flow import CASH_FLOW

    start = datetime(2025, 1, 1)
    end = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, period_start=start, period_end=end)

    engine = ReportEngine()
    result = engine.execute(CASH_FLOW, sn)

    net = result["net_operating"] + result["net_investing"] + result["net_financing"]
    assert abs(net - result["net_cash_flow"]) < 0.02

    ending = result["beginning_cash"] + result["net_cash_flow"]
    assert abs(ending - result["ending_cash"]) < 0.02


def test_cf_classified_amounts(cf_test_db):
    """销售收款应收进 CF01（正数），费用支付应收进 CF06（负数）"""
    db, la = cf_test_db

    from reports.engine import ReportEngine
    from reports.definitions.cash_flow import CASH_FLOW

    start = datetime(2025, 1, 1)
    end = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, period_start=start, period_end=end)

    engine = ReportEngine()
    result = engine.execute(CASH_FLOW, sn)

    assert float(result["CF01"]) > 0, "销售收款应收进正数"
    assert float(result["CF06"]) < 0, "费用支付应收进负数"
    assert float(result["operating_inflows"]) > 0
    assert float(result["operating_outflows"]) < 0


def test_cf_trace_returns_txn_contributions(cf_test_db):
    """CF trace 模式返回 txn 级别的 contributions"""
    db, la = cf_test_db

    from reports.engine import ReportEngine
    from reports.definitions.cash_flow import CASH_FLOW

    start = datetime(2025, 1, 1)
    end = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, period_start=start, period_end=end)

    engine = ReportEngine()
    result = engine.execute(CASH_FLOW, sn, trace=True)

    cf01 = result["CF01"]
    assert isinstance(cf01, dict)
    assert "contributions" in cf01
    assert len(cf01["contributions"]) == 1
    contrib = cf01["contributions"][0]
    assert contrib["source_type"] == "bank_txn"
