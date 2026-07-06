"""P7: trace API 集成测试"""
import pytest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Account
from models_finance import Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine
from crud.finance._snapshot import LedgerSnapshot

CHART = [
    ("1002", "银行存款", "asset"),
    ("1122", "应收账款", "asset"),
    ("2202", "应付账款", "liability"),
    ("222103", "应交增值税-小规模", "liability"),
    ("3001", "实收资本", "equity"),
    ("4103", "本年利润", "equity"),
    ("6001", "主营业务收入", "income"),
    ("6401", "主营业务成本", "expense"),
    ("6601", "管理费用", "expense"),
    ("6801", "所得税费用", "expense"),
]


@pytest.fixture
def api_test_db():
    engine = sa_create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    acc = Account(id=1, name="API测试", code="api_test", type="company",
                  taxpayer_type_l3="small_scale")
    db.add(acc); db.flush()
    ledger = Ledger(code=acc.code, name=acc.name, type=acc.type,
                    taxpayer_type_l3=acc.taxpayer_type_l3)
    db.add(ledger); db.flush()

    la = {}
    for ccode, cname, ctype in CHART:
        x = LedgerAccount(ledger_id=ledger.id, code=ccode, name=cname,
                          account_type=ctype, is_leaf=True, is_active=True)
        db.add(x); db.flush()
        db.add(LedgerAccountBalance(ledger_account_id=x.id, balance_l4=0))
        la[ccode] = x
    db.flush()

    # 实收资本
    mv = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 1, 10).date(),
                     source_model="opening", source_id=0, name="INIT-001")
    db.add(mv); db.flush()
    db.add_all([
        AccountMoveLine(move_id=mv.id, ledger_account_id=la["1002"].id,
                        debit_l2=Decimal("50000"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=mv.id, ledger_account_id=la["3001"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("50000")),
    ])

    # 收入
    m1 = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 6, 15).date(),
                     source_model="sale", source_id=1, name="SALE-001")
    db.add(m1); db.flush()
    db.add_all([
        AccountMoveLine(move_id=m1.id, ledger_account_id=la["1122"].id,
                        debit_l2=Decimal("11300"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=m1.id, ledger_account_id=la["6001"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("10000")),
        AccountMoveLine(move_id=m1.id, ledger_account_id=la["222103"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("1300")),
    ])

    # 结转
    m2 = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 6, 30).date(),
                     source_model="period_close", source_id=0, name="CLOSE-06")
    db.add(m2); db.flush()
    db.add_all([
        AccountMoveLine(move_id=m2.id, ledger_account_id=la["6001"].id,
                        debit_l2=Decimal("10000"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=m2.id, ledger_account_id=la["4103"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("10000")),
    ])

    db.commit()
    return db, la


def test_bs_no_trace_returns_flat(api_test_db):
    """trace=false 返回平铺数字"""
    db, la = api_test_db
    cutoff = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=cutoff)

    from reports.engine import ReportEngine
    from reports.definitions.balance_sheet import BALANCE_SHEET

    engine = ReportEngine()
    result = engine.execute(BALANCE_SHEET, sn, trace=False, source_mode="ledger")

    assert isinstance(result["total_assets"], float)
    assert isinstance(result["accounts_receivable"], float)


def test_bs_trace_returns_nested(api_test_db):
    """trace=true 返回嵌套 contributions"""
    db, la = api_test_db
    cutoff = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=cutoff)

    from reports.engine import ReportEngine
    from reports.definitions.balance_sheet import BALANCE_SHEET

    engine = ReportEngine()
    result = engine.execute(BALANCE_SHEET, sn, trace=True, source_mode="ledger")

    assert isinstance(result["accounts_receivable"], dict)
    assert "value" in result["accounts_receivable"]
    assert "contributions" in result["accounts_receivable"]


def test_is_trace_returns_nested(api_test_db):
    """IS trace 模式返回 contributions"""
    db, la = api_test_db
    ed = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=ed,
                        period_start=datetime(2025, 1, 1), period_end=ed)

    from reports.engine import ReportEngine
    from reports.definitions.income_statement import INCOME_STATEMENT

    engine = ReportEngine()
    result = engine.execute(INCOME_STATEMENT, sn, trace=True)

    assert isinstance(result["revenue"], dict)
    assert "contributions" in result["revenue"]
    assert len(result["revenue"]["contributions"]) > 0


def test_bs_balanced(api_test_db):
    """BS 必须平衡"""
    db, la = api_test_db
    cutoff = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=cutoff)

    from reports.engine import ReportEngine
    from reports.definitions.balance_sheet import BALANCE_SHEET

    engine = ReportEngine()
    result = engine.execute(BALANCE_SHEET, sn, trace=False, source_mode="ledger")

    diff = abs(result["total_assets"] - (result["total_liabilities"] + result["total_equity"]))
    assert diff < 0.02, f"不平衡: diff={diff}"
