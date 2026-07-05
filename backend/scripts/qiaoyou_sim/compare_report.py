"""对照分析报告：系统计算值 vs 预期值

用法: python -m scripts.qiaoyou_sim.compare_report
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from decimal import Decimal
from database import SessionLocal, set_maintenance_mode
import models
from models_finance import Ledger, AccountMove
from crud.finance._ledger_helpers import _lp, _crd
from engine_tax import _parse_period


ACCOUNT_ID = 1


# ── 预期值定义 ──

# 销项税预期：
# - 小规模纳税人（12-5月）：含税销售额 / 1.01 × 0.01（减按1%征收）
# - 一般纳税人（6月）：含税销售额 / 1.06 × 0.06
EXPECTED_OUTPUT_VAT = {
    "2025-12": Decimal("19.80"),    # 2000/1.01*0.01 = 19.80
    "2026-01": Decimal("0"),         # 无销售
    "2026-02": Decimal("59.41"),     # 6000/1.01*0.01 = 59.41 (59.40 实际精度)
    "2026-03": Decimal("11.88"),     # 1200/1.01*0.01 = 11.88
    "2026-04": Decimal("41.58"),     # 4200/1.01*0.01 = 41.58
    "2026-05": Decimal("0"),         # 无销售
    "2026-06": Decimal("1236.00"),   # 21836/1.06*0.06 = 1236.00
}

# 附加税预期：销项税 × 12% (城建税7% + 教育费附加3% + 地方教育附加2%)
# 小规模/小微减半 → × 6%
# 6月一般纳税人但仍是小型微利 → 减半 × 6%
EXPECTED_SURCHARGE = {
    "2025-12": Decimal("1.19"),      # 19.80 × 0.06 = 1.188 ≈ 1.19
    "2026-01": Decimal("0"),
    "2026-02": Decimal("3.56"),      # 59.41 × 0.06 = 3.56
    "2026-03": Decimal("0.71"),      # 11.88 × 0.06 = 0.713 ≈ 0.71 (系统0.72是精度)
    "2026-04": Decimal("2.49"),      # 41.58 × 0.06 = 2.49
    "2026-05": Decimal("0"),
    "2026-06": Decimal("74.16"),     # 1236 × 0.06 = 74.16
}

# 所得税预期（小型微利企业 5% 实际税负）
# 各月累计利润 × 5%
# 关键：
#   1. 4月采购2182.60是维修备件(track_inventory=True)，进1405库存，不影响利润
#   2. 固定资产折旧：购入当月及之前不计提，次月开始计提
#      - 主板套装(3/21购入)：4月起每月66.47
#      - 机箱(3/27购入)：4月起每月1.84
#      - 显示器(4/4购入)：5月起每月43.96
#      - 4月折旧 = 66.47 + 1.84 = 68.31
#      - 5月、6月折旧 = 66.47 + 1.84 + 43.96 = 112.27
#   3. 12月、1-3月无折旧（资产未购入或当月购入）
EXPECTED_INCOME_TAX_DELTA = {
    "2025-12": Decimal("24.37"),    # 累计利润 487.41 × 5% = 24.37
    "2026-01": Decimal("-24.37"),   # 1月亏损-1570，累计-1082.59 → 冲回24.37
    "2026-02": Decimal("147.53"),   # 累计利润 2950.59 × 5% = 147.53
    "2026-03": Decimal("-11.56"),   # 累计利润 2719.31 × 5% = 135.97，已147.53 → 冲回11.56
    "2026-04": Decimal("133.50"),   # 累计利润 5389.42 × 5% = 269.47，已135.97 → 补提133.50
    "2026-05": Decimal("-76.61"),   # 累计利润 3857.15 × 5% = 192.86，已269.47 → 冲回76.61
    "2026-06": Decimal("953.45"),   # 累计利润 22926.11 × 5% = 1146.31，已192.86 → 补提953.45
}


def get_system_values(db, account_id: int, period: str):
    """获取系统计算的三项税种值"""
    acc = db.query(models.Account).filter(models.Account.id == account_id).first()
    ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
    period_start, close_dt = _parse_period(period)

    # 销项税：小规模 222103 贷方，一般纳税人 222101 贷方
    # 6月是一般纳税人，其他月份小规模
    if period >= "2026-06":
        out_d, out_c = _lp(db, ledger, "222101", period_start, close_dt)
        output_vat = out_c - out_d
    else:
        _, output_vat = _lp(db, ledger, "222103", period_start, close_dt)

    # 附加税：640302+640303+640304 期间发生额
    surcharge = Decimal("0")
    for code in ["640302", "640303", "640304"]:
        d, c = _lp(db, ledger, code, period_start, close_dt)
        surcharge += d - c

    # 所得税 delta：222105 期间发生额（贷方计提 - 借方冲回）
    inc_d, inc_c = _lp(db, ledger, "222105", period_start, close_dt)
    income_tax_delta = inc_c - inc_d

    return output_vat, surcharge, income_tax_delta


def main():
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        periods = ["2025-12", "2026-01", "2026-02", "2026-03",
                   "2026-04", "2026-05", "2026-06"]

        print("\n" + "=" * 100)
        print("  对照分析报告：系统计算值 vs 预期值（巧游电子科技）")
        print("=" * 100)
        print(f"\n{'期间':<10}{'销项税(系统)':>14}{'销项税(预期)':>14}{'匹配':>8}"
              f"{'附加税(系统)':>14}{'附加税(预期)':>14}{'匹配':>8}"
              f"{'所得税(系统)':>14}{'所得税(预期)':>14}{'匹配':>8}")
        print("-" * 100)

        all_pass = True
        for period in periods:
            sys_vat, sys_sur, sys_inc = get_system_values(db, ACCOUNT_ID, period)
            exp_vat = EXPECTED_OUTPUT_VAT[period]
            exp_sur = EXPECTED_SURCHARGE[period]
            exp_inc = EXPECTED_INCOME_TAX_DELTA[period]

            vat_ok = abs(sys_vat - exp_vat) < Decimal("0.05")
            sur_ok = abs(sys_sur - exp_sur) < Decimal("0.05")
            inc_ok = abs(sys_inc - exp_inc) < Decimal("0.05")

            if not (vat_ok and sur_ok and inc_ok):
                all_pass = False

            print(f"{period:<10}"
                  f"{sys_vat:>14.2f}{exp_vat:>14.2f}{'✓' if vat_ok else '✗':>8}"
                  f"{sys_sur:>14.2f}{exp_sur:>14.2f}{'✓' if sur_ok else '✗':>8}"
                  f"{sys_inc:>14.2f}{exp_inc:>14.2f}{'✓' if inc_ok else '✗':>8}")

        print("-" * 100)
        print(f"\n{'全部通过 ✓' if all_pass else '存在差异 ✗'}")
        print("=" * 100)

    finally:
        db.close()
        set_maintenance_mode(False)


if __name__ == "__main__":
    main()
