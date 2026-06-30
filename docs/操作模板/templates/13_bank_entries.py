"""模板 13：银行分录

用于非业务往来的银行分录：手续费、利息收入等。
走 POST /api/bank/entry。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post


def create_bank_entry(entry_type, amount, transaction_date, description=None):
    """创建银行分录（走 POST /api/bank/entry）。

    参数：
        entry_type: 分录类型（合法值，严格匹配）：
            - "bank_fee"（银行手续费，支出）
            - "interest_income"（利息收入，收入）
        amount: 金额（正数）
        transaction_date: 交易日期 "YYYY-MM-DD"
        description: 备注
    """
    body = {
        "entry_type": entry_type,
        "amount": amount,
        "transaction_date": transaction_date,
    }
    if description: body["description"] = description
    return post("/api/bank/entry", body)


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("1. 银行手续费 50 元")
    bf = create_bank_entry(
        entry_type="bank_fee",
        amount=50,
        transaction_date="2026-06-28",
    )
    print(f"   {bf}")

    print("\n2. 利息收入 120 元")
    bi = create_bank_entry(
        entry_type="interest_income",
        amount=120,
        transaction_date="2026-06-28",
    )
    print(f"   {bi}")
