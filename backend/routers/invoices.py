from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional
from datetime import datetime
from fastapi.responses import FileResponse
from decimal import Decimal
import os

from database import get_db
from models import Invoice
from schemas import InvoiceCreate, InvoiceUpdate, InvoiceOut, InvoiceQuickCreate, PaginatedResponse
from account_dep import get_account_id, get_operator
from enums import InvoiceDirection, InvoiceType
from image_utils import delete_old_image
from uow import unit_of_work
from commands.base import dispatch
from commands.invoice_commands import (
    CreateInvoice, UpdateInvoice, DeleteInvoice, CertifyInvoice,
    CreateInvoiceWithFixedAsset,
)
from accounting_engine import AccountingEngine

from utils import _d, Q2
from workspace import get_pdfs_dir as _get_pdfs_dir
from errors import BusinessError, ErrorCode
from operation_result import OperationResult, EntityType, OperationType

router = APIRouter()

# 金额计算统一走 AccountingEngine（ROUND_HALF_UP），消除历史上的多套舍入实现
_engine = AccountingEngine()

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


@router.post("")
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
                related_order_id=invoice.related_order_id,
                related_order_type=invoice.related_order_type,
                notes=invoice.notes,
            )
            db_invoice = dispatch(cmd, db)
    except ValueError as e:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message=str(e))
    except IntegrityError:
        raise BusinessError(code=ErrorCode.INVOICE_DUPLICATE_NUMBER, data={"invoice_number": invoice.invoice_no})
    db.refresh(db_invoice)
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.INVOICE,
        entity_id=db_invoice.id,
        summary=f"发票 {db_invoice.invoice_no} 创建成功，金额 {db_invoice.amount_with_tax}",
        ai_hint="发票已创建。",
        data=_invoice_to_out(db_invoice).model_dump()
    )
    return result.to_dict()


