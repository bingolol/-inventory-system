"""模板 11：收款

业务流程：销售/其他业务产生应收 → 收款 → 银行入账 + 核销应收
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


def create_receipt(receipt_type, related_entity_type, related_entity_id,
                   amount, receipt_date, bank_account_id,
                   receipt_method="company", description=None):
    """创建收款（走 POST /api/receipts）。

    参数：
        receipt_type: 收款类型，目前仅 "sale"（销售收款）
        related_entity_type: 关联实体类型，"sale_order"（销售单）
        related_entity_id: 关联销售单 ID
        amount: 收款金额（必须 > 0）
        receipt_date: 收款日期 "YYYY-MM-DDTHH:MM:SS"（如 "2026-06-22T10:00:00"）
        bank_account_id: 收款银行账户 ID
        receipt_method: "company"（公司账户，默认）/ "private_advance"（私人垫付）
        description: 备注
    """
    body = {
        "receipt_type": receipt_type,
        "related_entity_type": related_entity_type,
        "related_entity_id": related_entity_id,
        "amount": amount,
        "receipt_date": receipt_date,
        "receipt_method": receipt_method,
        "bank_account_id": bank_account_id,
    }
    if description: body["description"] = description
    return post("/api/receipts", body)


def get_receipt(receipt_id):
    """查询收款详情。"""
    return get(f"/api/receipts/{receipt_id}")


def list_receipts():
    """查询全部收款。"""
    return get("/api/receipts")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)
    BANK_ID = 1
    SO_ID = 1  # 销售单 ID

    print("1. 销售收款（关联销售单）")
    rc = create_receipt(
        receipt_type="sale",
        related_entity_type="sale_order",
        related_entity_id=SO_ID,
        amount=1130.00,
        receipt_date="2026-06-22T10:00:00",
        bank_account_id=BANK_ID,
    )
    print(f"   {rc}")
