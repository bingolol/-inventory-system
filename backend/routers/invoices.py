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
from account_dep import get_account_id
from image_utils import delete_old_image
from uow import unit_of_work

router = APIRouter()

Q2 = Decimal('0.01')

def _d(val):
    """安全转换为 Decimal"""
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))

# PDF 文件存储路径
PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdfs")
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


@router.get("/", response_model=PaginatedResponse)
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


@router.post("/", response_model=InvoiceOut)
async def create_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """创建发票，校验发票号码唯一性"""
    # 验证发票号码唯一性
    existing_invoice = db.query(Invoice).filter(
        Invoice.account_id == account_id,
        Invoice.invoice_no == invoice.invoice_no
    ).first()
    if existing_invoice:
        raise HTTPException(status_code=400, detail="发票号码已存在")
    
    # 创建发票
    db_invoice = Invoice(
        account_id=account_id,
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
        notes=invoice.notes
    )
    try:
        with unit_of_work(db):
            db.add(db_invoice)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="发票号码已存在")
    db.refresh(db_invoice)
    return _invoice_to_out(db_invoice)


@router.post("/quick", response_model=InvoiceOut)
async def quick_create_invoice(
    invoice: InvoiceQuickCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """AI快捷录入发票，自动计算不含税金额和税额"""
    # 验证发票号码唯一性
    existing_invoice = db.query(Invoice).filter(
        Invoice.account_id == account_id,
        Invoice.invoice_no == invoice.invoice_no
    ).first()
    if existing_invoice:
        raise HTTPException(status_code=400, detail="发票号码已存在")
    
    # 自动计算不含税金额和税额
    amount_with_tax = _d(invoice.amount_with_tax)
    tax_rate = _d(invoice.tax_rate)
    amount_without_tax = (amount_with_tax / (Decimal('1') + tax_rate)).quantize(Q2)
    tax_amount = (amount_with_tax - amount_without_tax).quantize(Q2)
    
    # 创建发票
    db_invoice = Invoice(
        account_id=account_id,
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
        notes=invoice.notes
    )
    try:
        with unit_of_work(db):
            db.add(db_invoice)
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
    account_id: int = Depends(get_account_id)
):
    """上传发票PDF并创建发票记录，参数与quick接口相同，额外支持文件上传"""
    # 验证发票号码唯一性
    existing_invoice = db.query(Invoice).filter(
        Invoice.account_id == account_id,
        Invoice.invoice_no == invoice_no
    ).first()
    if existing_invoice:
        raise HTTPException(status_code=400, detail="发票号码已存在")

    # 保存PDF文件
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    file_path = os.path.join(PDF_DIR, f"{account_id}_{file.filename}")
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

    # 创建发票记录
    db_invoice = Invoice(
        account_id=account_id,
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
        notes=notes
    )
    try:
        with unit_of_work(db):
            db.add(db_invoice)
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
async def certify_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """认证进项专票"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.account_id == account_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    if invoice.direction != "in":
        raise HTTPException(status_code=400, detail="只有进项发票可以认证")
    
    if invoice.invoice_type != "special":
        raise HTTPException(status_code=400, detail="只有专票可以认证")
    
    # 认证发票
    with unit_of_work(db):
        invoice.certification_status = "certified"
        invoice.certification_date = datetime.now()
    
    return {"message": "发票认证成功"}


@router.put("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """更新发票"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.account_id == account_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    # 验证发票号码唯一性（如果修改了发票号码）
    if invoice_update.invoice_no and invoice_update.invoice_no != invoice.invoice_no:
        existing_invoice = db.query(Invoice).filter(
            Invoice.account_id == account_id,
            Invoice.invoice_no == invoice_update.invoice_no,
            Invoice.id != invoice_id
        ).first()
        if existing_invoice:
            raise HTTPException(status_code=400, detail="发票号码已存在")
    
    # 更新发票
    update_data = invoice_update.model_dump(exclude_unset=True)
    try:
        with unit_of_work(db):
            for field, value in update_data.items():
                setattr(invoice, field, value)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="发票号码已存在")
    db.refresh(invoice)
    return _invoice_to_out(invoice)


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """删除发票"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.account_id == account_id
    ).first()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    # 删除PDF文件（如果存在）
    if invoice.pdf_path and os.path.exists(invoice.pdf_path):
        try:
            os.remove(invoice.pdf_path)
        except Exception:
            pass
    
    # 删除关联图片文件
    if invoice.image_url:
        delete_old_image(invoice.image_url)
    
    # 删除发票
    with unit_of_work(db):
        db.delete(invoice)
    
    return {"message": "发票删除成功"}