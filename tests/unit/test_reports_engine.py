"""P3: ReportEngine + IS 定义 端到端测试"""
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
    ("1001", "库存现金", "asset"),
    ("4103", "本年利润", "equity"),
    ("6001", "主营业务收入", "income"),
    ("6051", "其他业务收入", "income"),
    ("6401", "主营业务成本", "expense"),
    ("6403", "税金及附加", "expense"),
    ("640302", "税金及附加-城建税", "expense"),
    ("6601", "管理费用", "expense"),
    ("6602", "销售费用", "expense"),
    ("6603", "财务费用", "expense"),
    ("6301", "营业外收入", "income"),
    ("6111", "资产处置收益", "income"),
    ("6701", "营业外支出", "expense"),
    ("6711", "资产处置损失", "expense"),
    ("6801", "所得税费用", "expense"),
]


@pytest.fixture
def is_test_db():
    engine = sa_create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    acc = Account(id=1, name="IS测试", code="is_test", type="company",
                  taxpayer_type_l3="small_scale")
    db.add(acc)
    db.flush()
    ledger = Ledger(code=acc.code, name=acc.name, type=acc.type,
                    taxpayer_type_l3=acc.taxpayer_type_l3)
    db.add(ledger)
    db.flush()

    la = {}
    for ccode, cname, ctype in CHART:
        x = LedgerAccount(ledger_id=ledger.id, code=ccode, name=cname,
                          account_type=ctype, is_leaf=True, is_active=True)
        db.add(x)
        db.flush()
        db.add(LedgerAccountBalance(ledger_account_id=x.id, balance_l4=0))
        la[ccode] = x
    db.flush()

    # 收入：6001 贷方 1000
    m1 = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 6, 15).date(),
                     source_model="sale", source_id=1, name="SALE-001")
    db.add(m1)
    db.flush()
    db.add_all([
        AccountMoveLine(move_id=m1.id, ledger_account_id=la["1001"].id,
                        debit_l2=Decimal("1130"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=m1.id, ledger_account_id=la["6001"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("1000")),
    ])

    # 费用：6601 借方 200
    m2 = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 6, 20).date(),
                     source_model="expense", source_id=1, name="EXP-001")
    db.add(m2)
    db.flush()
    db.add_all([
        AccountMoveLine(move_id=m2.id, ledger_account_id=la["6601"].id,
                        debit_l2=Decimal("200"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=m2.id, ledger_account_id=la["1001"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("200")),
    ])

    # 期间结转（应被 pnl 排除）
    m3 = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 6, 30).date(),
                     source_model="period_close", source_id=0, name="CLOSE-06")
    db.add(m3)
    db.flush()
    db.add_all([
        AccountMoveLine(move_id=m3.id, ledger_account_id=la["6001"].id,
                        debit_l2=Decimal("1000"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=m3.id, ledger_account_id=la["4103"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("1000")),
    ])

    db.commit()
    return db, la, ledger


def test_old_is_vs_new_engine(is_test_db):
    """旧版 generate_income_statement 与新 ReportEngine 输出一致"""
    db, la, ledger = is_test_db

    start = "2025-01-01"
    end = "2025-06-30"

    from crud.finance.income_statement import generate_income_statement
    old = generate_income_statement(db, account_id=1, start_date=start, end_date=end)

    from reports.engine import ReportEngine
    from reports.definitions.income_statement import INCOME_STATEMENT

    end_dt = datetime(2025, 6, 30, 23, 59, 59)
    snapshot = LedgerSnapshot(db, account_id=1, bs_cutoff=end_dt,
                              period_start=datetime(2025, 1, 1),
                              period_end=end_dt)
    engine = ReportEngine()
    new = engine.execute(INCOME_STATEMENT, snapshot)

    assert float(new["revenue"]) == float(old["revenue"])
    assert float(new["cost_of_goods_sold"]) == float(old["cost_of_goods_sold"])
    assert float(new["net_profit"]) == float(old["net_profit"])
    assert float(new["gross_profit_total"]) == float(old["gross_profit_total"])


def test_trace_mode_returns_contributions(is_test_db):
    """trace=true 时返回 AML ids"""
    db, la, ledger = is_test_db

    end_dt = datetime(2025, 6, 30, 23, 59, 59)
    snapshot = LedgerSnapshot(db, account_id=1, bs_cutoff=end_dt,
                              period_start=datetime(2025, 1, 1),
                              period_end=end_dt)

    from reports.engine import ReportEngine
    from reports.definitions.income_statement import INCOME_STATEMENT

    engine = ReportEngine()
    result = engine.execute(INCOME_STATEMENT, snapshot, trace=True)

    assert "contributions" in result["revenue"]
    assert len(result["revenue"]["contributions"]) > 0
