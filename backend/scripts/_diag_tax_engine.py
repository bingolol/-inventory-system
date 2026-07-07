"""直接调 TaxAccrualEngine 看附加税计提流程"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from database import SessionLocal, set_maintenance_mode
from engine_tax import TaxAccrualEngine

set_maintenance_mode(True)
db = SessionLocal()

# 先看当前状态（已月结过）
for period in ["2025-12", "2026-02", "2026-03", "2026-04"]:
    print(f"\n=== {period} ===")
    try:
        result = TaxAccrualEngine(db).execute(1, period, "")
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

db.close()
set_maintenance_mode(False)
