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

# 附加税预期：附加税随增值税申报，小规模按季度，一般纳税人按月
# 计税基数 = 销项税 × 城建税7% × 减半50% = 销项税 × 3.5%
# 教育费附加、地方教育附加：季度销售额≤30万免征（财税〔2016〕12号），巧游各季度均免征
#
# 小规模期间（2025-12 ~ 2026-05）按季度申报：
#   2025-Q4: 19.80 × 0.035 = 0.69（凭证 2025-12-31）
#   2026-Q1: (59.40+11.88) × 0.035 = 2.50（凭证 2026-03-31）
#   2026-Q2: 41.58 × 0.035 = 1.46（凭证 2026-06-30，结清小规模期间）
# 一般纳税人期间（2026-06起）按月申报：
#   2026-06: 1236 × 0.035 = 43.26（凭证 2026-06-30）
# 6月合计 = Q2结清 1.46 + 一般纳税人月 43.26 = 44.72
EXPECTED_SURCHARGE = {
    "2025-12": Decimal("0.69"),      # Q4 末月（季末申报）
    "2026-01": Decimal("0"),         # 非季末月，不申报
    "2026-02": Decimal("0"),         # 非季末月，不申报
    "2026-03": Decimal("2.50"),      # Q1 末月（季末申报）
    "2026-04": Decimal("0"),         # 非季末月，不申报
    "2026-05": Decimal("0"),         # 非季末月，不申报
    "2026-06": Decimal("44.72"),     # Q2结清(1.46) + 一般纳税人月申报(43.26)
}

# 所得税预期（小型微利企业 5% 实际税负 = 25% 法定税率 × 20% 小微优惠）
# delta = 当月应交所得税 - 上月已计提（222105 累计贷方-借方）
#
# 累计利润口径（IncomeTaxEngine.compute_cumulative_profit）：
#   从 11 个损益科目原值汇总（year_start → close_dt），排除 period_close/year_close 结转分录：
#     收入类(贷-借): 6001 主营 + 6051 其他
#     成本类(借-贷): 6401 主营成本
#     费用类(借-贷): 6601 管理 + 6602 销售 + 6603 财务 + 6403 税金及附加
#     营业外收入(贷-借): 6301 + 6111
#     营业外支出(借-贷): 6701 + 6711
#
# 关键口径差异（与读 4103 余额不同）：
#   1. 4103 "本年利润" 是 period_close 后的结转结果，被 6801 所得税费用借方抵减，
#      所以 4103 余额 < 真实累计利润。IncomeTaxEngine 从损益科目原值汇总，避免污染。
#   2. vat_exemption 凭证（小规模季度末结转）写 dr 222103 / cr 6301，
#      6301 贷方进入营业外收入 → 计入累计利润税基（财税〔2008〕151号财政性资金）。
#   3. 6403 主科目余额为 0（附加税写在 640302/303/304 明细），
#      IncomeTaxEngine 用 SUBACCOUNT_FALLBACK 读明细合计。
#   4. 6801 所得税费用不在 EXPENSE_CODES 中，避免"利润→所得税→利润"循环。
#
# 2025-12 单独年结（4103→4104），2026 年累计利润从 1/1 起独立计算。
# 2026-01 累计亏损 → target=0，delta=0（不冲回 2025 年已计提）。
EXPECTED_INCOME_TAX_DELTA = {
    "2025-12": Decimal("25.33"),    # 2025年累计利润 506.52 × 5% = 25.326 → 25.33
    "2026-01": Decimal("0.00"),     # 2026年累计 -1570.00（亏损）→ target=0，delta=0
    "2026-02": Decimal("147.53"),   # 2026年累计 2950.60 × 5% = 147.530 → 147.53
    "2026-03": Decimal("-8.12"),    # 2026年累计 2788.11 × 5% = 139.406 → 139.41，已147.53 → 冲回8.12
    "2026-04": Decimal("133.50"),   # 2026年累计 5458.22 × 5% = 272.911 → 272.91，已139.41 → 补提133.50
    "2026-05": Decimal("-76.61"),   # 2026年累计 3925.95 × 5% = 196.298 → 196.30，已272.91 → 冲回76.61
    "2026-06": Decimal("951.21"),   # 2026年累计 22950.19 × 5% = 1147.510 → 1147.51，已196.30 → 补提951.21
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
