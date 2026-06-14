from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from datetime import datetime
from fastapi.responses import FileResponse
from decimal import Decimal
import os

from database import get_db
from models import Invoice
from schemas import InvoiceCreate, InvoiceUpdate, InvoiceOut, InvoiceQuickCreate, InvoiceList, PaginatedResponse
from account_dep import get_account_id, get_operator
from enums import InvoiceDirection, InvoiceType
from image_utils import delete_old_image
from uow import unit_of_work
from commands.base import dispatch
from commands.invoice_commands import CreateInvoice, UpdateInvoice, DeleteInvoice, CertifyInvoice

from utils import _d, Q2
from workspace import get_pdfs_dir as _get_pdfs_dir

router = APIRouter()

# PDF 文件存储路径
PDF_DIR = _get_pdfs_dir()
if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)


def _invoice_to_out(inv: Invoice) -> InvoiceOut:
    """Invoice ORM 对象 → InvoiceOut 响应模型"""
    return InvoiceOut(
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
        project_name=inv.project_name,
        related_order_id=inv.related_order_id,
        related_order_type=inv.related_order_type,
        notes=inv.notes,
        image_url=inv.image_url or "",
        created_at=inv.created_at
    )


@router.get("", response_model=PaginatedResponse)
async def get_invoices(
    direction: Optional[str] = None,
    invoice_type: Optional[str] = None,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    certification_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取发票列表，支持筛选"""
    query = db.query(Invoice).filter(Invoice.account_id == account_id)
    
    if direction:
        query = query.filter(Invoice.direction == direction)
    if invoice_type:
        query = query.filter(Invoice.invoice_type == invoice_type)
    if year:
        if quarter:
            # 计算季度起止日期
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            start_date = datetime(year, start_month, 1)
            if quarter == 4:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, end_month + 1, 1)
            query = query.filter(Invoice.issue_date >= start_date, Invoice.issue_date < end_date)
        else:
            # 筛选全年
            start_date = datetime(year, 1, 1)
            end_date = datetime(year + 1, 1, 1)
            query = query.filter(Invoice.issue_date >= start_date, Invoice.issue_date < end_date)
    if certification_status:
        query = query.filter(Invoice.certification_status == certification_status)
    
    total = query.count()
    invoices = query.offset(skip).limit(limit).all()
    
    invoice_outs = [_invoice_to_out(inv) for inv in invoices]
    return PaginatedResponse(total=total, items=invoice_outs)


@router.post("", response_model=InvoiceOut)
async def create_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """创建发票，校验发票号码唯一性"""
    try:
        with unit_of_work(db):
            cmd = CreateInvoice(
                account_id=account_id,
                operator=operator,
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
                certification_date=invoice.certification_date if invoice.certification_date else None,
                project_name=invoice.project_name,
                related_order_id=invoice.related_order_id,
                related_order_type=invoice.related_order_type,
                notes=invoice.notes,
            )
            db_invoice = dispatch(cmd, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="发票号码已存在")
    db.refresh(db_invoice)
    return _invoice_to_out(db_invoice)


@router.post("/quick", response_model=InvoiceOut)
async def quick_create_invoice(
    invoice: InvoiceQuickCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """AI快捷录入发票，自动计算不含税金额和税额"""
    # 自动计算不含税金额和税额
    amount_with_tax = _d(invoice.amount_with_tax)
    tax_rate = _d(invoice.tax_rate)
    amount_without_tax = (amount_with_tax / (Decimal('1') + tax_rate)).quantize(Q2)
    tax_amount = (amount_with_tax - amount_without_tax).quantize(Q2)

    try:
        with unit_of_work(db):
            cmd = CreateInvoice(
                account_id=account_id,
                operator=operator,
                invoice_no=invoice.invoice_no,
                direction=invoice.direction,
                invoice_type=invoice.invoice_type,
                tax_rate=tax_rate,
                amount_without_tax=amount_without_tax,
                tax_amount=tax_amount,
                amount_with_tax=amount_with_tax,
                counterparty_name=invoice.counterparty_name,
                issue_date=invoice.issue_date,
                project_name=invoice.project_name,
                notes=invoice.notes,
            )
            db_invoice = dispatch(cmd, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="发票号码已存在")
    db.refresh(db_invoice)
    return _invoice_to_out(db_invoice)


@router.post("/upload", response_model=InvoiceOut)
async def upload_pdf(
    file: UploadFile = File(...),
    invoice_no: str = Form(...),
    direction: str = Form(...),
    invoice_type: str = Form(...),
    amount_with_tax: Decimal = Form(...),
    tax_rate: Decimal = Form(...),
    counterparty_name: str = Form(...),
    issue_date: str = Form(...),
    project_name: str = Form(None),
    notes: str = Form(None),
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """上传发票PDF并创建发票记录，参数与quick接口相同，额外支持文件上传"""
    # 验证发票号码唯一性（路由层快速校验，Command内部也会校验）
    existing_invoice = db.query(Invoice).filter(
        Invoice.account_id == account_id,
        Invoice.invoice_no == invoice_no
    ).first()
    if existing_invoice:
        raise HTTPException(status_code=400, detail="发票号码已存在")

    # 保存PDF文件
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(PDF_DIR, f"{account_id}_{safe_filename}")
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # 自动计算不含税金额和税额
    amount_with_tax = _d(amount_with_tax)
    tax_rate = _d(tax_rate)
    amount_without_tax = (amount_with_tax / (Decimal('1') + tax_rate)).quantize(Q2)
    tax_amount = (amount_with_tax - amount_without_tax).quantize(Q2)

    # 解析日期
    try:
        parsed_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")

    try:
        with unit_of_work(db):
            cmd = CreateInvoice(
                account_id=account_id,
                operator=operator,
                invoice_no=invoice_no,
                direction=direction,
                invoice_type=invoice_type,
                tax_rate=tax_rate,
                amount_without_tax=amount_without_tax,
                tax_amount=tax_amount,
                amount_with_tax=amount_with_tax,
                counterparty_name=counterparty_name,
                issue_date=parsed_date,
                pdf_path=file_path,
                project_name=project_name,
                notes=notes,
            )
            db_invoice = dispatch(cmd, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="发票号码已存在")
    db.refresh(db_invoice)
    return _invoice_to_out(db_invoice)


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """返回PDF文件"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.account_id == account_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    if not invoice.pdf_path or not os.path.exists(invoice.pdf_path):
        raise HTTPException(status_code=404, detail="PDF文件不存在")
    
    return FileResponse(invoice.pdf_path, media_type="application/pdf")


@router.post("/{invoice_id}/certify")
async def certify_invoice_endpoint(
    invoice_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """认证进项专票"""
    with unit_of_work(db):
        try:
            dispatch(CertifyInvoice(account_id=account_id, operator=operator, invoice_id=invoice_id), db)
        except ValueError as e:
            if "不存在" in str(e):
                raise HTTPException(status_code=404, detail=str(e))
            raise HTTPException(status_code=400, detail=str(e))
    return {"message": "发票认证成功"}


@router.put("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """更新发票"""
    try:
        with unit_of_work(db):
            update_kwargs = {}
            for k in ('invoice_no', 'direction', 'invoice_type', 'tax_rate',
                      'amount_without_tax', 'tax_amount', 'amount_with_tax',
                      'counterparty_name', 'issue_date', 'pdf_path',
                      'certification_status', 'certification_date',
                      'project_name', 'related_order_id', 'related_order_type',
                      'notes', 'image_url'):
                v = getattr(invoice_update, k, None)
                if v is not None:
                    update_kwargs[k] = v
            cmd = UpdateInvoice(
                account_id=account_id,
                operator=operator,
                invoice_id=invoice_id,
                **update_kwargs
            )
            invoice = dispatch(cmd, db)
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        raise HTTPException(status_code=400, detail="发票号码已存在")
    db.refresh(invoice)
    return _invoice_to_out(invoice)


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """删除发票"""
    # 先查记录获取pdf_path（路由层删除PDF文件，Command层删除DB记录+图片）
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.account_id == account_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")

    # 保存pdf_path，因为dispatch后会丢失
    pdf_path = invoice.pdf_path

    with unit_of_work(db):
        try:
            dispatch(DeleteInvoice(account_id=account_id, operator=operator, invoice_id=invoice_id), db)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # 删除PDF文件（如果存在）
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            pass  # 文件清理失败不影响主操作

    return {"message": "发票删除成功"}