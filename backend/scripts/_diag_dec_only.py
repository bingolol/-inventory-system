"""只跑阶段1+2，然后只月结 12月，看附加税"""
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

# 阶段2
from scripts.qiaoyou_sim.period_dec_2025 import step2_dec_2025
step2_dec_2025(db)
db.flush()
db.commit()

# 月结 12月
print("\n=== 月结 2025-12 ===")
try:
    with unit_of_work(db):
        result = dispatch(MonthEndClose(
            account_id=1,
            operator="sim",
            period="2025-12",
            force=False,
        ), db)
        print(f"  状态: {result.get('status')}")
        print(f"  明细: {'; '.join(result.get('lines', [])) or result.get('msg', '')}")
        print(f"  curr_vat: {result.get('curr_vat')}")
    db.commit()
    print("[12月] 月结成功")
except Exception as e:
    db.rollback()
    print(f"[12月] 月结失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# 验证 12月附加税凭证
from models_finance import Ledger, AccountMove
ledger = db.query(Ledger).filter(Ledger.code == "qiaoyou").first()
moves = db.query(AccountMove).filter(
    AccountMove.ledger_id == ledger.id,
    AccountMove.source_model.in_(["tax_surcharge", "tax_income"]),
    AccountMove.date_l1 >= "2025-12-01",
    AccountMove.date_l1 <= "2025-12-31",
).all()
print(f"\n12月税金凭证:")
for m in moves:
    print(f"  {m.date_l1} {m.source_model} amt={m.amount_total_l2}")

db.close()
set_maintenance_mode(False)
