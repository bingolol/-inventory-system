# crud/linkage.py — 联动业务逻辑层

"""库存↔成本、销售单↔项目收入 的联动操作，独立于路由层

三大不变量保证：
  I.  库存不变量：材料成本变动后库存变化 = 数量差值，失败自动回滚
  II. 收入不变量：同一 SaleOrder 最多一条 source_type='sale_order' 的 ProjectIncome
  III.汇总不变量：所有联动完成后调用 update_project_summary 重算，不依赖增量
"""

from sqlalchemy.orm import Session
from typing import Optional
import models
from .base import _log, get_or_create_inventory
from fastapi import HTTPException


# ── 成本 ↔ 库存（保证库存不变量 I）──

def cost_deduct_inventory(db: Session, account_id: int, cost: models.ProjectCost, operator: str = "user"):
    """材料类成本扣减库存（创建时调用）

    不变量 I 保证：扣减前校验库存充足，扣减后 inv.quantity >= 0。
    失败时抛出 HTTPException，由路由层 rollback 恢复原值。
    """
    if cost.cost_type != "材料" or not cost.product_id or not cost.quantity:
        return
    product = db.query(models.Product).filter(
        models.Product.id == cost.product_id,
        models.Product.account_id == account_id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"商品不存在: ID={cost.product_id}")
    inv = get_or_create_inventory(db, account_id, cost.product_id)
    if inv.quantity < cost.quantity:
        raise HTTPException(status_code=400,
            detail=f"库存不足: {product.name} 当前库存{inv.quantity}, 需要出库{cost.quantity}")
    inv.quantity -= cost.quantity
    assert inv.quantity >= 0, f"库存不变量违反: {product.name} 库存变为 {inv.quantity}"
    _log(db, account_id, "adjust", "inventory", inv.id,
         f"项目领料扣库存: {product.name} -{cost.quantity}", operator=operator)


def cost_restore_inventory(db: Session, account_id: int, cost: models.ProjectCost, operator: str = "user"):
    """材料类成本回补库存（删除时调用）

    不变量 I 保证：回补操作只会增加库存，不可能违反不变量。
    """
    if cost.cost_type != "材料" or not cost.product_id or not cost.quantity:
        return
    inv = get_or_create_inventory(db, account_id, cost.product_id)
    inv.quantity += cost.quantity
    _log(db, account_id, "adjust", "inventory", inv.id,
         f"删除项目成本回补库存: +{cost.quantity}", operator=operator)


def cost_update_inventory(db: Session, account_id: int, cost: models.ProjectCost,
                          old_cost_type: Optional[str], old_product_id: Optional[int],
                          old_quantity: Optional[int],
                          operator: str = "user"):
    """更新成本时调整库存差值（先回补旧的，再扣减新的）

    不变量 I 保证：
    1. 先回补旧库存（安全操作，只会增加）
    2. 再扣减新库存（含库存不足校验 + assert）
    3. 如果扣减新库存失败（HTTPException），路由层 rollback 会同时撤销回补，
       库存恢复到操作前的原值

    空值防护：旧值参数可为 None（旧记录没有 product_id/quantity），
    此时旧记录未关联库存，无需回补。
    """
    # 回补旧库存（空值防护：旧记录可能没有 product_id/quantity）
    old_quantity = old_quantity or 0
    if old_cost_type == "材料" and old_product_id and old_quantity > 0:
        inv = get_or_create_inventory(db, account_id, old_product_id)
        inv.quantity += old_quantity
        _log(db, account_id, "adjust", "inventory", inv.id,
             f"更新成本回补旧库存: +{old_quantity}", operator=operator)
    # 扣减新库存（含库存不足校验 + 不变量断言）
    cost_deduct_inventory(db, account_id, cost, operator)


# ── 销售单 ↔ 项目收入（保证收入不变量 II）──

