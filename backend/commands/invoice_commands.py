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
from utils import _d, Q2
from errors import BusinessError, ErrorCode

from .base import Command, CommandHandler, register
from .crud_compat import _log, delete_old_image
from accounting_engine import AccountingEngine
from crud.invoice_linkage import validate_link_target

# 全局 AccountingEngine 实例
_engine = AccountingEngine()


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
    image_url: Optional[str] = None
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
            raise BusinessError(
                code=ErrorCode.INVOICE_DUPLICATE_NUMBER,
                data={"invoice_number": cmd.invoice_no}
            )

        # 2. 校验关联目标存在(防孤儿引用)
        validate_link_target(db, cmd.account_id, cmd.related_order_type, cmd.related_order_id)

        # 3. 解析 issue_date
        issue_date = cmd.issue_date
        if isinstance(issue_date, str):
            try:
                issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
            except ValueError:
                raise BusinessError(
                    code=ErrorCode.INVOICE_INVALID_DATE,
                    data={"date": issue_date}
                )

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
            image_url=cmd.image_url,
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
            raise BusinessError(
                code=ErrorCode.INVOICE_NOT_FOUND,
                data={"invoice_id": cmd.invoice_id}
            )

        # 2. 校验发票号码唯一性（如果修改了发票号码）
        if cmd.invoice_no is not None and cmd.invoice_no != invoice.invoice_no:
            existing = db.query(models.Invoice).filter(
                models.Invoice.account_id == cmd.account_id,
                models.Invoice.invoice_no == cmd.invoice_no,
                models.Invoice.id != cmd.invoice_id,
            ).first()
            if existing:
                raise BusinessError(
                    code=ErrorCode.INVOICE_DUPLICATE_NUMBER,
                    data={"invoice_number": cmd.invoice_no}
                )

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
            raise BusinessError(
                code=ErrorCode.INVOICE_NOT_FOUND,
                data={"invoice_id": cmd.invoice_id}
            )

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
            raise BusinessError(
                code=ErrorCode.INVOICE_NOT_FOUND,
                data={"invoice_id": cmd.invoice_id}
            )

        # 2. 校验
        if invoice.direction != InvoiceDirection.IN:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="只有进项发票可以认证",
                ai_instruction="STOP_RETRYING. 只有进项发票（direction=in）可以认证。请检查发票方向。"
            )

        if invoice.invoice_type != InvoiceType.SPECIAL:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="只有专票可以认证",
                ai_instruction="STOP_RETRYING. 只有专用发票（invoice_type=special）可以认证。请检查发票类型。"
            )

        # 3. 认证
        invoice.certification_status = "certified"
        invoice.certification_date = datetime.now()

        # 4. 日志
        _log(db, cmd.account_id, "update", "invoice", cmd.invoice_id,
             f"认证发票: {invoice.invoice_no}", operator=cmd.operator)
        db.flush()
        return invoice


# ═══════════════════════════════════════════════════════════
# 5. CreateInvoiceWithFixedAsset — 发票+固定资产联合创建
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateInvoiceWithFixedAsset(Command):
    # 发票字段
    invoice_no: str = ""
    direction: str = "in"
    invoice_type: str = "ordinary"
    tax_rate: Any = None
    amount_with_tax: Any = None
    counterparty_name: str = ""
    issue_date: Any = None
    notes: str = ""

    # 固定资产字段
    asset_code: str = ""
    asset_name: str = ""
    category: Optional[str] = None
    salvage_rate: Any = None
    useful_life: int = 0
    depreciation_method: str = "年限平均法"
    start_date: str = ""
    accumulated_depreciation: Any = None
    asset_status: str = "在用"


