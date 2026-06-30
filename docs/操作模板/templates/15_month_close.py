"""模板 15：月结

业务流程：银行对账确认后 → 执行月结（折旧→增值税→附加税→所得税→结转）
前置条件：当月所有银行账户的余额调节表必须已确认。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post


def run_month_close(period):
    """执行月结（按顺序自动完成）：
    1. 固定资产折旧计提
    2. 增值税结转（销项-进项，含留抵）
    3. 附加税计提（城建税、教育费附加等）
    4. 所得税预提（按利润总额计算）
    5. 损益结转

    走 POST /api/finance/month-close

    前置条件：当月所有银行账户的余额调节表必须已确认（在 14_bank_reconcile 中执行）。
    如未确认，月结会失败并返回错误信息。

    参数：
        period: 结账期间 "YYYY-MM"（如 "2026-06"）
    """
    return post("/api/finance/month-close", {"period": period})


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("执行 6 月结账")
    mc = run_month_close(period="2026-06")
    print(f"   {mc}")
