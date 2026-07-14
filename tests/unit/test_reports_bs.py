"""P4: BS 定义对比测试 — 核心验证：BS 自身平衡 + trace 可用"""
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
    ("1002", "银行存款", "asset"),
    ("1122", "应收账款", "asset"),
    ("1123", "预付账款", "asset"),
    ("1405", "库存商品", "asset"),
    ("1601", "固定资产", "asset"),
    ("1602", "累计折旧", "liability"),
    ("1701", "无形资产", "asset"),
    ("1702", "累计摊销", "liability"),
    ("1901", "其他流动资产", "asset"),
    ("2202", "应付账款", "liability"),
    ("2211", "应付职工薪酬", "liability"),
    ("222101", "应交增值税-销项", "liability"),
    ("222102", "应交增值税-进项", "liability"),
    ("222103", "应交增值税-小规模", "liability"),
    ("222105", "应交所得税", "liability"),
    ("222107", "应交增值税-未交", "liability"),
    ("222108", "应交个人所得税", "liability"),
    ("2241", "其他应付款", "liability"),
    ("2501", "长期借款", "liability"),
    ("3001", "实收资本", "equity"),
    ("4103", "本年利润", "equity"),
    ("4104", "利润分配", "equity"),
    ("6001", "主营业务收入", "income"),
    ("6401", "主营业务成本", "expense"),
    ("6601", "管理费用", "expense"),
    ("6602", "销售费用", "expense"),
    ("6603", "财务费用", "expense"),
    ("6801", "所得税费用", "expense"),
]


@pytest.fixture
def bs_test_db():
    engine = sa_create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    acc = Account(id=1, name="BS测试", code="bs_test", type="company",
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

    # 实收资本 100000 → 银行存款
    mv = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 1, 10).date(),
                     source_model="opening", source_id=0, name="INIT-001")
    db.add(mv)
    db.flush()
    db.add_all([
        AccountMoveLine(move_id=mv.id, ledger_account_id=la["1002"].id,
                        debit_l2=Decimal("100000"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=mv.id, ledger_account_id=la["3001"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("100000")),
    ])

    # 销售：应收 11300，收入 10000，增值税 1300
    m1 = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 3, 15).date(),
                     source_model="sale", source_id=1, name="SALE-001")
    db.add(m1)
    db.flush()
    db.add_all([
        AccountMoveLine(move_id=m1.id, ledger_account_id=la["1122"].id,
                        debit_l2=Decimal("11300"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=m1.id, ledger_account_id=la["6001"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("10000")),
        AccountMoveLine(move_id=m1.id, ledger_account_id=la["222103"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("1300")),
    ])

    # 月末：收入结转至本年利润
    m2 = AccountMove(ledger_id=ledger.id, move_type="entry",
                     date_l1=datetime(2025, 3, 31).date(),
                     source_model="period_close", source_id=0, name="CLOSE-03")
    db.add(m2)
    db.flush()
    db.add_all([
        AccountMoveLine(move_id=m2.id, ledger_account_id=la["6001"].id,
                        debit_l2=Decimal("10000"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=m2.id, ledger_account_id=la["4103"].id,
                        debit_l2=Decimal("0"), credit_l2=Decimal("10000")),
    ])

    db.commit()
    return db, la, ledger


def test_bs_self_balanced(bs_test_db):
    """引擎生成的 BS 自身平衡：total_assets == total_liabilities + total_equity"""
    db, la, ledger = bs_test_db

    from reports.engine import ReportEngine
    from reports.definitions.balance_sheet import BALANCE_SHEET

    cutoff = datetime(2025, 6, 30, 23, 59, 59)
    snapshot = LedgerSnapshot(db, account_id=1, bs_cutoff=cutoff)
    engine = ReportEngine()
    new = engine.execute(BALANCE_SHEET, snapshot, source_mode="ledger")

    ta = float(new["total_assets"])
    tl = float(new["total_liabilities"])
    te = float(new["total_equity"])
    diff = abs(ta - (tl + te))
    assert diff < 0.02, f"不平衡: assets={ta}, liab={tl}, equity={te}, diff={diff}"

    # 核心字段正数校验
    assert new["monetary_funds"] >= 0
    assert new["accounts_receivable"] >= 0
    assert new["paid_in_capital"] >= 0
    assert new["vat_payable_l1"] >= 0
    assert float(new["tax_payable"]) > 0


def test_bs_trace_returns_contributions(bs_test_db):
    """BS trace 模式返回 contributions"""
    db, la, ledger = bs_test_db

    cutoff = datetime(2025, 6, 30, 23, 59, 59)
    snapshot = LedgerSnapshot(db, account_id=1, bs_cutoff=cutoff)

    from reports.engine import ReportEngine
    from reports.definitions.balance_sheet import BALANCE_SHEET

    engine = ReportEngine()
    result = engine.execute(BALANCE_SHEET, snapshot, trace=True)

    assert isinstance(result["accounts_receivable"], dict)
    assert "value" in result["accounts_receivable"]
    assert "contributions" in result["accounts_receivable"]
    assert len(result["accounts_receivable"]["contributions"]) > 0
