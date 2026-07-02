# ⚠️ 注意：本路由当前仅包含只读操作（GET），不需要 uow 包裹。
# 如未来新增写操作（POST/PUT/DELETE），务必使用 `with unit_of_work(db):` 包裹。

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal
from database import get_db
from models import PurchaseOrder, SaleOrder, Invoice, Supplier, Customer
from account_dep import get_account_id
from enums import OrderStatus, PaymentStatus, InvoiceDirection
from utils import _d, Q2
from errors import BusinessError, ErrorCode
from crud.invoice_linkage import has_invoice as linkage_has_invoice

router = APIRouter()


def _calc_partner_reconciliation(db: Session, account_id: int, party_type: str, partner_id: int,
                                  start_date: str, end_date: str):
    """计算单个合作伙伴的对账数据"""
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")

    if party_type == "supplier":
        partner = db.query(Supplier).filter(
            Supplier.id == partner_id, Supplier.account_id == account_id
        ).first()
        if not partner:
            return None

        # 期初：start_date 前未付款采购单
        opening = _d(db.query(func.coalesce(func.sum(PurchaseOrder.total_price_l1), 0)).filter(
            PurchaseOrder.account_id == account_id,
            PurchaseOrder.supplier_id == partner_id,
            PurchaseOrder.purchase_date_l1 < start_dt,
            PurchaseOrder.payment_status == PaymentStatus.UNPAID,
            PurchaseOrder.status == OrderStatus.COMPLETED
        ).scalar())

        # 本期所有采购单
        orders = db.query(PurchaseOrder).filter(
            PurchaseOrder.account_id == account_id,
            PurchaseOrder.supplier_id == partner_id,
            PurchaseOrder.purchase_date_l1 >= start_dt,
            PurchaseOrder.purchase_date_l1 <= end_dt,
            PurchaseOrder.status == OrderStatus.COMPLETED
        ).all()
        current = sum((_d(o.total_price_l1) for o in orders), Decimal('0'))
        paid = sum((_d(o.total_price_l1) for o in orders if o.payment_status == PaymentStatus.PAID), Decimal('0'))

        # 发票
        invs = db.query(Invoice).filter(
            Invoice.account_id == account_id,
            Invoice.direction == InvoiceDirection.IN,
            Invoice.counterparty_name == partner.name,
            Invoice.issue_date_l1 >= start_dt,
            Invoice.issue_date_l1 <= end_dt
        ).all()
        inv_amount = sum((_d(i.amount_with_tax_l1) for i in invs), Decimal('0'))

    else:
        partner = db.query(Customer).filter(
            Customer.id == partner_id, Customer.account_id == account_id
        ).first()
        if not partner:
            return None

        # 期初：start_date 前未收款销售单
        opening = _d(db.query(func.coalesce(func.sum(SaleOrder.total_price_l1), 0)).filter(
            SaleOrder.account_id == account_id,
            SaleOrder.customer_id == partner_id,
            SaleOrder.sale_date_l1 < start_dt,
            SaleOrder.payment_status == PaymentStatus.UNPAID,
            SaleOrder.status == OrderStatus.COMPLETED
        ).scalar())

        # 本期所有销售单
        orders = db.query(SaleOrder).filter(
            SaleOrder.account_id == account_id,
            SaleOrder.customer_id == partner_id,
            SaleOrder.sale_date_l1 >= start_dt,
            SaleOrder.sale_date_l1 <= end_dt,
            SaleOrder.status == OrderStatus.COMPLETED
        ).all()
        current = sum((_d(o.total_price_l1) for o in orders), Decimal('0'))
        paid = sum((_d(o.total_price_l1) for o in orders if o.payment_status == PaymentStatus.PAID), Decimal('0'))

        # 发票
        invs = db.query(Invoice).filter(
            Invoice.account_id == account_id,
            Invoice.direction == InvoiceDirection.OUT,
            Invoice.counterparty_name == partner.name,
            Invoice.issue_date_l1 >= start_dt,
            Invoice.issue_date_l1 <= end_dt
        ).all()
        inv_amount = sum((_d(i.amount_with_tax_l1) for i in invs), Decimal('0'))

    closing = opening + current - paid
    return {
        "partner_id": partner_id,
        "partner_name": partner.name,
        "opening_balance": opening.quantize(Q2),
        "current_amount": current.quantize(Q2),
        "paid_amount": paid.quantize(Q2),
        "closing_balance": closing.quantize(Q2),
        "invoice_amount": inv_amount.quantize(Q2),
        "order_count": len(orders),
        "unpaid_orders": len([o for o in orders if o.payment_status == PaymentStatus.UNPAID])
    }


