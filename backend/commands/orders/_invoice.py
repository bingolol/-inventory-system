"""发票 Command + Handler — 6 个命令覆盖发票全部业务操作

发票专有命令，不涉及销售/采购订单的创建/取消（那些在 _order.py）。
冲红级联逻辑在 _cascade.py。
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, List

import models
from enums import InvoiceDirection, InvoiceType, CertificationStatus
from utils import to_decimal, Q2
from errors import BusinessError, ErrorCode

from commands.base import Command, CommandHandler, register
from ._lifecycle import OrderLifecycle
from crud.base import log_op
from image_utils import delete_old_image
from accounting_engine import AccountingEngine
from lineage import reads, writes, TIER_L1, TIER_L3
from policy.vat_facts import VAT_SMALL_SCALE_REDUCED_RATE
from policy.entity_profile import build_profile
from crud.invoice_linkage import validate_link_target
from rules import enforce_rules

from . import _cascade

_engine = AccountingEngine()


def _date_iso(value) -> str:
    if value is None:
        from datetime import date as _date
        return _date.today().isoformat()
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


# ═══════════════════════════════════════════════════════════
# 1. CreateInvoice — 创建发票
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateInvoice(Command):
    invoice_no: str = ""
    direction: str = ""
    invoice_type: str = ""
    tax_rate: Any = None
    amount_without_tax: Any = None
    tax_amount: Any = None
    amount_with_tax: Any = None
    counterparty_name: str = ""
    seller_name: str = ""
    buyer_name: str = ""
    issue_date: Any = None
    pdf_path: Optional[str] = None
    image_url: Optional[str] = None
    certification_status: str = "n_a"
    certification_date: Any = None
    related_order_id: Optional[int] = None
    related_order_type: Optional[str] = None
    notes: str = ""
    items: List[dict] = field(default_factory=list)
    sale_order_action: Optional[str] = None
    purchase_order_action: Optional[str] = None


@register(CreateInvoice)
class CreateInvoiceHandler(CommandHandler):
    @writes("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.certification_date_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("Invoice.amount_without_tax_l1", tier=TIER_L1, source="external")
    @writes("Invoice.tax_amount_l1", tier=TIER_L1, source="external")
    @writes("Invoice.amount_with_tax_l1", tier=TIER_L1, source="external")
    @writes("Invoice.issue_date_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: CreateInvoice, db: Any) -> Any:
        existing = db.query(models.Invoice).filter(
            models.Invoice.account_id == cmd.account_id,
            models.Invoice.invoice_no == cmd.invoice_no,
        ).first()
        if existing:
            raise BusinessError(
                code=ErrorCode.INVOICE_DUPLICATE_NUMBER,
                data={"invoice_number": cmd.invoice_no}
            )
        validate_link_target(db, cmd.account_id, cmd.related_order_type, cmd.related_order_id)
        _engine.validate_invoice_amounts(
            amount_without_tax=cmd.amount_without_tax,
            tax_amount=cmd.tax_amount,
            amount_with_tax=cmd.amount_with_tax
        )
        issue_date = cmd.issue_date
        if isinstance(issue_date, str):
            try:
                issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
            except ValueError:
                raise BusinessError(
                    code=ErrorCode.INVOICE_INVALID_DATE,
                    data={"date": issue_date}
                )

        db_invoice = models.Invoice(
            account_id=cmd.account_id,
            invoice_no=cmd.invoice_no,
            direction=cmd.direction,
            invoice_type=cmd.invoice_type,
            tax_rate_l1=cmd.tax_rate,
            amount_without_tax_l1=cmd.amount_without_tax,
            tax_amount_l1=cmd.tax_amount,
            amount_with_tax_l1=cmd.amount_with_tax,
            counterparty_name=cmd.counterparty_name,
            seller_name=cmd.seller_name,
            buyer_name=cmd.buyer_name,
            issue_date_l1=issue_date,
            pdf_path=cmd.pdf_path,
            image_url=cmd.image_url,
            certification_status_l3=cmd.certification_status,
            certification_date_l3=cmd.certification_date,
            related_order_id=cmd.related_order_id,
            related_order_type=cmd.related_order_type,
            notes=cmd.notes,
        )
        db.add(db_invoice)
        db.flush()

        for it in cmd.items:
            line_total = (Decimal(str(it['quantity'])) * to_decimal(it['unit_price'])).quantize(Q2)
            inv_item = models.InvoiceItem(
                invoice_id=db_invoice.id,
                product_id=it['product_id'],
                quantity_l1=it['quantity'],
                unit_price_l1=it['unit_price'],
                tax_rate_l1=it.get('tax_rate', cmd.tax_rate),
                total_price_l1=line_total,
            )
            db.add(inv_item)

        if cmd.direction == InvoiceDirection.OUT:
            if cmd.sale_order_action == "link_existing":
                if not cmd.related_order_id:
                    raise BusinessError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="sale_order_action=link_existing 时必填 related_order_id"
                    )
                db_invoice.related_order_type = "sale_order"
                db_invoice.related_order_id = cmd.related_order_id
            elif cmd.sale_order_action == "auto_create":
                sale_order = _auto_generate_sale_order(
                    db, cmd.account_id, cmd.operator, db_invoice, cmd.items
                )
                db_invoice.related_order_type = "sale_order"
                db_invoice.related_order_id = sale_order.id

        if cmd.direction == InvoiceDirection.IN:
            if cmd.purchase_order_action == "link_existing":
                if not cmd.related_order_id:
                    raise BusinessError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="purchase_order_action=link_existing 时必填 related_order_id"
                    )
                db_invoice.related_order_type = "purchase_order"
                db_invoice.related_order_id = cmd.related_order_id
            elif cmd.purchase_order_action == "auto_create":
                purchase_order = _auto_generate_purchase_order(
                    db, cmd.account_id, cmd.operator, db_invoice, cmd.items
                )
                db_invoice.related_order_type = "purchase_order"
                db_invoice.related_order_id = purchase_order.id

        db.flush()
        enforce_rules(db, ["AS-02"], {"invoice_id": db_invoice.id})
        log_op(db, cmd.account_id, "create", "invoice", db_invoice.id,
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
    tax_rate: Any = None
    amount_without_tax: Any = None
    tax_amount: Any = None
    amount_with_tax: Any = None
    counterparty_name: Optional[str] = None
    issue_date: Any = None
    pdf_path: Optional[str] = None
    certification_status: Optional[str] = None
    certification_date: Any = None
    related_order_id: Optional[int] = None
    related_order_type: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None


@register(UpdateInvoice)
class UpdateInvoiceHandler(CommandHandler):
    @writes("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.certification_date_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: UpdateInvoice, db: Any) -> Any:
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise BusinessError(
                code=ErrorCode.INVOICE_NOT_FOUND,
                data={"invoice_id": cmd.invoice_id}
            )
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
        field_map = {
            'invoice_no': cmd.invoice_no,
            'direction': cmd.direction,
            'invoice_type': cmd.invoice_type,
            'tax_rate_l1': cmd.tax_rate,
            'amount_without_tax_l1': cmd.amount_without_tax,
            'tax_amount_l1': cmd.tax_amount,
            'amount_with_tax_l1': cmd.amount_with_tax,
            'counterparty_name': cmd.counterparty_name,
            'issue_date_l1': cmd.issue_date,
            'pdf_path': cmd.pdf_path,
            'certification_status_l3': cmd.certification_status,
            'certification_date_l3': cmd.certification_date,
            'related_order_id': cmd.related_order_id,
            'related_order_type': cmd.related_order_type,
            'notes': cmd.notes,
            'image_url': cmd.image_url,
        }
        for k, v in field_map.items():
            if v is not None:
                setattr(invoice, k, v)
        log_op(db, cmd.account_id, "update", "invoice", cmd.invoice_id,
             f"更新发票: {invoice.invoice_no}", operator=cmd.operator)
        db.flush()
        return invoice


# ═══════════════════════════════════════════════════════════
# 3. CertifyInvoice — 认证进项专票
# ═══════════════════════════════════════════════════════════

@dataclass
class CertifyInvoice(Command):
    invoice_id: int = 0


@register(CertifyInvoice)
class CertifyInvoiceHandler(CommandHandler):
    @writes("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.certification_date_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: CertifyInvoice, db: Any) -> Any:
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise BusinessError(
                code=ErrorCode.INVOICE_NOT_FOUND,
                data={"invoice_id": cmd.invoice_id}
            )
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
        invoice.certification_status_l3 = "certified"
        invoice.certification_date_l3 = datetime.now()
        log_op(db, cmd.account_id, "update", "invoice", cmd.invoice_id,
             f"认证发票: {invoice.invoice_no}", operator=cmd.operator)
        db.flush()
        return invoice


# ═══════════════════════════════════════════════════════════
# 4. CreateInvoiceWithFixedAsset — 发票+固定资产联合创建
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateInvoiceWithFixedAsset(Command):
    invoice_no: str = ""
    direction: str = "in"
    invoice_type: str = "ordinary"
    tax_rate: Any = None
    amount_with_tax: Any = None
    counterparty_name: str = ""
    seller_name: str = ""
    buyer_name: str = ""
    issue_date: Any = None
    notes: str = ""
    items: List[dict] = field(default_factory=list)
    purchase_order_action: Optional[str] = None
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
    @writes("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.certification_date_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.salvage_rate_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.useful_life_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.depreciation_method_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("Invoice.amount_without_tax_l1", tier=TIER_L1, source="external")
    @writes("Invoice.tax_amount_l1", tier=TIER_L1, source="external")
    @writes("Invoice.amount_with_tax_l1", tier=TIER_L1, source="external")
    @writes("Invoice.issue_date_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: CreateInvoiceWithFixedAsset, db: Any) -> Any:
        amounts = _engine.calculate_invoice_amounts(
            amount_with_tax=to_decimal(cmd.amount_with_tax),
            tax_rate=to_decimal(cmd.tax_rate)
        )
        amount_without_tax = amounts.amount_without_tax
        tax_amount = amounts.tax_amount
        amount_with_tax = amounts.amount_with_tax

        issue_date = datetime.strptime(cmd.issue_date, "%Y-%m-%d").date()
        start_date = datetime.strptime(cmd.start_date, "%Y-%m-%d").date()

        db_invoice = models.Invoice(
            account_id=cmd.account_id,
            invoice_no=cmd.invoice_no,
            direction=cmd.direction,
            invoice_type=cmd.invoice_type,
            tax_rate_l1=to_decimal(cmd.tax_rate),
            amount_without_tax_l1=amount_without_tax,
            tax_amount_l1=tax_amount,
            amount_with_tax_l1=amount_with_tax,
            counterparty_name=cmd.counterparty_name,
            seller_name=cmd.seller_name,
            buyer_name=cmd.buyer_name,
            issue_date_l1=issue_date,
            notes=cmd.notes,
            related_order_type="fixed_asset",
        )
        db.add(db_invoice)
        db.flush()

        for it in cmd.items:
            line_total = (Decimal(str(it['quantity'])) * to_decimal(it['unit_price'])).quantize(Q2)
            inv_item = models.InvoiceItem(
                invoice_id=db_invoice.id,
                product_id=it['product_id'],
                quantity_l1=it['quantity'],
                unit_price_l1=it['unit_price'],
                tax_rate_l1=it.get('tax_rate', cmd.tax_rate),
                total_price_l1=line_total,
            )
            db.add(inv_item)

        from finance_integration import post_journal
        from engine_finance import FinanceEngine
        fe = FinanceEngine(db, cmd.account_id)
        acct_conf = fe._account_config()
        enable_vat_deduction = acct_conf["enable_vat_deduction"] and cmd.invoice_type == InvoiceType.SPECIAL
        acct_conf["enable_vat_deduction"] = enable_vat_deduction
        asset_original_value = amount_with_tax if not enable_vat_deduction else amount_without_tax

        if enable_vat_deduction:
            db_invoice.certification_status_l3 = CertificationStatus.CERTIFIED
            db_invoice.certification_date_l3 = datetime.combine(issue_date, datetime.min.time())
            db.flush()

        db_asset = models.FixedAsset(
            account_id=cmd.account_id,
            asset_code=cmd.asset_code,
            name=cmd.asset_name,
            category=cmd.category,
            original_value_l1=asset_original_value,
            salvage_rate_l3=to_decimal(cmd.salvage_rate) if cmd.salvage_rate else Decimal('0.05'),
            useful_life_l3=cmd.useful_life,
            depreciation_method_l3=cmd.depreciation_method,
            start_date_l1=start_date,
            accumulated_depreciation_l4=to_decimal(cmd.accumulated_depreciation) if cmd.accumulated_depreciation else Decimal('0'),
            status=cmd.asset_status,
        )
        db.add(db_asset)
        db.flush()

        db_invoice.related_order_id = db_asset.id
        db.flush()

        enforce_rules(db, ["AS-02"], {"invoice_id": db_invoice.id})

        supplier_id = None
        if cmd.counterparty_name:
            supplier = db.query(models.Supplier).filter(
                models.Supplier.account_id == cmd.account_id,
                models.Supplier.name == cmd.counterparty_name,
            ).first()
            if supplier:
                supplier_id = supplier.id

        post_journal(db, cmd.account_id, "fixed_asset_purchase", {
            "original_value": asset_original_value,
            "tax_amount": tax_amount if enable_vat_deduction else Decimal("0"),
            "amount_with_tax": amount_with_tax,
            "asset_id": db_asset.id,
            "partner_id": supplier_id,
            "date": _date_iso(issue_date),
            "source_model": "fixed_asset_purchase",
            "source_id": db_asset.id,
            "account_config": acct_conf,
        })

        log_op(db, cmd.account_id, "create", "invoice", db_invoice.id,
             f"创建固定资产发票: {db_invoice.invoice_no}", operator=cmd.operator)
        log_op(db, cmd.account_id, "create", "fixed_asset", db_asset.id,
             f"创建固定资产: {db_asset.name}", operator=cmd.operator)

        return {"invoice": db_invoice, "asset": db_asset}


# ═══════════════════════════════════════════════════════════
# 5. ReverseInvoice — 红字发票冲红
# ═══════════════════════════════════════════════════════════

@dataclass
class ReverseInvoice(Command):
    invoice_id: int = 0
    reason: str = ""


@register(ReverseInvoice)
class ReverseInvoiceHandler(CommandHandler):
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("Invoice.amount_without_tax_l1", tier=TIER_L1, source="external")
    @writes("Invoice.tax_amount_l1", tier=TIER_L1, source="external")
    @writes("Invoice.amount_with_tax_l1", tier=TIER_L1, source="external")
    @writes("Invoice.issue_date_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: ReverseInvoice, db: Any) -> Any:
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise BusinessError(
                code=ErrorCode.INVOICE_NOT_FOUND,
                data={"invoice_id": cmd.invoice_id}
            )
        if invoice.is_reversed:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"发票 {invoice.invoice_no} 已被冲红，不可重复操作",
                ai_instruction="STOP_RETRYING. 该发票已冲红，无需再次冲红。"
            )

        invoice.is_reversed = True
        invoice.reversed_at = datetime.now()

        red_invoice_no = f"H-{invoice.invoice_no}"
        existing_red = db.query(models.Invoice).filter(
            models.Invoice.account_id == cmd.account_id,
            models.Invoice.invoice_no == red_invoice_no,
        ).first()
        if existing_red:
            red_invoice_no = f"H-{invoice.invoice_no}-{invoice.id}"

        red_invoice = models.Invoice(
            account_id=cmd.account_id,
            invoice_no=red_invoice_no,
            direction=invoice.direction,
            invoice_type=invoice.invoice_type,
            tax_rate_l1=invoice.tax_rate_l1,
            amount_without_tax_l1=-to_decimal(invoice.amount_without_tax_l1),
            tax_amount_l1=-to_decimal(invoice.tax_amount_l1),
            amount_with_tax_l1=-to_decimal(invoice.amount_with_tax_l1),
            counterparty_name=invoice.counterparty_name,
            seller_name=invoice.seller_name,
            buyer_name=invoice.buyer_name,
            issue_date_l1=invoice.issue_date_l1,  # BR-REV: 用原发票日期，避免跨期冲红时发票口径错位（与 BR-22 同源）
            related_order_id=invoice.related_order_id,
            related_order_type=invoice.related_order_type,
            notes=f"红字发票：冲红原发票 {invoice.invoice_no}(ID:{invoice.id})。原因：{cmd.reason}",
        )
        db.add(red_invoice)
        db.flush()

        enforce_rules(db, ["AS-06"], {"invoice_id": red_invoice.id})

        cascade_result = _cascade.resolve_reversal(
            db=db,
            account_id=cmd.account_id,
            operator=cmd.operator,
            invoice=invoice,
            red_invoice=red_invoice,
            reason=cmd.reason,
        )

        log_op(db, cmd.account_id, "reverse", "invoice", invoice.id,
             f"红字发票冲红: {invoice.invoice_no} → {red_invoice_no}, 级联: {', '.join(cascade_result)}",
             operator=cmd.operator)
        db.flush()

        return {"original_invoice": invoice, "red_invoice": red_invoice,
                "cascade": cascade_result}


# ═══════════════════════════════════════════════════════════
# 6. UpdateAssetWithInvoice — 资产更新联动发票
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateAssetWithInvoice(Command):
    asset_id: int = 0
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
    @writes("FixedAsset.salvage_rate_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.useful_life_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.depreciation_method_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: UpdateAssetWithInvoice, db: Any) -> Any:
        asset = db.query(models.FixedAsset).filter(
            models.FixedAsset.id == cmd.asset_id,
            models.FixedAsset.account_id == cmd.account_id,
        ).first()
        if not asset:
            raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND, data={"asset_id": cmd.asset_id})
        invoice = db.query(models.Invoice).filter(
            models.Invoice.related_order_id == cmd.asset_id,
            models.Invoice.related_order_type == "fixed_asset",
            models.Invoice.account_id == cmd.account_id,
        ).first()

        if cmd.original_value is not None:
            original_value = to_decimal(cmd.original_value)
            old_value = to_decimal(asset.original_value_l1)
            asset.original_value_l1 = original_value
            if invoice:
                amounts = _engine.calculate_invoice_amounts(
                    amount_with_tax=original_value,
                    tax_rate=invoice.tax_rate_l1
                )
                invoice.amount_without_tax_l1 = amounts.amount_without_tax
                invoice.tax_amount_l1 = amounts.tax_amount
                invoice.amount_with_tax_l1 = amounts.amount_with_tax
                if original_value != old_value:
                    from finance_integration import reverse_journal, post_journal
                    from engine_finance import FinanceEngine
                    fe = FinanceEngine(db, cmd.account_id)
                    acct_conf = fe._account_config()
                    enable_vat_deduction = acct_conf["enable_vat_deduction"] and invoice.invoice_type == InvoiceType.SPECIAL
                    acct_conf["enable_vat_deduction"] = enable_vat_deduction
                    new_asset_value = amounts.amount_with_tax if not enable_vat_deduction else amounts.amount_without_tax
                    reverse_journal(db, cmd.account_id, "fixed_asset_purchase", asset.id, force=True)
                    if asset.original_value_l1 != new_asset_value:
                        asset.original_value_l1 = new_asset_value
                    supplier_id = None
                    if invoice.counterparty_name:
                        supplier = db.query(models.Supplier).filter(
                            models.Supplier.account_id == cmd.account_id,
                            models.Supplier.name == invoice.counterparty_name,
                        ).first()
                        if supplier:
                            supplier_id = supplier.id
                    post_journal(db, cmd.account_id, "fixed_asset_purchase", {
                        "original_value": new_asset_value,
                        "tax_amount": amounts.tax_amount if enable_vat_deduction else Decimal("0"),
                        "amount_with_tax": amounts.amount_with_tax,
                        "asset_id": asset.id,
                        "partner_id": supplier_id,
                        "date": _date_iso(invoice.issue_date_l1),
                        "source_model": "fixed_asset_purchase",
                        "source_id": asset.id,
                        "account_config": acct_conf,
                    }, force=True)

        if cmd.name is not None:
            asset.name = cmd.name
        if cmd.category is not None:
            asset.category = cmd.category
        if cmd.salvage_rate is not None:
            asset.salvage_rate_l3 = to_decimal(cmd.salvage_rate)
        if cmd.useful_life is not None:
            asset.useful_life_l3 = cmd.useful_life
        if cmd.depreciation_method is not None:
            asset.depreciation_method_l3 = cmd.depreciation_method
        if cmd.start_date is not None:
            asset.start_date_l1 = datetime.strptime(cmd.start_date, "%Y-%m-%d").date()
        if cmd.status is not None:
            asset.status = cmd.status

        db.flush()
        log_op(db, cmd.account_id, "update", "fixed_asset", asset.id,
             f"更新资产: {asset.name}", operator=cmd.operator)
        if invoice:
            log_op(db, cmd.account_id, "update", "invoice", invoice.id,
                 f"联动更新发票: {invoice.invoice_no}", operator=cmd.operator)
        return {"asset": asset, "invoice": invoice}


# ═══════════════════════════════════════════════════════════
# 辅助函数：发票自动生成销售单/采购单
# ═══════════════════════════════════════════════════════════

def _auto_generate_sale_order(db, account_id, operator, invoice, items):
    customer = db.query(models.Customer).filter(
        models.Customer.account_id == account_id,
        models.Customer.name == invoice.counterparty_name,
    ).first()
    if not customer and invoice.counterparty_name:
        customer = models.Customer(
            account_id=account_id, name=invoice.counterparty_name,
            contact="", phone="",
        )
        db.add(customer)
        db.flush()
    customer_id = customer.id if customer else None
    return OrderLifecycle.create_sale_order(
        db=db, account_id=account_id, operator=operator,
        items=items, sale_date=invoice.issue_date_l1,
        customer_id=customer_id,
        total_price=invoice.amount_with_tax_l1,
        tax_amount=invoice.tax_amount_l1,
        has_invoice=True,
        notes=f"由发票 {invoice.invoice_no} 自动生成",
        auto_generated_from=invoice.invoice_no,
    )


def _auto_generate_purchase_order(db, account_id, operator, invoice, items):
    supplier_id = None
    supplier = db.query(models.Supplier).filter(
        models.Supplier.account_id == account_id,
        models.Supplier.name == invoice.counterparty_name,
    ).first()
    if supplier:
        supplier_id = supplier.id
    return OrderLifecycle.create_purchase_order(
        db=db, account_id=account_id, operator=operator,
        items=items, purchase_date=invoice.issue_date_l1,
        supplier_id=supplier_id,
        total_price=invoice.amount_with_tax_l1,
        tax_amount=invoice.tax_amount_l1,
        notes=f"由发票 {invoice.invoice_no} 自动生成",
        auto_generated_from=invoice.invoice_no,
    )
