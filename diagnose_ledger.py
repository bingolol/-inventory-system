"""检查 LedgerAccount 6001 的数量与 id"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))

import workspace
workspace.ensure_workspace()
from database import SessionLocal, set_maintenance_mode
set_maintenance_mode(True)

from models_finance import LedgerAccount, Ledger, AccountMoveLine

db = SessionLocal()
try:
    accounts_6001 = db.query(LedgerAccount).filter(LedgerAccount.code == "6001").all()
    print("6001 accounts count:", len(accounts_6001))
    for a in accounts_6001:
        ledger = db.query(Ledger).filter(Ledger.id == a.ledger_id).first()
        print(f"  id={a.id}, ledger_id={a.ledger_id}, ledger.code={ledger.code if ledger else None}, name={a.name}")
        lines = db.query(AccountMoveLine).filter(AccountMoveLine.ledger_account_id == a.id).all()
        print(f"    lines: {len(lines)}")
        for l in lines:
            print(f"      move_id={l.move_id}, debit={l.debit_l2}, credit={l.credit_l2}")
finally:
    db.close()
set_maintenance_mode(False)
