"""采购单 Command + Handler — 6个命令覆盖采购单全部业务操作

v7 改造后：移除项目模块
  采购单不再关联项目，不再触发项目汇总重算
"""

import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

import models
from enums import OrderStatus, OrderType, InvoiceDirection, CertificationStatus
from events import emit

from .base import Command, CommandHandler, register
from crud.base import _generate_order_no
from crud.products import get_product
from crud.orders import get_purchase_order, _d
from crud.reversal import reverse_payments
from errors import BusinessError, ErrorCode
from utils import Q2
from engine_inventory import InventoryEngine
from engine_finance import FinanceEngine
from lineage import reads, writes, TIER_L1, TIER_L3


# ═══════════════════════════════════════════════════════════
# 1. CreatePurchaseOrder — 创建采购单
# ═══════════════════════════════════════════════════════════

@dataclass
class CreatePurchaseOrder(Command):
    supplier_id: Optional[int] = None
    purchase_date: Optional[datetime] = None
    payment_method: str = "company"
    notes: str = ""
    image_url: str = ""
    items: List[dict] = field(default_factory=list)


@register(CreatePurchaseOrder)
class CreatePurchaseOrderHandler(CommandHandler):
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @writes("PurchaseOrder.total_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseOrder.tax_amount_l1", tier=TIER_L1, source="external")
    @writes("PurchaseOrder.purchase_date_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.quantity_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.unit_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.total_price_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: CreatePurchaseOrder, db: Any) -> Any:
        # 1. 校验
        if not cmd.items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS, data={"order_type": "采购单"})
        product_ids = [it['product_id'] for it in cmd.items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        # 1a. 业务日期必填（级联到凭证日期和库存移动日期，不能用当前时间兜底）
        if not cmd.purchase_date:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="采购日期不能为空，请提供业务发生日期",
                ai_instruction="STOP_RETRYING. purchase_date 字段必填，请补充采购业务日期（如 2025-06-28）。"
            )

        # 2. 生成订单号
        purchase_dt = datetime.fromisoformat(cmd.purchase_date) if isinstance(cmd.purchase_date, str) else cmd.purchase_date
        order_no = _generate_order_no(db, "PO", purchase_dt)

        # 3. 创建订单头
        order = models.PurchaseOrder(
            account_id=cmd.account_id,
            order_no=order_no,
            supplier_id=cmd.supplier_id,
            purchase_date_l1=purchase_dt,
            order_type=OrderType.RETAIL,
            payment_method=cmd.payment_method,
            status=OrderStatus.COMPLETED,
            notes=cmd.notes,
            image_url=cmd.image_url,
            total_price_l1=0,
        )
        db.add(order)
        db.flush()

        # 4. 创建明细行 + InventoryEngine 入库 + 收集价税数据
        total = Decimal('0')
        calculated_data = []
        for it in cmd.items:
            product = get_product(db, cmd.account_id, it['product_id'])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            item = models.PurchaseItem(
                order_id=order.id,
                product_id=it['product_id'],
                quantity_l1=it['quantity'],
                unit_price_l1=it['unit_price'],
                tax_rate_l1=it.get('tax_rate', Decimal('0.13')),
                total_price_l1=line_total,
            )
            db.add(item)
            if product.track_inventory_l3:
                calc = InventoryEngine(db).inbound(
                    account_id=cmd.account_id,
                    product_id=it['product_id'],
                    quantity=it['quantity'],
                    unit_price=it['unit_price'],
                    source_type="purchase_order",
                    source_id=order.id,
                    tax_rate=it.get('tax_rate'),
                    operator=cmd.operator,
                )
                calculated_data.append(calc)
            total += line_total

        order.total_price_l1 = total.quantize(Q2)
        db.flush()

        # 5. 生成会计凭证
        FinanceEngine(db, cmd.account_id).record_purchase(order, calculated_data or None)

        # 6. 事件（Emit-as-Log：emit 携带 log 元数据，由 handlers.py 单写一条 OperationLog）
        emit("purchase_order.created", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator,
             log_action="create",
             log_detail=f"创建采购单 {order_no}: {len(cmd.items)}项商品, 总价={total}")
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 2. CancelPurchaseOrder — 取消采购单
# ═══════════════════════════════════════════════════════════

@dataclass
class CancelPurchaseOrder(Command):
    order_id: int = 0