def sale_create_income(db: Session, account_id: int, order: models.SaleOrder, operator: str = "user"):
    """销售单关联项目时自动生成项目收入

    不变量 II 保证：
    1. 幂等检查：如果已存在同 source_type+source_id 的收入，跳过不重复创建
    2. 数据库层 UNIQUE 索引 uq_income_source 作为最终防线
    """
    if not order.project_id:
        return
    # ★ 幂等检查：保证不变量 II
    existing = db.query(models.ProjectIncome).filter(
        models.ProjectIncome.source_type == "sale_order",
        models.ProjectIncome.source_id == order.id
    ).first()
    if existing:
        return  # 已存在，幂等跳过
    project = db.query(models.Project).filter(
        models.Project.id == order.project_id,
        models.Project.account_id == account_id
    ).first()
    if not project:
        return
    income = models.ProjectIncome(
        project_id=order.project_id,
        amount=order.total_price,
        payment_status="pending",
        invoice_status="未开" if not order.has_invoice else "已开",
        notes=f"销售单 {order.order_no} 自动生成",
        source_type="sale_order",
        source_id=order.id
    )
    db.add(income)
    db.flush()
    _log(db, account_id, "create", "project_income", income.id,
         f"销售单 {order.order_no} 自动生成项目收入: ¥{order.total_price}", operator=operator)


def sale_delete_income(db: Session, account_id: int, order_id: int, operator: str = "user"):
    """删除/取消销售单时联动删除项目收入，返回受影响的 project_id

    不变量 II 保证：按 source_type+source_id 精确查找并删除，
    UNIQUE 约束保证最多一条，不会误删或漏删。
    """
    linked_income = db.query(models.ProjectIncome).filter(
        models.ProjectIncome.source_type == "sale_order",
        models.ProjectIncome.source_id == order_id
    ).first()
    if linked_income:
        _log(db, account_id, "delete", "project_income", linked_income.id,
             f"销售单联动删除项目收入", operator=operator)
        db.delete(linked_income)
        return linked_income.project_id
    return None


# ── 销售单 ↔ 库存（零售扣库存开关）──

def _sale_should_deduct_inventory(order: models.SaleOrder) -> bool:
    """销售单是否允许影响库存（零售场景）"""
    if not order:
        return False
    # 旧数据可能为 NULL：按 false 处理
    deduct = bool(order.deduct_inventory) if order.deduct_inventory is not None else False
    if not deduct:
        return False
    # 项目业务禁止销售单扣库存（避免双扣）
    if order.project_id is not None:
        return False
    # 仅生效状态扣库存
    return order.status == "completed"


def sale_deduct_inventory(db: Session, account_id: int, order: models.SaleOrder, operator: str = "user"):
    """零售销售单扣库存（创建/恢复完成时调用）"""
    if not _sale_should_deduct_inventory(order):
        return
    for item in order.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id,
            models.Product.account_id == account_id
        ).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"商品不存在: ID={item.product_id}")
        inv = get_or_create_inventory(db, account_id, item.product_id)
        if inv.quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"库存不足: {product.name} 当前库存{inv.quantity}, 需要出库{item.quantity}"
            )
        inv.quantity -= item.quantity
        assert inv.quantity >= 0, f"库存不变量违反: {product.name} 库存变为 {inv.quantity}"
        _log(db, account_id, "adjust", "inventory", inv.id,
             f"零售销售扣库存: {product.name} -{item.quantity}（{order.order_no}）", operator=operator)


def sale_restore_inventory(db: Session, account_id: int, order: models.SaleOrder, operator: str = "user"):
    """零售销售单回补库存（删除/取消时调用）
    
    注意：不检查 order.status，由调用方控制回补时机。
    update_sale_order 中 setattr 已将 status 改为 cancelled，但仍需回补；
    delete_sale_order 中 status 未变更（completed），也需回补。
    """
    if not order:
        return
    deduct = bool(order.deduct_inventory) if order.deduct_inventory is not None else False
    if not deduct:
        return
    if order.project_id is not None:
        return
    for item in order.items:
        inv = get_or_create_inventory(db, account_id, item.product_id)
        inv.quantity += item.quantity
        _log(db, account_id, "adjust", "inventory", inv.id,
             f"零售销售回补库存: +{item.quantity}（{order.order_no}）", operator=operator)