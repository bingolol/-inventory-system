"""采购单领域规则/校验 — 被 _order.py 的参数化命令调用"""

import time
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

import models
from enums import OrderStatus, InvoiceDirection, CertificationStatus
from events import emit
from commands.base import Command, CommandHandler
from crud.base import gen_order_no as _generate_order_no
from crud.products import get_product
from crud.orders import get_purchase_order
from utils import _d
from errors import BusinessError, ErrorCode
from utils import Q2
from engine_inventory import InventoryEngine
from engine_finance import FinanceEngine
from lineage import reads, writes, TIER_L1, TIER_L3
from policy.vat_facts import VAT_SMALL_SCALE_REDUCED_RATE


def return_purchase_order(db, account_id, operator, order_id, return_date, reason, items):
    """采购退货 — 提取自 ReturnPurchaseOrderHandler"""
    from finance_integration import post_journal
    StockMove = models.StockMove

    order = get_purchase_order(db, account_id, order_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                            data={"order_type": "采购单", "order_id": order_id})
    if order.status != OrderStatus.COMPLETED:
        raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE,
                            data={"status": order.status, "action": "退货"})

    if not return_date:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                            message="退货日期不能为空，请提供业务发生日期",
                            ai_instruction="STOP_RETRYING. return_date 字段必填。")
    if not items:
        raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS,
                            data={"order_type": "采购退货单"})

    original_qty_map = {item.product_id: item.quantity_l1 for item in order.items}
    for ret in items:
        pid = ret['product_id']
        if pid not in original_qty_map:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND,
                                data={"product_id": pid, "details": "商品不在原采购单中"})
        if ret['quantity'] > original_qty_map[pid]:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"退货数量 {ret['quantity']} 超过原采购数量 {original_qty_map[pid]}",
                ai_instruction=f"STOP_RETRYING. 商品 ID={pid} 原采购 {original_qty_map[pid]} 件，退货不能超过此数量。"
            )

    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    enable_vat_deduction = FinanceEngine._vat_deduction(account)

    # 先找原始发票（真相源）
    original_invoice = db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.related_order_type == "purchase_order",
        models.Invoice.related_order_id == order.id,
        models.Invoice.direction == InvoiceDirection.IN,
        models.Invoice.is_reversed == False,
    ).first()

    eng = InventoryEngine(db)
    return_id = int(time.time() * 1000)

    for ret in items:
        pid = ret['product_id']
        qty_ret = Decimal(str(ret['quantity']))
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
                source_type="purchase_order",
                source_id=order.id,
                operator=operator,
                source_id_override=return_id,
            )

    total_order_base = sum(_d(it.total_price_l1) for it in order.items)
    ret_base = Decimal("0")
    for ret in items:
        pid = ret['product_id']
        qty_ret = _d(ret['quantity'])
        orig_item = next((it for it in order.items if it.product_id == pid), None)
        if orig_item:
            denom = _d(orig_item.quantity_l1)
            if denom <= 0:
                raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                    data={"product_id": pid, "quantity": str(denom), "msg": "退货时商品数量为0或负数"})
            ret_base += _d(orig_item.total_price_l1) * (qty_ret / denom)
    ret_base = ret_base.quantize(Q2)
    pct = ret_base / total_order_base if total_order_base else Decimal('0')

    if original_invoice:
        # ── 有原始发票：全部金额来自发票（发票金额不可能为0） ──
        inv_without_tax = Decimal(str(original_invoice.amount_without_tax_l1 or 0))
        inv_tax = Decimal(str(original_invoice.tax_amount_l1 or 0))
        inv_with_tax = Decimal(str(original_invoice.amount_with_tax_l1 or 0))
        total_without_tax_ret = (inv_without_tax * pct).quantize(Q2) if pct else Decimal('0')
        inventory_cost_ret = total_without_tax_ret
        if enable_vat_deduction:
            tax_amount_ret = (inv_tax * pct).quantize(Q2) if pct else Decimal('0')
            total_with_tax_ret = (total_without_tax_ret + tax_amount_ret).quantize(Q2)
        else:
            total_with_tax_ret = (inv_with_tax * pct).quantize(Q2) if pct else Decimal('0')
            total_without_tax_ret = total_with_tax_ret
            tax_amount_ret = Decimal('0')
    elif enable_vat_deduction:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"采购退货未找到原始进项发票，无法计算税额。请先为采购单 {order.order_no} 录入进项发票后再退货，或联系管理员处理。",
            ai_instruction="STOP_RETRYING. 必须创建进项发票后才能退货（一般纳税人需发票税额做进项转出）。"
        )
    else:
        # ── 小规模无发票：用采购单原始行数据（不用加权成本） ──
        total_without_tax_ret = ret_base
        inventory_cost_ret = ret_base
        tax_amount_ret = Decimal('0')
        total_with_tax_ret = total_without_tax_ret

    post_journal(db, account_id, "purchase_return", {
        "partner_id": order.supplier_id or 0,
        "total_with_tax": total_with_tax_ret,
        "inventory_cost_return": inventory_cost_ret,
        "tax_return": tax_amount_ret if enable_vat_deduction else Decimal("0"),
        "enable_vat_deduction": enable_vat_deduction,
        "source_model": "purchase_return",
        "source_id": return_id,
        "date": return_date,
    })

    if original_invoice:
        red_invoice_no = f"RED-{original_invoice.invoice_no}-{return_id}"
        existing_red = db.query(models.Invoice).filter(
            models.Invoice.account_id == account_id,
            models.Invoice.invoice_no == red_invoice_no,
        ).first()
        if not existing_red:
            ret_dt = datetime.fromisoformat(return_date) if isinstance(return_date, str) else return_date
            red_cert_status = original_invoice.certification_status_l3 if (
                enable_vat_deduction and original_invoice.invoice_type == "special"
            ) else CertificationStatus.N_A
            red_invoice = models.Invoice(
                account_id=account_id,
                invoice_no=red_invoice_no,
                direction=InvoiceDirection.IN,
                invoice_type=original_invoice.invoice_type,
                tax_rate_l1=original_invoice.tax_rate_l1,
                amount_without_tax_l1=-inventory_cost_ret if enable_vat_deduction else -total_with_tax_ret,
                tax_amount_l1=-(tax_amount_ret if enable_vat_deduction else Decimal("0")),
                amount_with_tax_l1=-total_with_tax_ret,
                counterparty_name=order.supplier.name if order.supplier else (original_invoice.counterparty_name or ""),
                seller_name=original_invoice.seller_name,
                buyer_name=original_invoice.buyer_name,
                issue_date_l1=ret_dt,
                certification_status_l3=red_cert_status,
                related_order_id=order.id,
                related_order_type="purchase_order",
                notes=f"红字进项发票（采购退货）: {reason or '未提供'}",
            )
            db.add(red_invoice)
            db.flush()

    emit("purchase_order.returned", db=db, account_id=account_id, order=order,
         operator=operator, return_amount=total_with_tax_ret,
         log_action="return",
         log_detail=f"采购退货 {order.order_no}: 退货金额={total_with_tax_ret}, 原因={reason or '未提供'}")
    db.flush()
    return order


