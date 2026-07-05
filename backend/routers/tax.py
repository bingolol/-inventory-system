# ⚠️ 注意：本路由当前仅包含只读操作（GET），不需要 uow 包裹。
# 如未来新增写操作（POST/PUT/DELETE），务必使用 `with unit_of_work(db):` 包裹。

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from database import get_db
from schemas import TaxReport, TaxReportMonth, InvoiceOut
from account_dep import get_account_id
from datetime import datetime, timedelta
from decimal import Decimal
from utils import Q2
from errors import BusinessError, ErrorCode
from crud.finance import aggregate_vat_invoices
from crud.finance.tax_declarations import compute_carry_forward
from policy.entity_profile import build_profile
from policy.policy_engine import calculate_vat as policy_vat

router = APIRouter()


def _calculate_tax_data(db: Session, account_id: int, start_date: datetime, end_date: datetime):
    """汇总增值税属期数据（销项+进项抵扣）并计算应纳税额。

    发票汇总复用 crud.finance.aggregate_vat_invoices（单一真相源），
    与 generate_vat_declaration 共用同一套进项抵扣逻辑，避免双轨漂移。
    日期边界：左闭右开 [start_date, end_date)。
    """
    agg = aggregate_vat_invoices(db, account_id, start_date, end_date)
    account = agg["account"]

    # 使用 policy_engine 计算增值税（单一计算真相源）
    profile = build_profile(account)
    carry_forward = compute_carry_forward(db, account, start_date)
    vat_result = policy_vat(
        profile=profile,
        total_revenue=agg["output_total"],
        input_tax=agg["input_tax"],
        output_tax=agg["output_tax"],
        ordinary_revenue=agg["ordinary_revenue"],
        special_revenue=agg["special_revenue"],
        carry_forward=carry_forward,
    )

    invoice_outs = []
    for invoice in agg["out_invoices"] + agg["in_invoices"]:
        invoice_out = InvoiceOut(
            id=invoice.id,
            invoice_no=invoice.invoice_no,
            direction=invoice.direction,
            invoice_type=invoice.invoice_type,
            tax_rate=invoice.tax_rate_l1,
            amount_without_tax=invoice.amount_without_tax_l1,
            tax_amount=invoice.tax_amount_l1,
            amount_with_tax=invoice.amount_with_tax_l1,
            counterparty_name=invoice.counterparty_name,
            issue_date=invoice.issue_date_l1,
            pdf_path=invoice.pdf_path,
            certification_status=invoice.certification_status_l3,
            certification_date=invoice.certification_date_l3,
            related_order_id=invoice.related_order_id,
            related_order_type=invoice.related_order_type,
            notes=invoice.notes,
            created_at=invoice.created_at
        )
        invoice_outs.append(invoice_out)

    return {
        "account": account,
        "profile": profile,
        "output_total": agg["output_total"].quantize(Q2),
        "output_tax": agg["output_tax"].quantize(Q2),
        "input_total": agg["input_total"].quantize(Q2),
        "input_tax": agg["input_tax"].quantize(Q2),
        "tax_payable": vat_result.tax_payable.quantize(Q2),
        "tax_payable_gross": vat_result.tax_payable_gross.quantize(Q2),
        "surcharge_total": vat_result.surcharge_total,
        "surcharge_education": vat_result.surcharge_education,
        "surcharge_local_education": vat_result.surcharge_local_education,
        "surcharge_urban_construction": vat_result.surcharge_urban_construction,
        "tax_reduction": vat_result.tax_reduction,
        "reduction_item": vat_result.reduction_item,
        "carry_forward": carry_forward.quantize(Q2),
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
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="季度必须在 1-4 之间")

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
        taxpayer_type=data["profile"].vat_type,
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
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="月份必须在 1-12 之间")

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
        taxpayer_type=data["profile"].vat_type,
        output_total=data["output_total"],
        output_tax=data["output_tax"],
        input_total=data["input_total"],
        input_tax=data["input_tax"],
        tax_payable=data["tax_payable"],
        invoice_list=data["invoice_list"]
    )
