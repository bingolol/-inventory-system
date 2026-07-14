"""参数化订单命令 — 6 个命令覆盖销售/采购全部业务操作

order_type='sale' | 'purchase' 区分销售/采购类型。
类型专有逻辑委托给 _sale.py / _purchase.py。
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from commands.base import Command, CommandHandler, register
from enums import OrderStatus, PaymentStatus
from errors import BusinessError, ErrorCode
from lineage import reads, writes, TIER_L1, TIER_L3

from ._lifecycle import OrderLifecycle
from . import _sale, _purchase


# ═══════════════════════════════════════════════════════════
# 1. CreateOrder — 创建订单
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateOrder(Command):
    order_type: str = "sale"  # "sale" | "purchase"
    # sale fields
    customer_id: Optional[int] = None
    deduct_inventory: bool = True
    payment_status: str = PaymentStatus.UNPAID
    has_invoice: bool = True  # 已废弃：架构改造后所有订单必须由发票驱动，此字段仅作向后兼容保留
    # purchase fields
    supplier_id: Optional[int] = None
    payment_method: str = "company"
    # common fields
    business_date: Optional[datetime] = None
    notes: str = ""
    image_url: str = ""
    total_price: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    items: List[dict] = field(default_factory=list)
    auto_generated_from: Optional[str] = None  # 发票驱动路径标识，CreateOrderHandler 据此放行


@register(CreateOrder)
class CreateOrderHandler(CommandHandler):
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: CreateOrder, db: Any) -> Any:
        # 架构门禁（project_memory「禁止直接使用 CreateOrder」）：
        # 销售/采购业务必须走 CreateInvoice(direction='out'/'in', sale_order_action='auto_create') 路径，
        # 由发票驱动自动生成订单，确保发票是唯一真相源、增值税口径与会计口径统一。
        # 仅允许发票驱动路径（auto_generated_from 非空）通过；直接 CreateOrder 抛错。
        if not cmd.auto_generated_from:
            direction = 'out' if cmd.order_type == 'sale' else 'in'
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(
                    f"禁止直接创建{cmd.order_type}订单：系统只允许开票订单录入。"
                    f"请通过 POST /api/invoices（direction='{direction}'，"
                    f"sale_order_action='auto_create' / purchase_order_action='auto_create'）创建发票，由发票自动生成订单。"
                ),
                ai_instruction=(
                    f"STOP_RETRYING. CreateOrder 直接调用已被禁用。"
                    f"请改用 CreateInvoice(direction='{direction}', "
                    f"{'sale_order_action' if cmd.order_type == 'sale' else 'purchase_order_action'}='auto_create')。"
                ),
            )
        if cmd.order_type == "sale":
            return OrderLifecycle.create_sale_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                items=cmd.items, sale_date=cmd.business_date,
                customer_id=cmd.customer_id, total_price=cmd.total_price,
                tax_amount=cmd.tax_amount, has_invoice=cmd.has_invoice,
                notes=cmd.notes, image_url=cmd.image_url,
                payment_status=cmd.payment_status,
                deduct_inventory=cmd.deduct_inventory,
                auto_generated_from=cmd.auto_generated_from,
            )
        elif cmd.order_type == "purchase":
            return OrderLifecycle.create_purchase_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                items=cmd.items, purchase_date=cmd.business_date,
                supplier_id=cmd.supplier_id, total_price=cmd.total_price,
                tax_amount=cmd.tax_amount, payment_method=cmd.payment_method,
                notes=cmd.notes, image_url=cmd.image_url,
                auto_generated_from=cmd.auto_generated_from,
            )
        else:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message=f"未知订单类型: {cmd.order_type}")


# ═══════════════════════════════════════════════════════════
# 2. CancelOrder — 取消订单
# ═══════════════════════════════════════════════════════════

@dataclass
class CancelOrder(Command):
    order_type: str = "sale"
    order_id: int = 0


@register(CancelOrder)
class CancelOrderHandler(CommandHandler):
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: CancelOrder, db: Any) -> Any:
        if cmd.order_type == "sale":
            return OrderLifecycle.cancel_or_delete_sale_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id, delete=False,
            )
        elif cmd.order_type == "purchase":
            return OrderLifecycle.cancel_or_delete_purchase_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id, delete=False,
            )
        else:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message=f"未知订单类型: {cmd.order_type}")


# ═══════════════════════════════════════════════════════════
# 3. ReturnOrder — 订单退货（部分冲红，保留原单）
# ═══════════════════════════════════════════════════════════

@dataclass
class ReturnOrder(Command):
    order_type: str = "sale"
    order_id: int = 0
    return_date: str = ""
    reason: str = ""
    items: List[dict] = field(default_factory=list)


@register(ReturnOrder)
class ReturnOrderHandler(CommandHandler):
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: ReturnOrder, db: Any) -> Any:
        if cmd.order_type == "sale":
            return _sale.return_sale_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id, return_date=cmd.return_date,
                reason=cmd.reason, items=cmd.items,
            )
        elif cmd.order_type == "purchase":
            return _purchase.return_purchase_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id, return_date=cmd.return_date,
                reason=cmd.reason, items=cmd.items,
            )
        else:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message=f"未知订单类型: {cmd.order_type}")


# ═══════════════════════════════════════════════════════════
# 4. DeleteOrder — 删除订单
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteOrder(Command):
    order_type: str = "sale"
    order_id: int = 0


@register(DeleteOrder)
class DeleteOrderHandler(CommandHandler):
    def handle(self, cmd: DeleteOrder, db: Any) -> Any:
        if cmd.order_type == "sale":
            from domain.sale_order import SaleOrderDomain
            order = db.query(models.SaleOrder).filter(
                models.SaleOrder.id == cmd.order_id,
                models.SaleOrder.account_id == cmd.account_id,
            ).first()
            if not order:
                raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                                    data={"order_type": "销售单", "order_id": cmd.order_id})
            domain = SaleOrderDomain.from_orm(order)
            if not domain.can_delete():
                raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE,
                                    data={"status": order.status, "action": "删除"})
            return OrderLifecycle.cancel_or_delete_sale_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id, delete=True,
            )
        elif cmd.order_type == "purchase":
            return OrderLifecycle.cancel_or_delete_purchase_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id, delete=True,
            )
        else:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message=f"未知订单类型: {cmd.order_type}")


# ═══════════════════════════════════════════════════════════
# 5. UpdateOrderItems — 更新订单明细（全量替换）
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateOrderItems(Command):
    order_type: str = "sale"
    order_id: int = 0
    items: List[dict] = field(default_factory=list)
    total_price: Optional[Decimal] = None
    # purchase-specific extra fields
    supplier_id: Optional[int] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@register(UpdateOrderItems)
class UpdateOrderItemsHandler(CommandHandler):
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @writes("SaleItem.quantity_l1", tier=TIER_L1, source="external")
    @writes("SaleItem.unit_price_l1", tier=TIER_L1, source="external")
    @writes("SaleItem.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("SaleItem.total_price_l1", tier=TIER_L1, source="external")
    @writes("SaleOrder.total_price_l1", tier=TIER_L1, source="external")
    @writes("SaleOrder.tax_amount_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.quantity_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.unit_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.total_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseOrder.total_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseOrder.tax_amount_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: UpdateOrderItems, db: Any) -> Any:
        if cmd.order_type == "sale":
            return _sale.update_sale_items(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id, items=cmd.items, total_price=cmd.total_price,
            )
        elif cmd.order_type == "purchase":
            return _purchase.update_purchase_items(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id, items=cmd.items,
                supplier_id=cmd.supplier_id, payment_method=cmd.payment_method,
                notes=cmd.notes, status=cmd.status,
            )
        else:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message=f"未知订单类型: {cmd.order_type}")


# ═══════════════════════════════════════════════════════════
# 6. UpdateOrderFields — 更新订单普通字段
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateOrderFields(Command):
    order_type: str = "sale"
    order_id: int = 0
    # sale fields
    customer_id: Optional[int] = None
    payment_status: Optional[str] = None
    # purchase fields
    supplier_id: Optional[int] = None
    payment_method: Optional[str] = None
    # common fields
    notes: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


@register(UpdateOrderFields)
class UpdateOrderFieldsHandler(CommandHandler):
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: UpdateOrderFields, db: Any) -> Any:
        if cmd.order_type == "sale":
            return _sale.update_sale_fields(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id,
                customer_id=cmd.customer_id, payment_status=cmd.payment_status,
                notes=cmd.notes, image_url=cmd.image_url, status=cmd.status,
            )
        elif cmd.order_type == "purchase":
            return _purchase.update_purchase_fields(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id,
                supplier_id=cmd.supplier_id, payment_method=cmd.payment_method,
                payment_status=cmd.payment_status,
                notes=cmd.notes, image_url=cmd.image_url, status=cmd.status,
            )
        else:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message=f"未知订单类型: {cmd.order_type}")


# ═══════════════════════════════════════════════════════════
# 7. RestoreOrder — 恢复订单（取消→完成）
# ═══════════════════════════════════════════════════════════

@dataclass
class RestoreOrder(Command):
    order_type: str = "sale"
    order_id: int = 0


@register(RestoreOrder)
class RestoreOrderHandler(CommandHandler):
    def handle(self, cmd: RestoreOrder, db: Any) -> Any:
        if cmd.order_type == "sale":
            return _sale.restore_sale_order(
                db=db, account_id=cmd.account_id, operator=cmd.operator,
                order_id=cmd.order_id,
            )
        else:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message=f"订单类型不支持恢复: {cmd.order_type}")


# 运行时导入避免循环
import models  # noqa: E402