@register(CancelPurchaseOrder)
class CancelPurchaseOrderHandler(CommandHandler):
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: CancelPurchaseOrder, db: Any) -> Any:
        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": cmd.order_id})
        if order.status == OrderStatus.CANCELLED:
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": order.status, "action": "取消"})

        old_status = order.status

        # 状态变更
        order.status = OrderStatus.CANCELLED

        # 已完成→取消：InventoryEngine 红冲 + FinanceEngine 冲红凭证
        if old_status == OrderStatus.COMPLETED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory_l3:
                    InventoryEngine(db).reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity_l1,
                        unit_cost=Decimal("0"),
                        source_type="purchase_order",
                        source_id=order.id,
                        operator=cmd.operator,
                    )
            FinanceEngine(db, cmd.account_id).reverse_purchase(order.id)

        # 冲销付款记录 + 银行流水
        reverse_payments(db, cmd.account_id, cmd.order_id)

        emit("purchase_order.updated", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator,
             log_action="update",
             log_detail=f"取消采购单 {order.order_no}: 状态={old_status}->cancelled")
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 2b. ReturnPurchaseOrder — 采购退货（部分冲红，保留原单）
# ═══════════════════════════════════════════════════════════

@dataclass
class ReturnPurchaseOrder(Command):
    order_id: int = 0
    return_date: str = ""
    reason: str = ""
    items: List[dict] = field(default_factory=list)  # [{product_id, quantity}]


