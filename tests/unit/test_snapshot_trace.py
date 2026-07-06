"""LedgerSnapshot trace_* 方法单元测试 — P1 tracer bullet"""
import pytest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Account
from models_finance import Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine
from crud.finance._snapshot import LedgerSnapshot

CHART_OF_ACCOUNTS = [
    ("1001", "库存现金", "asset"),
    ("1002", "银行存款", "asset"),
    ("1122", "应收账款", "asset"),
    ("1405", "库存商品", "asset"),
    ("1601", "固定资产", "asset"),
    ("1602", "累计折旧", "liability"),
    ("1701", "无形资产", "asset"),
    ("2202", "应付账款", "liability"),
    ("222101", "应交增值税-销项", "liability"),
    ("222103", "应交增值税-小规模", "liability"),
    ("222107", "应交增值税-未交", "liability"),
    ("2241", "其他应付款", "liability"),
    ("3001", "实收资本", "equity"),
    ("4103", "本年利润", "equity"),
    ("4104", "利润分配", "equity"),
    ("6001", "主营业务收入", "income"),
    ("6051", "其他业务收入", "income"),
    ("6401", "主营业务成本", "expense"),
    ("6403", "税金及附加", "expense"),
    ("640302", "税金及附加-城建税", "expense"),
    ("6601", "管理费用", "expense"),
    ("6602", "销售费用", "expense"),
    ("6603", "财务费用", "expense"),
    ("6701", "营业外支出", "expense"),
    ("6801", "所得税费用", "expense"),
]


