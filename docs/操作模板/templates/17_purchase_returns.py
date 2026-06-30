"""模板 17：采购退货与整单取消

⚠️ 本模板所有操作都是危险操作，必须用户确认后才能执行。
流程：发起 → 把系统提示转告用户 → 用户确认 → confirm / 用户取消 → cancel_pending
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post_pending, confirm, cancel_pending


def purchase_return_pending(purchase_order_id, return_date, items, reason=None, notes=None):
    """发起采购退货（返回 confirm_token，不立即执行）。

    系统会自动：
    - 冲红采购单（库存减少，需检查库存充足，不足报 INVENTORY_INSUFFICIENT）
    - 创建红字进项发票（amount<0，冲减当期进项税额）

    参数：
        purchase_order_id: 采购单 ID
        return_date: "YYYY-MM-DD"
        items: [{"product_id": 1, "quantity": 2}, ...]（退货数量）
        reason: 退货原因
        notes: 备注
    """
    body = {"return_date": return_date, "items": items}
    if reason: body["reason"] = reason
    if notes: body["notes"] = notes
    return post_pending(f"/api/purchases/{purchase_order_id}/return", body)


def cancel_purchase_order_pending(purchase_order_id, reason=None):
    """发起采购整单取消（返回 confirm_token，不立即执行）。

    系统会自动：
    - 冲红整个采购单（库存全部减少）
    - 创建红字进项发票
    - 级联冲红关联的付款（若有）
    """
    body = {}
    if reason: body["reason"] = reason
    return post_pending(f"/api/purchases/{purchase_order_id}/cancel", body)


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)
    PO_ID = 1
    PROD_ID = 2

    print("=== 采购退货三步走示例 ===\n")

    print("第 1 步：发起（pending，未执行）")
    pending = purchase_return_pending(
        purchase_order_id=PO_ID,
        return_date="2026-06-27",
        items=[{"product_id": PROD_ID, "quantity": 5}],
        reason="退回 5 件次品给供应商",
    )
    print(f"   完整返回：{pending}")
    token = pending.get("confirm_token")
    if token:
        print(f"   系统提示：{pending.get('message')}")
        print("   → AI 应停在这里问用户：是否确认执行此退货？")
        print("\n第 3 步：confirm(token) 或 cancel_pending(token)")
