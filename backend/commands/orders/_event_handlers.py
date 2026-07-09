"""订单领域事件业务处理器

把销售/采购单与库存、财务的联动从 _lifecycle.py 迁移到 EventBus，
使 OrderLifecycle 只负责 entity 创建与状态转换，业务副作用通过事件 seam 解耦。

handler 优先级约定：
  10 库存处理（必须先出库/入库，才能拿到 unit_cost 生成凭证）
  20 收付款冲销
  30 财务凭证生成/冲红
 100 审计日志（handlers.py 中注册）
"""

from decimal import Decimal

import models
from commands.reversal_ops import reverse_payments, reverse_receipts
from crud.products import get_product
from engine_finance import FinanceEngine
from engine_inventory import InventoryEngine
from enums import OrderStatus
from events import on


PRIORITY_INVENTORY = 10
PRIORITY_RECEIPT = 20
PRIORITY_FINANCE = 30


# ═══════════════════════════════════════════════════════════
# 销售单创建
# ═══════════════════════════════════════════════════════════

@on("sale_order.created", priority=PRIORITY_INVENTORY)
def handle_sale_order_created_inventory(
    *, db, account_id, operator, order, deduct_inventory=True, **kwargs
):
    """销售单创建：库存出库并回写 unit_cost"""
    if not deduct_inventory:
        for item in order.items:
            item.set_calculated_cost(Decimal("0"))
        return

    eng = InventoryEngine(db)
    for item in order.items:
        product = get_product(db, account_id, item.product_id)
        if product and product.track_inventory_l3:
            unit_cost = eng.outbound(
                account_id=account_id,
                product_id=item.product_id,
                quantity=item.quantity_l1,
                source_type="sale_order",
                source_id=order.id,
                operator=operator,
                move_date=order.sale_date_l1,
            )
            item.set_calculated_cost(unit_cost)
        else:
            item.set_calculated_cost(Decimal("0"))


@on("sale_order.created", priority=PRIORITY_FINANCE)
def handle_sale_order_created_finance(*, db, account_id, order, **kwargs):
    """销售单创建：生成销售凭证"""
    FinanceEngine(db, account_id).record_sale(order)


# ═══════════════════════════════════════════════════════════
# 采购单创建
# ═══════════════════════════════════════════════════════════

@on("purchase_order.created", priority=PRIORITY_INVENTORY)
def handle_purchase_order_created_inventory(
    *, db, account_id, operator, order, **kwargs
):
    """采购单创建：库存入库"""
    eng = InventoryEngine(db)
    for item in order.items:
        product = get_product(db, account_id, item.product_id)
        if product and product.track_inventory_l3:
            eng.inbound(
                account_id=account_id,
                product_id=item.product_id,
                quantity=item.quantity_l1,
                unit_price=item.unit_price_l1,
                source_type="purchase_order",
                source_id=order.id,
                tax_rate=item.tax_rate_l1,
                operator=operator,
                move_date=order.purchase_date_l1,
            )


@on("purchase_order.created", priority=PRIORITY_FINANCE)
def handle_purchase_order_created_finance(*, db, account_id, order, **kwargs):
    """采购单创建：生成采购凭证"""
    FinanceEngine(db, account_id).record_purchase(order)


# ═══════════════════════════════════════════════════════════
# 销售单取消 / 删除
# ═══════════════════════════════════════════════════════════

@on("sale_order.cancelled", priority=PRIORITY_INVENTORY)
@on("sale_order.deleted", priority=PRIORITY_INVENTORY)
def handle_sale_order_cancel_inventory(
    *, db, account_id, operator, order, old_status, **kwargs
):
    """销售单取消/删除：冲回库存"""
    if old_status != OrderStatus.COMPLETED:
        return
    eng = InventoryEngine(db)
    for item in order.items:
        eng.reverse(
            account_id=account_id,
            product_id=item.product_id,
            quantity=item.quantity_l1,
            unit_cost=item.unit_cost_l2 or Decimal("0"),
            source_type="sale_order",
            source_id=order.id,
            operator=operator,
            force=True,
        )


@on("sale_order.cancelled", priority=PRIORITY_RECEIPT)
@on("sale_order.deleted", priority=PRIORITY_RECEIPT)
def handle_sale_order_cancel_receipts(*, db, account_id, order, **kwargs):
    """销售单取消/删除：冲回收款"""
    reverse_receipts(db, account_id, order.id)


@on("sale_order.cancelled", priority=PRIORITY_FINANCE)
@on("sale_order.deleted", priority=PRIORITY_FINANCE)
def handle_sale_order_cancel_finance(*, db, account_id, order, old_status, **kwargs):
    """销售单取消/删除：冲红销售凭证"""
    if old_status != OrderStatus.COMPLETED:
        return
    FinanceEngine(db, account_id).reverse_sale(order.id, force=True)


# ═══════════════════════════════════════════════════════════
# 采购单取消 / 删除
# ═══════════════════════════════════════════════════════════

@on("purchase_order.cancelled", priority=PRIORITY_INVENTORY)
@on("purchase_order.deleted", priority=PRIORITY_INVENTORY)
def handle_purchase_order_cancel_inventory(
    *, db, account_id, operator, order, old_status, **kwargs
):
    """采购单取消/删除：冲回库存"""
    if old_status != OrderStatus.COMPLETED:
        return
    eng = InventoryEngine(db)
    for item in order.items:
        product = db.get(models.Product, item.product_id)
        if product and product.track_inventory_l3:
            eng.reverse(
                account_id=account_id,
                product_id=item.product_id,
                quantity=item.quantity_l1,
                unit_cost=Decimal("0"),
                source_type="purchase_order",
                source_id=order.id,
                operator=operator,
                force=True,
            )


@on("purchase_order.cancelled", priority=PRIORITY_RECEIPT)
@on("purchase_order.deleted", priority=PRIORITY_RECEIPT)
def handle_purchase_order_cancel_payments(*, db, account_id, order, **kwargs):
    """采购单取消/删除：冲回付款"""
    reverse_payments(db, account_id, order.id)


@on("purchase_order.cancelled", priority=PRIORITY_FINANCE)
@on("purchase_order.deleted", priority=PRIORITY_FINANCE)
def handle_purchase_order_cancel_finance(*, db, account_id, order, old_status, **kwargs):
    """采购单取消/删除：冲红采购凭证"""
    if old_status != OrderStatus.COMPLETED:
        return
    FinanceEngine(db, account_id).reverse_purchase(order.id, force=True)


# ═══════════════════════════════════════════════════════════
# 销售单恢复
# ═══════════════════════════════════════════════════════════

@on("sale_order.restored", priority=PRIORITY_INVENTORY)
def handle_sale_order_restored_inventory(
    *, db, account_id, operator, order, **kwargs
):
    """恢复销售单：重新出库"""
    eng = InventoryEngine(db)
    for item in order.items:
        product = get_product(db, account_id, item.product_id)
        if product and product.track_inventory_l3:
            unit_cost = eng.force_outbound(
                account_id=account_id,
                product_id=item.product_id,
                quantity=item.quantity_l1,
                source_type="sale_order",
                source_id=order.id,
                operator=operator,
                move_date=order.sale_date_l1,
            )
            item.set_calculated_cost(unit_cost)
        else:
            item.set_calculated_cost(Decimal("0"))


@on("sale_order.restored", priority=PRIORITY_FINANCE)
def handle_sale_order_restored_finance(*, db, account_id, order, **kwargs):
    """恢复销售单：重建销售凭证"""
    FinanceEngine(db, account_id).record_sale(order, force=True)
