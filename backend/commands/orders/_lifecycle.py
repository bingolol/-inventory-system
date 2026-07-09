"""订单生命周期编排对象

集中销售单/采购单的创建、取消、删除等重复编排逻辑，
通过 OrderIntake seam 共享创建流程，类型专有行为由 adapter 注入。
"""

from typing import Any

import models
from crud.orders import get_purchase_order, get_sale_order
from enums import OrderStatus
from errors import BusinessError, ErrorCode
from events import emit
from lineage import reads, writes, TIER_L1, TIER_L2, TIER_L3

from ._intake import OrderIntake, SaleIntakeAdapter, PurchaseIntakeAdapter


class OrderLifecycle:
    """销售/采购订单生命周期编排

    所有方法均假设已处于有效的 db session/事务上下文中，
    调用方负责 commit/rollback 边界。
    """

    _sale_intake = OrderIntake(SaleIntakeAdapter())
    _purchase_intake = OrderIntake(PurchaseIntakeAdapter())

    # ═══════════════════════════════════════════════════════════
    # 销售单创建
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @writes("SaleOrder.total_price_l1", tier=TIER_L1, source="external")
    @writes("SaleOrder.tax_amount_l1", tier=TIER_L1, source="external")
    @writes("SaleOrder.has_invoice_l1", tier=TIER_L1, source="external")
    @writes("SaleOrder.sale_date_l1", tier=TIER_L1, source="external")
    @writes("SaleItem.quantity_l1", tier=TIER_L1, source="external")
    @writes("SaleItem.unit_price_l1", tier=TIER_L1, source="external")
    @writes("SaleItem.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("SaleItem.total_price_l1", tier=TIER_L1, source="external")
    @writes("SaleItem.unit_cost_l2", tier=TIER_L2, source="engine")
    def create_sale_order(
        db: Any,
        account_id: int,
        operator: str,
        items,
        sale_date: Any,
        customer_id: int = None,
        total_price: Any = None,
        tax_amount: Any = None,
        has_invoice: bool = True,
        notes: str = "",
        image_url: str = "",
        payment_status: str = "unpaid",
        order_no: str = None,
        auto_generated_from: str = None,
        deduct_inventory: bool = True,
    ) -> models.SaleOrder:
        """创建销售单并触发库存出库、销售凭证生成事件。"""
        return OrderLifecycle._sale_intake.create_order(
            db=db, account_id=account_id, operator=operator,
            items=items, business_date=sale_date, partner_id=customer_id,
            total_price=total_price, tax_amount=tax_amount,
            has_invoice=has_invoice, notes=notes, image_url=image_url,
            payment_status=payment_status, order_no=order_no,
            auto_generated_from=auto_generated_from,
            deduct_inventory=deduct_inventory,
        )

    # ═══════════════════════════════════════════════════════════
    # 采购单创建
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    @writes("PurchaseOrder.total_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseOrder.tax_amount_l1", tier=TIER_L1, source="external")
    @writes("PurchaseOrder.purchase_date_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.quantity_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.unit_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.total_price_l1", tier=TIER_L1, source="external")
    def create_purchase_order(
        db: Any,
        account_id: int,
        operator: str,
        items,
        purchase_date: Any,
        supplier_id: int = None,
        total_price: Any = None,
        tax_amount: Any = None,
        notes: str = "",
        image_url: str = "",
        payment_method: str = "company",
        order_no: str = None,
        auto_generated_from: str = None,
    ) -> models.PurchaseOrder:
        """创建采购单并触发库存入库、采购凭证生成事件。"""
        return OrderLifecycle._purchase_intake.create_order(
            db=db, account_id=account_id, operator=operator,
            items=items, business_date=purchase_date, partner_id=supplier_id,
            total_price=total_price, tax_amount=tax_amount,
            notes=notes, image_url=image_url,
            payment_method=payment_method, order_no=order_no,
            auto_generated_from=auto_generated_from,
        )

    # ═══════════════════════════════════════════════════════════
    # 销售单取消 / 删除
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @writes("SaleOrder.status", tier=TIER_L1, source="external")
    @writes("SaleItem.unit_cost_l2", tier=TIER_L2, source="engine")
    def cancel_or_delete_sale_order(
        db: Any,
        account_id: int,
        operator: str,
        order_id: int,
        delete: bool = False,
    ) -> Any:
        """取消或删除销售单。"""
        order = get_sale_order(db, account_id, order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                                data={"order_type": "销售单", "order_id": order_id})

        old_status = order.status

        if not delete:
            from domain.sale_order import SaleOrderDomain
            domain = SaleOrderDomain.from_orm(order)
            violations = domain.validate()
            if violations:
                raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                    data={"details": f"销售单校验失败: {'; '.join(violations)}"})
            domain.transition_to(OrderStatus.CANCELLED)
            order.status = domain.status

        event_name = "sale_order.deleted" if delete else "sale_order.cancelled"
        log_action = "delete" if delete else "update"
        log_detail = (
            f"删除销售单 {order.order_no}: 状态={old_status}"
            if delete
            else f"取消销售单 {order.order_no}: 状态={old_status}->cancelled"
        )
        emit(event_name, db=db, account_id=account_id, order=order, operator=operator,
             old_status=old_status, log_action=log_action, log_detail=log_detail)

        if delete:
            db.delete(order)
        db.flush()
        return True if delete else order

    # ═══════════════════════════════════════════════════════════
    # 采购单取消 / 删除
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @writes("PurchaseOrder.status", tier=TIER_L1, source="external")
    def cancel_or_delete_purchase_order(
        db: Any,
        account_id: int,
        operator: str,
        order_id: int,
        delete: bool = False,
    ) -> Any:
        """取消或删除采购单。"""
        order = get_purchase_order(db, account_id, order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                                data={"order_type": "采购单", "order_id": order_id})

        if not delete and order.status == OrderStatus.CANCELLED:
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE,
                                data={"status": order.status, "action": "取消"})

        old_status = order.status
        if not delete:
            order.status = OrderStatus.CANCELLED

        event_name = "purchase_order.deleted" if delete else "purchase_order.cancelled"
        log_detail = (
            f"删除采购单 {order.order_no}: 状态={old_status}"
            if delete
            else f"取消采购单 {order.order_no}: 状态={old_status}->cancelled"
        )
        emit(event_name, db=db, account_id=account_id, order=order, operator=operator,
             old_status=old_status, log_action="delete" if delete else "update", log_detail=log_detail)

        if delete:
            db.delete(order)
        db.flush()
        return True if delete else order
