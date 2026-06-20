# crud/inventory_ops.py — 纯库存操作，不涉及任何业务语义

"""库存扣减/回补的原子操作，由 Command Handler 显式调用。

不依赖事件总线，不知道 SaleOrder/ProjectIncome 的存在。
track_inventory=False 的商品自动跳过。
零售销售单和项目专属销售单均通过 sale_deduct/sale_restore 扣减/回补库存。
"""

from sqlalchemy.orm import Session
import models
from domain.inventory import InventoryDomain
from .base import _log, get_or_create_inventory
from errors import BusinessError, ErrorCode


def deduct_stock(db: Session, account_id: int, product_id: int, quantity: int, operator: str = "user"):
    """扣减库存（材料成本出库时调用）

    校验库存充足 → 扣减 → 写操作日志。
    失败抛 HTTPException，由上层事务 rollback。
    track_inventory=False 的商品跳过。
    """
    if not product_id or not quantity:
        return
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.account_id == account_id,
    ).first()
    if not product:
        raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
    if not product.track_inventory:
        return
    inv = get_or_create_inventory(db, account_id, product_id)
    violations = InventoryDomain.from_orm(inv).validate()
    if violations:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": '; '.join(violations)})
    if inv.quantity < quantity:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"库存不足: {product.name} 当前库存{inv.quantity}, 需要出库{quantity}"})
    inv.quantity -= quantity
    _log(db, account_id, "adjust", "inventory", inv.id,
         f"项目领料扣库存: {product.name} -{quantity}", operator=operator)


def restore_stock(db: Session, account_id: int, product_id: int, quantity: int, operator: str = "user"):
    """回补库存（材料成本删除时调用）

    直接增加库存 → 写操作日志。
    track_inventory=False 的商品跳过。
    """
    if not product_id or not quantity:
        return
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.account_id == account_id,
    ).first()
    if not product:
        return
    if not product.track_inventory:
        return
    inv = get_or_create_inventory(db, account_id, product_id)
    violations = InventoryDomain.from_orm(inv).validate()
    if violations:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": '; '.join(violations)})
    inv.quantity += quantity
    _log(db, account_id, "adjust", "inventory", inv.id,
         f"删除项目成本回补库存: +{quantity}", operator=operator)


def sale_deduct(db: Session, account_id: int, order: models.SaleOrder, operator: str = "user"):
    """销售单扣库存（零售/项目专属销售单均调用）"""
    for item in order.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id,
            models.Product.account_id == account_id,
        ).first()
        if not product:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": item.product_id})
        inv = get_or_create_inventory(db, account_id, item.product_id)
        violations = InventoryDomain.from_orm(inv).validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": '; '.join(violations)})
        if inv.quantity < item.quantity:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"库存不足: {product.name} 当前库存{inv.quantity}, 需要出库{item.quantity}"})
        inv.quantity -= item.quantity
        _log(db, account_id, "adjust", "inventory", inv.id,
             f"销售扣库存: {product.name} -{item.quantity}（{order.order_no}）", operator=operator)


def sale_restore(db: Session, account_id: int, order: models.SaleOrder, operator: str = "user"):
    """销售单回补库存（CancelSaleOrderHandler/DeleteSaleOrderHandler 调用）"""
    for item in order.items:
        inv = get_or_create_inventory(db, account_id, item.product_id)
        violations = InventoryDomain.from_orm(inv).validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": '; '.join(violations)})
        inv.quantity += item.quantity
        _log(db, account_id, "adjust", "inventory", inv.id,
             f"销售回补库存: +{item.quantity}（{order.order_no}）", operator=operator)
