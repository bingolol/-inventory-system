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

_PARTY_CONFIG = {
    "supplier": {
        "model": Supplier, "partner_key": "supplier_id",
        "order_model": PurchaseOrder, "order_date_attr": "purchase_date_l1",
        "order_label": "采购单", "error_code": ErrorCode.ORDER_NOT_FOUND,
        "inv_dir": InvoiceDirection.IN,
    },
    "customer": {
        "model": Customer, "partner_key": "customer_id",
        "order_model": SaleOrder, "order_date_attr": "sale_date_l1",
        "order_label": "销售单", "error_code": ErrorCode.CUSTOMER_NOT_FOUND,
        "inv_dir": InvoiceDirection.OUT,
    },
}


def _calc_partner_reconciliation(db: Session, account_id: int, party_type: str, partner_id: int,
                                  start_date: str, end_date: str):
    """计算单个合作伙伴的对账数据"""
    cfg = _PARTY_CONFIG[party_type]
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")

    partner = db.query(cfg["model"]).filter(
        cfg["model"].id == partner_id, cfg["model"].account_id == account_id
    ).first()
    if not partner:
        return None

    order_model = cfg["order_model"]
    partner_fk = getattr(order_model, cfg["partner_key"])
    order_date = getattr(order_model, cfg["order_date_attr"])

    opening = _d(db.query(func.coalesce(func.sum(order_model.total_price_l1), 0)).filter(
        order_model.account_id == account_id,
        partner_fk == partner_id,
        order_date < start_dt,
        order_model.payment_status == PaymentStatus.UNPAID,
        order_model.status == OrderStatus.COMPLETED
    ).scalar())

    orders = db.query(order_model).filter(
        order_model.account_id == account_id,
        partner_fk == partner_id,
        order_date >= start_dt,
        order_date <= end_dt,
        order_model.status == OrderStatus.COMPLETED
    ).all()
    current = sum((_d(o.total_price_l1) for o in orders), Decimal('0'))
    paid = sum((_d(o.total_price_l1) for o in orders if o.payment_status == PaymentStatus.PAID), Decimal('0'))

    invs = db.query(Invoice).filter(
        Invoice.account_id == account_id,
        Invoice.direction == cfg["inv_dir"],
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

    partners = db.query(_PARTY_CONFIG[party_type]["model"]).filter(
        _PARTY_CONFIG[party_type]["model"].account_id == account_id
    ).all()

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

    cfg = _PARTY_CONFIG[party_type]
    order_model = cfg["order_model"]
    partner_fk = getattr(order_model, cfg["partner_key"])
    order_date = getattr(order_model, cfg["order_date_attr"])

    partner = db.query(cfg["model"]).filter(
        cfg["model"].id == partner_id, cfg["model"].account_id == account_id
    ).first()
    if not partner:
        raise BusinessError(code=cfg["error_code"], data={"order_type": cfg["order_label"], "order_id": partner_id})

    opening = _d(db.query(func.coalesce(func.sum(order_model.total_price_l1), 0)).filter(
        order_model.account_id == account_id,
        partner_fk == partner_id,
        order_date < start_dt,
        order_model.payment_status == PaymentStatus.UNPAID,
        order_model.status == OrderStatus.COMPLETED
    ).scalar())

    orders = db.query(order_model).filter(
        order_model.account_id == account_id,
        partner_fk == partner_id,
        order_date >= start_dt,
        order_date <= end_dt,
        order_model.status == OrderStatus.COMPLETED
    ).order_by(order_date).all()

    items = []
    for o in orders:
        date_val = getattr(o, cfg["order_date_attr"])
        items.append({
            "date": date_val.strftime("%Y-%m-%d") if date_val else "",
            "description": f"{cfg['order_label']} {o.order_no}",
            "amount": o.total_price_l1,
            "payment_status": o.payment_status,
            "has_invoice": linkage_has_invoice(db, account_id, f"{cfg['partner_key'].replace('_id', '')}_order", o.id),
            "notes": o.notes or ""
        })

    invs = db.query(Invoice).filter(
        Invoice.account_id == account_id,
        Invoice.direction == cfg["inv_dir"],
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