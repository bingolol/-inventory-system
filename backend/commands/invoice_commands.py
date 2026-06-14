"""发票 Command + Handler — 4个命令覆盖发票全部业务操作

从 routers/invoices.py 发票逻辑提取，Command 模式封装。
每个 Handler 包含：数据校验 → ORM 操作 → 日志记录。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import models
from enums import InvoiceDirection, InvoiceType

from .base import Command, CommandHandler, register
from .crud_compat import _log, delete_old_image


# ═══════════════════════════════════════════════════════════
# 1. CreateInvoice — 创建发票
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateInvoice(Command):
    invoice_no: str = ""
    direction: str = ""
    invoice_type: str = ""
    tax_rate: Any = None                # Decimal
    amount_without_tax: Any = None      # Decimal
    tax_amount: Any = None              # Decimal
    amount_with_tax: Any = None         # Decimal
    counterparty_name: str = ""
    issue_date: Any = None              # datetime or str
    pdf_path: Optional[str] = None
    certification_status: str = "n_a"
    certification_date: Any = None      # Optional[datetime]
    related_order_id: Optional[int] = None
    related_order_type: Optional[str] = None
    notes: str = ""


@register(CreateInvoice)
class CreateInvoiceHandler(CommandHandler):
    def handle(self, cmd: CreateInvoice, db: Any) -> Any:
        # 1. 校验发票号码唯一性
        existing = db.query(models.Invoice).filter(
            models.Invoice.account_id == cmd.account_id,
            models.Invoice.invoice_no == cmd.invoice_no,
        ).first()
        if existing:
            raise ValueError("发票号码已存在")

        # 2. 解析 issue_date
        issue_date = cmd.issue_date
        if isinstance(issue_date, str):
            try:
                issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"日期格式无效: {issue_date}，应为 YYYY-MM-DD")

        # 3. 创建 ORM 对象
        db_invoice = models.Invoice(
            account_id=cmd.account_id,
            invoice_no=cmd.invoice_no,
            direction=cmd.direction,
            invoice_type=cmd.invoice_type,
            tax_rate=cmd.tax_rate,
            amount_without_tax=cmd.amount_without_tax,
            tax_amount=cmd.tax_amount,
            amount_with_tax=cmd.amount_with_tax,
            counterparty_name=cmd.counterparty_name,
            issue_date=issue_date,
            pdf_path=cmd.pdf_path,
            certification_status=cmd.certification_status,
            certification_date=cmd.certification_date,
            related_order_id=cmd.related_order_id,
            related_order_type=cmd.related_order_type,
            notes=cmd.notes,
        )
        db.add(db_invoice)
        db.flush()

        # 4. 日志
        _log(db, cmd.account_id, "create", "invoice", db_invoice.id,
             f"创建发票: {db_invoice.invoice_no} ({db_invoice.direction}/{db_invoice.invoice_type})",
             operator=cmd.operator)
        db.flush()
        return db_invoice


# ═══════════════════════════════════════════════════════════
# 2. UpdateInvoice — 更新发票
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateInvoice(Command):
    invoice_id: int = 0
    invoice_no: Optional[str] = None
    direction: Optional[str] = None
    invoice_type: Optional[str] = None
    tax_rate: Any = None                    # Optional[Decimal]
    amount_without_tax: Any = None          # Optional[Decimal]
    tax_amount: Any = None                  # Optional[Decimal]
    amount_with_tax: Any = None             # Optional[Decimal]
    counterparty_name: Optional[str] = None
    issue_date: Any = None                  # Optional[datetime]
    pdf_path: Optional[str] = None
    certification_status: Optional[str] = None
    certification_date: Any = None          # Optional[datetime]
    related_order_id: Optional[int] = None
    related_order_type: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None


@register(UpdateInvoice)
class UpdateInvoiceHandler(CommandHandler):
    def handle(self, cmd: UpdateInvoice, db: Any) -> Any:
        # 1. 查记录
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise ValueError("发票不存在")

        # 2. 校验发票号码唯一性（如果修改了发票号码）
        if cmd.invoice_no is not None and cmd.invoice_no != invoice.invoice_no:
            existing = db.query(models.Invoice).filter(
                models.Invoice.account_id == cmd.account_id,
                models.Invoice.invoice_no == cmd.invoice_no,
                models.Invoice.id != cmd.invoice_id,
            ).first()
            if existing:
                raise ValueError("发票号码已存在")

        # 3. 更新字段
        field_map = {
            'invoice_no': cmd.invoice_no,
            'direction': cmd.direction,
            'invoice_type': cmd.invoice_type,
            'tax_rate': cmd.tax_rate,
            'amount_without_tax': cmd.amount_without_tax,
            'tax_amount': cmd.tax_amount,
            'amount_with_tax': cmd.amount_with_tax,
            'counterparty_name': cmd.counterparty_name,
            'issue_date': cmd.issue_date,
            'pdf_path': cmd.pdf_path,
            'certification_status': cmd.certification_status,
            'certification_date': cmd.certification_date,
            'related_order_id': cmd.related_order_id,
            'related_order_type': cmd.related_order_type,
            'notes': cmd.notes,
            'image_url': cmd.image_url,
        }
        for k, v in field_map.items():
            if v is not None:
                setattr(invoice, k, v)

        # 4. 日志
        _log(db, cmd.account_id, "update", "invoice", cmd.invoice_id,
             f"更新发票: {invoice.invoice_no}", operator=cmd.operator)
        db.flush()
        return invoice


# ═══════════════════════════════════════════════════════════
# 3. DeleteInvoice — 删除发票
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteInvoice(Command):
    invoice_id: int = 0


@register(DeleteInvoice)
class DeleteInvoiceHandler(CommandHandler):
    def handle(self, cmd: DeleteInvoice, db: Any) -> Any:
        # 1. 查记录
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise ValueError("发票不存在")

        # 2. 删除关联图片
        if invoice.image_url:
            delete_old_image(invoice.image_url)

        # 3. 日志 + 删除
        _log(db, cmd.account_id, "delete", "invoice", cmd.invoice_id,
             f"删除发票: {invoice.invoice_no}", operator=cmd.operator)

        db.delete(invoice)
        db.flush()
        return True


# ═══════════════════════════════════════════════════════════
# 4. CertifyInvoice — 认证进项专票
# ═══════════════════════════════════════════════════════════

@dataclass
class CertifyInvoice(Command):
    invoice_id: int = 0


@register(CertifyInvoice)
class CertifyInvoiceHandler(CommandHandler):
    def handle(self, cmd: CertifyInvoice, db: Any) -> Any:
        # 1. 查记录
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise ValueError("发票不存在")

        # 2. 校验
        if invoice.direction != InvoiceDirection.IN:
            raise ValueError("只有进项发票可以认证")

        if invoice.invoice_type != InvoiceType.SPECIAL:
            raise ValueError("只有专票可以认证")

        # 3. 认证
        invoice.certification_status = "certified"
        invoice.certification_date = datetime.now()

        # 4. 日志
        _log(db, cmd.account_id, "update", "invoice", cmd.invoice_id,
             f"认证发票: {invoice.invoice_no}", operator=cmd.operator)
        db.flush()
        return invoice