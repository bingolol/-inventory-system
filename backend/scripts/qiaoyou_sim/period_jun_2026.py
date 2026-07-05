"""阶段7: 2026年6月业务（纳税人切换 small_scale → general）"""
from datetime import datetime, date
from decimal import Decimal

from .helpers import (
    create_sale_order, create_customer_payment,
    create_bank_interest, create_expense,
)


def step7_jun_2026(db, account_id: int):
    """2026 年 6 月业务

    6月初切换为一般纳税人（同时写 TaxpayerTypeHistory 以便回溯查询）
    """
    print("\n=== 阶段 7：2026 年 6 月（纳税人切换）===")

    import models

    # 6月初切换为一般纳税人
    acc = db.query(models.Account).filter(models.Account.id == account_id).first()
    old_type = acc.taxpayer_type_l3
    acc.taxpayer_type_l3 = "general"

    # 写 TaxpayerTypeHistory 以便回溯查询（如果模型存在）
    try:
        db.add(models.TaxpayerTypeHistory(
            account_id=account_id,
            taxpayer_type_l3="general",
            effective_period="2026-06",
        ))
        db.flush()
        print(f"[6月] 纳税人切换: {old_type} → general（生效期间 2026-06，已写历史记录）")
    except AttributeError:
        # TaxpayerTypeHistory 模型不存在（旧版本），跳过
        db.flush()
        print(f"[6月] 纳税人切换: {old_type} → general（生效期间 2026-06，未写历史记录）")

    # 销售：联通 21836（含税6%，一般纳税人）
    # 注意：切换后默认税率应为 0.06（信息服务税目）
    o1 = create_sale_order(db, account_id, "中国联通宜宾分公司",
        datetime(2026, 6, 15),
        [("信息系统服务", 1, 21836.00, Decimal("0.06"), "技术服务费")],
        has_invoice=True, notes="专票 21836")
    print(f"[6月] 销售单1: 含税{o1.total_price_l1}")

    # 银行利息
    create_bank_interest(db, account_id, 1.23, date(2026, 6, 20))
    print("[6月] 银行利息: 1.23")

    # 客户收款
    create_customer_payment(db, account_id, "中国联通宜宾分公司",
        o1.id, 21836, date(2026, 6, 25))
    print("[6月] 客户收款: 联通 21836")

    # 费用
    create_expense(db, account_id, "房租", 1300.00, date(2026, 6, 30), "2026年6月房租")
    print("[6月] 费用: 房租 1300")

    create_expense(db, account_id, "水电", 120.00, date(2026, 6, 30), "2026年6月水电")
    print("[6月] 费用: 水电 120")

    db.flush()