@router.get("")
def get_all_reconciliations(
    party_type: str = Query(..., pattern="^(supplier|customer)$"),
    start_date: str = Query(...),
    end_date: str = Query(...),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """一键获取所有合作伙伴的对账汇总数据"""
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise BusinessError(code=ErrorCode.INVOICE_INVALID_DATE, data={"date": f"{start_date} ~ {end_date}"})

    # 获取所有合作伙伴
    if party_type == "supplier":
        partners = db.query(Supplier).filter(Supplier.account_id == account_id).all()
    else:
        partners = db.query(Customer).filter(Customer.account_id == account_id).all()

    # 计算每个合作伙伴的对账数据
    results = []
    total_opening = total_current = total_paid = total_closing = total_invoice = Decimal('0')

    for p in partners:
        rec = _calc_partner_reconciliation(db, account_id, party_type, p.id, start_date, end_date)
        if rec and (rec["current_amount"] > 0 or rec["opening_balance"] > 0 or rec["closing_balance"] > 0):
            results.append(rec)
            total_opening += rec["opening_balance"]
            total_current += rec["current_amount"]
            total_paid += rec["paid_amount"]
            total_closing += rec["closing_balance"]
            total_invoice += rec["invoice_amount"]

    # 按期末欠款降序排列
    results.sort(key=lambda x: x["closing_balance"], reverse=True)

    return {
        "party_type": party_type,
        "period_start": start_date,
        "period_end": end_date,
        "summary": {
            "partner_count": len(results),
            "total_opening": total_opening.quantize(Q2),
            "total_current": total_current.quantize(Q2),
            "total_paid": total_paid.quantize(Q2),
            "total_closing": total_closing.quantize(Q2),
            "total_invoice": total_invoice.quantize(Q2)
        },
        "items": results
    }


@router.get("/detail")
def get_reconciliation_detail(
    party_type: str = Query(..., pattern="^(supplier|customer)$"),
    partner_id: int = Query(..., gt=0),
    start_date: str = Query(...),
    end_date: str = Query(...),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """获取单个合作伙伴的对账明细"""
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        raise BusinessError(code=ErrorCode.INVOICE_INVALID_DATE, data={"date": f"{start_date} ~ {end_date}"})

    if party_type == "supplier":
        partner = db.query(Supplier).filter(
            Supplier.id == partner_id, Supplier.account_id == account_id
        ).first()
        if not partner:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "供应商", "order_id": partner_id})

        # 期初
        opening = _d(db.query(func.coalesce(func.sum(PurchaseOrder.total_price_l1), 0)).filter(
            PurchaseOrder.account_id == account_id,
            PurchaseOrder.supplier_id == partner_id,
            PurchaseOrder.purchase_date_l1 < start_dt,
            PurchaseOrder.payment_status == PaymentStatus.UNPAID,
            PurchaseOrder.status == OrderStatus.COMPLETED
        ).scalar())

        # 明细
        orders = db.query(PurchaseOrder).filter(
            PurchaseOrder.account_id == account_id,
            PurchaseOrder.supplier_id == partner_id,
            PurchaseOrder.purchase_date_l1 >= start_dt,
            PurchaseOrder.purchase_date_l1 <= end_dt,
            PurchaseOrder.status == OrderStatus.COMPLETED
        ).order_by(PurchaseOrder.purchase_date_l1).all()

        items = []
        for o in orders:
            items.append({
                "date": o.purchase_date_l1.strftime("%Y-%m-%d") if o.purchase_date_l1 else "",
                "description": f"采购单 {o.order_no}",
                "amount": o.total_price_l1,
                "payment_status": o.payment_status,
                "has_invoice": linkage_has_invoice(db, account_id, "purchase_order", o.id),
                "notes": o.notes or ""
            })

        # 发票
        invs = db.query(Invoice).filter(
            Invoice.account_id == account_id,
            Invoice.direction == InvoiceDirection.IN,
            Invoice.counterparty_name == partner.name,
            Invoice.issue_date_l1 >= start_dt,
            Invoice.issue_date_l1 <= end_dt
        ).all()

    else:
        partner = db.query(Customer).filter(
            Customer.id == partner_id, Customer.account_id == account_id
        ).first()
        if not partner:
            raise BusinessError(code=ErrorCode.CUSTOMER_NOT_FOUND, data={"customer_id": partner_id})

        # 期初
        opening = _d(db.query(func.coalesce(func.sum(SaleOrder.total_price_l1), 0)).filter(
            SaleOrder.account_id == account_id,
            SaleOrder.customer_id == partner_id,
            SaleOrder.sale_date_l1 < start_dt,
            SaleOrder.payment_status == PaymentStatus.UNPAID,
            SaleOrder.status == OrderStatus.COMPLETED
        ).scalar())

        # 明细
        orders = db.query(SaleOrder).filter(
            SaleOrder.account_id == account_id,
            SaleOrder.customer_id == partner_id,
            SaleOrder.sale_date_l1 >= start_dt,
            SaleOrder.sale_date_l1 <= end_dt,
            SaleOrder.status == OrderStatus.COMPLETED
        ).order_by(SaleOrder.sale_date_l1).all()

        items = []
        for o in orders:
            items.append({
                "date": o.sale_date_l1.strftime("%Y-%m-%d") if o.sale_date_l1 else "",
                "description": f"销售单 {o.order_no}",
                "amount": o.total_price_l1,
                "payment_status": o.payment_status,
                "has_invoice": linkage_has_invoice(db, account_id, "sale_order", o.id),
                "notes": o.notes or ""
            })

        # 发票
        invs = db.query(Invoice).filter(
            Invoice.account_id == account_id,
            Invoice.direction == InvoiceDirection.OUT,
            Invoice.counterparty_name == partner.name,
            Invoice.issue_date_l1 >= start_dt,
            Invoice.issue_date_l1 <= end_dt
        ).all()

    for i in invs:
        items.append({
            "date": i.issue_date_l1.strftime("%Y-%m-%d") if i.issue_date_l1 else "",
            "description": f"发票 {i.invoice_no}",
            "amount": i.amount_with_tax_l1,
            "payment_status": "invoice",
            "has_invoice": True,
            "notes": i.notes or ""
        })

    items.sort(key=lambda x: x["date"])
    current = sum((_d(o.total_price_l1) for o in orders), Decimal('0'))
    paid = sum((_d(o.total_price_l1) for o in orders if o.payment_status == PaymentStatus.PAID), Decimal('0'))
    closing = opening + current - paid
    inv_amount = sum((_d(i.amount_with_tax_l1) for i in invs), Decimal('0'))

    return {
        "partner_name": partner.name,
        "party_type": party_type,
        "period_start": start_date,
        "period_end": end_date,
        "opening_balance": opening.quantize(Q2),
        "current_amount": current.quantize(Q2),
        "paid_amount": paid.quantize(Q2),
        "closing_balance": closing.quantize(Q2),
        "invoice_amount": inv_amount.quantize(Q2),
        "items": items
    }