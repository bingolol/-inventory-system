"""检查 Account 与 Ledger 的对应关系"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))

import workspace
workspace.ensure_workspace()
from database import SessionLocal, set_maintenance_mode
set_maintenance_mode(True)

from models import Account
from models_finance import Ledger, AccountMove

db = SessionLocal()
try:
    accounts = db.query(Account).all()
    print("accounts:")
    for a in accounts:
        print(f"  id={a.id}, code={a.code}, name={a.name}, taxpayer={a.taxpayer_type_l3}")
    ledgers = db.query(Ledger).all()
    print("ledgers:")
    for l in ledgers:
        print(f"  id={l.id}, code={l.code}, name={l.name}, taxpayer={l.taxpayer_type_l3}")
    moves = db.query(AccountMove).order_by(AccountMove.id.desc()).limit(5).all()
    print("latest moves:")
    for m in moves:
        print(f"  id={m.id}, ledger_id={m.ledger_id}, type={m.move_type}, date={m.date_l1}")
finally:
    db.close()
set_maintenance_mode(False)
