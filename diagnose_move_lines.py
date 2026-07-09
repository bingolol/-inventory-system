"""查看刚才生成的 move 19 的分录"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))

import workspace
workspace.ensure_workspace()
from database import SessionLocal, set_maintenance_mode
set_maintenance_mode(True)

from models_finance import AccountMove, AccountMoveLine, LedgerAccount

db = SessionLocal()
try:
    move = db.query(AccountMove).order_by(AccountMove.id.desc()).first()
    print("latest move:", move.id, move.move_type, move.name, move.amount_total_l2)
    lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == move.id).all()
    print("lines count:", len(lines))
    for l in lines:
        la = db.query(LedgerAccount).filter(LedgerAccount.id == l.ledger_account_id).first()
        print(f"  account={la.code if la else l.ledger_account_id}, debit={l.debit_l2}, credit={l.credit_l2}")
finally:
    db.close()
set_maintenance_mode(False)