@pytest.fixture
def fresh_db():
    """函数级隔离内存 DB（不与 conftest 的 db 冲突）"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def seeded_db(fresh_db):
    """播种：1个账本 + 全部科目 + 4条分录（跨两个凭证）"""
    db = fresh_db
    acc = Account(id=1, name="trace测试", code="trace_test", type="company",
                  taxpayer_type_l3="small_scale")
    db.add(acc)
    db.flush()

    ledger = Ledger(code=acc.code, name=acc.name, type=acc.type,
                    taxpayer_type_l3=acc.taxpayer_type_l3)
    db.add(ledger)
    db.flush()

    la_map = {}
    for ccode, cname, ctype in CHART_OF_ACCOUNTS:
        la = LedgerAccount(ledger_id=ledger.id, code=ccode, name=cname,
                           account_type=ctype, is_leaf=True, is_active=True)
        db.add(la)
        db.flush()
        db.add(LedgerAccountBalance(ledger_account_id=la.id, balance_l4=0))
        la_map[ccode] = la
    db.flush()

    move1 = AccountMove(ledger_id=ledger.id, move_type="entry",
                        date_l1=datetime(2025, 3, 15).date(),
                        source_model="sale", source_id=1, name="SALE-2025-0001")
    db.add(move1)
    db.flush()
    move2 = AccountMove(ledger_id=ledger.id, move_type="entry",
                        date_l1=datetime(2025, 4, 10).date(),
                        source_model="sale", source_id=2, name="SALE-2025-0002")
    db.add(move2)
    db.flush()

    aml1 = AccountMoveLine(move_id=move1.id, ledger_account_id=la_map["1001"].id,
                           debit_l2=Decimal("1000"), credit_l2=Decimal("0"))
    aml2 = AccountMoveLine(move_id=move1.id, ledger_account_id=la_map["6001"].id,
                           debit_l2=Decimal("0"), credit_l2=Decimal("1000"))
    aml3 = AccountMoveLine(move_id=move2.id, ledger_account_id=la_map["1001"].id,
                           debit_l2=Decimal("500"), credit_l2=Decimal("0"))
    aml4 = AccountMoveLine(move_id=move2.id, ledger_account_id=la_map["6001"].id,
                           debit_l2=Decimal("0"), credit_l2=Decimal("500"))
    db.add_all([aml1, aml2, aml3, aml4])
    db.flush()

    return db, [aml1, aml2, aml3, aml4], [move1, move2], ledger, la_map


def test_trace_cum_dc_matches_cum_dc(seeded_db):
    db, amls, moves, ledger, la_map = seeded_db
    cutoff = datetime(2025, 12, 31)
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=cutoff)

    d1, c1 = sn.cum_dc("1001")
    d2, c2, ids = sn.trace_cum_dc("1001")
    assert d1 == d2
    assert c1 == c2
    assert len(ids) == 2, f"1001 应有 2 条，实际 {len(ids)}"
    assert amls[0].id in ids
    assert amls[2].id in ids

    d1, c1 = sn.cum_dc("6001")
    d2, c2, ids = sn.trace_cum_dc("6001")
    assert d1 == d2
    assert c1 == c2
    assert len(ids) == 2


def test_trace_bal_matches_bal(seeded_db):
    db, amls, moves, ledger, la_map = seeded_db
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=datetime(2025, 12, 31))

    bal1 = sn.bal("1001")
    bal2, ids = sn.trace_bal("1001")
    assert bal1 == bal2

    meta = sn.get_move_meta(set(ids))
    assert len(meta) == 2
    assert meta[amls[0].id]["move_name"] == "SALE-2025-0001"
    assert meta[amls[0].id]["source_model"] == "sale"
    assert meta[amls[0].id]["source_id"] == 1
    assert meta[amls[0].id]["move_id"] == moves[0].id

    crd1 = sn.crd("6001")
    crd2, ids = sn.trace_crd("6001")
    assert crd1 == crd2


def test_trace_per_dc_filters_by_date(seeded_db):
    db, amls, moves, ledger, la_map = seeded_db
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=datetime(2025, 6, 30))

    start = datetime(2025, 1, 1)
    end = datetime(2025, 3, 31, 23, 59, 59)

    d1, c1 = sn.per_dc("1001", start, end)
    d2, c2, ids = sn.trace_per_dc("1001", start, end)
    assert d1 == d2
    assert c1 == c2
    assert len(ids) == 1, f"3月期间应只有1笔(AML1={amls[0].id}), 实际 {len(ids)}: {ids}"
    assert amls[0].id in ids
    assert amls[2].id not in ids


def test_trace_pnl_dc_excludes_period_close(seeded_db):
    db, amls, moves, ledger, la_map = seeded_db

    move_close = AccountMove(ledger_id=ledger.id, move_type="entry",
                             date_l1=datetime(2025, 3, 31).date(),
                             source_model="period_close", source_id=0,
                             name="CLOSE-2025-03")
    db.add(move_close)
    db.flush()
    aml_close = AccountMoveLine(move_id=move_close.id,
                                ledger_account_id=la_map["1001"].id,
                                debit_l2=Decimal("999"), credit_l2=Decimal("0"))
    db.add(aml_close)
    db.commit()

    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=datetime(2025, 6, 30))
    start = datetime(2025, 1, 1)
    end = datetime(2025, 4, 30, 23, 59, 59)

    d1, c1 = sn.pnl_dc("1001", start, end)
    d2, c2, ids = sn.trace_pnl_dc("1001", start, end)
    assert d1 == d2
    assert c1 == c2
    assert aml_close.id not in ids


def test_get_move_meta_correct(seeded_db):
    db, amls, moves, ledger, la_map = seeded_db
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=datetime(2025, 12, 31))

    meta = sn.get_move_meta({amls[0].id, amls[2].id})
    assert len(meta) == 2
    assert meta[amls[0].id]["source_id"] == 1
    assert meta[amls[0].id]["move_name"] == "SALE-2025-0001"
    assert meta[amls[2].id]["source_id"] == 2
    assert meta[amls[2].id]["move_name"] == "SALE-2025-0002"


def test_regression_bs_is_still_generated(seeded_db):
    """P1 改动后 BS/IS 输出结构不变"""
    db, amls, moves, ledger, la_map = seeded_db
    db.commit()

    from crud.finance.balance_sheet import generate_balance_sheet
    bs = generate_balance_sheet(db, account_id=1, date="2025-06-30")
    assert "balanced" in bs
    assert "total_assets" in bs

    from crud.finance.income_statement import generate_income_statement
    is_data = generate_income_statement(db, account_id=1,
                                        start_date="2025-01-01", end_date="2025-06-30")
    assert "revenue" in is_data
    assert "net_profit" in is_data
