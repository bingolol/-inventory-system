"""模板 12：付款

业务流程：采购/费用/工资产生应付 → 付款 → 银行出账 + 核销应付

⚠️ 付费用（房租/水电/工资）走 08_expenses.py 的 pay_expense()，
   本模板用于付采购款和独立付款场景。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


def create_payment(payment_type, related_entity_type, related_entity_id,
                   amount, payment_date, bank_account_id,
                   payment_method="company", description=None):
    """创建付款（走 POST /api/payments）。

    参数：
        payment_type: 付款类型
            - "expense"（付费用）
            - "salary"（发工资）
            - "purchase"（付采购款）
            - "tax"（缴税清负债）
        related_entity_type: 关联实体类型
            - "expense"（费用）
            - "purchase_order"（采购单）
        related_entity_id: 关联实体 ID
        amount: 付款金额（必须 > 0）
        payment_date: 付款日期 "YYYY-MM-DD"
        bank_account_id: 付款银行账户 ID
        payment_method: "company"（公司账户，默认）
        description: 备注
    """
    body = {
        "payment_type": payment_type,
        "related_entity_type": related_entity_type,
        "related_entity_id": related_entity_id,
        "amount": amount,
        "payment_date": payment_date,
        "bank_account_id": bank_account_id,
    }
    if description: body["description"] = description
    return post("/api/payments", body)


def pay_purchase(purchase_order_id, amount, payment_date, bank_account_id,
                  description=None):
    """付采购款（封装 create_payment，payment_type="purchase"）。"""
    return create_payment(
        payment_type="purchase",
        related_entity_type="purchase_order",
        related_entity_id=purchase_order_id,
        amount=amount,
        payment_date=payment_date,
        bank_account_id=bank_account_id,
        description=description,
    )


def pay_salary(expense_id, amount, payment_date, bank_account_id,
                description=None):
    """发工资（封装 create_payment，payment_type="salary"）。

    参数：
        expense_id: 工资费用 ID（先在 08_expenses 创建 category="工资" 的费用）
    """
    return create_payment(
        payment_type="salary",
        related_entity_type="expense",
        related_entity_id=expense_id,
        amount=amount,
        payment_date=payment_date,
        bank_account_id=bank_account_id,
        description=description,
    )


def get_payment(payment_id):
    """查询付款详情。"""
    return get(f"/api/payments/{payment_id}")


def list_payments():
    """查询全部付款。"""
    return get("/api/payments")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)
    BANK_ID = 1

    print("1. 付采购款")
    pay = pay_purchase(
        purchase_order_id=1,
        amount=11300.00,
        payment_date="2026-06-16",
        bank_account_id=BANK_ID,
    )
    print(f"   {pay}")
