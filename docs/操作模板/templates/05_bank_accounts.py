"""模板 05：银行账户管理"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


def create_bank_account(bank_name, account_number, account_type="checking"):
    """创建银行账户。

    参数：
        bank_name: 银行名称
        account_number: 银行账号
        account_type: "checking"（活期，默认）或 "savings"（定期）
    """
    return post("/api/bank-accounts", {
        "bank_name": bank_name,
        "account_number": account_number,
        "account_type": account_type,
    })


def list_bank_accounts():
    """查询全部银行账户（含实时余额）。"""
    return get("/api/bank-accounts")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("创建银行账户")
    bank = create_bank_account(bank_name="工商银行", account_number="6222000099887766550")
    print(f"   {bank}")
    bank_id = extract_id(bank)
    print(f"   ID: {bank_id}")

    print("\n查询全部银行账户")
    print(f"   {list_bank_accounts()}")