@register(ReturnPurchaseOrder)
class ReturnPurchaseOrderHandler(CommandHandler):
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: ReturnPurchaseOrder, db: Any) -> Any:
        from finance_integration import post_journal
        # StockMove 定义在 models.py（库存真相源），不在 models_finance.py
        StockMove = models.StockMove

        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                                data={"order_type": "采购单", "order_id": cmd.order_id})
        if order.status != OrderStatus.COMPLETED:
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE,
                                data={"status": order.status, "action": "退货"})

        if not cmd.return_date:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message="退货日期不能为空，请提供业务发生日期",
                                ai_instruction="STOP_RETRYING. return_date 字段必填。")
        if not cmd.items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS,
                                data={"order_type": "采购退货单"})

        # 1. 校验退货数量不超原采购数量
        original_qty_map = {item.product_id: item.quantity_l1 for item in order.items}
        for ret in cmd.items:
            pid = ret['product_id']
            if pid not in original_qty_map:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND,
                                    data={"product_id": pid, "details": "商品不在原采购单中"})
            if ret['quantity'] > original_qty_map[pid]:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"退货数量 {ret['quantity']} 超过原采购数量 {original_qty_map[pid]}",
                    ai_instruction=f"STOP_RETRYING. 商品 ID={pid} 原采购 {original_qty_map[pid]} 件，退货不能超过此数量。"
                )

        # 2. 获取账本配置
        # enable_vat_deduction 不是 Account 字段，而是基于 taxpayer_type 派生
        # （与 engine_finance.py:30 _vat_deduction() 保持一致：一般纳税人=true，小规模=false）
        account = db.query(models.Account).filter(models.Account.id == cmd.account_id).first()
        enable_vat_deduction = (account is not None and account.taxpayer_type_l3 == "general")

        # 3. 库存退回 + 按行计算退货金额
        total_with_tax_ret = Decimal("0")
        tax_amount_ret = Decimal("0")
        inventory_cost_ret = Decimal("0")
        eng = InventoryEngine(db)
        return_id = int(time.time() * 1000)

        for ret in cmd.items:
            pid = ret['product_id']
            qty_ret = Decimal(str(ret['quantity']))
            orig_item = next((it for it in order.items if it.product_id == pid), None)
            if not orig_item:
                continue

            product = db.query(models.Product).filter(
                models.Product.id == pid,
                models.Product.account_id == cmd.account_id,
            ).first()
            if product and product.track_inventory_l3:
                # 库存退回（InventoryEngine.reverse 会创建 quantity<0 的反向流水）
                eng.reverse(
                    account_id=cmd.account_id,
                    product_id=pid,
                    quantity=int(qty_ret),
                    unit_cost=Decimal("0"),
                    source_type="purchase_order",
                    source_id=order.id,
                    operator=cmd.operator,
                    source_id_override=return_id,
                )
                # 取原采购单明细单价计算库存退回金额
                # ⚠️ 必须用 orig_item.unit_price（原发票不含税单价），不能用 StockMove.unit_cost
                # （unit_cost 是移动加权平均成本，会让贷方库存与借方应付账款不一致 → 借贷不平衡）
                orig_unit_price = Decimal(str(orig_item.unit_price_l1))
                # 一般纳税人：不含税金额进成本；小规模：价税合计进成本
                if enable_vat_deduction:
                    inventory_cost_ret += (qty_ret * orig_unit_price).quantize(Q2)
                else:
                    inventory_cost_ret += (qty_ret * orig_unit_price).quantize(Q2)

            # 退货的税额/价税合计计算（按纳税人类型区分）
            # - 一般纳税人：unit_price 不含税，total_with_tax = qty*price*(1+rate)
            # - 小规模：unit_price 含税，total_with_tax = qty*price（无分离）
            unit_price = Decimal(str(orig_item.unit_price_l1))
            rate = orig_item.tax_rate_l1
            if enable_vat_deduction:
                line_without_tax = (unit_price * qty_ret).quantize(Q2)
                line_tax = (line_without_tax * Decimal(str(rate))).quantize(Q2) if rate else Decimal("0")
                line_with_tax = line_without_tax + line_tax
            else:
                # 小规模：unit_price 视为含税，无税额分离
                line_with_tax = (unit_price * qty_ret).quantize(Q2)
                line_tax = Decimal("0")

            total_with_tax_ret += line_with_tax
            tax_amount_ret += line_tax

        total_with_tax_ret = total_with_tax_ret.quantize(Q2)
        tax_amount_ret = tax_amount_ret.quantize(Q2)
        inventory_cost_ret = inventory_cost_ret.quantize(Q2)

        # 4. 过账部分冲红凭证
        post_journal(db, cmd.account_id, "purchase_return", {
            "partner_id": order.supplier_id or 0,
            "total_with_tax": total_with_tax_ret,
            "inventory_cost_return": inventory_cost_ret,
            "tax_return": tax_amount_ret if enable_vat_deduction else Decimal("0"),
            "enable_vat_deduction": enable_vat_deduction,
            "source_model": "purchase_return",
            "source_id": return_id,
            "date": cmd.return_date,
        })

        # 4b. 创建红字进项发票（amount<0，冲减当期进项税额）
        # 按会计实务：采购退货应开具红字增值税发票，红字发票税额直接冲减当期进项税额
        # 季度税务报表查询发票表时自动扣除（正发票 - 红字发票 = 净额）
        original_invoice = db.query(models.Invoice).filter(
            models.Invoice.account_id == cmd.account_id,
            models.Invoice.related_order_type == "purchase_order",
            models.Invoice.related_order_id == order.id,
            models.Invoice.direction == InvoiceDirection.IN,
            models.Invoice.is_reversed == False,
        ).first()

        if original_invoice:
            # 继承原发票类型和税率，金额取负
            red_invoice_no = f"RED-{original_invoice.invoice_no}-{return_id}"
            # 检查是否已存在相同 return_id 的红字发票（幂等：支持多次部分退货各自一张红字发票）
            existing_red = db.query(models.Invoice).filter(
                models.Invoice.account_id == cmd.account_id,
                models.Invoice.invoice_no == red_invoice_no,
            ).first()
            if not existing_red:
                # 解析退货日期
                ret_dt = datetime.fromisoformat(cmd.return_date) if isinstance(cmd.return_date, str) else cmd.return_date
                # 红字进项发票：若原发票已认证，红字发票也设为 certified（让 get_tax_report 自动扣除进项税）
                red_cert_status = original_invoice.certification_status_l3 if (
                    enable_vat_deduction and original_invoice.invoice_type == "special"
                ) else CertificationStatus.N_A
                red_invoice = models.Invoice(
                    account_id=cmd.account_id,
                    invoice_no=red_invoice_no,
                    direction=InvoiceDirection.IN,
                    invoice_type=original_invoice.invoice_type,
                    tax_rate_l1=original_invoice.tax_rate_l1,
                    amount_without_tax_l1=-inventory_cost_ret if enable_vat_deduction else -total_with_tax_ret,
                    tax_amount_l1=-(tax_amount_ret if enable_vat_deduction else Decimal("0")),
                    amount_with_tax_l1=-total_with_tax_ret,
                    counterparty_name=order.supplier.name if order.supplier else (original_invoice.counterparty_name or ""),
                    seller_name=original_invoice.seller_name,
                    buyer_name=original_invoice.buyer_name,
                    issue_date_l1=ret_dt,
                    certification_status_l3=red_cert_status,
                    related_order_id=order.id,
                    related_order_type="purchase_order",
                    notes=f"红字进项发票（采购退货）: {cmd.reason or '未提供'}",
                )
                db.add(red_invoice)
                db.flush()

        # 5. 事件（Emit-as-Log：emit 携带 log 元数据，由 handlers.py 单写一条 OperationLog）
        emit("purchase_order.returned", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator, return_amount=total_with_tax_ret,
             log_action="return",
             log_detail=f"采购退货 {order.order_no}: 退货金额={total_with_tax_ret}, 原因={cmd.reason or '未提供'}")
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 3. DeletePurchaseOrder — 删除采购单
# ═══════════════════════════════════════════════════════════

