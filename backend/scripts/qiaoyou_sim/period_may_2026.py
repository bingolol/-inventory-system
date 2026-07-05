"""阶段6: 2026年5月业务"""
from datetime import date

from .helpers import create_customer_payment, create_expense


def step6_may_2026(db, account_id: int):
    """2026 年 5 月业务"""
    print("\n=== 阶段 6：2026 年 5 月 ===")

    # 客户收款（4月销售的未收款 + 3月未收款）
    # 查找未收款的 sales orders
    import models
    pending = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.payment_status == "unpaid",
        models.SaleOrder.status == "completed",
    ).order_by(models.SaleOrder.sale_date_l1).all()

    for order in pending:
        amount = float(order.total_price_l1)
        create_customer_payment(db, account_id, "客户", order.id, amount, date(2026, 5, 15))
        print(f"[5月] 客户收款: {amount}")

    # 费用
    create_expense(db, account_id, "房租", 1300.00, date(2026, 5, 31), "2026年5月房租")
    print("[5月] 费用: 房租 1300")

    create_expense(db, account_id, "水电", 120.00, date(2026, 5, 31), "2026年5月水电")
    print("[5月] 费用: 水电 120")

    db.flush()