@router.post("/quick")
async def quick_create_invoice(
    invoice: InvoiceQuickCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """AI 快捷录入发票（规范接口）

    - 仅传 amount_with_tax + tax_rate，系统自动算不含税金额/税额（统一走 AccountingEngine，ROUND_HALF_UP）。
    - 携带可选 `fixed_asset` 嵌套对象时，同事务内原子创建发票 + 固定资产并关联
      （合并自原 POST /with-fixed-asset，能力保留、入口统一）。
    """
    # 统一金额计算（消除历史上 ROUND_HALF_EVEN / ROUND_HALF_UP 两套实现的不一致）
    amounts = _engine.calculate_invoice_amounts(
        amount_with_tax=_d(invoice.amount_with_tax),
        tax_rate=_d(invoice.tax_rate),
    )

    try:
        with unit_of_work(db):
            if invoice.fixed_asset is not None:
                fa = invoice.fixed_asset
                cmd = CreateInvoiceWithFixedAsset(
                    account_id=account_id,
                    operator=operator,
                    invoice_no=invoice.invoice_no,
                    direction=invoice.direction,
                    invoice_type=invoice.invoice_type,
                    tax_rate=invoice.tax_rate,
                    amount_with_tax=invoice.amount_with_tax,
                    counterparty_name=invoice.counterparty_name,
                    issue_date=invoice.issue_date,
                    notes=invoice.notes,
                    asset_code=fa.asset_code,
                    asset_name=fa.asset_name,
                    category=fa.category,
                    salvage_rate=fa.salvage_rate,
                    useful_life=fa.useful_life,
                    depreciation_method=fa.depreciation_method,
                    start_date=fa.start_date,
                    accumulated_depreciation=fa.accumulated_depreciation,
                    asset_status=fa.asset_status,
                )
                result = dispatch(cmd, db)
                db_invoice = result["invoice"]
                db_asset = result["asset"]
            else:
                cmd = CreateInvoice(
                    account_id=account_id,
                    operator=operator,
                    invoice_no=invoice.invoice_no,
                    direction=invoice.direction,
                    invoice_type=invoice.invoice_type,
                    tax_rate=invoice.tax_rate,
                    amount_without_tax=amounts.amount_without_tax,
                    tax_amount=amounts.tax_amount,
                    amount_with_tax=amounts.amount_with_tax,
                    counterparty_name=invoice.counterparty_name,
                    issue_date=invoice.issue_date,
                    image_url=invoice.image_url,  # 修复：原 handler 丢弃了 schema 里的 image_url
                    notes=invoice.notes,
                )
                db_invoice = dispatch(cmd, db)
                db_asset = None
    except ValueError as e:
        raise BusinessError(code=ErrorCode.INVOICE_INVALID_DATE, message=str(e))
    except IntegrityError:
        raise BusinessError(code=ErrorCode.INVOICE_DUPLICATE_NUMBER, data={"invoice_number": invoice.invoice_no})
    db.refresh(db_invoice)
    if db_asset is not None:
        db.refresh(db_asset)

    # 统一返回 OperationResult（修复：原 response_model=InvoiceOut 与实际返回体不一致）
    op = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.INVOICE,
        entity_id=db_invoice.id,
        summary=f"发票 {db_invoice.invoice_no} 创建成功，金额 {db_invoice.amount_with_tax}",
        ai_hint="发票 + 固定资产已原子创建并关联。" if db_asset else "发票已创建。",
        data=_invoice_to_out(db_invoice).model_dump(),
    )
    out = op.to_dict()
    if db_asset is not None:
        out["data"]["fixed_asset"] = {
            "id": db_asset.id,
            "asset_code": db_asset.asset_code,
            "name": db_asset.name,
            "original_value": str(db_asset.original_value),
            "start_date": db_asset.start_date.isoformat() if db_asset.start_date else None,
        }
    return out


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
    notes: str = Form(None),
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """上传发票PDF并创建发票记录（前端 el-upload 使用，AI 应走 /quick）"""
    # 保存PDF文件（.pdf 扩展名校验）
    if not file.filename.endswith('.pdf'):
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="只支持PDF文件")
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(PDF_DIR, f"{account_id}_{safe_filename}")
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # 金额计算统一走 AccountingEngine（原为路由层内联 quantize，舍入行为不一致）
    amounts = _engine.calculate_invoice_amounts(
        amount_with_tax=_d(amount_with_tax),
        tax_rate=_d(tax_rate),
    )

    # 日期解析与唯一性校验由 CreateInvoice Command 负责，路由层不再重复
    try:
        with unit_of_work(db):
            cmd = CreateInvoice(
                account_id=account_id,
                operator=operator,
                invoice_no=invoice_no,
                direction=direction,
                invoice_type=invoice_type,
                tax_rate=tax_rate,
                amount_without_tax=amounts.amount_without_tax,
                tax_amount=amounts.tax_amount,
                amount_with_tax=amounts.amount_with_tax,
                counterparty_name=counterparty_name,
                issue_date=issue_date,
                pdf_path=file_path,
                notes=notes,
            )
            db_invoice = dispatch(cmd, db)
    except IntegrityError:
        raise BusinessError(code=ErrorCode.INVOICE_DUPLICATE_NUMBER, data={"invoice_number": invoice_no})
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
        dispatch(CertifyInvoice(account_id=account_id, operator=operator, invoice_id=invoice_id), db)
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.INVOICE,
        entity_id=invoice_id,
        summary=f"发票认证成功",
        ai_hint="发票已认证，可在税务报表中抵扣进项税额。",
        data={"invoice_id": invoice_id}
    )
    return result.to_dict()


@router.put("/{invoice_id}")
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
                      'related_order_id', 'related_order_type',
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
    except IntegrityError:
        raise BusinessError(code=ErrorCode.INVOICE_DUPLICATE_NUMBER, data={"invoice_number": invoice_update.invoice_no})
    db.refresh(invoice)
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.INVOICE,
        entity_id=invoice.id,
        summary=f"发票 {invoice.invoice_no} 更新成功",
        ai_hint="发票已更新。",
        data=_invoice_to_out(invoice).model_dump()
    )
    return result.to_dict()


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
        raise BusinessError(code=ErrorCode.INVOICE_NOT_FOUND, data={"invoice_id": invoice_id})

    # 保存pdf_path，因为dispatch后会丢失
    pdf_path = invoice.pdf_path

    with unit_of_work(db):
        dispatch(DeleteInvoice(account_id=account_id, operator=operator, invoice_id=invoice_id), db)

    # 删除PDF文件（如果存在）
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            pass  # 文件清理失败不影响主操作

    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.DELETE,
        entity_type=EntityType.INVOICE,
        entity_id=invoice_id,
        summary=f"发票 {invoice.invoice_no} 删除成功",
        ai_hint="发票已删除。",
        data={"invoice_id": invoice_id, "invoice_no": invoice.invoice_no}
    )
    return result.to_dict()