@dataclass
class DeletePurchaseOrder(Command):
    order_id: int = 0


@register(DeletePurchaseOrder)
class DeletePurchaseOrderHandler(CommandHandler):
    def handle(self, cmd: DeletePurchaseOrder, db: Any) -> Any:
        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": cmd.order_id})

        # 已完成：InventoryEngine 红冲 + FinanceEngine 冲红凭证
        if order.status == OrderStatus.COMPLETED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory_l3:
                    InventoryEngine(db).reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity_l1,
                        unit_cost=Decimal("0"),
                        source_type="purchase_order",
                        source_id=order.id,
                        operator=cmd.operator,
                    )
            FinanceEngine(db, cmd.account_id).reverse_purchase(order.id)

        # 冲销付款记录 + 银行流水
        reverse_payments(db, cmd.account_id, cmd.order_id)

        # 事件（Emit-as-Log：emit 携带 log 元数据，由 handlers.py 单写一条 OperationLog）
        emit("purchase_order.deleted", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator,
             log_action="delete",
             log_detail=f"删除采购单 {order.order_no}: 状态={order.status}")

        db.delete(order)
        db.flush()
        return True


# ═══════════════════════════════════════════════════════════
# 4. UpdatePurchaseOrderItems — 更新采购单明细（全量替换）
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdatePurchaseOrderItems(Command):
    order_id: int = 0
    items: List[dict] = field(default_factory=list)
    supplier_id: Optional[int] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@register(UpdatePurchaseOrderItems)
class UpdatePurchaseOrderItemsHandler(CommandHandler):
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @writes("PurchaseItem.quantity_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.unit_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.tax_rate_l1", tier=TIER_L1, source="external")
    @writes("PurchaseItem.total_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseOrder.total_price_l1", tier=TIER_L1, source="external")
    @writes("PurchaseOrder.tax_amount_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: UpdatePurchaseOrderItems, db: Any) -> Any:
        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": cmd.order_id})

        if cmd.items:
            product_ids = [it['product_id'] for it in cmd.items]
            dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
            if dup_pids:
                raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        old_status = order.status

        # 旧行冲红：InventoryEngine 红冲 + FinanceEngine 冲红凭证（BR-7/BR-8）
        # force=True：跳过幂等检查 + 取最近正向流水/凭证，支持反复更新
        if old_status == OrderStatus.COMPLETED:
            eng = InventoryEngine(db)
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory_l3:
                    eng.reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity_l1,
                        unit_cost=Decimal("0"),
                        source_type="purchase_order",
                        source_id=order.id,
                        operator=cmd.operator,
                        force=True,
                    )
            FinanceEngine(db, cmd.account_id).reverse_purchase(order.id, force=True)

        # 删除旧行
        for item in order.items[:]:
            db.delete(item)
        db.flush()

        # 新 items 为空 → 删除整个采购单
        if len(cmd.items) == 0:
            # Emit-as-Log：复用 deleted 事件，携带自动删除的 log_detail
            emit("purchase_order.deleted", db=db, account_id=cmd.account_id, order=order,
                 operator=cmd.operator,
                 log_action="delete",
                 log_detail=f"删除采购单 {order.order_no}（商品行数归零自动删除）")
            db.delete(order)
            db.flush()
            return None

        # 更新普通字段
        field_map = {
            'supplier_id': cmd.supplier_id,
            'payment_method': cmd.payment_method,
            'notes': cmd.notes,
            'status': cmd.status,
        }
        for k, v in field_map.items():
            if v is not None:
                setattr(order, k, v)
        new_status = order.status

        # 创建新行 + 库存处理（BR-7: 通过 InventoryEngine 写 StockMove）
        total = Decimal('0')
        calculated_data = []
        for it in cmd.items:
            product = get_product(db, cmd.account_id, it['product_id'])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            new_item = models.PurchaseItem(
                order_id=order.id,
                product_id=it['product_id'],
                quantity_l1=it['quantity'],
                unit_price_l1=it['unit_price'],
                tax_rate_l1=it.get('tax_rate', Decimal('0.13')),
                total_price_l1=line_total,
            )
            db.add(new_item)
            if new_status == OrderStatus.COMPLETED and product.track_inventory_l3:
                calc = InventoryEngine(db).force_inbound(
                    account_id=cmd.account_id,
                    product_id=it['product_id'],
                    quantity=it['quantity'],
                    unit_price=it['unit_price'],
                    source_type="purchase_order",
                    source_id=order.id,
                    tax_rate=it.get('tax_rate'),
                    operator=cmd.operator,
                )
                calculated_data.append(calc)
            total += line_total

        order.total_price_l1 = total.quantize(Q2)

        # 重建会计凭证（BR-8: force 跳过幂等，source_id 复用原单）
        if new_status == OrderStatus.COMPLETED:
            FinanceEngine(db, cmd.account_id).record_purchase(order, calculated_data or None, force=True)

        emit("purchase_order.updated", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator,
             log_action="update",
             log_detail=f"更新采购单明细 {order.order_no}: 状态={old_status}->{new_status}")
        db.flush()
        db.refresh(order)
        return order


