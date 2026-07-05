"""阶段5: 2026年4月业务"""
from datetime import datetime, date
from decimal import Decimal

from .helpers import (
    create_sale_order, create_purchase_order, create_fixed_asset_purchase, create_expense,
)


def step5_apr_2026(db, account_id: int):
    """2026 年 4 月业务"""
    print("\n=== 阶段 5：2026 年 4 月 ===")

    # 固定资产（个人垫付）
    create_fixed_asset_purchase(db, account_id, "雷鸟Q7显示器",
        1665.67, date(2026, 4, 4), "拼多多采购，个人垫付",
        useful_life=36)
    print("[4月] 固定资产: 显示器 1665.67")

    # 采购（进项发票）
    create_purchase_order(db, account_id, "吴江恒净净化设备经营部",
        datetime(2026, 4, 20),
        [("维修备件", 2, 90.00, Decimal("0.01"), "初效过滤器")],
        has_invoice=True, notes="普票 180")
    print("[4月] 采购: 初效过滤器 180.00")

    create_purchase_order(db, account_id, "临泉县嘉涵商贸有限公司",
        datetime(2026, 4, 20),
        [("维修备件", 1, 398.00, Decimal("0.01"), "压力表")],
        has_invoice=True, notes="普票 398")
    print("[4月] 采购: 压力表 398.00")

    # 销售（未收款）
    o1 = create_sale_order(db, account_id, "四川南山射钉紧固器材有限公司",
        datetime(2026, 4, 21),
        [("修理修配劳务", 1, 1800.00, Decimal("0.01"), "维修费")],
        has_invoice=True, notes="专票 1800（未收款）")
    print(f"[4月] 销售单1: 含税{o1.total_price_l1}（未收款）")

    o2 = create_sale_order(db, account_id, "四川南山射钉紧固器材有限公司",
        datetime(2026, 4, 21),
        [("其他加工劳务", 1, 2400.00, Decimal("0.01"), "加工费")],
        has_invoice=True, notes="专票 2400（未收款）")
    print(f"[4月] 销售单2: 含税{o2.total_price_l1}（未收款）")

    create_purchase_order(db, account_id, "乐清市申港电气厂",
        datetime(2026, 4, 21),
        [("维修备件", 1, 176.21, Decimal("0.01"), "浮球开关")],
        has_invoice=True, notes="普票 176.21")
    print("[4月] 采购: 浮球开关 176.21")

    create_purchase_order(db, account_id, "博控科技（淮安）有限公司",
        datetime(2026, 4, 24),
        [("维修备件", 1, 1428.39, Decimal("0.01"), "超声波明渠流量计")],
        has_invoice=True, notes="普票 1428.39")
    print("[4月] 采购: 超声波明渠流量计 1428.39")

    # 费用
    create_expense(db, account_id, "房租", 1300.00, date(2026, 4, 30), "2026年4月房租")
    print("[4月] 费用: 房租 1300")

    create_expense(db, account_id, "水电", 120.00, date(2026, 4, 30), "2026年4月水电")
    print("[4月] 费用: 水电 120")

    db.flush()
