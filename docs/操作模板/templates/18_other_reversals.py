"""模板 18：其他红冲（发票/费用/收款/付款红冲）

⚠️ 本模板所有操作都是危险操作，必须用户确认后才能执行。
流程：发起 → 把系统提示转告用户 → 用户确认 → confirm / 用户取消 → cancel_pending

适用：单独冲红一张发票/费用/收款/付款。
关联订单的发票建议走 16/17 的订单 return/cancel，会自动级联红冲发票。

⚠️ 后端注意：
- 发票红冲接受 reason（写入日志）；其他红冲端点不接受 body，reason 不持久化。
- 所有红冲端点都不接受 reverse_date（红冲日期取当前日期）。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post_pending, confirm, cancel_pending


def reverse_invoice_pending(invoice_id, reason=None):
    """发起发票红冲（返回 confirm_token，不立即执行）。

    适用：发票本身开错、纠错场景。
    关联订单的发票建议走 16/17 订单 return/cancel，会自动级联红冲发票。

    参数：
        invoice_id: 发票 ID
        reason: 红冲原因（后端写入日志）
    """
    body = {"reason": reason} if reason else {}
    return post_pending(f"/api/invoices/{invoice_id}/reverse", body)


def reverse_expense_pending(expense_id):
    """发起费用冲红（返回 confirm_token，不立即执行）。

    参数：
        expense_id: 费用 ID

    ⚠️ 后端不接受 body，红冲日期取当前日期。
    """
    return post_pending(f"/api/expenses/{expense_id}/reverse", {})


def reverse_receipt_pending(receipt_id):
    """发起收款冲红（返回 confirm_token，不立即执行）。

    系统自动幂等：若已被整单取消触发过冲红，不会重复扣减银行余额。

    参数：
        receipt_id: 收款 ID

    ⚠️ 后端不接受 body，红冲日期取当前日期。
    """
    return post_pending(f"/api/receipts/{receipt_id}/reverse", {})


def reverse_payment_pending(payment_id):
    """发起付款冲红（返回 confirm_token，不立即执行）。

    系统自动幂等：若已被整单取消触发过冲红，不会重复扣减银行余额。

    参数：
        payment_id: 付款 ID

    ⚠️ 后端不接受 body，红冲日期取当前日期。
    """
    return post_pending(f"/api/payments/{payment_id}/reverse", {})


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)
    EXP_ID = 11

    print("=== 费用冲红三步走示例 ===\n")

    print("第 1 步：发起（pending，未执行）")
    pending = reverse_expense_pending(expense_id=EXP_ID)
    print(f"   完整返回：{pending}")
    token = pending.get("confirm_token")
    if token:
        print(f"   系统提示：{pending.get('message')}")
        print("   → AI 应停在这里问用户：是否确认执行此冲红？")
        print("\n第 3 步：confirm(token) 或 cancel_pending(token)")
