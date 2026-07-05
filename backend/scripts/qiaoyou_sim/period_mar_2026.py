"""阶段4: 2026年3月业务"""
from datetime import datetime, date
from decimal import Decimal

from .helpers import (
    create_sale_order, create_bank_interest,
    create_fixed_asset_purchase, create_expense,
)


def step4_mar_2026(db, account_id: int):
    """2026 年 3 月业务"""
    print("\n=== 阶段 4：2026 年 3 月 ===")

    # 销售：南山射钉 1200（含税1%，未收款）
    o1 = create_sale_order(db, account_id, "四川南山射钉紧固器材有限公司",
        datetime(2026, 3, 10),
        [("修理修配劳务", 1, 1200.00, Decimal("0.01"), "维修费")],
        has_invoice=True, notes="专票 1200（未收款）")
    print(f"[3月] 销售单1: 含税{o1.total_price_l1}（未收款）")

    # 银行利息
    create_bank_interest(db, account_id, 0.60, date(2026, 3, 20))
    print("[3月] 银行利息: 0.60")

    # 固定资产：CPU+主板套装 2518.90（个人垫付）
    create_fixed_asset_purchase(db, account_id, "雷鸟CPU+主板套装",
        2518.90, date(2026, 3, 21), "拼多多采购，个人垫付",
        useful_life=36)
    print("[3月] 固定资产: CPU+主板套装 2518.90")

    # 固定资产：机箱 69.90（个人垫付）
    create_fixed_asset_purchase(db, account_id, "机箱",
        69.90, date(2026, 3, 27), "拼多多采购，个人垫付",
        useful_life=36)
    print("[3月] 固定资产: 机箱 69.90")

    # 费用
    create_expense(db, account_id, "房租", 1300.00, date(2026, 3, 31), "2026年3月房租")
    print("[3月] 费用: 房租 1300")

    create_expense(db, account_id, "水电", 120.00, date(2026, 3, 31), "2026年3月水电")
    print("[3月] 费用: 水电 120")

    db.flush()
