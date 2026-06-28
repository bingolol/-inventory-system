"""采购单 Command + Handler — 5个命令覆盖采购单全部业务操作

v7 改造后：移除项目模块
  采购单不再关联项目，不再触发项目汇总重算
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

import models
from enums import OrderStatus, OrderType
from events import emit

from .base import Command, CommandHandler, register
from .crud_compat import (
    _d, _generate_order_no, _log,
    get_or_create_inventory, get_product, get_purchase_order,
)
from crud.reversal import reverse_payments
from errors import BusinessError, ErrorCode
from utils import Q2
from engine_inventory import InventoryEngine
from engine_finance import FinanceEngine


# ═══════════════════════════════════════════════════════════
# 1. CreatePurchaseOrder — 创建采购单
# ═══════════════════════════════════════════════════════════

@dataclass
class CreatePurchaseOrder(Command):
    supplier_id: Optional[int] = None
    purchase_date: Optional[datetime] = None
    payment_method: str = "company"
    notes: str = ""
    image_url: str = ""
    items: List[dict] = field(default_factory=list)


@register(CreatePurchaseOrder)
class CreatePurchaseOrderHandler(CommandHandler):
    def handle(self, cmd: CreatePurchaseOrder, db: Any) -> Any:
        # 1. 校验
        if not cmd.items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS, data={"order_type": "采购单"})
        product_ids = [it['product_id'] for it in cmd.items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        # 2. 生成订单号
        purchase_dt = datetime.fromisoformat(cmd.purchase_date) if isinstance(cmd.purchase_date, str) else (cmd.purchase_date or datetime.now())
        order_no = _generate_order_no(db, "PO", purchase_dt)

        # 3. 创建订单头
        order = models.PurchaseOrder(
            account_id=cmd.account_id,
            order_no=order_no,
            supplier_id=cmd.supplier_id,
            purchase_date=datetime.fromisoformat(cmd.purchase_date) if isinstance(cmd.purchase_date, str) else (cmd.purchase_date or datetime.now()),
            order_type=OrderType.RETAIL,
            payment_method=cmd.payment_method,
            status=OrderStatus.COMPLETED,
            notes=cmd.notes,
            image_url=cmd.image_url,
            total_price=0,
        )
        db.add(order)
        db.flush()

        # 4. 创建明细行 + InventoryEngine 入库 + 收集价税数据
        total = Decimal('0')
        calculated_data = []
        for it in cmd.items:
            product = get_product(db, cmd.account_id, it['product_id'])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            item = models.PurchaseItem(
                order_id=order.id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                tax_rate=it.get('tax_rate', Decimal('0.13')),
                total_price=line_total,
            )
            db.add(item)
            if product.track_inventory:
                calc = InventoryEngine(db).inbound(
                    account_id=cmd.account_id,
                    product_id=it['product_id'],
                    quantity=it['quantity'],
                    unit_price=it['unit_price'],
                    source_type="purchase_order",
                    source_id=order.id,
                    tax_rate=it.get('tax_rate'),
                    operator=cmd.operator,
                )
                calculated_data.append(calc)
            total += line_total

        order.total_price = total.quantize(Q2)
        db.flush()

        # 5. 生成会计凭证
        FinanceEngine(db, cmd.account_id).record_purchase(order, calculated_data or None)

        # 6. 事件（仅日志）
        emit("purchase_order.created", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        # 7. 操作日志
        _log(db, cmd.account_id, "create", "purchase_order", order.id,
             f"创建采购单 {order_no}: {len(cmd.items)}项商品, 总价={total}", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 2. CancelPurchaseOrder — 取消采购单
# ═══════════════════════════════════════════════════════════

@dataclass
class CancelPurchaseOrder(Command):
    order_id: int = 0


@register(CancelPurchaseOrder)
class CancelPurchaseOrderHandler(CommandHandler):
    def handle(self, cmd: CancelPurchaseOrder, db: Any) -> Any:
        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": cmd.order_id})
        if order.status == OrderStatus.CANCELLED:
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": order.status, "action": "取消"})

        old_status = order.status

        # 状态变更
        order.status = OrderStatus.CANCELLED

        # 已完成→取消：InventoryEngine 红冲 + FinanceEngine 冲红凭证
        if old_status == OrderStatus.COMPLETED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory:
                    InventoryEngine(db).reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        unit_cost=Decimal("0"),
                        source_type="purchase_order",
                        source_id=order.id,
                        operator=cmd.operator,
                    )
            FinanceEngine(db, cmd.account_id).reverse_purchase(order.id)

        # 冲销付款记录 + 银行流水
        reverse_payments(db, cmd.account_id, cmd.order_id)

        emit("purchase_order.updated", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        _log(db, cmd.account_id, "update", "purchase_order", cmd.order_id,
             f"取消采购单 {order.order_no}: 状态={old_status}->cancelled", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 3. DeletePurchaseOrder — 删除采购单
# ═══════════════════════════════════════════════════════════

@dataclass
class DeletePurchaseOrder(Command):
    order_id: int = 0


@register(DeletePurchaseOrder)
class DeletePurchaseOrderHandler(CommandHandler):
    def handle(self, cmd: DeletePurchaseOrder, db: Any) -> Any:
        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": cmd.order_id})

        # 已完成：InventoryEngine 红冲 + FinanceEngine 冲红凭证
        if order.status == OrderStatus.COMPLETED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory:
                    InventoryEngine(db).reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        unit_cost=Decimal("0"),
                        source_type="purchase_order",
                        source_id=order.id,
                        operator=cmd.operator,
                    )
            FinanceEngine(db, cmd.account_id).reverse_purchase(order.id)

        # 冲销付款记录 + 银行流水
        reverse_payments(db, cmd.account_id, cmd.order_id)

        _log(db, cmd.account_id, "delete", "purchase_order", cmd.order_id,
             f"删除采购单 {order.order_no}: 状态={order.status}", operator=cmd.operator)

        emit("purchase_order.deleted", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        db.delete(order)
        db.flush()
        return True


# ═══════════════════════════════════════════════════════════
# 4. UpdatePurchaseOrderItems — 更新采购单明细（全量替换）
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdatePurchaseOrderItems(Command):
    order_id: int = 0
    items: List[dict] = field(default_factory=list)
    supplier_id: Optional[int] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@register(UpdatePurchaseOrderItems)
class UpdatePurchaseOrderItemsHandler(CommandHandler):
    def handle(self, cmd: UpdatePurchaseOrderItems, db: Any) -> Any:
        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": cmd.order_id})

        if cmd.items:
            product_ids = [it['product_id'] for it in cmd.items]
            dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
            if dup_pids:
                raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        old_status = order.status

        # 旧行库存回补
        if old_status == OrderStatus.COMPLETED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory:
                    inv = get_or_create_inventory(db, cmd.account_id, item.product_id)
                    inv.quantity -= item.quantity

        # 删除旧行
        for item in order.items[:]:
            db.delete(item)
        db.flush()

        # 新 items 为空 → 删除整个采购单
        if len(cmd.items) == 0:
            _log(db, cmd.account_id, "delete", "purchase_order", cmd.order_id,
                 f"删除采购单 {order.order_no}（商品行数归零自动删除）", operator=cmd.operator)
            db.delete(order)
            db.flush()
            return None

        # 更新普通字段
        field_map = {
            'supplier_id': cmd.supplier_id,
            'payment_method': cmd.payment_method,
            'notes': cmd.notes,
            'status': cmd.status,
        }
        for k, v in field_map.items():
            if v is not None:
                setattr(order, k, v)
        new_status = order.status

        # 创建新行 + 库存处理
        total = Decimal('0')
        for it in cmd.items:
            product = get_product(db, cmd.account_id, it['product_id'])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            new_item = models.PurchaseItem(
                order_id=order.id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                tax_rate=it.get('tax_rate', Decimal('0.13')),
                total_price=line_total,
            )
            db.add(new_item)
            if new_status == OrderStatus.COMPLETED and product.track_inventory:
                inv = get_or_create_inventory(db, cmd.account_id, it['product_id'])
                inv.quantity += it['quantity']
            total += line_total

        order.total_price = total.quantize(Q2)

        emit("purchase_order.updated", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        _log(db, cmd.account_id, "update", "purchase_order", cmd.order_id,
             f"更新采购单明细 {order.order_no}: 状态={old_status}->{new_status}", operator=cmd.operator)
        db.flush()
        db.refresh(order)
        return order


# ═══════════════════════════════════════════════════════════
# 5. UpdatePurchaseOrderFields — 更新采购单普通字段
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdatePurchaseOrderFields(Command):
    order_id: int = 0
    supplier_id: Optional[int] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


@register(UpdatePurchaseOrderFields)
class UpdatePurchaseOrderFieldsHandler(CommandHandler):
    def handle(self, cmd: UpdatePurchaseOrderFields, db: Any) -> Any:
        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": cmd.order_id})

        old_status = order.status

        field_map = {
            'supplier_id': cmd.supplier_id,
            'payment_method': cmd.payment_method,
            'payment_status': cmd.payment_status,
            'notes': cmd.notes,
            'image_url': cmd.image_url,
            'status': cmd.status,
        }
        for k, v in field_map.items():
            if v is not None:
                setattr(order, k, v)

        new_status = order.status

        # 状态切换库存处理
        if old_status == OrderStatus.COMPLETED and new_status == OrderStatus.CANCELLED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory:
                    inv = get_or_create_inventory(db, cmd.account_id, item.product_id)
                    inv.quantity -= item.quantity
        elif old_status == OrderStatus.CANCELLED and new_status == OrderStatus.COMPLETED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory:
                    inv = get_or_create_inventory(db, cmd.account_id, item.product_id)
                    inv.quantity += item.quantity

        emit("purchase_order.updated", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        _log(db, cmd.account_id, "update", "purchase_order", cmd.order_id,
             f"更新采购单字段 {order.order_no}: 状态={old_status}->{new_status}", operator=cmd.operator)
        db.flush()
        return order