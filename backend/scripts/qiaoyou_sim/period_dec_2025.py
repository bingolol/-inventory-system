"""阶段2: 2025年12月业务（开账首月）"""
from datetime import datetime, date
from decimal import Decimal

from .helpers import (
    create_sale_order, create_customer_payment,
    create_bank_fee, create_bank_interest, create_expense,
)


def step2_dec_2025(db, account_id: int):
    """2025 年 12 月业务"""
    print("\n=== 阶段 2：2025 年 12 月 ===")

    # 销售1：联通 1500（含税1%）
    o1 = create_sale_order(db, account_id, "中国联通宜宾分公司",
        datetime(2025, 12, 10),
        [("信息系统服务", 1, 1500.00, Decimal("0.01"), "技术服务费")],
        has_invoice=True, notes="普票 1500")
    print(f"[12月] 销售单1: 含税{o1.total_price_l1}")

    # 销售2：南山射钉 500（含税1%）
    o2 = create_sale_order(db, account_id, "四川南山射钉紧固器材有限公司",
        datetime(2025, 12, 15),
        [("修理修配劳务", 1, 500.00, Decimal("0.01"), "维修费")],
        has_invoice=True, notes="普票 500")
    print(f"[12月] 销售单2: 含税{o2.total_price_l1}")

    # 客户收款
    create_customer_payment(db, account_id, "四川南山射钉紧固器材有限公司",
        o2.id, 500, date(2025, 12, 15))
    print("[12月] 客户收款: 500")

    create_customer_payment(db, account_id, "中国联通宜宾分公司",
        o1.id, 1500, date(2025, 12, 20))
    print("[12月] 客户收款: 1500")

    # 银行扣款：开户费
    create_bank_fee(db, account_id, 50.00, date(2025, 12, 5), "银行开户费")
    print("[12月] 银行扣款: 开户费 50.00")

    create_bank_fee(db, account_id, 22.80, date(2025, 12, 5), "网银U盾费")
    print("[12月] 银行扣款: 开户费 22.80")

    # 银行利息
    create_bank_interest(db, account_id, 0.01, date(2025, 12, 20))
    print("[12月] 银行利息: 0.01")

    # 费用
    create_expense(db, account_id, "房租", 1300.00, date(2025, 12, 31), "2025年12月房租")
    print("[12月] 费用: 房租 1300")

    create_expense(db, account_id, "水电", 120.00, date(2025, 12, 31), "2025年12月水电")
    print("[12月] 费用: 水电 120")

    db.flush()
