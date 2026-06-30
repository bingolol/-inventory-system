"""模板 19：财务报表（BS / IS / 试算平衡表）

业务流程：查询资产负债表、利润表、试算平衡表，验证账目平衡
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import get


def get_balance_sheet(date):
    """查询资产负债表。走 GET /api/financial-reports/balance-sheet?date=YYYY-MM-DD

    参数：
        date: 截至日期 "YYYY-MM-DD"

    返回字段：
        assets, liabilities, equity: 资产/负债/权益明细
        total_assets, total_liabilities_equity: 合计（应相等，否则 BS 不平衡）
        diff: 差额（0 表示平衡）
    """
    return get(f"/api/financial-reports/balance-sheet?date={date}")


def get_income_statement(start_date, end_date):
    """查询利润表。走 GET /api/financial-reports/income-statement?start_date=&end_date=

    参数：
        start_date, end_date: 期间 [start, end] "YYYY-MM-DD"

    返回字段：
        revenue: 营业收入
        cost_of_goods_sold: 营业成本
        operating_profit: 营业利润
        net_profit: 净利润
    """
    return get(f"/api/financial-reports/income-statement?start_date={start_date}&end_date={end_date}")


def get_trial_balance(date):
    """查询试算平衡表（所有科目的借方/贷方累计余额）。

    走 GET /api/finance/reports/trial-balance?date=YYYY-MM-DD

    参数：
        date: 截至日期 "YYYY-MM-DD"
    """
    return get(f"/api/finance/reports/trial-balance?date={date}")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("1. 查询 6 月 BS")
    bs = get_balance_sheet("2026-06-30")
    print(f"   资产合计：{bs.get('total_assets')}")
    print(f"   负债+权益合计：{bs.get('total_liabilities_equity')}")
    print(f"   差额（应为 0）：{bs.get('diff')}")

    print("\n2. 查询 6 月利润表")
    is_r = get_income_statement("2026-06-01", "2026-06-30")
    print(f"   营业收入：{is_r.get('revenue')}")
    print(f"   营业成本：{is_r.get('cost_of_goods_sold')}")
    print(f"   营业利润：{is_r.get('operating_profit')}")
    print(f"   净利润：{is_r.get('net_profit')}")

    print("\n3. 查询试算平衡表")
    trial = get_trial_balance("2026-06-30")
    print(f"   balanced: {trial.get('balanced')}")