@register(CreateInvoiceWithFixedAsset)
class CreateInvoiceWithFixedAssetHandler(CommandHandler):
    def handle(self, cmd: CreateInvoiceWithFixedAsset, db: Any) -> Any:
        # 使用 AccountingEngine 计算发票金额
        amounts = _engine.calculate_invoice_amounts(
            amount_with_tax=_d(cmd.amount_with_tax),
            tax_rate=_d(cmd.tax_rate)
        )
        amount_without_tax = amounts.amount_without_tax
        tax_amount = amounts.tax_amount
        amount_with_tax = amounts.amount_with_tax

        issue_date = datetime.strptime(cmd.issue_date, "%Y-%m-%d").date()
        start_date = datetime.strptime(cmd.start_date, "%Y-%m-%d").date()

        # 创建发票
        db_invoice = models.Invoice(
            account_id=cmd.account_id,
            invoice_no=cmd.invoice_no,
            direction=cmd.direction,
            invoice_type=cmd.invoice_type,
            tax_rate=_d(cmd.tax_rate),
            amount_without_tax=amount_without_tax,
            tax_amount=tax_amount,
            amount_with_tax=amount_with_tax,
            counterparty_name=cmd.counterparty_name,
            issue_date=issue_date,
            notes=cmd.notes,
            related_order_type="fixed_asset",
        )
        db.add(db_invoice)
        db.flush()

        # 创建固定资产（原值 = 发票含税金额）
        db_asset = models.FixedAsset(
            account_id=cmd.account_id,
            asset_code=cmd.asset_code,
            name=cmd.asset_name,
            category=cmd.category,
            original_value=amount_with_tax,
            salvage_rate=_d(cmd.salvage_rate) if cmd.salvage_rate else Decimal('0.05'),
            useful_life=cmd.useful_life,
            depreciation_method=cmd.depreciation_method,
            start_date=start_date,
            accumulated_depreciation=_d(cmd.accumulated_depreciation) if cmd.accumulated_depreciation else Decimal('0'),
            status=cmd.asset_status,
        )
        db.add(db_asset)
        db.flush()

        # 回写关联ID
        db_invoice.related_order_id = db_asset.id
        db.flush()

        _log(db, cmd.account_id, "create", "invoice", db_invoice.id,
             f"创建固定资产发票: {db_invoice.invoice_no}", operator=cmd.operator)
        _log(db, cmd.account_id, "create", "fixed_asset", db_asset.id,
             f"创建固定资产: {db_asset.name}", operator=cmd.operator)

        return {"invoice": db_invoice, "asset": db_asset}


# ═══════════════════════════════════════════════════════════
# 6. UpdateInvoiceWithFixedAsset — 发票+固定资产联合更新
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateInvoiceWithFixedAsset(Command):
    invoice_id: int = 0
    # 发票可更新字段
    amount_with_tax: Any = None
    tax_rate: Any = None
    counterparty_name: Optional[str] = None
    issue_date: Optional[str] = None
    notes: Optional[str] = None
    # 资产可更新字段
    asset_name: Optional[str] = None
    category: Optional[str] = None
    salvage_rate: Any = None
    useful_life: Optional[int] = None
    depreciation_method: Optional[str] = None
    start_date: Optional[str] = None
    asset_status: Optional[str] = None


@register(UpdateInvoiceWithFixedAsset)
class UpdateInvoiceWithFixedAssetHandler(CommandHandler):
    def handle(self, cmd: UpdateInvoiceWithFixedAsset, db: Any) -> Any:
        # 1. 查找发票
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise BusinessError(code=ErrorCode.INVOICE_NOT_FOUND, data={"invoice_id": cmd.invoice_id})

        # 2. 查找关联资产
        asset = None
        if invoice.related_order_id and invoice.related_order_type == "fixed_asset":
            asset = db.query(models.FixedAsset).filter(
                models.FixedAsset.id == invoice.related_order_id,
                models.FixedAsset.account_id == cmd.account_id,
            ).first()

        # 3. 更新发票金额（如果传了）
        if cmd.amount_with_tax is not None:
            # 使用 AccountingEngine 计算发票金额
            tax_rate = _d(cmd.tax_rate) if cmd.tax_rate is not None else invoice.tax_rate
            amounts = _engine.calculate_invoice_amounts(
                amount_with_tax=_d(cmd.amount_with_tax),
                tax_rate=tax_rate
            )

            invoice.tax_rate = tax_rate
            invoice.amount_without_tax = amounts.amount_without_tax
            invoice.tax_amount = amounts.tax_amount
            invoice.amount_with_tax = amounts.amount_with_tax

            # 联动：资产原值同步
            if asset:
                asset.original_value = amounts.amount_with_tax

        # 4. 更新其他发票字段
        if cmd.counterparty_name is not None:
            invoice.counterparty_name = cmd.counterparty_name
        if cmd.issue_date is not None:
            invoice.issue_date = datetime.strptime(cmd.issue_date, "%Y-%m-%d").date()
        if cmd.notes is not None:
            invoice.notes = cmd.notes

        # 5. 更新资产字段
        if asset:
            if cmd.asset_name is not None:
                asset.name = cmd.asset_name
            if cmd.category is not None:
                asset.category = cmd.category
            if cmd.salvage_rate is not None:
                asset.salvage_rate = _d(cmd.salvage_rate)
            if cmd.useful_life is not None:
                asset.useful_life = cmd.useful_life
            if cmd.depreciation_method is not None:
                asset.depreciation_method = cmd.depreciation_method
            if cmd.start_date is not None:
                asset.start_date = datetime.strptime(cmd.start_date, "%Y-%m-%d").date()
            if cmd.asset_status is not None:
                asset.status = cmd.asset_status

        db.flush()

        _log(db, cmd.account_id, "update", "invoice", invoice.id,
             f"更新固定资产发票: {invoice.invoice_no}", operator=cmd.operator)
        if asset:
            _log(db, cmd.account_id, "update", "fixed_asset", asset.id,
                 f"联动更新资产: {asset.name}", operator=cmd.operator)

        return {"invoice": invoice, "asset": asset}