def update_purchase_items(db, account_id, operator, order_id, items, supplier_id=None, payment_method=None, notes=None, status=None):
    """更新采购单明细 — 提取自 UpdatePurchaseOrderItemsHandler"""
    order = get_purchase_order(db, account_id, order_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": order_id})

    if items:
        product_ids = [it['product_id'] for it in items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

    old_status = order.status

    if old_status == OrderStatus.COMPLETED:
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
        FinanceEngine(db, account_id).reverse_purchase(order.id, force=True)

    if len(items) == 0:
        # 直接删除 order，cascade 会自动删除关联 items，避免先删 items 再删 order 的双重删除警告
        emit("purchase_order.deleted", db=db, account_id=account_id, order=order,
             operator=operator,
             log_action="delete",
             log_detail=f"删除采购单 {order.order_no}（商品行数归零自动删除）")
        db.delete(order)
        db.flush()
        return None

    for item in order.items[:]:
        db.delete(item)
    db.flush()

    field_map = {
        'supplier_id': supplier_id,
        'payment_method': payment_method,
        'notes': notes,
        'status': status,
    }
    for k, v in field_map.items():
        if v is not None:
            setattr(order, k, v)
    new_status = order.status

    account = db.get(models.Account, account_id)
    default_tax_rate = FinanceEngine._vat_rate(account)
    total = Decimal('0')
    calculated_data = []
    for it in items:
        product = get_product(db, account_id, it['product_id'])
        if not product:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
        line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
        new_item = models.PurchaseItem(
            order_id=order.id,
            product_id=it['product_id'],
            quantity_l1=it['quantity'],
            unit_price_l1=it['unit_price'],
            tax_rate_l1=it.get('tax_rate', default_tax_rate),
            total_price_l1=line_total,
        )
        db.add(new_item)
        if new_status == OrderStatus.COMPLETED and product.track_inventory_l3:
            calc = InventoryEngine(db).force_inbound(
                account_id=account_id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                source_type="purchase_order",
                source_id=order.id,
                tax_rate=it.get('tax_rate'),
                operator=operator,
            )
            calculated_data.append(calc)
        total += line_total

    order.total_price_l1 = total.quantize(Q2)

    if new_status == OrderStatus.COMPLETED:
        FinanceEngine(db, account_id).record_purchase(order, force=True)

    emit("purchase_order.updated", db=db, account_id=account_id, order=order, operator=operator,
         log_action="update",
         log_detail=f"更新采购单明细 {order.order_no}: 状态={old_status}->{new_status}")
    db.flush()
    db.refresh(order)
    return order


def update_purchase_fields(db, account_id, operator, order_id, **fields):
    """更新采购单字段 — 提取自 UpdatePurchaseOrderFieldsHandler"""
    order = get_purchase_order(db, account_id, order_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": order_id})

    old_status = order.status
    field_map = {
        'supplier_id': fields.get('supplier_id'),
        'payment_method': fields.get('payment_method'),
        'payment_status': fields.get('payment_status'),
        'notes': fields.get('notes'),
        'image_url': fields.get('image_url'),
        'status': fields.get('status'),
    }
    for k, v in field_map.items():
        if v is not None:
            setattr(order, k, v)

    new_status = order.status
    eng = InventoryEngine(db)
    fin = FinanceEngine(db, account_id)
    if old_status == OrderStatus.COMPLETED and new_status == OrderStatus.CANCELLED:
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
        fin.reverse_purchase(order.id, force=True)
    elif old_status == OrderStatus.CANCELLED and new_status == OrderStatus.COMPLETED:
        calculated_data = []
        for item in order.items:
            product = db.get(models.Product, item.product_id)
            if product and product.track_inventory_l3:
                calc = eng.force_inbound(
                    account_id=account_id,
                    product_id=item.product_id,
                    quantity=item.quantity_l1,
                    unit_price=item.unit_price_l1,
                    source_type="purchase_order",
                    source_id=order.id,
                    tax_rate=item.tax_rate_l1,
                    operator=operator,
                )
                calculated_data.append(calc)
        fin.record_purchase(order, force=True)

    emit("purchase_order.updated", db=db, account_id=account_id, order=order, operator=operator,
         log_action="update",
         log_detail=f"更新采购单字段 {order.order_no}: 状态={old_status}->{new_status}")
    db.flush()
    return order
