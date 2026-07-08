"""模板 14：银行对账

业务流程：录入对账单 → 生成调节表 → 确认调节表
月结前必须确认所有银行账户的调节表。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


def create_bank_statement(period_start, period_end, opening_balance,
                          closing_balance, lines):
    """创建银行对账单。走 POST /api/bank/statement。

    参数：
        period_start, period_end: 对账单期间 "YYYY-MM-DD"
        opening_balance: 期初余额
        closing_balance: 期末余额（账面应余额）
        lines: 对账明细 [{"transaction_date": "2026-06-15", "amount": 101700, "description": "收款"}, ...]
               amount 正数=收款，负数=付款
    """
    return post("/api/bank/statement", {
        "period_start": period_start,
        "period_end": period_end,
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "lines": lines,
    })


def run_bank_reconcile(period):
    """执行银行对账（生成调节表）。走 POST /api/bank/reconcile?period=YYYY-MM

    参数：
        period: 对账期间 "YYYY-MM"（如 "2026-06"）
    """
    return post(f"/api/bank/reconcile?period={period}", {})


def get_bank_reconciliation(period):
    """查询银行存款余额调节表。走 GET /api/bank/reconciliation?period=YYYY-MM

    返回字段含 id（用于 confirm_bank_reconciliation）。
    """
    return get(f"/api/bank/reconciliation?period={period}")


def confirm_bank_reconciliation(reconciliation_id):
    """确认银行余额调节表（status=confirmed）。走 POST /api/bank/reconciliation/{id}/confirm

    月结前必须确认所有银行账户的调节表。
    """
    return post(f"/api/bank/reconciliation/{reconciliation_id}/confirm", {})


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("1. 创建 6 月银行对账单")
    bank_end = 500000 + 101700 - 113000 - 25000 - 3000 - 50 + 120
    stmt = create_bank_statement(
        period_start="2026-06-01",
        period_end="2026-06-30",
        opening_balance=500000,
        closing_balance=bank_end,
        lines=[
            {"transaction_date": "2026-06-22", "amount": 101700, "description": "收款"},
            {"transaction_date": "2026-06-25", "amount": -113000, "description": "付款采购"},
            {"transaction_date": "2026-06-28", "amount": -50, "description": "手续费"},
        ],
    )
    print(f"   {stmt}")

    print("\n2. 执行对账（生成调节表）")
    recon = run_bank_reconcile(period="2026-06")
    print(f"   {recon}")

    print("\n3. 查询调节表 ID")
    rec_data = get_bank_reconciliation(period="2026-06")
    print(f"   {rec_data}")
    rec_id = None
    if isinstance(rec_data, list) and rec_data:
        rec_id = rec_data[0].get("id")
    elif isinstance(rec_data, dict):
        rec_id = rec_data.get("id")
        if not rec_id:
            items_r = rec_data.get("items", [])
            if items_r:
                rec_id = items_r[0].get("id")
    print(f"   rec_id={rec_id}")

    print("\n4. 确认调节表")
    if rec_id:
        conf = confirm_bank_reconciliation(rec_id)
        print(f"   {conf}")
