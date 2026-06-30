"""模板 16：销售退货与整单取消

⚠️ 本模板所有操作都是危险操作，必须用户确认后才能执行。
流程：发起 → 把系统提示转告用户 → 用户确认 → confirm / 用户取消 → cancel_pending
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post_pending, confirm, cancel_pending


def sale_return_pending(sale_order_id, return_date, items, reason=None, notes=None):
    """发起销售退货（返回 confirm_token，不立即执行）。

    系统会自动：
    - 冲红销售单（库存回退）
    - 创建红字销项发票（amount<0，冲减当期销项税额）

    参数：
        sale_order_id: 销售单 ID
        return_date: "YYYY-MM-DD"
        items: [{"product_id": 1, "quantity": 2}, ...]（退货数量）
        reason: 退货原因
        notes: 备注
    """
    body = {"return_date": return_date, "items": items}
    if reason: body["reason"] = reason
    if notes: body["notes"] = notes
    return post_pending(f"/api/sales/{sale_order_id}/return", body)


def cancel_sale_order_pending(sale_order_id, reason=None):
    """发起销售整单取消（返回 confirm_token，不立即执行）。

    系统会自动：
    - 冲红整个销售单（库存全部回退）
    - 创建红字销项发票（amount<0）
    - 级联冲红关联的收款（若有）
    """
    body = {}
    if reason: body["reason"] = reason
    return post_pending(f"/api/sales/{sale_order_id}/cancel", body)


# === 端到端示例：完整三步走流程 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)
    SO_ID = 5
    PROD_ID = 2

    print("=== 销售退货三步走示例 ===\n")

    print("第 1 步：发起（pending，未执行）")
    pending = sale_return_pending(
        sale_order_id=SO_ID,
        return_date="2026-06-27",
        items=[{"product_id": PROD_ID, "quantity": 5}],
        reason="客户退回 5 件次品",
    )
    print(f"   完整返回：{pending}")
    token = pending.get("confirm_token")
    message = pending.get("message", "")
    if not token:
        print("   ⚠️ 未拿到 token，可能参数错误或库存不足")
    else:
        print(f"\n第 2 步：转告用户系统提示")
        print(f"   系统提示：{message}")
        print(f"   → AI 应该停在这里，问用户：是否确认执行此退货？")

        print(f"\n第 3 步：根据用户回答调用 confirm/cancel_pending")
        user_answer = "yes"
        if user_answer == "yes":
            result = confirm(token)
            print(f"   确认结果：{result}")
        else:
            result = cancel_pending(token)
            print(f"   取消结果：{result}")
