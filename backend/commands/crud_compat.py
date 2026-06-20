"""CRUD 兼容桥接层 — 将 crud 模块函数统一导出给 commands 使用

commands 不直接 import crud.*，而是通过本模块桥接，
便于后续 crud 层重构时不影响 commands 层。
"""

# crud/base.py
from crud.base import _generate_order_no, _log, get_or_create_inventory

# crud/products.py
from crud.products import get_product, list_products, list_inventory, get_stock_alerts

# crud/orders.py
from crud.orders import get_purchase_order, get_sale_order, _d, _distribute_total_price

# image_utils
from image_utils import delete_old_image

# crud/partners.py
from crud.partners import (
    list_suppliers, get_supplier,
    list_customers, get_customer,
)

# crud/personal.py
from crud.personal import (
    list_personal_transactions,
    get_personal_category_summary,
    get_personal_monthly_summary,
    get_personal_summary,
)

# crud/inventory_ops.py
from crud.inventory_ops import sale_deduct, sale_restore

# 兼容旧名称
sale_deduct_inventory = sale_deduct
sale_restore_inventory = sale_restore

__all__ = [
    "_generate_order_no", "_log", "get_or_create_inventory",
    "get_product", "list_products", "list_inventory", "get_stock_alerts",
    "get_purchase_order", "get_sale_order", "_d", "_distribute_total_price",
    "sale_deduct", "sale_restore",
    "sale_deduct_inventory", "sale_restore_inventory",
    "delete_old_image",
    "list_suppliers", "get_supplier", "list_customers", "get_customer",
    "list_personal_transactions", "get_personal_category_summary",
    "get_personal_monthly_summary", "get_personal_summary",
]