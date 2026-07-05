"""输出三大财务报表：资产负债表、利润表、现金流量表

用法: python -m scripts.qiaoyou_sim.three_statements
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from decimal import Decimal
from database import SessionLocal, set_maintenance_mode
import models
from crud.finance import (
    generate_balance_sheet,
    generate_income_statement,
    generate_cash_flow_statement,
)


ACCOUNT_ID = 1


def _fmt(v, width=16):
    """格式化数值"""
    if v is None:
        return " " * width
    try:
        f = float(v)
        if abs(f) < 0.005:
            return " ".rjust(width)
        return f"{f:,.2f}".rjust(width)
    except Exception:
        return str(v).rjust(width)


def print_balance_sheet(db, account_id, date_str):
    """资产负债表"""
    print("\n" + "=" * 96)
    print(f"  资产负债表 (会小企01表)    巧游电子科技    报告期：{date_str}")
    print("=" * 96)

    bs = generate_balance_sheet(db, account_id, date_str)

    asset_rows = [
        ("一、流动资产", None),
        ("  货币资金", bs.get("monetary_funds")),
        ("  应收账款", bs.get("accounts_receivable")),
        ("  预付款项", bs.get("prepayments")),
        ("  存货", bs.get("inventory")),
        ("  待处理财产损溢", None),
        ("  流动资产合计", bs.get("total_current_assets")),
        ("二、非流动资产", None),
        ("  固定资产原值", bs.get("fixed_assets_original")),
        ("  减：累计折旧", bs.get("accumulated_depreciation")),
        ("  固定资产净值", bs.get("fixed_assets_net")),
        ("  无形资产原值", bs.get("intangible_assets_original")),
        ("  减：累计摊销", bs.get("accumulated_amortization")),
        ("  无形资产净值", bs.get("intangible_assets_net")),
        ("  非流动资产合计", bs.get("total_non_current_assets")),
        ("资产总计", bs.get("total_assets")),
    ]

    liab_equity_rows = [
        ("一、流动负债", None),
        ("  应付账款", bs.get("accounts_payable")),
        ("  其他应付款", bs.get("other_payable")),
        ("  应付职工薪酬", bs.get("salaries_payable")),
        ("  应交税费", bs.get("tax_payable")),
        ("    其中：应交增值税", bs.get("vat_payable")),
        ("          附加税", bs.get("surcharge_liability")),
        ("          所得税", bs.get("income_tax_liability")),
        ("          个人所得税", bs.get("personal_income_tax_liability")),
        ("  流动负债合计", bs.get("total_current_liabilities")),
        ("二、非流动负债", None),
        ("  长期借款", bs.get("long_term_borrowings")),
        ("  非流动负债合计", bs.get("total_non_current_liabilities")),
        ("三、所有者权益", None),
        ("  实收资本", bs.get("paid_in_capital")),
        ("  未分配利润", bs.get("retained_earnings")),
        ("  所有者权益合计", bs.get("total_equity")),
        ("负债和所有者权益总计", bs.get("total_liabilities_and_equity")),
    ]

    print(f"{'资产':<46}{'金额':>16}  │  {'负债及所有者权益':<46}{'金额':>16}")
    print("-" * 96)
    max_rows = max(len(asset_rows), len(liab_equity_rows))
    for i in range(max_rows):
        if i < len(asset_rows):
            label, val = asset_rows[i]
            l_str = f"{label:<46}{_fmt(val)}"
        else:
            l_str = " " * 62
        if i < len(liab_equity_rows):
            label, val = liab_equity_rows[i]
            r_str = f"{label:<46}{_fmt(val)}"
        else:
            r_str = " " * 62
        print(f"{l_str}  │  {r_str}")

    print("=" * 96)
    diff = Decimal(str(bs.get("total_assets", 0))) - Decimal(str(bs.get("total_liabilities_and_equity", 0)))
    flag = "✓ 平衡" if abs(diff) < Decimal("0.01") else f"✗ 不平衡（差 {diff}）"
    print(f"  平衡校验: 资产总计 - 负债权益总计 = {diff}    {flag}")
    print(f"  当期发生额: 收入={bs.get('period_revenue')} 成本={bs.get('period_cogs')} 费用={bs.get('period_expenses')} 税金={bs.get('surcharge_expense')} 所得税={bs.get('income_tax_expense')} 利润={bs.get('period_profit')}")


def print_income_statement(db, account_id, start, end):
    """利润表"""
    print("\n" + "=" * 70)
    print(f"  利润表 (会小企02表)    巧游电子科技")
    print(f"  期间：{start} ~ {end}")
    print("=" * 70)

    is_data = generate_income_statement(db, account_id, start, end)

    items = [
        ("一、营业收入", is_data.get("revenue"), False),
        ("  减：营业成本", is_data.get("cost_of_goods_sold"), False),
        ("      税金及附加", is_data.get("tax_surcharges"), False),
        ("      销售费用", is_data.get("selling_expenses"), False),
        ("      管理费用", is_data.get("administrative_expenses"), False),
        ("      财务费用", is_data.get("financial_expenses"), False),
        ("二、营业利润", is_data.get("operating_profit"), True),
        ("  加：营业外收入", is_data.get("non_operating_income"), False),
        ("  减：营业外支出", is_data.get("non_operating_expense"), False),
        ("三、利润总额", is_data.get("gross_profit_total"), True),
        ("  减：所得税费用", is_data.get("income_tax_expense"), False),
        ("四、净利润", is_data.get("net_profit"), True),
    ]

    for label, val, is_total in items:
        print(f"  {label:<40}{_fmt(val, 20)}")
        if is_total:
            print("  " + "-" * 60)

    print(f"\n  税金及附加明细：")
    detail_labels = {
        "urban_construction_tax": "  城建税",
        "education_surcharge": "  教育费附加",
        "local_education_surcharge": "  地方教育费附加",
        "stamp_tax": "  印花税",
    }
    for key, lbl in detail_labels.items():
        v = is_data.get(key)
        if v and abs(float(v)) > 0.005:
            print(f"    {lbl:<36}{_fmt(v, 20)}")

    print("=" * 70)


def print_cash_flow_statement(db, account_id, start, end):
    """现金流量表"""
    print("\n" + "=" * 80)
    print(f"  现金流量表 (会小企03表)    巧游电子科技")
    print(f"  期间：{start} ~ {end}")
    print("=" * 80)

    cf = generate_cash_flow_statement(db, account_id, start, end)

    op = cf.get("operating_activities", {})
    inv = cf.get("investing_activities", {})
    fin = cf.get("financing_activities", {})
    details = cf.get("cf_details", {})

    cf_map = {
        "CF01": "  销售商品、提供劳务收到的现金",
        "CF02": "  收到其他与经营活动有关的现金",
        "CF03": "  购买商品、接受劳务支付的现金",
        "CF04": "  支付给职工以及为职工支付的现金",
        "CF05": "  支付的各项税费",
        "CF06": "  支付其他与经营活动有关的现金",
        "CF08": "  收回投资收到的现金",
        "CF09": "  取得投资收益收到的现金",
        "CF10": "  处置固定资产、无形资产收回的现金净额",
        "CF11": "  购建固定资产、无形资产支付的现金",
        "CF12": "  投资支付的现金",
        "CF14": "  吸收投资收到的现金",
        "CF15": "  取得借款收到的现金",
        "CF16": "  偿还债务支付的现金",
        "CF17": "  分配股利、利润或偿付利息支付的现金",
        "CF18": "  支付其他与筹资活动有关的现金",
    }

    print(f"\n  一、经营活动产生的现金流量")
    print("  " + "-" * 70)
    for code in ["CF01", "CF02", "CF03", "CF04", "CF05", "CF06"]:
        if code in details:
            v = details[code]
            if v and abs(float(v)) > 0.005:
                print(f"    {cf_map[code]:<36}{_fmt(v, 20)}")
    print(f"    {'经营活动现金流入小计':<36}{_fmt(op.get('inflows'), 20)}")
    print(f"    {'经营活动现金流出小计':<36}{_fmt(op.get('outflows'), 20)}")
    print(f"    {'经营活动现金流量净额':<36}{_fmt(op.get('net'), 20)}")

    print(f"\n  二、投资活动产生的现金流量")
    print("  " + "-" * 70)
    for code in ["CF08", "CF09", "CF10", "CF11", "CF12"]:
        if code in details:
            v = details[code]
            if v and abs(float(v)) > 0.005:
                print(f"    {cf_map[code]:<36}{_fmt(v, 20)}")
    print(f"    {'投资活动现金流入小计':<36}{_fmt(inv.get('inflows'), 20)}")
    print(f"    {'投资活动现金流出小计':<36}{_fmt(inv.get('outflows'), 20)}")
    print(f"    {'投资活动现金流量净额':<36}{_fmt(inv.get('net'), 20)}")

    print(f"\n  三、筹资活动产生的现金流量")
    print("  " + "-" * 70)
    for code in ["CF14", "CF15", "CF16", "CF17", "CF18"]:
        if code in details:
            v = details[code]
            if v and abs(float(v)) > 0.005:
                print(f"    {cf_map[code]:<36}{_fmt(v, 20)}")
    print(f"    {'筹资活动现金流入小计':<36}{_fmt(fin.get('inflows'), 20)}")
    print(f"    {'筹资活动现金流出小计':<36}{_fmt(fin.get('outflows'), 20)}")
    print(f"    {'筹资活动现金流量净额':<36}{_fmt(fin.get('net'), 20)}")

    print("\n  " + "-" * 70)
    print(f"  {'四、现金及现金等价物净增加额':<40}{_fmt(cf.get('net_cash_flow'), 20)}")
    print(f"  {'加：期初现金及现金等价物余额':<40}{_fmt(cf.get('beginning_cash_balance'), 20)}")
    print(f"  {'五、期末现金及现金等价物余额':<40}{_fmt(cf.get('ending_cash_balance'), 20)}")
    print("=" * 80)


def main():
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        end_date = "2026-06-30"
        print(f"\n三大财务报表 - 巧游电子科技（截至 {end_date}）")

        # 1. 资产负债表（截至 2026-06-30）
        print_balance_sheet(db, ACCOUNT_ID, end_date)

        # 2. 利润表（2026 年 1-6 月累计）
        print_income_statement(db, ACCOUNT_ID, "2026-01-01", end_date)

        # 3. 现金流量表（2026 年 1-6 月累计）
        print_cash_flow_statement(db, ACCOUNT_ID, "2026-01-01", end_date)

        # 附加：2025-12 单月利润表（开账首月）
        print_income_statement(db, ACCOUNT_ID, "2025-12-01", "2025-12-31")

    finally:
        db.close()
        set_maintenance_mode(False)


if __name__ == "__main__":
    main()
