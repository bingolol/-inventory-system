"""6个月全流程 — API 原生输出"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import json, calendar, uuid, tempfile, os as _os, atexit
from datetime import datetime, timedelta
from decimal import Decimal

# 文件 DB
_db_path = _os.path.join(tempfile.gettempdir(), f"api6m_{uuid.uuid4().hex}.db")
_db_url = f"sqlite:///{_db_path}"
atexit.register(lambda: _os.path.exists(_db_path) and _os.remove(_db_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db, _request_write_perm

import models, models_finance

engine = create_engine(_db_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
_request_write_perm.set(True)

def _override_get_db():
    db = TestSession()
    try: yield db
    finally: db.close()

from main import app
app.dependency_overrides[get_db] = _override_get_db
from fastapi.testclient import TestClient
client = TestClient(app)

# === 建账 ===
db = TestSession()
tag = uuid.uuid4().hex[:4]
acc = models.Account(name=f"API-{tag}", code=f"A6-{tag}", taxpayer_type_l3="general")
db.add(acc); db.flush(); aid = acc.id

from finance_integration import get_or_create_ledger_id
lid = get_or_create_ledger_id(db, aid)

# 期初: dr 银行 1000, cr 实收 1000
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
def _bal_move(db, lid, dt, drs, crs):
    m = AccountMove(ledger_id=lid, move_type="test", date_l1=dt, state="posted")
    db.add(m); db.flush()
    for c, a in drs.items():
        ac = db.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid, LedgerAccount.code==c).first()
        if ac and a: db.add(AccountMoveLine(move_id=m.id,ledger_account_id=ac.id,debit_l2=Decimal(str(a)),credit_l2=0,amount_residual_l2=Decimal(str(a))))
    for c, a in crs.items():
        ac = db.query(LedgerAccount).filter(LedgerAccount.ledger_id==lid, LedgerAccount.code==c).first()
        if ac and a: db.add(AccountMoveLine(move_id=m.id,ledger_account_id=ac.id,debit_l2=0,credit_l2=Decimal(str(a)),amount_residual_l2=Decimal(str(a))))
    db.flush()

_bal_move(db, lid, datetime(2024,12,31,23,59,59), {"1002": 1000}, {"3001": 1000})
db.commit(); db.close()

HEADERS = {"X-Account-ID": str(aid), "X-Operator": "user"}

from finance_integration import post_journal
from crud.finance import generate_balance_sheet, generate_income_statement

# === 6个月 ===
DATA = [
    ("2025-01", 200, 26, 13, 100, 20),
    ("2025-02", 300, 39, 10, 150, 10),
    ("2025-03", 100, 13,  0,  50, 30),
    ("2025-04", 400, 52, 20, 200, 15),
    ("2025-05", 250, 33,  5, 120, 25),
    ("2025-06", 350, 46, 10, 180, 20),
]

for period, rev, ov, iv, cogs, exp in DATA:
    db = TestSession()
    mid = datetime(int(period[:4]), int(period[5:7]), 15)
    # 销售: dr AR, cr 收入+销项
    post_journal(db, aid, "sale_order", {
        "partner_id":1,"partner_type":"customer",
        "total_with_tax":Decimal(str(rev+ov)),"total_without_tax":Decimal(str(rev)),
        "tax_amount":Decimal(str(ov)),"items":[{"product_id":1,"quantity":1,"unit_cost":0}],
        "date":mid,"source_model":"s","source_id":int(f"1{period.replace('-','')}")
    })
    # 采购: dr 进项+库存, cr 应付
    post_journal(db, aid, "purchase_order", {
        "partner_id":1,"partner_type":"supplier",
        "total_with_tax":Decimal(str(cogs+iv)),"total_without_tax":Decimal(str(cogs)),
        "tax_amount":Decimal(str(iv)),
        "date":mid,"source_model":"p","source_id":int(f"2{period.replace('-','')}"),
        "account_config":{"enable_vat_deduction":True}
    })
    # COGS 出库: dr 6401, cr 1405
    post_journal(db, aid, "expense", {
        "amount":Decimal(str(cogs)),"expense_account_code":"6401","credit_account_code":"1405",
        "date":mid,"source_model":"c","source_id":int(f"3{period.replace('-','')}")
    })
    # 费用
    post_journal(db, aid, "expense", {
        "amount":Decimal(str(exp)),"expense_account_code":"6601","credit_account_code":"2202",
        "date":mid,"source_model":"e","source_id":int(f"4{period.replace('-','')}")
    })
    db.commit(); db.close()

    # === 月结 API ===
    r = client.post("/api/finance/month-close", headers=HEADERS, json={"period": period})
    body = r.json()
    print(f"\n>>> POST /api/finance/month-close  period={period}  HTTP {r.status_code}")
    for k in ["curr_vat","cumulative_profit","target_income_tax","posted_income_tax","lines"]:
        print(f"    {k}: {body.get(k)}")

    # 快照
    db2 = TestSession()
    last_day = calendar.monthrange(int(period[:4]), int(period[5:7]))[1]
    bs = generate_balance_sheet(db2, aid, f"{period}-{last_day:02d}")
    ist = generate_income_statement(db2, aid, "2025-01-01", f"{period}-{last_day:02d}")
    print(f"    BS: 资产{bs['total_assets']} 负债{bs['total_liabilities']} 权益{bs['total_equity']} "
          f"税{bs['tax_payable']} 留抵{bs['prepayments']} 平衡={bs['balanced']} diff={bs['diff']}")
    print(f"    IS: 收{ist['revenue']} 成本{ist['cost_of_goods_sold']} "
          f"附加{ist['tax_surcharges']} 所得{ist['income_tax_expense']} 净利{ist['net_profit']}")
    db2.close()

# === 期末 ===
db = TestSession()
print(f"\n===== 期末 BS 2025-06-30 =====")
bs = generate_balance_sheet(db, aid, "2025-06-30")
for k, v in bs.items():
    if isinstance(v, str): print(f"  {k}: {v}")
    elif isinstance(v, (Decimal, int, float)) and abs(float(v)) > 0.001:
        print(f"  {k}: {v}")
    elif isinstance(v, bool):
        print(f"  {k}: {v}")

print(f"\n===== 期末 IS 2025-01-01~2025-06-30 =====")
ist = generate_income_statement(db, aid, "2025-01-01", "2025-06-30")
for k, v in ist.items():
    if isinstance(v, str): print(f"  {k}: {v}")
    else: print(f"  {k}: {v}")
db.close()
