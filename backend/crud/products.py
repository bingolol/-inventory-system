"""商品 + 库存 CRUD

写操作（create/update/delete product）已迁移至 commands 层。
本模块保留 list/get 查询函数和库存操作（adjust_inventory, get_stock_alerts）。
"""

import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func as sqlfunc
import models, schemas

from .base import get_or_create_inventory
from errors import BusinessError, ErrorCode
from lineage import reads, TIER_L1, TIER_L3, TIER_L4

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
    """查询商品（含库存联表），不存在则抛 BusinessError"""
    p = db.query(models.Product).options(joinedload(models.Product.inventory)).filter(
        models.Product.account_id == account_id,
        models.Product.id == product_id
    ).first()
    if not p:
        raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
    return p


@reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
@reads("Product.min_stock_l3", tier=TIER_L3, source="policy")
@reads("StockMove.quantity_l1", tier=TIER_L1, source="external")
def list_inventory(db: Session, account_id: int, skip: int = 0, limit: int = 100, alert_only: bool = False, search: str = None, category: str = None):
    stock_subq = db.query(
        models.StockMove.product_id,
        sqlfunc.sum(models.StockMove.quantity_l1).label('current_qty')
    ).filter(
        models.StockMove.account_id == account_id
    ).group_by(models.StockMove.product_id).subquery()

    q = db.query(
        models.Product,
        sqlfunc.coalesce(stock_subq.c.current_qty, 0).label('current_qty')
    ).outerjoin(
        stock_subq, models.Product.id == stock_subq.c.product_id
    ).filter(
        models.Product.account_id == account_id,
        models.Product.track_inventory_l3 == True,
    )
    if alert_only:
        q = q.filter(sqlfunc.coalesce(stock_subq.c.current_qty, 0) < models.Product.min_stock_l3)
    if search:
        q = q.filter(
            models.Product.name.contains(search) |
            models.Product.sku.contains(search)
        )
    if category:
        q = q.filter(models.Product.category == category)

    total = q.count()
    rows = q.offset(skip).limit(limit).all()
    items = [(row[0], int(row[1]) if row[1] else 0) for row in rows]
    return total, items


@reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
@reads("Product.min_stock_l3", tier=TIER_L3, source="policy")
@reads("StockMove.quantity_l1", tier=TIER_L1, source="external")
def get_stock_alerts(db: Session, account_id: int):
    stock_subq = db.query(
        models.StockMove.product_id,
        sqlfunc.sum(models.StockMove.quantity_l1).label('current_qty')
    ).filter(
        models.StockMove.account_id == account_id
    ).group_by(models.StockMove.product_id).subquery()

    rows = db.query(
        models.Product,
        sqlfunc.coalesce(stock_subq.c.current_qty, 0).label('current_qty')
    ).outerjoin(
        stock_subq, models.Product.id == stock_subq.c.product_id
    ).filter(
        models.Product.account_id == account_id,
        models.Product.track_inventory_l3 == True,
        sqlfunc.coalesce(stock_subq.c.current_qty, 0) < models.Product.min_stock_l3,
    ).all()
    return [(row[0], int(row[1]) if row[1] else 0) for row in rows]