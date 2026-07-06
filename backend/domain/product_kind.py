"""商品类型判定 — 根据 track_inventory 分支逻辑

系统区分两类商品:
- 实体商品(track_inventory=True): 走库存流水，采/销走 StockMove，采购入 1405 库存商品
- 服务类商品(track_inventory=False): 不走库存流水，采购入 6601 管理费用
"""

from decimal import Decimal
from typing import Protocol


class ProductLike(Protocol):
    track_inventory_l3: bool
    sale_price_l1: Decimal


def is_service_product(product):
    return not getattr(product, "track_inventory_l3", True)


def should_track_inventory(product):
    return getattr(product, "track_inventory_l3", True)


def purchase_account_code(product):
    return "1405" if should_track_inventory(product) else "6601"


def sale_cogs_amount(product):
    return Decimal("0") if is_service_product(product) else (
        getattr(product, "sale_price_l1", Decimal("0")) or Decimal("0")
    )
