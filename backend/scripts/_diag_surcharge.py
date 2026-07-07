"""诊断附加税计提问题"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from decimal import Decimal
from database import SessionLocal
import models
from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
from crud.finance._ledger_helpers import _lp, _bal, _crd
import sqlalchemy.sql.functions as sqlfunc

db = SessionLocal()
ACCOUNT_ID = 1
ledger = db.query(Ledger).filter(Ledger.code == "巧游电子科技").first()
if not ledger:
    # 找其他方式
    ledger = db.query(Ledger).first()
print(f"账本: id={ledger.id} code={ledger.code}")

for period in ["2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]:
    year, month = period.split("-")
    period_start = datetime(int(year), int(month), 1, 0, 0, 0)
    if month == "12":
        close_dt = datetime(int(year), int(month), 31, 23, 59, 59)
    elif month in ["01","03","05","07","08","10","12"]:
        close_dt = datetime(int(year), int(month), 31, 23, 59, 59)
    elif month in ["04","06","09","11"]:
        close_dt = datetime(int(year), int(month), 30, 23, 59, 59)
    else:
        # 2月
        close_dt = datetime(int(year), int(month), 28, 23, 59, 59)

    # 小规模: 222103
    d_103, c_103 = _lp(db, ledger, "222103", period_start, close_dt)
    curr_vat_small = c_103 - d_103
    # 一般纳税人: 222101
    d_101, c_101 = _lp(db, ledger, "222101", period_start, close_dt)
    curr_vat_general = c_101 - d_101

    print(f"\n=== {period} ===")
    print(f"  222103 期间: 借={d_103} 贷={c_103} → 小规模VAT={curr_vat_small}")
    print(f"  222101 期间: 借={d_101} 贷={c_101} → 一般VAT销项={curr_vat_general}")
    print(f"  curr_vat 判断: {'>0 会计提附加税' if (curr_vat_small > 0 or curr_vat_general > 0) else '0 不计提附加税'}")

db.close()
