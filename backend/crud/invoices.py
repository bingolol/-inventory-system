"""发票 + 税务报表 CRUD

写操作已迁移至 commands 层（CreateInvoice/UpdateInvoice/DeleteInvoice）。
本模块仅保留 list/get 查询函数和 get_tax_report 报表，供 routers 直接调用。
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
import models, schemas

from enums import InvoiceDirection
from utils import _d, Q2

logger = logging.getLogger("inventory")


def list_invoices(db: Session, account_id: int, skip: int = 0, limit: int = 100, direction: str = None, invoice_type: str = None, year: int = None, quarter: int = None):
    q = db.query(models.Invoice).filter(models.Invoice.account_id == account_id)
    if direction:
        q = q.filter(models.Invoice.direction == direction)
    if invoice_type:
        q = q.filter(models.Invoice.invoice_type == invoice_type)
    if year and quarter:
        quarter_start = datetime(year, (quarter - 1) * 3 + 1, 1)
        if quarter == 4:
            quarter_end = datetime(year + 1, 1, 1)
        else:
            quarter_end = datetime(year, quarter * 3 + 1, 1)
        q = q.filter(models.Invoice.issue_date >= quarter_start, models.Invoice.issue_date < quarter_end)
    total = q.count()
    items = q.order_by(models.Invoice.issue_date.desc()).offset(skip).limit(limit).all()
    return total, items


def get_invoice(db: Session, account_id: int, invoice_id: int):
    return db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.id == invoice_id
    ).first()


def get_tax_report(db: Session, account_id: int, year: int, quarter: int):
    """获取税务报表"""
    # 获取账本的纳税人类型
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    taxpayer_type = account.taxpayer_type if account else "small_scale"
    quarter_start_str = f"{year}-{(quarter - 1) * 3 + 1:02d}-01"
    if quarter == 4:
        quarter_end_str = f"{year + 1}-01-01"
    else:
        quarter_end_str = f"{year}-{quarter * 3 + 1:02d}-01"

    out_invoices = db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.direction == InvoiceDirection.OUT,
        models.Invoice.issue_date >= quarter_start_str,
        models.Invoice.issue_date < quarter_end_str
    ).all()

    in_invoices = db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.direction == InvoiceDirection.IN,
        models.Invoice.issue_date >= quarter_start_str,
        models.Invoice.issue_date < quarter_end_str
    ).all()

    output_total = _d(sum(_d(inv.amount_without_tax) for inv in out_invoices))
    output_tax = _d(sum(_d(inv.tax_amount) for inv in out_invoices))
    input_total = _d(sum(_d(inv.amount_without_tax) for inv in in_invoices))
    
    # 进项税额：一般纳税人只计算已认证的专票
    if taxpayer_type == "general":
        input_tax = _d(sum(_d(inv.tax_amount) for inv in in_invoices 
                       if inv.certification_status == "certified" and inv.invoice_type == "special"))
    else:
        input_tax = _d(sum(_d(inv.tax_amount) for inv in in_invoices))
    
    tax_payable = max(output_tax - input_tax, Decimal('0'))

    invoice_list = []
    for inv in out_invoices + in_invoices:
        invoice_list.append(schemas.InvoiceOut(
            id=inv.id,
            invoice_no=inv.invoice_no,
            direction=inv.direction,
            invoice_type=inv.invoice_type,
            tax_rate=inv.tax_rate,
            amount_without_tax=inv.amount_without_tax,
            tax_amount=inv.tax_amount,
            amount_with_tax=inv.amount_with_tax,
            counterparty_name=inv.counterparty_name,
            issue_date=inv.issue_date.strftime("%Y-%m-%d") if inv.issue_date else None,
            pdf_path=inv.pdf_path,
            certification_status=inv.certification_status,
            certification_date=inv.certification_date.strftime("%Y-%m-%d") if inv.certification_date else None,
            related_order_id=inv.related_order_id,
            related_order_type=inv.related_order_type,
            notes=inv.notes,
            created_at=inv.created_at
        ))

    report = schemas.TaxReport(
        year=year,
        quarter=quarter,
        period_start=quarter_start_str,
        period_end=(datetime.strptime(quarter_end_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d") if quarter_end_str else quarter_start_str,
        taxpayer_type=taxpayer_type,
        output_total=output_total,
        output_tax=output_tax,
        input_total=input_total,
        input_tax=input_tax,
        tax_payable=tax_payable,
        invoice_list=invoice_list
    )
    return report