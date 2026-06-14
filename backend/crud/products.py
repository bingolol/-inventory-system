"""商品 + 库存 CRUD（含事务包裹）"""

import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
import models, schemas

from .base import _log, get_or_create_inventory

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


def create_product(db: Session, account_id: int, data: schemas.ProductCreate, operator: str = "user"):
    product = models.Product(account_id=account_id, **data.model_dump(exclude={"initial_stock"}))
    db.add(product)
    db.flush()
    inv = models.Inventory(account_id=account_id, product_id=product.id, quantity=data.initial_stock)
    db.add(inv)
    _log(db, account_id, "create", "product", product.id, f"创建商品: {product.name} (SKU:{product.sku})", operator=operator)
    db.flush()
    return product


def update_product(db: Session, account_id: int, product_id: int, data: schemas.ProductUpdate, operator: str = "user"):
    product = get_product(db, account_id, product_id)
    if not product:
        return None
    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(product, k, v)
    _log(db, account_id, "update", "product", product_id, f"更新商品: {product.name}", operator=operator)
    db.flush()
    return product


def delete_product(db: Session, account_id: int, product_id: int, operator: str = "user"):
    product = get_product(db, account_id, product_id)
    if not product:
        return False
    purchase_count = db.query(models.PurchaseItem).join(models.PurchaseOrder).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseItem.product_id == product_id
    ).count()
    sale_count = db.query(models.SaleItem).join(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleItem.product_id == product_id
    ).count()
    if purchase_count > 0 or sale_count > 0:
        logger.warning(f"删除商品失败-存在业务记录: ID={product_id}, 采购={purchase_count}, 销售={sale_count}")
        raise ValueError(f"该商品存在 {purchase_count} 条采购记录和 {sale_count} 条销售记录，无法删除")
    _log(db, account_id, "delete", "product", product_id, f"删除商品: {product.name}", operator=operator)
    db.query(models.Inventory).filter(
        models.Inventory.account_id == account_id,
        models.Inventory.product_id == product_id
    ).delete()
    db.delete(product)
    db.flush()
    return True


def list_inventory(db: Session, account_id: int, skip: int = 0, limit: int = 100, alert_only: bool = False, search: str = None, category: str = None):
    q = db.query(models.Inventory).filter(models.Inventory.account_id == account_id)
    q = q.join(models.Product)
    # 默认只显示追踪库存的商品
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
    _log(db, account_id, "adjust", "inventory", product_id, f"库存盘点: {old_qty}->{data.quantity}", operator=operator)
    db.flush()
    return inv


def get_stock_alerts(db: Session, account_id: int):
    return db.query(models.Inventory).join(models.Product).filter(
        models.Inventory.account_id == account_id,
        models.Inventory.quantity < models.Product.min_stock,
        models.Product.track_inventory == True,
    ).all()