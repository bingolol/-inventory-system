"""阶段3: 2026年1-2月业务"""
from datetime import datetime, date
from decimal import Decimal

from .helpers import (
    create_sale_order, create_customer_payment,
    create_bank_fee, create_expense,
)


def step3_jan_feb_2026(db, account_id: int):
    """2026 年 1-2 月业务"""
    print("\n=== 阶段 3：2026 年 1-2 月 ===")

    # ── 1月 ──
    # 银行扣款：账户年费
    create_bank_fee(db, account_id, 150.00, date(2026, 1, 5), "银行账户年费")
    print("[1月] 银行扣款: 账户年费 150.00")

    # 费用
    create_expense(db, account_id, "房租", 1300.00, date(2026, 1, 31), "2026年1月房租",
                   payment_method="private_advance")
    print("[1月] 费用: 房租 1300")

    create_expense(db, account_id, "水电", 120.00, date(2026, 1, 31), "2026年1月水电",
                   payment_method="private_advance")
    print("[1月] 费用: 水电 120")

    # ── 2月 ──
    # 销售1：联通 5000（含税1%）
    o1 = create_sale_order(db, account_id, "中国联通宜宾分公司",
        datetime(2026, 2, 10),
        [("信息系统服务", 1, 5000.00, Decimal("0.01"), "技术服务费")],
        has_invoice=True, notes="普票 5000")
    print(f"[2月] 销售单1: 含税{o1.total_price_l1}")

    # 销售2：南山射钉 1000（含税1%）
    o2 = create_sale_order(db, account_id, "四川南山射钉紧固器材有限公司",
        datetime(2026, 2, 15),
        [("修理修配劳务", 1, 1000.00, Decimal("0.01"), "维修费")],
        has_invoice=True, notes="普票 1000")
    print(f"[2月] 销售单2: 含税{o2.total_price_l1}")

    # 客户收款
    create_customer_payment(db, account_id, "四川南山射钉紧固器材有限公司",
        o2.id, 1000, date(2026, 2, 15))
    print("[2月] 客户收款: 1000")

    create_customer_payment(db, account_id, "中国联通宜宾分公司",
        o1.id, 5000, date(2026, 2, 20))
    print("[2月] 客户收款: 5000")

    # 费用
    create_expense(db, account_id, "房租", 1300.00, date(2026, 2, 28), "2026年2月房租",
                   payment_method="private_advance")
    print("[2月] 费用: 房租 1300")

    create_expense(db, account_id, "水电", 120.00, date(2026, 2, 28), "2026年2月水电",
                   payment_method="private_advance")
    print("[2月] 费用: 水电 120")

    db.flush()
