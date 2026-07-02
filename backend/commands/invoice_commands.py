"""发票 Command + Handler — 4个命令覆盖发票全部业务操作

从 routers/invoices.py 发票逻辑提取，Command 模式封装。
每个 Handler 包含：数据校验 → ORM 操作 → 日志记录。
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, List

import models
from enums import InvoiceDirection, InvoiceType, CertificationStatus
from utils import _d, Q2
from errors import BusinessError, ErrorCode

from .base import Command, CommandHandler, register
from crud.base import _log
from image_utils import delete_old_image
from accounting_engine import AccountingEngine
from lineage import reads, TIER_L3
from lineage import writes, TIER_L3
from crud.invoice_linkage import validate_link_target
from rules import enforce_rules

# 全局 AccountingEngine 实例
_engine = AccountingEngine()


def _date_iso(value) -> str:
    """规范化日期为 YYYY-MM-DD（兼容 date / datetime / 字符串）"""
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
    @writes("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.certification_date_l3", tier=TIER_L3, source="policy")
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

        # 5.1 保存发票商品明细
        for it in cmd.items:
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            inv_item = models.InvoiceItem(
                invoice_id=db_invoice.id,
                product_id=it['product_id'],
                quantity_l1=it['quantity'],
                unit_price_l1=it['unit_price'],
                tax_rate_l1=it.get('tax_rate', cmd.tax_rate),
                total_price_l1=line_total,
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

        # AS-02 价税分离校验(发票三段平衡 + 税率合法性)
        enforce_rules(db, ["AS-02"], {"invoice_id": db_invoice.id})

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
    @writes("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.certification_date_l3", tier=TIER_L3, source="policy")
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
    @writes("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.certification_date_l3", tier=TIER_L3, source="policy")
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
        invoice.certification_status_l3 = "certified"
        invoice.certification_date_l3 = datetime.now()

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
    items: List[dict] = field(default_factory=list)  # 发票商品明细行
    purchase_order_action: Optional[str] = None  # 固定资产场景一般留空，直接过账 1601/222102/2202

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
    @writes("Invoice.certification_status_l3", tier=TIER_L3, source="policy")
    @writes("Invoice.certification_date_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.salvage_rate_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.useful_life_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.depreciation_method_l3", tier=TIER_L3, source="policy")
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
            tax_rate_l1=_d(cmd.tax_rate),
            amount_without_tax_l1=amount_without_tax,
            tax_amount_l1=tax_amount,
            amount_with_tax_l1=amount_with_tax,
            counterparty_name=cmd.counterparty_name,
            seller_name=cmd.seller_name,
            buyer_name=cmd.buyer_name,
            issue_date_l1=issue_date,
            notes=cmd.notes,
            related_order_type="fixed_asset",
            # 默认 n_a，下方根据纳税人类型 + 发票类型 + 是否抵扣决定是否自动认证
        )
        db.add(db_invoice)
        db.flush()

        # 5.1 保存发票商品明细行（与 CreateInvoiceHandler 一致）
        for it in cmd.items:
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            inv_item = models.InvoiceItem(
                invoice_id=db_invoice.id,
                product_id=it['product_id'],
                quantity_l1=it['quantity'],
                unit_price_l1=it['unit_price'],
                tax_rate_l1=it.get('tax_rate', cmd.tax_rate),
                total_price_l1=line_total,
            )
            db.add(inv_item)

        # 判断进项税抵扣：需同时满足「一般纳税人」+「增值税专用发票」
        # 会计实务：普票（普通发票）即使一般纳税人也不能抵扣进项税，全额进资产成本。
        # - 小规模 / 普票：全额进资产（不抵扣进项税）
        # - 一般纳税人 + 专票：不含税金额进资产 + 税额进 222102 抵扣
        from finance_integration import post_journal
        from engine_finance import FinanceEngine
        fe = FinanceEngine(db, cmd.account_id)
        acct_conf = fe._account_config()
        enable_vat_deduction = acct_conf["enable_vat_deduction"] and cmd.invoice_type == InvoiceType.SPECIAL
        # 覆盖 account_config 中的标志，确保凭证模板 _build_fixed_asset_purchase
        # 使用修正后的口径（否则一般纳税人普票会错误地拆分进项税）
        acct_conf["enable_vat_deduction"] = enable_vat_deduction
        asset_original_value = amount_with_tax if not enable_vat_deduction else amount_without_tax

        # 自动认证：一般纳税人 + 专票 + 实际抵扣进项税 → 发票即抵扣即认证
        # 会计实务：固定资产采购专票在入账抵扣时同步认证（无独立认证流程）。
        # 数据一致性：dr 222102 已在下方分录中申报抵扣，发票表 certification_status
        # 必须同步为 "certified"，否则 crud/invoices.py 与 crud/finance/tax_declarations.py
        # 按 "certified" 过滤会漏掉这笔税额 → 申报 input_vat 与 222102 总账不一致。
        if enable_vat_deduction:
            db_invoice.certification_status_l3 = CertificationStatus.CERTIFIED
            db_invoice.certification_date_l3 = datetime.combine(issue_date, datetime.min.time())
            db.flush()

        # 创建固定资产（原值口径与总账分录保持一致，确保 BS 平衡）
        db_asset = models.FixedAsset(
            account_id=cmd.account_id,
            asset_code=cmd.asset_code,
            name=cmd.asset_name,
            category=cmd.category,
            original_value_l1=asset_original_value,
            salvage_rate_l3=_d(cmd.salvage_rate) if cmd.salvage_rate else Decimal('0.05'),
            useful_life_l3=cmd.useful_life,
            depreciation_method_l3=cmd.depreciation_method,
            start_date_l1=start_date,
            accumulated_depreciation_l4=_d(cmd.accumulated_depreciation) if cmd.accumulated_depreciation else Decimal('0'),
            status=cmd.asset_status,
        )
        db.add(db_asset)
        db.flush()

        # 回写关联ID
        db_invoice.related_order_id = db_asset.id
        db.flush()

        # AS-02 价税分离校验(固定资产发票同普通发票,三段平衡 + 税率合法性)
        enforce_rules(db, ["AS-02"], {"invoice_id": db_invoice.id})

        # 5.2 总账过账：dr 1601(不含税或价税合计) / dr 222102(进项税额) / cr 2202(价税合计)
        # source_model + source_id 提供幂等防御（重复提交不会重复过账）
        # 按 counterparty_name 匹配供应商作为 partner_id（与 _auto_generate_purchase_order 一致）
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

        _log(db, cmd.account_id, "create", "invoice", db_invoice.id,
             f"创建固定资产发票: {db_invoice.invoice_no}", operator=cmd.operator)
        _log(db, cmd.account_id, "create", "fixed_asset", db_asset.id,
             f"创建固定资产: {db_asset.name}", operator=cmd.operator)

        return {"invoice": db_invoice, "asset": db_asset}


# ═══════════════════════════════════════════════════════════
# 6. UpdateInvoiceWithFixedAsset — 发票+固定资产联合更新
# ═══════════════════════════════════════════════════════════

@dataclass
# ═══════════════════════════════════════════════════════════
# 9. ReverseInvoice — 红字发票冲红
# ═══════════════════════════════════════════════════════════

@dataclass
class ReverseInvoice(Command):
    invoice_id: int = 0
    reason: str = ""


@register(ReverseInvoice)
class ReverseInvoiceHandler(CommandHandler):
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: ReverseInvoice, db: Any) -> Any:
        """红字发票冲红：标记原发票 + 创建红字发票 + 级联冲红凭证和库存

        级联规则：
        - 关联销售单：reverse_sale（冲红收入/应收/税额凭证）+ InventoryEngine.reverse（库存回退）
        - 关联采购单：reverse_purchase（冲红存货/应付/税额凭证）+ InventoryEngine.reverse（库存退回）
        - 无关联订单：仅标记+创建红字发票（独立发票无凭证需冲红）
        - 固定资产发票：reverse_journal("fixed_asset_purchase") + 资产卡片 status="已冲红"
          （不物理删除，资产处置走单独流程）
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
            tax_rate_l1=invoice.tax_rate_l1,
            amount_without_tax_l1=-_d(invoice.amount_without_tax_l1),
            tax_amount_l1=-_d(invoice.tax_amount_l1),
            amount_with_tax_l1=-_d(invoice.amount_with_tax_l1),
            counterparty_name=invoice.counterparty_name,
            seller_name=invoice.seller_name,
            buyer_name=invoice.buyer_name,
            issue_date_l1=datetime.now().date(),
            related_order_id=invoice.related_order_id,
            related_order_type=invoice.related_order_type,
            notes=f"红字发票：冲红原发票 {invoice.invoice_no}(ID:{invoice.id})。原因：{cmd.reason}",
        )
        db.add(red_invoice)
        db.flush()

        # AS-06 红字发票金额为负校验(防止冲红方向错误)
        enforce_rules(db, ["AS-06"], {"invoice_id": red_invoice.id})

        # 5. 级联冲红凭证和库存
        # 修复 #12：检查已有部分退货，冲红剩余部分而非整单
        # 原代码对已部分退货的销售单仍调用 reverse_sale 整单冲红，
        # 导致已退货部分被重复冲红（收入/应收/税额/库存全部错乱）。
        cascade_lines = []

        if invoice.related_order_type == "sale_order" and invoice.related_order_id:
            from engine_finance import FinanceEngine
            from engine_inventory import InventoryEngine
            from enums import OrderStatus
            from sqlalchemy import func as sqlfunc
            import time as _time

            sale_order = db.query(models.SaleOrder).filter(
                models.SaleOrder.id == invoice.related_order_id,
                models.SaleOrder.account_id == cmd.account_id,
            ).first()

            if sale_order and sale_order.status == OrderStatus.CANCELLED:
                # 订单已取消（凭证和库存已整单冲红），无需重复操作
                cascade_lines.append("销售单已取消（凭证库存已冲红，跳过）")

            elif sale_order and sale_order.status == OrderStatus.COMPLETED:
                # 计算已部分退货数量（通过 ref_source_id 关联到原销售单）
                reversed_qty_map = {}
                reversal_moves = db.query(
                    models.StockMove.product_id,
                    sqlfunc.sum(models.StockMove.quantity_l1).label('rev_qty')
                ).filter(
                    models.StockMove.source_type == "sale_order_reversal",
                    models.StockMove.account_id == cmd.account_id,
                    models.StockMove.ref_source_id == sale_order.id,
                ).group_by(models.StockMove.product_id).all()

                for row in reversal_moves:
                    reversed_qty_map[row.product_id] = abs(int(row.rev_qty))

                # 计算剩余需冲红数量
                remaining_items = []
                for item in sale_order.items:
                    already_reversed = reversed_qty_map.get(item.product_id, 0)
                    remaining_qty = item.quantity_l1 - already_reversed
                    if remaining_qty > 0:
                        remaining_items.append((item, remaining_qty))

                if not remaining_items:
                    # 全部已退货，只需冲红销售凭证（库存已全部回退）
                    FinanceEngine(db, cmd.account_id).reverse_sale(sale_order.id)
                    cascade_lines.append("冲红销售凭证（库存已全部退货）")
                else:
                    # 有剩余部分需冲红
                    # 检查是否已有部分退货（决定用 reverse_sale 还是 sale_return）
                    has_partial_return = any(v > 0 for v in reversed_qty_map.values())

                    if has_partial_return:
                        # 已有部分退货 → 用 sale_return 凭证冲红剩余部分
                        # 避免 reverse_sale 整单冲红导致已退货部分重复冲减
                        from finance_integration import post_journal
                        account = db.query(models.Account).filter(
                            models.Account.id == cmd.account_id
                        ).first()
                        taxpayer_type = account.taxpayer_type_l3 if account else "general"

                        total_wt_ret = Decimal("0")
                        total_wot_ret = Decimal("0")
                        tax_ret = Decimal("0")
                        cost_ret = Decimal("0")
                        eng_inv = InventoryEngine(db)
                        red_return_id = int(_time.time() * 1000)

                        for item, rem_qty in remaining_items:
                            product = db.query(models.Product).filter(
                                models.Product.id == item.product_id,
                                models.Product.account_id == cmd.account_id,
                            ).first()
                            if product and product.track_inventory_l3:
                                eng_inv.reverse(
                                    account_id=cmd.account_id,
                                    product_id=item.product_id,
                                    quantity=rem_qty,
                                    unit_cost=Decimal("0"),
                                    source_type="sale_order",
                                    source_id=sale_order.id,
                                    operator=cmd.operator,
                                    source_id_override=red_return_id,
                                )
                                move = db.query(models.StockMove).filter(
                                    models.StockMove.source_type == "sale_order",
                                    models.StockMove.source_id == sale_order.id,
                                    models.StockMove.product_id == item.product_id,
                                ).first()
                                uc = move.unit_cost_l2 if move and move.unit_cost_l2 else Decimal("0")
                                cost_ret += (Decimal(str(rem_qty)) * uc).quantize(Q2)

                            line_total = Decimal(str(item.total_price_l1))
                            ratio = Decimal(str(rem_qty)) / Decimal(str(item.quantity_l1))
                            rev_ret = (line_total * ratio).quantize(Q2)
                            rate = item.tax_rate_l1
                            if taxpayer_type == "small_scale" and rate and rate > 0:
                                rate = Decimal("0.01")
                            t_ret = (rev_ret * Decimal(str(rate))).quantize(Q2) if rate else Decimal("0")

                            total_wot_ret += rev_ret
                            tax_ret += t_ret
                            total_wt_ret += (rev_ret + t_ret).quantize(Q2)

                        post_journal(db, cmd.account_id, "sale_return", {
                            "partner_id": sale_order.customer_id or 0,
                            "total_with_tax": total_wt_ret.quantize(Q2),
                            "total_without_tax": total_wot_ret.quantize(Q2),
                            "tax_amount": tax_ret.quantize(Q2),
                            "cost_return": cost_ret.quantize(Q2),
                            "taxpayer_type": taxpayer_type,
                            "source_model": "sale_return",
                            "source_id": red_return_id,
                            "date": red_invoice.issue_date_l1,
                        })
                        cascade_lines.append(
                            f"冲红剩余销售部分({len(remaining_items)}项，已扣减部分退货)"
                        )
                    else:
                        # 无部分退货 → 整单冲红
                        FinanceEngine(db, cmd.account_id).reverse_sale(sale_order.id)
                        cascade_lines.append("冲红销售凭证")

                        eng_inv = InventoryEngine(db)
                        for item in sale_order.items:
                            unit_cost = _d(item.unit_cost_l2) if item.unit_cost_l2 else Decimal('0')
                            engine_inv_res = eng_inv.reverse(
                                account_id=cmd.account_id,
                                product_id=item.product_id,
                                quantity=item.quantity_l1,
                                unit_cost=unit_cost,
                                source_type="sale_order",
                                source_id=sale_order.id,
                                operator=cmd.operator,
                            )
                        cascade_lines.append(f"库存回退({len(sale_order.items)}项)")
            else:
                cascade_lines.append("销售单状态异常，跳过级联冲红")

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
                    unit_cost = _d(item.unit_price_l1) if item.unit_price_l1 else Decimal('0')
                    engine_inv.reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity_l1,
                        unit_cost=unit_cost,
                        source_type="purchase_order",
                        source_id=purchase_order.id,
                        operator=cmd.operator,
                    )
                cascade_lines.append(f"库存退回({len(purchase_order.items)}项)")

        elif invoice.related_order_type == "expense":
            cascade_lines.append("费用发票（无库存冲红）")

        elif invoice.related_order_type == "fixed_asset":
            # 固定资产发票冲红：
            # 1. 冲红总账凭证（dr 负 1601 / dr 负 222102 / cr 负 2202）—— 反向应付/资产/进项税
            # 2. 资产卡片 status 改为 "已冲红"（停止折旧，保留审计轨迹；不物理删除，因为
            #    资产处置涉及"固定资产清理 + 营业外收支"等单独流程，不应在发票冲红时一并处理）
            asset_id = invoice.related_order_id
            asset = db.query(models.FixedAsset).filter(
                models.FixedAsset.id == asset_id,
                models.FixedAsset.account_id == cmd.account_id,
            ).first()
            if asset:
                if asset.status == "已冲红":
                    cascade_lines.append("资产卡片已冲红，跳过")
                else:
                    # 冲红原固定资产入账凭证（reverse_journal 自带幂等）
                    from finance_integration import reverse_journal
                    reverse_journal(db, cmd.account_id, "fixed_asset_purchase", asset_id)
                    asset.status = "已冲红"
                    cascade_lines.append(f"冲红固定资产凭证 + 资产卡片 #{asset_id} 标记已冲红")
            else:
                cascade_lines.append(f"资产卡片 #{asset_id} 不存在，跳过")

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
    """销项发票联动自动创建销售单：取发票金额，扣库存

    使用 InventoryEngine.outbound() 创建 StockMove + set_calculated_cost 锁定成本（BR-7 合规），
    弃用直接改 inv.quantity 的 sale_deduct。
    """
    from crud.base import _generate_order_no, _log
    from enums import OrderStatus, OrderType, PaymentStatus
    from engine_inventory import InventoryEngine
    from crud.products import get_product
    from datetime import datetime as dt_mod

    issue_dt = invoice.issue_date_l1 if isinstance(invoice.issue_date_l1, dt_mod) else dt_mod.combine(invoice.issue_date_l1, dt_mod.min.time())
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
        total_price_l1=_d(invoice.amount_with_tax_l1),
        tax_amount_l1=_d(invoice.tax_amount_l1),
        sale_date_l1=invoice.issue_date_l1,
    )
    db.add(order)
    db.flush()

    for it in items:
        line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
        item = models.SaleItem(
            order_id=order.id,
            product_id=it['product_id'],
            quantity_l1=it['quantity'],
            unit_price_l1=it['unit_price'],
            tax_rate_l1=it.get('tax_rate', invoice.tax_rate_l1),
            total_price_l1=line_total,
        )
        db.add(item)

    db.flush()

    # 出库写 StockMove + 锁定 unit_cost 到 SaleItem（BR-7 合规）
    eng = InventoryEngine(db)
    for item in order.items:
        product = get_product(db, account_id, item.product_id)
        if product and product.track_inventory_l3:
            unit_cost = eng.outbound(
                account_id=account_id,
                product_id=item.product_id,
                quantity=item.quantity_l1,
                source_type="sale_order",
                source_id=order.id,
                operator=operator,
            )
            item.set_calculated_cost(unit_cost)
        else:
            item.set_calculated_cost(Decimal("0"))

    # 生成会计凭证: dr 1122, cr 6001+222101 + dr 6401, cr 1405
    from engine_finance import FinanceEngine
    FinanceEngine(db, account_id).record_sale(order)

    _log(db, account_id, "create", "sale_order", order.id,
         f"发票 {invoice.invoice_no} 自动生成销售单 {order_no}: 价税合计={invoice.amount_with_tax_l1}, 税额={invoice.tax_amount_l1}",
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
    issue_dt = invoice.issue_date_l1 if isinstance(invoice.issue_date_l1, dt_mod) else dt_mod.combine(invoice.issue_date_l1, dt_mod.min.time())
    order_no = _generate_order_no(db, "PO", issue_dt)
    order = models.PurchaseOrder(
        account_id=account_id,
        order_no=order_no,
        supplier_id=supplier_id,
        order_type=OrderType.RETAIL,
        payment_method=PaymentMethod.COMPANY,
        status=OrderStatus.COMPLETED,
        notes=f"由发票 {invoice.invoice_no} 自动生成",
        total_price_l1=Decimal("0"),  # 下面逐行累加
        tax_amount_l1=_d(invoice.tax_amount_l1),
        purchase_date_l1=invoice.issue_date_l1,
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
            quantity_l1=it['quantity'],
            unit_price_l1=it['unit_price'],
            tax_rate_l1=it.get('tax_rate', invoice.tax_rate_l1),
            total_price_l1=line_total,
        )
        db.add(item)
        if product.track_inventory_l3:
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

    order.total_price_l1 = total.quantize(Q2)
    db.flush()

    # 生成会计凭证
    if calculated_data:
        FinanceEngine(db, account_id).record_purchase(order, calculated_data)

    _log(db, account_id, "create", "purchase_order", order.id,
         f"发票 {invoice.invoice_no} 自动生成采购单 {order_no}: 价税合计={invoice.amount_with_tax_l1}, 税额={invoice.tax_amount_l1}",
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
    @writes("FixedAsset.salvage_rate_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.useful_life_l3", tier=TIER_L3, source="policy")
    @writes("FixedAsset.depreciation_method_l3", tier=TIER_L3, source="policy")
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
            old_value = _d(asset.original_value_l1)
            asset.original_value_l1 = original_value

            # 联动：发票金额同步（使用 AccountingEngine）
            if invoice:
                amounts = _engine.calculate_invoice_amounts(
                    amount_with_tax=original_value,
                    tax_rate=invoice.tax_rate_l1
                )
                invoice.amount_without_tax_l1 = amounts.amount_without_tax
                invoice.tax_amount_l1 = amounts.tax_amount
                invoice.amount_with_tax_l1 = amounts.amount_with_tax

                # 同步总账：原值变更必须冲红原 fixed_asset_purchase 凭证 + 按新金额重过账
                # 否则 BS 上 1601 余额与资产卡片原值不一致（资产卡片改了总账没改）
                if original_value != old_value:
                    from finance_integration import reverse_journal, post_journal
                    from engine_finance import FinanceEngine
                    fe = FinanceEngine(db, cmd.account_id)
                    acct_conf = fe._account_config()
                    # 进项税抵扣需同时满足「一般纳税人」+「专票」（与创建时口径一致）
                    enable_vat_deduction = acct_conf["enable_vat_deduction"] and invoice.invoice_type == InvoiceType.SPECIAL
                    acct_conf["enable_vat_deduction"] = enable_vat_deduction
                    # 新原值口径：小规模/普票含税 / 一般纳税人专票不含税（与创建时一致）
                    new_asset_value = amounts.amount_with_tax if not enable_vat_deduction else amounts.amount_without_tax

                    # 1. 冲红旧凭证（force=True 跳过幂等：允许反复"冲红+重过"）
                    reverse_journal(db, cmd.account_id, "fixed_asset_purchase", asset.id, force=True)

                    # 2. 修正资产卡片原值口径（若与新计算口径不一致则覆盖）
                    if asset.original_value_l1 != new_asset_value:
                        asset.original_value_l1 = new_asset_value

                    # 3. 按 new_asset_value 重新过账（force=True：跳过幂等防御创建新正向凭证）
                    # 按 counterparty_name 匹配供应商
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

                # 同步总账：原值变更必须冲红原 fixed_asset_purchase 凭证 + 按新金额重过账
                # 否则 BS 上 1601 余额与资产卡片原值不一致（资产卡片改了总账没改）
                if original_value != old_value:
                    from finance_integration import reverse_journal, post_journal
                    from engine_finance import FinanceEngine
                    fe = FinanceEngine(db, cmd.account_id)
                    acct_conf = fe._account_config()
                    # 进项税抵扣需同时满足「一般纳税人」+「专票」（与创建时口径一致）
                    enable_vat_deduction = acct_conf["enable_vat_deduction"] and invoice.invoice_type == InvoiceType.SPECIAL
                    acct_conf["enable_vat_deduction"] = enable_vat_deduction
                    # 新原值口径：小规模/普票含税 / 一般纳税人专票不含税（与创建时一致）
                    new_asset_value = amounts.amount_with_tax if not enable_vat_deduction else amounts.amount_without_tax

                    # 1. 冲红旧凭证（force=True 跳过幂等：允许反复"冲红+重过"）
                    reverse_journal(db, cmd.account_id, "fixed_asset_purchase", asset.id, force=True)

                    # 2. 修正资产卡片原值口径（若与新计算口径不一致则覆盖）
                    if asset.original_value != new_asset_value:
                        asset.original_value = new_asset_value

                    # 3. 按 new_asset_value 重新过账（force=True：跳过幂等防御创建新正向凭证）
                    # 按 counterparty_name 匹配供应商
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
                        "date": _date_iso(invoice.issue_date),
                        "source_model": "fixed_asset_purchase",
                        "source_id": asset.id,
                        "account_config": acct_conf,
                    }, force=True)

        # 4. 更新其他资产字段
        if cmd.name is not None:
            asset.name = cmd.name
        if cmd.category is not None:
            asset.category = cmd.category
        if cmd.salvage_rate is not None:
            asset.salvage_rate_l3 = _d(cmd.salvage_rate)
        if cmd.useful_life is not None:
            asset.useful_life_l3 = cmd.useful_life
        if cmd.depreciation_method is not None:
            asset.depreciation_method_l3 = cmd.depreciation_method
        if cmd.start_date is not None:
            asset.start_date_l1 = datetime.strptime(cmd.start_date, "%Y-%m-%d").date()
        if cmd.status is not None:
            asset.status = cmd.status

        db.flush()

        _log(db, cmd.account_id, "update", "fixed_asset", asset.id,
             f"更新资产: {asset.name}", operator=cmd.operator)
        if invoice:
            _log(db, cmd.account_id, "update", "invoice", invoice.id,
                 f"联动更新发票: {invoice.invoice_no}", operator=cmd.operator)

        return {"asset": asset, "invoice": invoice}

        return {"invoice": invoice, "asset": asset}