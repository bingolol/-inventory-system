"""对照实验：12月+1月业务，然后月结12月、1月"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from database import SessionLocal, set_maintenance_mode
from uow import unit_of_work
from commands.base import dispatch
from commands.month_end import MonthEndClose

set_maintenance_mode(True)
db = SessionLocal()

# 阶段1
from scripts.qiaoyou_sim.setup_data import step1_setup
step1_setup(db)
db.flush()

# 阶段2 (12月)
from scripts.qiaoyou_sim.period_dec_2025 import step2_dec_2025
step2_dec_2025(db)
db.flush()

# 阶段3部分 (1月部分)
from datetime import datetime
from scripts.qiaoyou_sim.helpers import create_bank_fee_outflow, create_expense
create_bank_fee_outflow(db, 150.00, datetime(2026, 1, 24), "2026年账户年费")
from datetime import date
create_expense(db, "房租", 1300.00, date(2026, 1, 31), "2026年1月房租")
create_expense(db, "水电", 120.00, date(2026, 1, 31), "2026年1月水电")
db.flush()
db.commit()

# 月结 12月
print("\n=== 月结 2025-12 ===")
try:
    with unit_of_work(db):
        result = dispatch(MonthEndClose(account_id=1, operator="sim", period="2025-12", force=False), db)
        print(f"  状态: {result.get('status')}")
        print(f"  明细: {'; '.join(result.get('lines', []))}")
        print(f"  curr_vat: {result.get('curr_vat')}")
    db.commit()
except Exception as e:
    db.rollback()
    print(f"  失败: {type(e).__name__}: {e}")

# 验证12月附加税
from models_finance import Ledger, AccountMove
ledger = db.query(Ledger).filter(Ledger.code == "qiaoyou").first()
moves = db.query(AccountMove).filter(
    AccountMove.ledger_id == ledger.id,
    AccountMove.source_model == "tax_surcharge",
).all()
print(f"\n12月月结后 tax_surcharge 凭证数: {len(moves)}")
for m in moves:
    print(f"  {m.date_l1} amt={m.amount_total_l2} is_reversal={m.is_reversal}")

db.close()
set_maintenance_mode(False)
