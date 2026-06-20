"""销售单 Command + Handler — 6个命令覆盖销售单全部业务操作

v7 改造后：移除项目模块
  所有销售单均为零售型，deduct_inventory=True
  不再关联项目、不再创建项目收入
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Optional

import models
from enums import OrderStatus, OrderType, PaymentStatus
from events import emit
from domain.sale_order import SaleOrderDomain
from domain.inventory import InventoryDomain

from .base import Command, CommandHandler, register
from .crud_compat import (
    _d, _distribute_total_price, _generate_order_no, _log,
    get_or_create_inventory, get_product, get_sale_order,
)
from errors import BusinessError, ErrorCode
from crud.inventory_ops import sale_deduct, sale_restore
from utils import Q2


# ═══════════════════════════════════════════════════════════
# 1. CreateSaleOrder — 创建销售单
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateSaleOrder(Command):
    customer_id: Optional[int] = None
    deduct_inventory: bool = True
    has_invoice: bool = False
    payment_status: str = PaymentStatus.UNPAID
    notes: str = ""
    image_url: str = ""
    total_price: Optional[Decimal] = None
    sale_date: Optional[datetime] = None
    items: List[dict] = field(default_factory=list)


@register(CreateSaleOrder)
class CreateSaleOrderHandler(CommandHandler):
    def handle(self, cmd: CreateSaleOrder, db: Any) -> Any:
        # 1. 校验
        if not cmd.items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS, data={"order_type": "销售单"})
        product_ids = [it['product_id'] for it in cmd.items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        # 2. 生成订单号
        order_no = _generate_order_no(db, "SO")

        # 3. 创建订单头
        order = models.SaleOrder(
            account_id=cmd.account_id,
            order_no=order_no,
            customer_id=cmd.customer_id,
            order_type=OrderType.RETAIL,
            has_invoice=cmd.has_invoice,
            payment_status=cmd.payment_status,
            status=OrderStatus.PENDING,
            notes=cmd.notes,
            image_url=cmd.image_url,
            total_price=0,
            sale_date=cmd.sale_date or datetime.now(),
        )
        db.add(order)
        db.flush()

        # 4. 计算明细 + 创建行
        items_data = []
        total = Decimal('0')
        for it in cmd.items:
            product = get_product(db, cmd.account_id, it['product_id'])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            items_data.append({
                'product_id': it['product_id'],
                'quantity': it['quantity'],
                'unit_price': it['unit_price'],
                'tax_rate': it.get('tax_rate', Decimal('0.01')),
                'total_price': line_total,
            })
            total += line_total

        # 5. 自定义金额分配
        if cmd.total_price is not None:
            _distribute_total_price(items_data, cmd.total_price)

        # 6. 创建 SaleItem 行
        for it in items_data:
            item = models.SaleItem(
                order_id=order.id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                tax_rate=it['tax_rate'],
                total_price=it['total_price'],
            )
            db.add(item)

        final_total = sum(_d(it['total_price']) for it in items_data)
        order.total_price = _d(cmd.total_price) if cmd.total_price is not None else final_total.quantize(Q2)
        db.flush()

        # 7. Domain 状态机转换：pending → completed
        domain = SaleOrderDomain.from_orm(order)
        violations = domain.validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"销售单校验失败: {'; '.join(violations)}"})
        domain.transition_to(OrderStatus.COMPLETED)
        order.status = domain.status
        db.flush()

        # 8. 显式联动：扣库存
        if cmd.deduct_inventory:
            sale_deduct(db, cmd.account_id, order, operator=cmd.operator)

        # 9. 事件（仅日志）
        emit("sale_order.created", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        # 10. 操作日志
        _log(db, cmd.account_id, "create", "sale_order", order.id,
             f"创建销售单 {order_no}: {len(cmd.items)}项商品, 总价={total}", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 2. CancelSaleOrder — 取消销售单
# ═══════════════════════════════════════════════════════════

@dataclass
class CancelSaleOrder(Command):
    order_id: int = 0


@register(CancelSaleOrder)
class CancelSaleOrderHandler(CommandHandler):
    def handle(self, cmd: CancelSaleOrder, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        old_status = order.status

        # Domain 状态机校验 + 转换
        domain = SaleOrderDomain.from_orm(order)
        violations = domain.validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"销售单校验失败: {'; '.join(violations)}"})
        domain.transition_to(OrderStatus.CANCELLED)
        order.status = domain.status

        # 显式联动：回补库存
        sale_restore(db, cmd.account_id, order, operator=cmd.operator)

        # 事件（仅日志）
        emit("sale_order.cancelled", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator, old_status=old_status)

        # 操作日志
        _log(db, cmd.account_id, "update", "sale_order", cmd.order_id,
             f"取消销售单 {order.order_no}: 状态={old_status}->cancelled", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 3. RestoreSaleOrder — 恢复销售单（取消→完成）
# ═══════════════════════════════════════════════════════════

@dataclass
class RestoreSaleOrder(Command):
    order_id: int = 0


@register(RestoreSaleOrder)
class RestoreSaleOrderHandler(CommandHandler):
    def handle(self, cmd: RestoreSaleOrder, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        if order.status != OrderStatus.CANCELLED:
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": order.status, "action": "恢复"})

        old_status = order.status

        # Domain 状态机校验 + 转换
        domain = SaleOrderDomain.from_orm(order)
        violations = domain.validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"销售单校验失败: {'; '.join(violations)}"})
        domain.transition_to(OrderStatus.COMPLETED)
        order.status = domain.status

        # 显式联动：扣库存
        sale_deduct(db, cmd.account_id, order, operator=cmd.operator)

        # 事件（仅日志）
        emit("sale_order.restored", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator, old_status=old_status)

        # 操作日志
        _log(db, cmd.account_id, "update", "sale_order", cmd.order_id,
             f"恢复销售单 {order.order_no}: 状态={old_status}->completed", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 4. DeleteSaleOrder — 删除销售单
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteSaleOrder(Command):
    order_id: int = 0


@register(DeleteSaleOrder)
class DeleteSaleOrderHandler(CommandHandler):
    def handle(self, cmd: DeleteSaleOrder, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        # Domain 校验是否可删除
        domain = SaleOrderDomain.from_orm(order)
        if not domain.can_delete():
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": order.status, "action": "删除"})

        # 显式联动：回补库存
        if order.status == OrderStatus.COMPLETED:
            sale_restore(db, cmd.account_id, order, operator=cmd.operator)

        # 事件（仅日志）
        emit("sale_order.deleted", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator, old_status=order.status)

        # 操作日志
        _log(db, cmd.account_id, "delete", "sale_order", cmd.order_id,
             f"删除销售单 {order.order_no}: 状态={order.status}", operator=cmd.operator)

        # 删除
        db.delete(order)
        db.flush()
        return True


# ═══════════════════════════════════════════════════════════
# 5. UpdateSaleOrderItems — 更新销售单明细（全量替换）
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateSaleOrderItems(Command):
    order_id: int = 0
    items: List[dict] = field(default_factory=list)
    total_price: Optional[Decimal] = None


@register(UpdateSaleOrderItems)
class UpdateSaleOrderItemsHandler(CommandHandler):
    def handle(self, cmd: UpdateSaleOrderItems, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        # 商品重复校验
        if cmd.items:
            product_ids = [it['product_id'] for it in cmd.items]
            dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
            if dup_pids:
                raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        old_status = order.status

        # 记录旧行数据
        old_items = [
            {'product_id': item.product_id, 'quantity': item.quantity}
            for item in order.items
        ]

        # 删除旧行
        for item in order.items[:]:
            db.delete(item)
        db.flush()

        # 新 items 为空 → 删除整个销售单
        if len(cmd.items) == 0:
            if old_status == OrderStatus.COMPLETED:
                for item_data in old_items:
                    inv = get_or_create_inventory(db, cmd.account_id, item_data['product_id'])
                    violations = InventoryDomain.from_orm(inv).validate()
                    if violations:
                        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"库存数据校验失败: {'; '.join(violations)}"})
                    inv.quantity += item_data['quantity']
            _log(db, cmd.account_id, "delete", "sale_order", cmd.order_id,
                 f"删除销售单 {order.order_no}（商品行数归零自动删除）", operator=cmd.operator)
            db.delete(order)
            db.flush()
            return None

        # 创建新行 + 自定义金额分配
        items_data = []
        total = Decimal('0')
        for it in cmd.items:
            product = get_product(db, cmd.account_id, it['product_id'])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            items_data.append({
                'product_id': it['product_id'],
                'quantity': it['quantity'],
                'unit_price': it['unit_price'],
                'tax_rate': it.get('tax_rate', Decimal('0.01')),
                'total_price': line_total,
            })
            total += line_total

        if cmd.total_price is not None:
            _distribute_total_price(items_data, cmd.total_price)

        for it in items_data:
            new_item = models.SaleItem(
                order_id=order.id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                tax_rate=it['tax_rate'],
                total_price=it['total_price'],
            )
            db.add(new_item)

        final_total = sum(_d(it['total_price']) for it in items_data)
        order.total_price = _d(cmd.total_price) if cmd.total_price is not None else final_total.quantize(Q2)

        db.flush()

        # 显式联动：旧行回补 + 新行扣减
        if old_status == OrderStatus.COMPLETED:
            for item_data in old_items:
                inv = get_or_create_inventory(db, cmd.account_id, item_data['product_id'])
                violations = InventoryDomain.from_orm(inv).validate()
                if violations:
                    raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"库存数据校验失败: {'; '.join(violations)}"})
                inv.quantity += item_data['quantity']
        if order.status == OrderStatus.COMPLETED:
            sale_deduct(db, cmd.account_id, order, operator=cmd.operator)

        # 事件（仅日志）
        emit("sale_order.items_updated", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator)

        # 操作日志
        _log(db, cmd.account_id, "update", "sale_order", cmd.order_id,
             f"更新销售单明细 {order.order_no}", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 6. UpdateSaleOrderFields — 更新销售单普通字段
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateSaleOrderFields(Command):
    order_id: int = 0
    customer_id: Optional[int] = None
    has_invoice: Optional[bool] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


@register(UpdateSaleOrderFields)
class UpdateSaleOrderFieldsHandler(CommandHandler):
    def handle(self, cmd: UpdateSaleOrderFields, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        field_map = {
            'customer_id': cmd.customer_id,
            'has_invoice': cmd.has_invoice,
            'payment_status': cmd.payment_status,
            'notes': cmd.notes,
            'image_url': cmd.image_url,
            'status': cmd.status,
        }
        for k, v in field_map.items():
            if v is not None:
                setattr(order, k, v)

        # 事件（仅日志）
        emit("sale_order.fields_updated", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        # 操作日志
        _log(db, cmd.account_id, "update", "sale_order", cmd.order_id,
             f"更新销售单字段 {order.order_no}", operator=cmd.operator)
        db.flush()
        return order