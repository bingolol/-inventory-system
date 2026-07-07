"""验证 period_close 是否影响 222103"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from decimal import Decimal
from database import SessionLocal
from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
import sqlalchemy.sql.functions as sqlfunc

db = SessionLocal()
ledger = db.query(Ledger).filter(Ledger.code == "qiaoyou").first()

period = "2025-12"
period_start = datetime(2025, 12, 1, 0, 0, 0)
close_dt = datetime(2025, 12, 31, 23, 59, 59)

# 222103 期间借贷（所有 source_model）
q_d = db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit_l2),0)).join(
    LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
    LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "222103",
    AccountMove.date_l1 >= period_start, AccountMove.date_l1 <= close_dt,
)
q_c = db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit_l2),0)).join(
    LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
    LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "222103",
    AccountMove.date_l1 >= period_start, AccountMove.date_l1 <= close_dt,
)
d_all = Decimal(q_d.scalar())
c_all = Decimal(q_c.scalar())
print(f"222103 12月全部凭证: 借={d_all} 贷={c_all} 净={c_all - d_all}")

# 按 source_model 分组
from sqlalchemy import distinct
sms = db.query(AccountMove.source_model).filter(
    AccountMove.ledger_id == ledger.id,
    AccountMove.date_l1 >= period_start,
    AccountMove.date_l1 <= close_dt,
).distinct().all()
print(f"12月凭证 source_models: {[s[0] for s in sms]}")

# 222103 排除 period_close 后
q_d2 = q_d.filter(AccountMove.source_model != "period_close")
q_c2 = q_c.filter(AccountMove.source_model != "period_close")
d_ex = Decimal(q_d2.scalar())
c_ex = Decimal(q_c2.scalar())
print(f"222103 12月排除 period_close: 借={d_ex} 贷={c_ex} 净={c_ex - d_ex}")

db.close()