# ═══════════════════════════════════════════════════════════
# 8. UpdateAssetWithInvoice — 资产更新联动发票
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateAssetWithInvoice(Command):
    asset_id: int = 0
    # 资产可更新字段
    original_value: Any = None
    name: Optional[str] = None
    category: Optional[str] = None
    salvage_rate: Any = None
    useful_life: Optional[int] = None
    depreciation_method: Optional[str] = None
    start_date: Optional[str] = None
    status: Optional[str] = None


@register(UpdateAssetWithInvoice)
class UpdateAssetWithInvoiceHandler(CommandHandler):
    def handle(self, cmd: UpdateAssetWithInvoice, db: Any) -> Any:
        # 1. 查找资产
        asset = db.query(models.FixedAsset).filter(
            models.FixedAsset.id == cmd.asset_id,
            models.FixedAsset.account_id == cmd.account_id,
        ).first()
        if not asset:
            raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND, data={"asset_id": cmd.asset_id})

        # 2. 查找关联发票
        invoice = db.query(models.Invoice).filter(
            models.Invoice.related_order_id == cmd.asset_id,
            models.Invoice.related_order_type == "fixed_asset",
            models.Invoice.account_id == cmd.account_id,
        ).first()

        # 3. 更新资产原值（如果传了）
        if cmd.original_value is not None:
            original_value = _d(cmd.original_value)
            asset.original_value = original_value

            # 联动：发票金额同步（使用 AccountingEngine）
            if invoice:
                amounts = _engine.calculate_invoice_amounts(
                    amount_with_tax=original_value,
                    tax_rate=invoice.tax_rate
                )
                invoice.amount_without_tax = amounts.amount_without_tax
                invoice.tax_amount = amounts.tax_amount
                invoice.amount_with_tax = amounts.amount_with_tax

        # 4. 更新其他资产字段
        if cmd.name is not None:
            asset.name = cmd.name
        if cmd.category is not None:
            asset.category = cmd.category
        if cmd.salvage_rate is not None:
            asset.salvage_rate = _d(cmd.salvage_rate)
        if cmd.useful_life is not None:
            asset.useful_life = cmd.useful_life
        if cmd.depreciation_method is not None:
            asset.depreciation_method = cmd.depreciation_method
        if cmd.start_date is not None:
            asset.start_date = datetime.strptime(cmd.start_date, "%Y-%m-%d").date()
        if cmd.status is not None:
            asset.status = cmd.status

        db.flush()

        _log(db, cmd.account_id, "update", "fixed_asset", asset.id,
             f"更新资产: {asset.name}", operator=cmd.operator)
        if invoice:
            _log(db, cmd.account_id, "update", "invoice", invoice.id,
                 f"联动更新发票: {invoice.invoice_no}", operator=cmd.operator)

        return {"asset": asset, "invoice": invoice}


# ═══════════════════════════════════════════════════════════
# 7. DeleteInvoiceWithFixedAsset — 发票+固定资产联合删除
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteInvoiceWithFixedAsset(Command):
    invoice_id: int = 0


@register(DeleteInvoiceWithFixedAsset)
class DeleteInvoiceWithFixedAssetHandler(CommandHandler):
    def handle(self, cmd: DeleteInvoiceWithFixedAsset, db: Any) -> Any:
        # 1. 查找发票
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise BusinessError(code=ErrorCode.INVOICE_NOT_FOUND, data={"invoice_id": cmd.invoice_id})

        # 2. 查找关联资产
        asset = None
        if invoice.related_order_id and invoice.related_order_type == "fixed_asset":
            asset = db.query(models.FixedAsset).filter(
                models.FixedAsset.id == invoice.related_order_id,
                models.FixedAsset.account_id == cmd.account_id,
            ).first()

        # 3. 删除资产（先删子表）
        if asset:
            _log(db, cmd.account_id, "delete", "fixed_asset", asset.id,
                 f"级联删除资产: {asset.name}", operator=cmd.operator)
            db.delete(asset)

        # 4. 删除发票
        _log(db, cmd.account_id, "delete", "invoice", invoice.id,
             f"删除固定资产发票: {invoice.invoice_no}", operator=cmd.operator)
        db.delete(invoice)
        db.flush()

        return {"invoice": invoice, "asset": asset}