"""发票 Command + Handler — 4个命令覆盖发票全部业务操作

从 routers/invoices.py 发票逻辑提取，Command 模式封装。
每个 Handler 包含：数据校验 → ORM 操作 → 日志记录。
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, List

import models
from enums import InvoiceDirection, InvoiceType
from utils import _d, Q2
from errors import BusinessError, ErrorCode

from .base import Command, CommandHandler, register
from crud.base import _log
from image_utils import delete_old_image
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
    seller_name: str = ""
    buyer_name: str = ""
    issue_date: Any = None              # datetime or str
    pdf_path: Optional[str] = None
    image_url: Optional[str] = None
    certification_status: str = "n_a"
    certification_date: Any = None      # Optional[datetime]
    related_order_id: Optional[int] = None
    related_order_type: Optional[str] = None
    notes: str = ""
    items: List[dict] = field(default_factory=list)
    sale_order_action: Optional[str] = None  # link_existing / auto_create (销项)
    purchase_order_action: Optional[str] = None  # link_existing / auto_create (进项)


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

        # 3. 校验发票金额等式
        _engine.validate_invoice_amounts(
            amount_without_tax=cmd.amount_without_tax,
            tax_amount=cmd.tax_amount,
            amount_with_tax=cmd.amount_with_tax
        )

        # 4. 解析 issue_date
        issue_date = cmd.issue_date
        if isinstance(issue_date, str):
            try:
                issue_date = datetime.strptime(issue_date, "%Y-%m-%d").date()
            except ValueError:
                raise BusinessError(
                    code=ErrorCode.INVOICE_INVALID_DATE,
                    data={"date": issue_date}
                )

        # 5. 创建 ORM 对象
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
            seller_name=cmd.seller_name,
            buyer_name=cmd.buyer_name,
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

        # 5.1 保存发票商品明细
        for it in cmd.items:
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            inv_item = models.InvoiceItem(
                invoice_id=db_invoice.id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                tax_rate=it.get('tax_rate', cmd.tax_rate),
                total_price=line_total,
            )
            db.add(inv_item)

        # 5.2 销项发票：根据 sale_order_action 关联或自动生成销售单
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

        # 5.3 进项发票：根据 purchase_order_action 关联或自动生成采购单
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

        # 6. 日志
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
    seller_name: str = ""
    buyer_name: str = ""
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
            seller_name=cmd.seller_name,
            buyer_name=cmd.buyer_name,
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
# 9. ReverseInvoice — 红字发票冲红
# ═══════════════════════════════════════════════════════════

@dataclass
class ReverseInvoice(Command):
    invoice_id: int = 0
    reason: str = ""


@register(ReverseInvoice)
class ReverseInvoiceHandler(CommandHandler):
    def handle(self, cmd: ReverseInvoice, db: Any) -> Any:
        """红字发票冲红：标记原发票 + 创建红字发票 + 级联冲红凭证和库存

        级联规则：
        - 关联销售单：reverse_sale（冲红收入/应收/税额凭证）+ InventoryEngine.reverse（库存回退）
        - 关联采购单：reverse_purchase（冲红存货/应付/税额凭证）+ InventoryEngine.reverse（库存退回）
        - 无关联订单：仅标记+创建红字发票（独立发票无凭证需冲红）
        - 固定资产发票：标记+创建红字发票（资产冲红需人工处理）
        """

        # 1. 查原发票
        invoice = db.query(models.Invoice).filter(
            models.Invoice.id == cmd.invoice_id,
            models.Invoice.account_id == cmd.account_id,
        ).first()
        if not invoice:
            raise BusinessError(
                code=ErrorCode.INVOICE_NOT_FOUND,
                data={"invoice_id": cmd.invoice_id}
            )

        # 2. 幂等：已冲红则报错
        if invoice.is_reversed:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"发票 {invoice.invoice_no} 已被冲红，不可重复操作",
                ai_instruction="STOP_RETRYING. 该发票已冲红，无需再次冲红。"
            )

        # 3. 标记原发票
        invoice.is_reversed = True
        invoice.reversed_at = datetime.now()

        # 4. 创建红字发票（负数金额，方向不变）
        red_invoice_no = f"H-{invoice.invoice_no}"
        # 确保红字发票号唯一
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
            tax_rate=invoice.tax_rate,
            amount_without_tax=-_d(invoice.amount_without_tax),
            tax_amount=-_d(invoice.tax_amount),
            amount_with_tax=-_d(invoice.amount_with_tax),
            counterparty_name=invoice.counterparty_name,
            seller_name=invoice.seller_name,
            buyer_name=invoice.buyer_name,
            issue_date=datetime.now().date(),
            related_order_id=invoice.related_order_id,
            related_order_type=invoice.related_order_type,
            notes=f"红字发票：冲红原发票 {invoice.invoice_no}(ID:{invoice.id})。原因：{cmd.reason}",
        )
        db.add(red_invoice)
        db.flush()

        # 5. 级联冲红凭证和库存
        cascade_lines = []

        if invoice.related_order_type == "sale_order" and invoice.related_order_id:
            # 销项发票 → 冲红销售凭证（收入/应收/税额）
            from engine_finance import FinanceEngine
            FinanceEngine(db, cmd.account_id).reverse_sale(invoice.related_order_id)
            cascade_lines.append("冲红销售凭证")

            # 冲红库存（库存回退）
            from engine_inventory import InventoryEngine
            engine_inv = InventoryEngine(db)
            sale_order = db.query(models.SaleOrder).filter(
                models.SaleOrder.id == invoice.related_order_id,
                models.SaleOrder.account_id == cmd.account_id,
            ).first()
            if sale_order:
                for item in sale_order.items:
                    unit_cost = _d(item.unit_cost) if item.unit_cost else Decimal('0')
                    engine_inv.reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        unit_cost=unit_cost,
                        source_type="sale_order",
                        source_id=sale_order.id,
                        operator=cmd.operator,
                    )
                cascade_lines.append(f"库存回退({len(sale_order.items)}项)")

        elif invoice.related_order_type == "purchase_order" and invoice.related_order_id:
            # 进项发票 → 冲红采购凭证（存货/应付/税额）
            from engine_finance import FinanceEngine
            FinanceEngine(db, cmd.account_id).reverse_purchase(invoice.related_order_id)
            cascade_lines.append("冲红采购凭证")

            # 冲红库存（库存退回）
            from engine_inventory import InventoryEngine
            engine_inv = InventoryEngine(db)
            purchase_order = db.query(models.PurchaseOrder).filter(
                models.PurchaseOrder.id == invoice.related_order_id,
                models.PurchaseOrder.account_id == cmd.account_id,
            ).first()
            if purchase_order:
                for item in purchase_order.items:
                    unit_cost = _d(item.unit_price) if item.unit_price else Decimal('0')
                    engine_inv.reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        unit_cost=unit_cost,
                        source_type="purchase_order",
                        source_id=purchase_order.id,
                        operator=cmd.operator,
                    )
                cascade_lines.append(f"库存退回({len(purchase_order.items)}项)")

        elif invoice.related_order_type == "expense":
            cascade_lines.append("费用发票（无库存冲红）")

        elif invoice.related_order_type == "fixed_asset":
            cascade_lines.append("固定资产发票（资产冲红需人工处理）")

        else:
            cascade_lines.append("独立发票（无级联冲红）")

        # 6. 日志
        _log(db, cmd.account_id, "reverse", "invoice", invoice.id,
             f"红字发票冲红: {invoice.invoice_no} → {red_invoice_no}, 级联: {', '.join(cascade_lines)}",
             operator=cmd.operator)
        db.flush()

        return {"original_invoice": invoice, "red_invoice": red_invoice,
                "cascade": cascade_lines}


# ═══════════════════════════════════════════════════════════
# 辅助函数：发票自动生成销售单/采购单
# ═══════════════════════════════════════════════════════════

def _auto_generate_sale_order(db, account_id: int, operator: str, invoice, items: list):
    """销项发票联动自动创建销售单：取发票金额，扣库存"""
    from crud.base import _generate_order_no, _log
    from enums import OrderStatus, OrderType, PaymentStatus
    from crud.inventory_ops import sale_deduct
    from datetime import datetime as dt_mod

    issue_dt = invoice.issue_date if isinstance(invoice.issue_date, dt_mod) else dt_mod.combine(invoice.issue_date, dt_mod.min.time())
    order_no = _generate_order_no(db, "SO", issue_dt)

    # 从发票 counterparty_name 查找或创建客户
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

    order = models.SaleOrder(
        account_id=account_id,
        order_no=order_no,
        customer_id=customer_id,
        order_type=OrderType.RETAIL,
        payment_status=PaymentStatus.UNPAID,
        status=OrderStatus.COMPLETED,
        notes=f"由发票 {invoice.invoice_no} 自动生成",
        total_price=_d(invoice.amount_with_tax),
        tax_amount=_d(invoice.tax_amount),
        sale_date=invoice.issue_date,
    )
    db.add(order)
    db.flush()

    for it in items:
        line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
        item = models.SaleItem(
            order_id=order.id,
            product_id=it['product_id'],
            quantity=it['quantity'],
            unit_price=it['unit_price'],
            tax_rate=it.get('tax_rate', invoice.tax_rate),
            total_price=line_total,
        )
        db.add(item)

    db.flush()
    sale_deduct(db, account_id, order, operator=operator)

    # 生成会计凭证: dr 1122, cr 6001+222101 + dr 6401, cr 1405
    from engine_finance import FinanceEngine
    FinanceEngine(db, account_id).record_sale(order)

    _log(db, account_id, "create", "sale_order", order.id,
         f"发票 {invoice.invoice_no} 自动生成销售单 {order_no}: 价税合计={invoice.amount_with_tax}, 税额={invoice.tax_amount}",
         operator=operator)
    db.flush()
    return order


def _auto_generate_purchase_order(db, account_id: int, operator: str, invoice, items: list):
    """进项发票创建后自动生成采购单，金额取发票金额，入库。

    使用 InventoryEngine.inbound() 创建 StockMove（BR-7 合规）。
    按 counterparty_name 匹配已有供应商。
    """
    from crud.base import _generate_order_no, _log
    from crud.products import get_product
    from enums import OrderStatus, OrderType, PaymentMethod
    from engine_inventory import InventoryEngine
    from engine_finance import FinanceEngine

    # 按发票 counterparty_name 匹配已有供应商
    supplier_id = None
    supplier = db.query(models.Supplier).filter(
        models.Supplier.account_id == account_id,
        models.Supplier.name == invoice.counterparty_name,
    ).first()
    if supplier:
        supplier_id = supplier.id

    from datetime import datetime as dt_mod
    issue_dt = invoice.issue_date if isinstance(invoice.issue_date, dt_mod) else dt_mod.combine(invoice.issue_date, dt_mod.min.time())
    order_no = _generate_order_no(db, "PO", issue_dt)
    order = models.PurchaseOrder(
        account_id=account_id,
        order_no=order_no,
        supplier_id=supplier_id,
        order_type=OrderType.RETAIL,
        payment_method=PaymentMethod.COMPANY,
        status=OrderStatus.COMPLETED,
        notes=f"由发票 {invoice.invoice_no} 自动生成",
        total_price=Decimal("0"),  # 下面逐行累加
        tax_amount=_d(invoice.tax_amount),
        purchase_date=invoice.issue_date,
    )
    db.add(order)
    db.flush()

    total = Decimal("0")
    calculated_data = []
    for it in items:
        product = get_product(db, account_id, it['product_id'])
        if not product:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
        line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
        item = models.PurchaseItem(
            order_id=order.id,
            product_id=it['product_id'],
            quantity=it['quantity'],
            unit_price=it['unit_price'],
            tax_rate=it.get('tax_rate', invoice.tax_rate),
            total_price=line_total,
        )
        db.add(item)
        if product.track_inventory:
            calc = InventoryEngine(db).inbound(
                account_id=account_id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                source_type="purchase_order",
                source_id=order.id,
                tax_rate=it.get('tax_rate'),
                operator=operator,
            )
            calculated_data.append(calc)
        total += line_total

    order.total_price = total.quantize(Q2)
    db.flush()

    # 生成会计凭证
    if calculated_data:
        FinanceEngine(db, account_id).record_purchase(order, calculated_data)

    _log(db, account_id, "create", "purchase_order", order.id,
         f"发票 {invoice.invoice_no} 自动生成采购单 {order_no}: 价税合计={invoice.amount_with_tax}, 税额={invoice.tax_amount}",
         operator=operator)
    db.flush()
    return order


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