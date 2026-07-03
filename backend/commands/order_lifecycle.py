"""订单生命周期编排对象

集中销售单/采购单的创建、取消、删除等重复编排逻辑，
消除 CreateSaleOrderHandler 与 _auto_generate_sale_order、
CreatePurchaseOrderHandler 与 _auto_generate_purchase_order、
Cancel/Delete Handler 之间的代码复制。
"""

from calendar import monthrange
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

import models
from crud.base import gen_order_no, log_op
from crud.orders import get_purchase_order, get_sale_order
from crud.products import get_product
from crud.reversal import reverse_payments, reverse_receipts
from domain.sale_order import SaleOrderDomain
from engine_finance import FinanceEngine
from engine_inventory import InventoryEngine
from enums import OrderStatus, OrderType, PaymentMethod, PaymentStatus
from errors import BusinessError, ErrorCode
from events import emit
from rules import enforce_rules
from utils import _d, Q2
from lineage import reads, writes, TIER_L1, TIER_L2, TIER_L3


class OrderLifecycle:
    """销售/采购订单生命周期编排

    所有方法均假设已处于有效的 db session/事务上下文中，
    调用方负责 commit/rollback 边界。
    """

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
        items: List[dict],
        sale_date: Any,
        customer_id: Optional[int] = None,
        total_price: Optional[Any] = None,
        tax_amount: Optional[Any] = None,
        has_invoice: bool = True,
        notes: str = "",
        image_url: str = "",
        payment_status: str = PaymentStatus.UNPAID,
        order_no: Optional[str] = None,
        auto_generated_from: Optional[str] = None,
        deduct_inventory: bool = True,
    ) -> models.SaleOrder:
        """创建销售单并联动库存出库、生成销售凭证。

        供 CreateSaleOrderHandler 与发票自动生单共用。
        """
        if not items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS, data={"order_type": "销售单"})

        product_ids = [it["product_id"] for it in items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        if not sale_date:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="销售日期不能为空，请提供业务发生日期",
                ai_instruction="STOP_RETRYING. sale_date 字段必填，请补充销售业务日期（如 2025-06-28）。"
            )

        if isinstance(sale_date, str):
            sale_dt = datetime.fromisoformat(sale_date)
        elif isinstance(sale_date, datetime):
            sale_dt = sale_date
        elif hasattr(sale_date, "year"):
            # date 对象兼容
            sale_dt = datetime(sale_date.year, sale_date.month, sale_date.day)
        else:
            sale_dt = sale_date
        if order_no is None:
            order_no = gen_order_no(db, "SO", sale_dt)

        order = models.SaleOrder(
            account_id=account_id,
            order_no=order_no,
            customer_id=customer_id,
            order_type=OrderType.RETAIL,
            payment_status=payment_status,
            has_invoice_l1=has_invoice,
            status=OrderStatus.PENDING,
            notes=notes,
            image_url=image_url,
            total_price_l1=0,
            tax_amount_l1=_d(tax_amount) if tax_amount is not None else Decimal("0"),
            sale_date_l1=sale_dt,
        )
        db.add(order)
        db.flush()

        # 计算明细并创建 SaleItem
        items_data = []
        total = Decimal("0")
        for it in items:
            product = get_product(db, account_id, it["product_id"])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it["product_id"]})
            line_total = (Decimal(str(it["quantity"])) * _d(it["unit_price"])).quantize(Q2)
            items_data.append({
                "product_id": it["product_id"],
                "quantity": it["quantity"],
                "unit_price": it["unit_price"],
                "tax_rate": it.get("tax_rate", Decimal("0.01")),
                "total_price": line_total,
            })
            total += line_total

        if total_price is not None:
            from crud.orders import _distribute_total_price
            _distribute_total_price(items_data, total_price)

        for it in items_data:
            item = models.SaleItem(
                order_id=order.id,
                product_id=it["product_id"],
                quantity_l1=it["quantity"],
                unit_price_l1=it["unit_price"],
                tax_rate_l1=it["tax_rate"],
                total_price_l1=it["total_price"],
            )
            db.add(item)

        final_total = sum(_d(it["total_price"]) for it in items_data)
        order.total_price_l1 = _d(total_price) if total_price is not None else final_total.quantize(Q2)
        db.flush()

        # Domain 状态机转换
        domain = SaleOrderDomain.from_orm(order)
        violations = domain.validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"销售单校验失败: {'; '.join(violations)}"})
        domain.transition_to(OrderStatus.COMPLETED)
        order.status = domain.status
        db.flush()

        # 库存出库 + 销售凭证
        if deduct_inventory:
            for item in order.items:
                product = get_product(db, account_id, item.product_id)
                if product.track_inventory_l3:
                    unit_cost = InventoryEngine(db).outbound(
                        account_id=account_id,
                        product_id=item.product_id,
                        quantity=item.quantity_l1,
                        source_type="sale_order",
                        source_id=order.id,
                        operator=operator,
                    )
                    item.set_calculated_cost(unit_cost)
                else:
                    item.set_calculated_cost(Decimal("0"))
        else:
            for item in order.items:
                item.set_calculated_cost(Decimal("0"))
        FinanceEngine(db, account_id).record_sale(order)

        # AS-04 权责发生制校验：期间有销售订单时总账 6001 应有贷方发生额
        # 注意：必须传 date 对象（非 datetime），避免 SQLite 字符串比较 Date vs Datetime 失败
        s_date = sale_dt.date() if isinstance(sale_dt, datetime) else sale_dt
        enforce_rules(db, ["AS-04"], {
            "account_id": account_id,
            "start_date": s_date.replace(day=1),
            "end_date": s_date.replace(day=monthrange(s_date.year, s_date.month)[1]),
        })

        log_detail = (
            f"创建销售单 {order_no}: {len(items)}项商品, 总价={order.total_price_l1}"
            if not auto_generated_from
            else f"发票 {auto_generated_from} 自动生成销售单 {order_no}: 价税合计={order.total_price_l1}, 税额={order.tax_amount_l1}"
        )
        emit("sale_order.created", db=db, account_id=account_id, order=order, operator=operator,
             log_action="create", log_detail=log_detail)
        db.flush()
        return order

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
        items: List[dict],
        purchase_date: Any,
        supplier_id: Optional[int] = None,
        total_price: Optional[Any] = None,
        tax_amount: Optional[Any] = None,
        notes: str = "",
        image_url: str = "",
        payment_method: str = PaymentMethod.COMPANY,
        order_no: Optional[str] = None,
        auto_generated_from: Optional[str] = None,
    ) -> models.PurchaseOrder:
        """创建采购单并联动库存入库、生成采购凭证。

        供 CreatePurchaseOrderHandler 与发票自动生单共用。
        """
        if not items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS, data={"order_type": "采购单"})

        product_ids = [it["product_id"] for it in items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        if not purchase_date:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="采购日期不能为空，请提供业务发生日期",
                ai_instruction="STOP_RETRYING. purchase_date 字段必填，请补充采购业务日期（如 2025-06-28）。"
            )

        if isinstance(purchase_date, str):
            purchase_dt = datetime.fromisoformat(purchase_date)
        elif isinstance(purchase_date, datetime):
            purchase_dt = purchase_date
        elif hasattr(purchase_date, "year"):
            purchase_dt = datetime(purchase_date.year, purchase_date.month, purchase_date.day)
        else:
            purchase_dt = purchase_date
        if order_no is None:
            order_no = gen_order_no(db, "PO", purchase_dt)

        order = models.PurchaseOrder(
            account_id=account_id,
            order_no=order_no,
            supplier_id=supplier_id,
            purchase_date_l1=purchase_dt,
            order_type=OrderType.RETAIL,
            payment_method=payment_method,
            status=OrderStatus.COMPLETED,
            notes=notes,
            image_url=image_url,
            total_price_l1=0,
            tax_amount_l1=_d(tax_amount) if tax_amount is not None else Decimal("0"),
        )
        db.add(order)
        db.flush()

        account = db.query(models.Account).get(account_id)
        default_tax_rate = FinanceEngine._vat_rate(account)
        total = Decimal("0")
        calculated_data = []
        for it in items:
            product = get_product(db, account_id, it["product_id"])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it["product_id"]})
            line_total = (Decimal(str(it["quantity"])) * _d(it["unit_price"])).quantize(Q2)
            item = models.PurchaseItem(
                order_id=order.id,
                product_id=it["product_id"],
                quantity_l1=it["quantity"],
                unit_price_l1=it["unit_price"],
                tax_rate_l1=it.get("tax_rate", default_tax_rate),
                total_price_l1=line_total,
            )
            db.add(item)
            if product.track_inventory_l3:
                calc = InventoryEngine(db).inbound(
                    account_id=account_id,
                    product_id=it["product_id"],
                    quantity=it["quantity"],
                    unit_price=it["unit_price"],
                    source_type="purchase_order",
                    source_id=order.id,
                    tax_rate=it.get("tax_rate"),
                    operator=operator,
                )
                calculated_data.append(calc)
            total += line_total

        order.total_price_l1 = _d(total_price) if total_price is not None else total.quantize(Q2)
        db.flush()

        FinanceEngine(db, account_id).record_purchase(order, calculated_data or None)

        log_detail = (
            f"创建采购单 {order_no}: {len(items)}项商品, 总价={total}"
            if not auto_generated_from
            else f"发票 {auto_generated_from} 自动生成采购单 {order_no}: 价税合计={order.total_price_l1}, 税额={order.tax_amount_l1}"
        )
        emit("purchase_order.created", db=db, account_id=account_id, order=order, operator=operator,
             log_action="create", log_detail=log_detail)
        db.flush()
        return order

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
        """取消或删除销售单。

        取消：状态机校验 → 库存回退 → 收款冲销 → 销售凭证冲红 → 事件
        删除：同上 → db.delete(order)
        """
        order = get_sale_order(db, account_id, order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                                data={"order_type": "销售单", "order_id": order_id})

        old_status = order.status

        if not delete:
            domain = SaleOrderDomain.from_orm(order)
            violations = domain.validate()
            if violations:
                raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                    data={"details": f"销售单校验失败: {'; '.join(violations)}"})
            domain.transition_to(OrderStatus.CANCELLED)
            order.status = domain.status

        # 库存回退
        if old_status == OrderStatus.COMPLETED:
            eng = InventoryEngine(db)
            for item in order.items:
                eng.reverse(
                    account_id=account_id,
                    product_id=item.product_id,
                    quantity=item.quantity_l1,
                    unit_cost=Decimal(str(item.unit_cost_l2)) if item.unit_cost_l2 else Decimal("0"),
                    source_type="sale_order",
                    source_id=order.id,
                    operator=operator,
                )

        # 收款冲销 + 银行流水
        reverse_receipts(db, account_id, order_id)

        # 销售凭证冲红
        if old_status == OrderStatus.COMPLETED:
            FinanceEngine(db, account_id).reverse_sale(order.id)

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
        """取消或删除采购单。

        取消/删除：状态变更 → 库存回退 → 付款冲销 → 采购凭证冲红 → 事件 → 可选删除
        """
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

        if old_status == OrderStatus.COMPLETED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory_l3:
                    InventoryEngine(db).reverse(
                        account_id=account_id,
                        product_id=item.product_id,
                        quantity=item.quantity_l1,
                        unit_cost=Decimal("0"),
                        source_type="purchase_order",
                        source_id=order.id,
                        operator=operator,
                    )
            FinanceEngine(db, account_id).reverse_purchase(order.id)

        reverse_payments(db, account_id, order_id)

        event_name = "purchase_order.deleted" if delete else "purchase_order.updated"
        log_detail = (
            f"删除采购单 {order.order_no}: 状态={old_status}"
            if delete
            else f"取消采购单 {order.order_no}: 状态={old_status}->cancelled"
        )
        emit(event_name, db=db, account_id=account_id, order=order, operator=operator,
             log_action="delete" if delete else "update", log_detail=log_detail)

        if delete:
            db.delete(order)
        db.flush()
        return True if delete else order
