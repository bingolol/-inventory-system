"""4.1: DualSource both 模式测试"""
import pytest
from datetime import datetime
from decimal import Decimal

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Account
from models_finance import Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine
from crud.finance._snapshot import LedgerSnapshot
from reports.engine import ReportEngine
from reports.dsl import (
    Field, Part,
    LEDGER_COMPOSITE, SUM_FIELDS,
    DualSource, INVOICE_TAX_NET, PositivePart,
)

CHART = [
    ("1001", "库存现金", "asset"),
    ("222103", "应交增值税-小规模", "liability"),
    ("222101", "应交增值税-销项", "liability"),
    ("222102", "应交增值税-进项", "liability"),
    ("222107", "应交增值税-未交", "liability"),
    ("222106", "应交增值税-转出未交", "liability"),
    ("3001", "实收资本", "equity"),
]


@pytest.fixture
def both_db():
    engine = sa_create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    acc = Account(id=1, name="both", code="both", type="company", taxpayer_type_l3="small_scale")
    db.add(acc); db.flush()
    ledger = Ledger(code=acc.code, name=acc.name, type=acc.type, taxpayer_type_l3=acc.taxpayer_type_l3)
    db.add(ledger); db.flush()
    la = {}
    for ccode, cname, ctype in CHART:
        x = LedgerAccount(ledger_id=ledger.id, code=ccode, name=cname, account_type=ctype, is_leaf=True, is_active=True)
        db.add(x); db.flush()
        db.add(LedgerAccountBalance(ledger_account_id=x.id, balance_l4=0))
        la[ccode] = x
    db.flush()
    # 总账：222103 贷方 1300（增值税）
    m = AccountMove(ledger_id=ledger.id, move_type="entry", date_l1=datetime(2025, 6, 15).date(),
                    source_model="sale", source_id=1, name="SALE-001")
    db.add(m); db.flush()
    db.add_all([
        AccountMoveLine(move_id=m.id, ledger_account_id=la["1001"].id, debit_l2=Decimal("11300"), credit_l2=Decimal("0")),
        AccountMoveLine(move_id=m.id, ledger_account_id=la["222103"].id, debit_l2=Decimal("0"), credit_l2=Decimal("1300")),
        AccountMoveLine(move_id=m.id, ledger_account_id=la["3001"].id, debit_l2=Decimal("0"), credit_l2=Decimal("0")),
    ])
    db.commit()
    return db, la


def test_dual_source_both_mode(both_db):
    """source=both 时返回 primary 值 + verification（总账对账）"""
    db, la = both_db

    fields = [
        Field("_vat_net", None,
            source=DualSource(
                primary=INVOICE_TAX_NET(),
                secondary=LEDGER_COMPOSITE(parts=[
                    Part(codes=["222101", "222103", "222107"], side="credit", sign=+1),
                    Part(codes=["222102", "222106"], side="debit", sign=-1),
                ]),
            ),
        ),
        Field("vat_payable_l1", "应交增值税",
            source=SUM_FIELDS(["_vat_net"]),
            transform=PositivePart(),
        ),
    ]

    cutoff = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=cutoff)
    engine = ReportEngine()

    result = engine.execute(fields, sn, source_mode="both")

    # primary = 发票口径（无发票数据=0）
    # secondary = 总账口径（222103 credit=1300）
    assert "_vat_net" in result
    assert "verification" in result["_vat_net"]
    # primary 值随源模式
    if result["_vat_net"]["value"] == 0:
        assert result["_vat_net"]["verification"]["ledger_value"] == 1300
    assert abs(result["_vat_net"]["verification"]["diff"]) > 0  # 发票口径≠总账口径（无发票数据时）


def test_dual_source_ledger_mode(both_db):
    """source=ledger 时走总账口径"""
    db, la = both_db

    fields = [
        Field("_vat_net", None,
            source=DualSource(
                primary=INVOICE_TAX_NET(),
                secondary=LEDGER_COMPOSITE(parts=[
                    Part(codes=["222101", "222103", "222107"], side="credit", sign=+1),
                    Part(codes=["222102", "222106"], side="debit", sign=-1),
                ]),
            ),
        ),
        Field("vat_payable_l1", "应交增值税",
            source=SUM_FIELDS(["_vat_net"]),
            transform=PositivePart(),
        ),
    ]

    cutoff = datetime(2025, 6, 30, 23, 59, 59)
    sn = LedgerSnapshot(db, account_id=1, bs_cutoff=cutoff)
    engine = ReportEngine()
    result = engine.execute(fields, sn, source_mode="ledger")

    # 总账口径：222103 credit=1300 → vat_payable_l1 = 1300
    assert abs(float(result["vat_payable_l1"]) - 1300) < 0.02
