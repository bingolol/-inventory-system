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
from crud.finance._ledger_helpers import _lp, _crd, business_lp, pnl_lp
from utils.period import parse_period


ACCOUNT_ID = 1


# ── 预期值定义 ──

# 销项税预期：
# - 小规模纳税人（12-5月）：含税销售额 / 1.01 × 0.01（减按1%征收）
# - 一般纳税人（6月）：含税销售额 / 1.06 × 0.06
EXPECTED_OUTPUT_VAT = {
    "2025-12": Decimal("19.80"),    # 2000/1.01*0.01 = 19.80
    "2026-01": Decimal("0"),         # 无销售
    "2026-02": Decimal("59.40"),     # 按行 split: 49.50 + 9.90 = 59.40（每张发票独立价税分离，不是按总额算）
    "2026-03": Decimal("11.88"),     # 1200/1.01*0.01 = 11.88
    "2026-04": Decimal("41.58"),     # 4200/1.01*0.01 = 41.58
    "2026-05": Decimal("0"),         # 无销售
    "2026-06": Decimal("1236.00"),   # 21836/1.06*0.06 = 1236.00
}

# 附加税预期：销项税 × 12% (城建税7% + 教育费附加3% + 地方教育附加2%)
# 小规模/小微减半 → × 6%
# 教育费附加、地方教育附加：季度销售额≤30万免征（财税〔2016〕12号）
# 巧游所有季度销售额都≤30万，因此只有城建税（7%×50%=3.5%）
EXPECTED_SURCHARGE = {
    "2025-12": Decimal("0.69"),      # 19.80 × 0.035 = 0.693 ≈ 0.69（仅城建税）
    "2026-01": Decimal("0"),
    "2026-02": Decimal("2.08"),      # 59.40 × 0.035 = 2.079 ≈ 2.08（仅城建税）
    "2026-03": Decimal("0.42"),      # 11.88 × 0.035 = 0.4158 ≈ 0.42（仅城建税）
    "2026-04": Decimal("1.46"),      # 41.58 × 0.035 = 1.4553 ≈ 1.46（仅城建税）
    "2026-05": Decimal("0"),
    "2026-06": Decimal("43.26"),     # 1236 × 0.035 = 43.26（仅城建税）
}

# 所得税预期（小型微利企业 5% 实际税负）
# 各月累计利润 × 5%，delta = 当期应交 - 已计提
# 累计利润口径与利润表一致（收入 - 成本 - 费用 - 附加税 + 营业外收支）
# 关键：
#   1. 4月采购2182.60是维修备件(track_inventory=True)，进1405库存，不影响利润
#   2. 固定资产折旧：购入当月及之前不计提，次月开始计提
#      - 主板套装(3/21购入)：4月起每月66.47
#      - 机箱(3/27购入)：4月起每月1.84
#      - 显示器(4/4购入)：5月起每月43.96
#      - 4月折旧 = 66.47 + 1.84 = 68.31
#      - 5月、6月折旧 = 66.47 + 1.84 + 43.96 = 112.27
#   3. 12月、1-3月无折旧（资产未购入或当月购入）
#   4. 银行手续费进 6603 借方（财务费用），银行利息进 6603 贷方（冲减财务费用）。
#      会计准则要求利息收入贷记 6603 财务费用，不进 6301 营业外收入。
#      手续费：12月72.80(50+22.80) + 1月150.00 = 222.80（6603借方）
#      利息：12月0.01 + 3月0.60 + 6月1.23 = 1.84（6603贷方）
#   5. engine_tax.py 费用科目取净额（借方-贷方），与利润表口径一致。
#   6. 附加税计入 640302/303/304 明细科目，6403 主科目余额为 0。
#      engine_tax 读 6403 时主科目为 0 回退到明细合计（与 income_statement.py 口径一致）。
#      修复前只读主科目，漏扣附加税 → 累计利润虚高 → 所得税多计提。
#   7. 2025年12月单独年结（4103→4104），2026年累计利润从1月开始独立计算。
#      所得税计提按"本年累计"口径：2025-12 的 24.34 是 2025 年度的，不在 2026 年冲回。
#      2026-01 累计利润为负（亏损）→ target=0，本年已计提=0 → delta=0（不冲回上年）。
#   8. 附加税修复后（教育费附加/地方教育附加季度≤30万免征，财税〔2016〕12号），
#      附加税只计提城建税（7%×50%=3.5%），累计利润相应增加。
EXPECTED_INCOME_TAX_DELTA = {
    "2025-12": Decimal("24.34"),    # 2025年累计利润 486.72 × 5% = 24.336 → 24.34
    "2026-01": Decimal("0.00"),     # 2026年累计 -1570.00（亏损）→ target=0，本年已计提=0 → delta=0
    "2026-02": Decimal("147.43"),   # 2026年累计 2948.52 × 5% = 147.426 → 147.43
    "2026-03": Decimal("-11.59"),   # 2026年累计 2716.82 × 5% = 135.841 → 135.84，已147.43 → 冲回11.59
    "2026-04": Decimal("133.43"),   # 2026年累计 5385.47 × 5% = 269.2735 → 269.27，已135.84 → 补提133.43
    "2026-05": Decimal("-76.61"),   # 2026年累计 3853.20 × 5% = 192.660 → 192.66，已269.27 → 冲回76.61
    "2026-06": Decimal("951.28"),   # 2026年累计 22878.90 × 5% = 1143.945 → 1143.94，已192.66 → 补提951.28
}


def get_system_values(db, account_id: int, period: str):
    """获取系统计算的三项税种值"""
    acc = db.query(models.Account).filter(models.Account.id == account_id).first()
    ledger = db.query(Ledger).filter(Ledger.code == acc.code).first()
    period_start, close_dt = parse_period(period)

    # 销项税：小规模 222103 贷方，一般纳税人 222101 贷方
    # 6月是一般纳税人，其他月份小规模
    # 用 business_lp 排除所有内部结转（vat_transfer_out 等），避免污染
    if period >= "2026-06":
        out_d, out_c = business_lp(db, ledger, "222101", period_start, close_dt)
        output_vat = out_c - out_d
    else:
        _, output_vat = business_lp(db, ledger, "222103", period_start, close_dt)

    # 附加税：640302+640303+640304 期间发生额
    # 用 pnl_lp 排除 period_close（损益结转分录会写入这些科目的贷方，与计提的借方抵消）
    # period_close 后 640302/303/304 余额归零，但 _lp 取的是期间发生额会被抵消
    surcharge = Decimal("0")
    for code in ["640302", "640303", "640304"]:
        d, c = pnl_lp(db, ledger, code, period_start, close_dt)
        surcharge += d - c

    # 所得税 delta：222105 期间发生额（贷方计提 - 借方冲回）
    # 用 pnl_lp 排除 period_close/year_close，但保留 tax_income/tax_income_reversal
    # （所得税计提通过 source_model=tax_income 写入 222105 贷方）
    inc_d, inc_c = pnl_lp(db, ledger, "222105", period_start, close_dt)
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
