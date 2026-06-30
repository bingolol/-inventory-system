"""模板 01：系统初始化、创建账本、录入期初余额

第一次使用系统时跑这个模板。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id, set_account


def init_system():
    """初始化系统（首次启动数据库后调用一次）。

    返回：{"ok": True, "message": "..."}
    """
    return post("/api/bootstrap/init")


def create_account(name, taxpayer_type, account_type="company"):
    """创建账本。

    参数：
        name: 账本名称（如"我的公司"）
        taxpayer_type: "general"（一般纳税人）或 "small_scale"（小规模纳税人）
        account_type: 默认 "company"，个体工商户填 "individual"

    返回：账本 dict，含 id 字段。后续所有调用前用 set_account(id) 设置账本。
    """
    return post("/api/accounts", {
        "name": name,
        "type": account_type,
        "taxpayer_type": taxpayer_type,
    })


def set_opening_balance(date, cash_balance, bank_balance, paid_in_capital):
    """录入期初余额。

    参数：
        date: 期初日期，如 "2026-06-01"
        cash_balance: 库存现金期初余额
        bank_balance: 银行存款期初余额
        paid_in_capital: 实收资本（必须等于 cash + bank）

    返回：期初余额 dict。
    """
    return post("/api/opening-balances", {
        "date": date,
        "cash_balance": cash_balance,
        "bank_balance": bank_balance,
        "paid_in_capital": paid_in_capital,
    })


def get_balance_sheet(date):
    """查询资产负债表（用于验证期初是否平衡）。

    参数：
        date: 查询日期，如 "2026-06-01"

    返回：BS dict，关键字段 balanced、diff、total_assets。
    """
    return get(f"/api/financial-reports/balance-sheet?date={date}")


# === 端到端示例：直接运行这个文件就能跑 ===
if __name__ == "__main__":
    # 1. 初始化系统
    print("1. 初始化系统")
    r = init_system()
    print(f"   {r}")

    # 2. 创建账本
    print("\n2. 创建账本")
    acct = create_account(name="演示公司", taxpayer_type="general")
    print(f"   {acct}")
    aid = extract_id(acct)
    set_account(aid)
    print(f"   账本 ID={aid}，已设置到客户端")

    # 3. 录入期初余额
    print("\n3. 录入期初余额")
    ob = set_opening_balance(
        date="2026-06-01",
        cash_balance=50000,
        bank_balance=500000,
        paid_in_capital=550000,
    )
    print(f"   {ob}")

    # 4. 验证期初 BS 平衡
    print("\n4. 验证期初资产负债表")
    bs = get_balance_sheet("2026-06-01")
    print(f"   balanced={bs.get('balanced')}, diff={bs.get('diff')}, total_assets={bs.get('total_assets')}")
    if bs.get("diff") != 0:
        print(f"   ⚠️ 不平衡！diff={bs.get('diff')}")
