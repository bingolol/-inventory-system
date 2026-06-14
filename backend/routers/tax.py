# ⚠️ 注意：本路由当前仅包含只读操作（GET），不需要 uow 包裹。
# 如未来新增写操作（POST/PUT/DELETE），务必使用 `with unit_of_work(db):` 包裹。

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal

from database import get_db
from models import Account, Invoice
from schemas import TaxReport, TaxReportMonth, InvoiceOut
from account_dep import get_account_id
from enums import InvoiceDirection, InvoiceType, CertificationStatus, TaxpayerType
from utils import _d, Q2

router = APIRouter()


def _calculate_tax_data(db: Session, account_id: int, start_date: datetime, end_date: datetime):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账本不存在")

    out_invoices = db.query(Invoice).filter(
        Invoice.account_id == account_id,
        Invoice.direction == InvoiceDirection.OUT,
        Invoice.issue_date >= start_date,
        Invoice.issue_date < end_date
    ).all()

    in_invoices = db.query(Invoice).filter(
        Invoice.account_id == account_id,
        Invoice.direction == InvoiceDirection.IN,
        Invoice.issue_date >= start_date,
        Invoice.issue_date < end_date
    ).all()

    output_total = Decimal('0')
    output_tax = Decimal('0')
    for inv in out_invoices:
        output_total += _d(inv.amount_without_tax)
        output_tax += _d(inv.tax_amount)

    input_total = Decimal('0')
    input_tax = Decimal('0')

    if account.taxpayer_type == TaxpayerType.GENERAL:
        for inv in in_invoices:
            if inv.invoice_type == InvoiceType.SPECIAL and inv.certification_status == CertificationStatus.CERTIFIED:
                input_total += _d(inv.amount_without_tax)
                input_tax += _d(inv.tax_amount)
    else:
        input_total = Decimal('0')
        input_tax = Decimal('0')

    tax_payable = output_tax - input_tax
    if tax_payable < 0:
        tax_payable = Decimal('0')

    invoice_outs = []
    for invoice in out_invoices + in_invoices:
        invoice_out = InvoiceOut(
            id=invoice.id,
            invoice_no=invoice.invoice_no,
            direction=invoice.direction,
            invoice_type=invoice.invoice_type,
            tax_rate=invoice.tax_rate,
            amount_without_tax=invoice.amount_without_tax,
            tax_amount=invoice.tax_amount,
            amount_with_tax=invoice.amount_with_tax,
            counterparty_name=invoice.counterparty_name,
            issue_date=invoice.issue_date,
            pdf_path=invoice.pdf_path,
            certification_status=invoice.certification_status,
            certification_date=invoice.certification_date,
            related_order_id=invoice.related_order_id,
            related_order_type=invoice.related_order_type,
            notes=invoice.notes,
            created_at=invoice.created_at
        )
        invoice_outs.append(invoice_out)

    return {
        "account": account,
        "output_total": output_total.quantize(Q2),
        "output_tax": output_tax.quantize(Q2),
        "input_total": input_total.quantize(Q2),
        "input_tax": input_tax.quantize(Q2),
        "tax_payable": tax_payable.quantize(Q2),
        "invoice_list": invoice_outs,
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": (end_date - timedelta(days=1)).strftime("%Y-%m-%d"),
    }


@router.get("", response_model=TaxReport)
async def get_tax_report(
    year: int,
    quarter: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取增值税季度报表"""
    if quarter < 1 or quarter > 4:
        raise HTTPException(status_code=400, detail="季度必须在 1-4 之间")

    start_month = (quarter - 1) * 3 + 1
    start_date = datetime(year, start_month, 1)
    if quarter == 4:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, quarter * 3 + 1, 1)

    data = _calculate_tax_data(db, account_id, start_date, end_date)

    return TaxReport(
        year=year,
        quarter=quarter,
        period_start=data["period_start"],
        period_end=data["period_end"],
        taxpayer_type=data["account"].taxpayer_type,
        output_total=data["output_total"],
        output_tax=data["output_tax"],
        input_total=data["input_total"],
        input_tax=data["input_tax"],
        tax_payable=data["tax_payable"],
        invoice_list=data["invoice_list"]
    )


@router.get("/monthly", response_model=TaxReportMonth)
async def get_tax_report_monthly(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取增值税月度报表"""
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="月份必须在 1-12 之间")

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    data = _calculate_tax_data(db, account_id, start_date, end_date)

    return TaxReportMonth(
        year=year,
        month=month,
        period_start=data["period_start"],
        period_end=data["period_end"],
        taxpayer_type=data["account"].taxpayer_type,
        output_total=data["output_total"],
        output_tax=data["output_tax"],
        input_total=data["input_total"],
        input_tax=data["input_tax"],
        tax_payable=data["tax_payable"],
        invoice_list=data["invoice_list"]
    )
