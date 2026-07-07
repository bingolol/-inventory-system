"""销售单领域规则/校验 — 被 _order.py 的参数化命令调用"""

import time
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

import models
from enums import OrderStatus, InvoiceDirection, CertificationStatus
from events import emit
from domain.sale_order import SaleOrderDomain
from commands.base import Command, CommandHandler
from crud.base import gen_order_no as _generate_order_no
from crud.products import get_product
from crud.orders import get_sale_order, _distribute_total_price
from utils import _d, Q2
from utils.price import without_tax_from
from errors import BusinessError, ErrorCode
from engine_inventory import InventoryEngine
from engine_finance import FinanceEngine
from lineage import reads, writes, TIER_L1, TIER_L2, TIER_L3
from policy.vat_facts import VAT_SMALL_SCALE_REDUCED_RATE




def validate_sale_items(db, account_id, items):
    """校验销售单商品 — 提取自 CreateSaleOrderHandler / UpdateSaleOrderItemsHandler"""
    product_ids = [it['product_id'] for it in items]
    dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
    if dup_pids:
        raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})
    for it in items:
        product = get_product(db, account_id, it['product_id'])
        if not product:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})


def return_sale_order(db, account_id, operator, order_id, return_date, reason, items):
    """销售退货 — 提取自 ReturnSaleOrderHandler"""
    from finance_integration import post_journal
    StockMove = models.StockMove

    order = get_sale_order(db, account_id, order_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                            data={"order_type": "销售单", "order_id": order_id})
    if order.status != OrderStatus.COMPLETED:
        raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE,
                            data={"status": order.status, "action": "退货"})

    if not return_date:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                            message="退货日期不能为空，请提供业务发生日期",
                            ai_instruction="STOP_RETRYING. return_date 字段必填。")
    if not items:
        raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS,
                            data={"order_type": "销售退货单"})

    original_qty_map = {item.product_id: item.quantity_l1 for item in order.items}
    for ret in items:
        pid = ret['product_id']
        if pid not in original_qty_map:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND,
                                data={"product_id": pid, "details": "商品不在原销售单中"})
        if ret['quantity'] > original_qty_map[pid]:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"退货数量 {ret['quantity']} 超过原销售数量 {original_qty_map[pid]}",
                ai_instruction=f"STOP_RETRYING. 商品 ID={pid} 原销售 {original_qty_map[pid]} 件，退货不能超过此数量。"
            )

    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    taxpayer_type = account.taxpayer_type_l3 if account else "general"

    total_with_tax_ret = Decimal("0")
    total_without_tax_ret = Decimal("0")
    tax_amount_ret = Decimal("0")
    cost_return = Decimal("0")
    eng = InventoryEngine(db)
    return_id = int(time.time() * 1000)

    for ret in items:
        pid = ret['product_id']
        qty_ret = _d(ret['quantity'])
        orig_item = next((it for it in order.items if it.product_id == pid), None)
        if not orig_item:
            continue

        product = db.query(models.Product).filter(
            models.Product.id == pid,
            models.Product.account_id == account_id,
        ).first()
        if product and product.track_inventory_l3:
            eng.reverse(
                account_id=account_id,
                product_id=pid,
                quantity=int(qty_ret),
                unit_cost=Decimal("0"),
                source_type="sale_order",
                source_id=order.id,
                operator=operator,
                source_id_override=return_id,
            )
            move = db.query(StockMove).filter(
                StockMove.source_type == "sale_order",
                StockMove.source_id == order.id,
                StockMove.product_id == pid,
            ).first()
            unit_cost = move.unit_cost_l2 if move and move.unit_cost_l2 else Decimal("0")
            cost_return += (qty_ret * unit_cost).quantize(Q2)

        line_total = _d(orig_item.total_price_l1)
        denom = _d(orig_item.quantity_l1)
        if denom <= 0:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                data={"product_id": pid, "quantity": str(denom), "msg": "退货时商品数量为0或负数"})
        ratio = qty_ret / denom
        revenue_ret = line_total * ratio
        total_with_tax_ret += revenue_ret

    total_with_tax_ret = total_with_tax_ret.quantize(Q2)
    order_tax = Decimal(str(order.tax_amount_l1 or 0))
    order_total = Decimal(str(order.total_price_l1 or 0))
    if order_tax and order_total and order_total != Decimal('0'):
        tax_ratio = total_with_tax_ret / order_total
        tax_amount_ret = (order_tax * tax_ratio).quantize(Q2)
    else:
        tax_amount_ret = Decimal('0')
    total_without_tax_ret = without_tax_from(total_with_tax_ret, tax_amount_ret)
    cost_return = cost_return.quantize(Q2)

    post_journal(db, account_id, "sale_return", {
        "partner_id": order.customer_id or 0,
        "total_with_tax": total_with_tax_ret,
        "total_without_tax": total_without_tax_ret,
        "tax_amount": tax_amount_ret,
        "cost_return": cost_return,
        "taxpayer_type": taxpayer_type,
        "source_model": "sale_return",
        "source_id": return_id,
        "date": return_date,
    })

    original_invoice = db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.related_order_type == "sale_order",
        models.Invoice.related_order_id == order.id,
        models.Invoice.direction == InvoiceDirection.OUT,
        models.Invoice.is_reversed == False,
    ).first()

    if original_invoice:
        red_invoice_no = f"RED-{original_invoice.invoice_no}-{return_id}"
        existing_red = db.query(models.Invoice).filter(
            models.Invoice.account_id == account_id,
            models.Invoice.invoice_no == red_invoice_no,
        ).first()
        if not existing_red:
            ret_dt = datetime.fromisoformat(return_date) if isinstance(return_date, str) else return_date
            red_invoice = models.Invoice(
                account_id=account_id,
                invoice_no=red_invoice_no,
                direction=InvoiceDirection.OUT,
                invoice_type=original_invoice.invoice_type,
                tax_rate_l1=original_invoice.tax_rate_l1,
                amount_without_tax_l1=-total_without_tax_ret,
                tax_amount_l1=-tax_amount_ret,
                amount_with_tax_l1=-total_with_tax_ret,
                counterparty_name=order.customer.name if order.customer else (original_invoice.counterparty_name or ""),
                seller_name=original_invoice.seller_name,
                buyer_name=original_invoice.buyer_name,
                issue_date_l1=ret_dt,
                certification_status_l3=CertificationStatus.N_A,
                related_order_id=order.id,
                related_order_type="sale_order",
                notes=f"红字销项发票（销售退货）: {reason or '未提供'}",
            )
            db.add(red_invoice)
            db.flush()

    emit("sale_order.returned", db=db, account_id=account_id, order=order,
         operator=operator, return_amount=total_with_tax_ret,
         log_action="return",
         log_detail=f"销售退货 {order.order_no}: 退货金额={total_with_tax_ret}, 原因={reason or '未提供'}")
    db.flush()
    return order


