"""6个月全流程时间轴演示 — 用内存 SQLite"""
import sys, os, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
import models, models_finance  # ensure tables registered on Base

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
db = Session()

import models
from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
from finance_integration import get_or_create_ledger_id
from engine_tax import TaxAccrualEngine, _bal, _crd, _lp

tag = uuid.uuid4().hex[:6]
acc = models.Account(name="6M Flow", code=f"D6-{tag}", taxpayer_type="general")
db.add(acc); db.flush(); aid = acc.id
lid = get_or_create_ledger_id(db, aid)


def post(db, lid, date, drs, crs):
    m = AccountMove(ledger_id=lid, move_type="test", date=date, state="posted")
    db.add(m); db.flush()
    for c, a in drs.items():
        ac = db.query(LedgerAccount).filter(
            LedgerAccount.ledger_id == lid, LedgerAccount.code == c
        ).first()
        if ac and a:
            db.add(AccountMoveLine(move_id=m.id, ledger_account_id=ac.id,
                   debit=Decimal(str(a)), credit=0, amount_residual=Decimal(str(a))))
    for c, a in crs.items():
        ac = db.query(LedgerAccount).filter(
            LedgerAccount.ledger_id == lid, LedgerAccount.code == c
        ).first()
        if ac and a:
            db.add(AccountMoveLine(move_id=m.id, ledger_account_id=ac.id,
                   debit=0, credit=Decimal(str(a)), amount_residual=Decimal(str(a))))
    db.flush()


engine_tax = TaxAccrualEngine(db)

# ---- 期初 ----
post(db, lid, datetime(2024,12,31,23,59,59),
     {"1002": 1000}, {"3001": 1000})

ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()

# ---- 6个月 ----
months = [
    ("2025-01", 200, 26, 13, 100, 20),
    ("2025-02", 300, 39, 10, 150, 10),
    ("2025-03", 100, 13,  0,  50, 30),
    ("2025-04", 400, 52, 20, 200, 15),
    ("2025-05", 250, 33,  5, 120, 25),
    ("2025-06", 350, 46, 10, 180, 20),
]

print()
print("=" * 120)
print("  6个月全流程时间轴  |  一般纳税人  |  期初: 银行存款 1000 = 实收资本 1000")
print("=" * 120)

for i, (period, rev, ov, iv, cogs, exp) in enumerate(months):
    mid = datetime(int(period[:4]), int(period[5:7]), 15)

    # --- 操作记录 ---
    ops = []
    ops.append(f"  dr 1122 AR {rev+ov} / cr 6001 收入 {rev} + cr 222101 销项 {ov}")
    ops.append(f"  dr 222102 进项 {iv} + dr 6401 成本 {cogs} / cr 2202 AP {cogs+iv}")
    ops.append(f"  dr 6601 费用 {exp} / cr 2202 AP {exp}")

    print(f"\n--- {period} 业务录入 ---")
    for o in ops:
        print(o)

    for o in ops:
        # parse and post
        pass

    # Actually post
    post(db, lid, mid, {"1122": rev+ov}, {"6001": rev, "222101": ov})
    post(db, lid, mid, {"222102": iv, "6401": cogs}, {"2202": cogs+iv})
    post(db, lid, mid, {"6601": exp}, {"2202": exp})

    # 月结
    ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
    ps = datetime(int(period[:4]), int(period[5:7]), 1)
    import calendar
    pe = datetime(int(period[:4]), int(period[5:7]),
                  calendar.monthrange(int(period[:4]), int(period[5:7]))[1], 23, 59, 59)

    _, per_out = _lp(db, ledger, "222101", ps, pe)
    per_in, _ = _lp(db, ledger, "222102", ps, pe)
    pe_prev = ps - timedelta(seconds=1)
    prev_in = _bal(db, ledger, "222102", pe_prev)
    curr_vat = max(per_out - prev_in - per_in, Decimal("0"))

    r = engine_tax.execute(aid, period)

    print(f"\n  >> 月结 {period}")
    print(f"     当月销项: {per_out}  当月进项: {per_in}  期初留抵: {prev_in}")
    print(f"     => 应交增值税: {curr_vat}")

    for line in r.get("lines", []):
        print(f"     => {line}")

    # 快照：累计值
    cum_rev = _crd(db, ledger, "6001", pe)
    cum_cogs = _bal(db, ledger, "6401", pe)
    cum_exp = _bal(db, ledger, "6601", pe)
    cum_sur = _bal(db, ledger, "6403", pe)
    cum_it = _bal(db, ledger, "6801", pe)
    cum_profit = cum_rev - cum_cogs - cum_exp - cum_sur - cum_it

    print(f"     快照: 累收 {cum_rev}  累成本 {cum_cogs}  累费用 {cum_exp}")
    print(f"           累附加税 {cum_sur}  累所得税 {cum_it}  累利 {cum_profit}")
    print(f"           222101余额 {_crd(db, ledger, '222101', pe)}  222102余额 {_bal(db, ledger, '222102', pe)}")
    print(f"           222104余额 {_crd(db, ledger, '222104', pe)}  222105余额 {_crd(db, ledger, '222105', pe)}")

# 期末报表
from crud.finance import generate_balance_sheet, generate_income_statement

print(f"\n{'='*60}")
print(f"  期末资产负债表 (2025-06-30)")
print(f"{'='*60}")
bs = generate_balance_sheet(db, aid, "2025-06-30")
for k, v in bs.items():
    print(f"  {k}: {v}")

print(f"\n{'='*60}")
print(f"  利润表 (2025-01-01 ~ 2025-06-30)")
print(f"{'='*60}")
ist = generate_income_statement(db, aid, "2025-01-01", "2025-06-30")
for k, v in ist.items():
    print(f"  {k}: {v}")

db.close()
