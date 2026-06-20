"""商品 + 库存 CRUD

写操作（create/update/delete product）已迁移至 commands 层。
本模块保留 list/get 查询函数和库存操作（adjust_inventory, get_stock_alerts）。
"""

import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
import models, schemas

from .base import get_or_create_inventory
from errors import BusinessError, ErrorCode

logger = logging.getLogger("inventory")


def list_products(db: Session, account_id: int, skip: int = 0, limit: int = 100, search: str = None, sku: str = None, category: str = None):
    q = db.query(models.Product).options(joinedload(models.Product.inventory)).filter(models.Product.account_id == account_id)
    if search:
        q = q.filter(or_(models.Product.name.contains(search), models.Product.sku.contains(search)))
    if sku:
        q = q.filter(models.Product.sku == sku)
    if category:
        q = q.filter(models.Product.category == category)
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return total, items


def get_product(db: Session, account_id: int, product_id: int):
    return db.query(models.Product).options(joinedload(models.Product.inventory)).filter(
        models.Product.account_id == account_id,
        models.Product.id == product_id
    ).first()


def list_inventory(db: Session, account_id: int, skip: int = 0, limit: int = 100, alert_only: bool = False, search: str = None, category: str = None):
    q = db.query(models.Inventory).filter(models.Inventory.account_id == account_id)
    q = q.join(models.Product)
    q = q.filter(models.Product.track_inventory == True)
    if alert_only:
        q = q.filter(models.Inventory.quantity < models.Product.min_stock)
    if search:
        q = q.filter(
            models.Product.name.contains(search) |
            models.Product.sku.contains(search)
        )
    if category:
        q = q.filter(models.Product.category == category)
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return total, items


def adjust_inventory(db: Session, account_id: int, product_id: int, data: schemas.InventoryAdjust, operator: str = "user"):
    inv = get_or_create_inventory(db, account_id, product_id)
    old_qty = inv.quantity
    inv.quantity = data.quantity
    from .base import _log
    _log(db, account_id, "adjust", "inventory", product_id, f"库存盘点: {old_qty}->{data.quantity}", operator=operator)
    db.flush()
    return inv


def get_stock_alerts(db: Session, account_id: int):
    return db.query(models.Inventory).join(models.Product).filter(
        models.Inventory.account_id == account_id,
        models.Inventory.quantity < models.Product.min_stock,
        models.Product.track_inventory == True,
    ).all()