def restore_sale_order(db, account_id, operator, order_id):
    """恢复销售单 — 提取自 RestoreSaleOrderHandler"""
    order = get_sale_order(db, account_id, order_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": order_id})
    if order.status != OrderStatus.CANCELLED:
        raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": order.status, "action": "恢复"})

    old_status = order.status
    domain = SaleOrderDomain.from_orm(order)
    violations = domain.validate()
    if violations:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"销售单校验失败: {'; '.join(violations)}"})
    domain.transition_to(OrderStatus.COMPLETED)
    order.status = domain.status

    eng = InventoryEngine(db)
    for item in order.items:
        product = get_product(db, account_id, item.product_id)
        if product.track_inventory_l3:
            unit_cost = eng.force_outbound(
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
    FinanceEngine(db, account_id).record_sale(order, force=True)

    emit("sale_order.restored", db=db, account_id=account_id, order=order,
         operator=operator, old_status=old_status,
         log_action="update",
         log_detail=f"恢复销售单 {order.order_no}: 状态={old_status}->completed")
    db.flush()
    return order


def update_sale_items(db, account_id, operator, order_id, items, total_price=None):
    """更新销售单明细 — 提取自 UpdateSaleOrderItemsHandler"""
    order = get_sale_order(db, account_id, order_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": order_id})

    if items:
        product_ids = [it['product_id'] for it in items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

    old_status = order.status
    old_items = [
        {'product_id': item.product_id, 'quantity': item.quantity_l1,
         'unit_cost': Decimal(str(item.unit_cost_l2)) if item.unit_cost_l2 else Decimal('0')}
        for item in order.items
    ]

    if old_status == OrderStatus.COMPLETED:
        eng = InventoryEngine(db)
        for item_data in old_items:
            eng.reverse(
                account_id=account_id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_cost=item_data['unit_cost'],
                source_type="sale_order",
                source_id=order.id,
                operator=operator,
                force=True,
            )
        FinanceEngine(db, account_id).reverse_sale(order.id, force=True)

    if len(items) == 0:
        # 直接删除 order，cascade 会自动删除关联 items，避免先删 items 再删 order 的双重删除警告
        emit("sale_order.deleted", db=db, account_id=account_id, order=order,
             operator=operator,
             log_action="delete",
             log_detail=f"删除销售单 {order.order_no}（商品行数归零自动删除）")
        db.delete(order)
        db.flush()
        return None

    for item in order.items[:]:
        db.delete(item)
    db.flush()

    items_data = []
    total = Decimal('0')
    for it in items:
        product = get_product(db, account_id, it['product_id'])
        if not product:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
        line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
        items_data.append({
            'product_id': it['product_id'],
            'quantity': it['quantity'],
            'unit_price': it['unit_price'],
            'tax_rate': it.get('tax_rate', VAT_SMALL_SCALE_REDUCED_RATE.value),
            'total_price': line_total,
        })
        total += line_total

    if total_price is not None:
        _distribute_total_price(items_data, total_price)

    for it in items_data:
        new_item = models.SaleItem(
            order_id=order.id,
            product_id=it['product_id'],
            quantity_l1=it['quantity'],
            unit_price_l1=it['unit_price'],
            tax_rate_l1=it['tax_rate'],
            total_price_l1=it['total_price'],
        )
        db.add(new_item)

    final_total = sum(_d(it['total_price']) for it in items_data)
    order.total_price_l1 = _d(total_price) if total_price is not None else final_total.quantize(Q2)
    db.flush()

    if order.status == OrderStatus.COMPLETED:
        eng = InventoryEngine(db)
        for item in order.items:
            product = get_product(db, account_id, item.product_id)
            if product.track_inventory_l3:
                unit_cost = eng.force_outbound(
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
        FinanceEngine(db, account_id).record_sale(order, force=True)

    emit("sale_order.items_updated", db=db, account_id=account_id, order=order,
         operator=operator,
         log_action="update",
         log_detail=f"更新销售单明细 {order.order_no}")
    db.flush()
    return order


def update_sale_fields(db, account_id, operator, order_id, **fields):
    """更新销售单字段 — 提取自 UpdateSaleOrderFieldsHandler"""
    order = get_sale_order(db, account_id, order_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": order_id})

    field_map = {
        'customer_id': fields.get('customer_id'),
        'payment_status': fields.get('payment_status'),
        'notes': fields.get('notes'),
        'image_url': fields.get('image_url'),
        'status': fields.get('status'),
    }
    for k, v in field_map.items():
        if v is not None:
            setattr(order, k, v)

    emit("sale_order.fields_updated", db=db, account_id=account_id, order=order, operator=operator,
         log_action="update",
         log_detail=f"更新销售单字段 {order.order_no}")
    db.flush()
    return order