# ═══════════════════════════════════════════════════════════
# 5. UpdatePurchaseOrderFields — 更新采购单普通字段
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdatePurchaseOrderFields(Command):
    order_id: int = 0
    supplier_id: Optional[int] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


@register(UpdatePurchaseOrderFields)
class UpdatePurchaseOrderFieldsHandler(CommandHandler):
    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: UpdatePurchaseOrderFields, db: Any) -> Any:
        order = get_purchase_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": cmd.order_id})

        old_status = order.status

        field_map = {
            'supplier_id': cmd.supplier_id,
            'payment_method': cmd.payment_method,
            'payment_status': cmd.payment_status,
            'notes': cmd.notes,
            'image_url': cmd.image_url,
            'status': cmd.status,
        }
        for k, v in field_map.items():
            if v is not None:
                setattr(order, k, v)

        new_status = order.status

        # 状态切换库存处理（BR-7: StockMove 真相源 / BR-8: 凭证真相源）
        # completed→cancelled: InventoryEngine 红冲 + FinanceEngine 冲红凭证
        #   与 CancelPurchaseOrderHandler 保持一致，不再直接操作 inv.quantity
        # cancelled→completed: InventoryEngine 重建入库 + FinanceEngine 重建凭证
        #   使用 force 跳过幂等检查（source_id 复用，原流水/凭证仍存在）
        eng = InventoryEngine(db)
        fin = FinanceEngine(db, cmd.account_id)
        if old_status == OrderStatus.COMPLETED and new_status == OrderStatus.CANCELLED:
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory_l3:
                    eng.reverse(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity_l1,
                        unit_cost=Decimal("0"),
                        source_type="purchase_order",
                        source_id=order.id,
                        operator=cmd.operator,
                        force=True,
                    )
            fin.reverse_purchase(order.id, force=True)
        elif old_status == OrderStatus.CANCELLED and new_status == OrderStatus.COMPLETED:
            calculated_data = []
            for item in order.items:
                product = db.query(models.Product).get(item.product_id)
                if product and product.track_inventory_l3:
                    calc = eng.force_inbound(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity_l1,
                        unit_price=item.unit_price_l1,
                        source_type="purchase_order",
                        source_id=order.id,
                        tax_rate=item.tax_rate_l1,
                        operator=cmd.operator,
                    )
                    calculated_data.append(calc)
            fin.record_purchase(order, calculated_data or None, force=True)

        emit("purchase_order.updated", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator,
             log_action="update",
             log_detail=f"更新采购单字段 {order.order_no}: 状态={old_status}->{new_status}")
        db.flush()
        return order