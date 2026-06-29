"""销售单 Command + Handler — 7个命令覆盖销售单全部业务操作

v7 改造后：移除项目模块
  所有销售单均为零售型，deduct_inventory=True
  不再关联项目、不再创建项目收入
"""

import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List, Optional

import models
from enums import OrderStatus, OrderType, PaymentStatus
from events import emit
from domain.sale_order import SaleOrderDomain

from .base import Command, CommandHandler, register
from crud.base import _generate_order_no, _log
from crud.products import get_product
from crud.orders import get_sale_order, _d, _distribute_total_price
from crud.reversal import reverse_receipts
from errors import BusinessError, ErrorCode
from utils import Q2
from engine_inventory import InventoryEngine
from engine_finance import FinanceEngine


# ═══════════════════════════════════════════════════════════
# 1. CreateSaleOrder — 创建销售单
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateSaleOrder(Command):
    customer_id: Optional[int] = None
    deduct_inventory: bool = True
    payment_status: str = PaymentStatus.UNPAID
    notes: str = ""
    image_url: str = ""
    total_price: Optional[Decimal] = None
    sale_date: Optional[datetime] = None
    items: List[dict] = field(default_factory=list)


@register(CreateSaleOrder)
class CreateSaleOrderHandler(CommandHandler):
    def handle(self, cmd: CreateSaleOrder, db: Any) -> Any:
        # 1. 校验
        if not cmd.items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS, data={"order_type": "销售单"})
        product_ids = [it['product_id'] for it in cmd.items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        # 1a. 业务日期必填（级联到凭证日期和库存移动日期，不能用当前时间兜底）
        if not cmd.sale_date:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="销售日期不能为空，请提供业务发生日期",
                ai_instruction="STOP_RETRYING. sale_date 字段必填，请补充销售业务日期（如 2025-06-28）。"
            )

        # 2. 生成订单号
        order_no = _generate_order_no(db, "SO", cmd.sale_date)

        # 3. 创建订单头
        sale_dt = datetime.fromisoformat(cmd.sale_date) if isinstance(cmd.sale_date, str) else cmd.sale_date
        order = models.SaleOrder(
            account_id=cmd.account_id,
            order_no=order_no,
            customer_id=cmd.customer_id,
            order_type=OrderType.RETAIL,
            payment_status=cmd.payment_status,
            status=OrderStatus.PENDING,
            notes=cmd.notes,
            image_url=cmd.image_url,
            total_price=0,
            sale_date=sale_dt,
        )
        db.add(order)
        db.flush()

        # 4. 计算明细 + 创建行
        items_data = []
        total = Decimal('0')
        for it in cmd.items:
            product = get_product(db, cmd.account_id, it['product_id'])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            items_data.append({
                'product_id': it['product_id'],
                'quantity': it['quantity'],
                'unit_price': it['unit_price'],
                'tax_rate': it.get('tax_rate', Decimal('0.01')),
                'total_price': line_total,
            })
            total += line_total

        # 5. 自定义金额分配
        if cmd.total_price is not None:
            _distribute_total_price(items_data, cmd.total_price)

        # 6. 创建 SaleItem 行
        for it in items_data:
            item = models.SaleItem(
                order_id=order.id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                tax_rate=it['tax_rate'],
                total_price=it['total_price'],
            )
            db.add(item)

        final_total = sum(_d(it['total_price']) for it in items_data)
        order.total_price = _d(cmd.total_price) if cmd.total_price is not None else final_total.quantize(Q2)
        db.flush()

        # 7. Domain 状态机转换：pending → completed
        domain = SaleOrderDomain.from_orm(order)
        violations = domain.validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"销售单校验失败: {'; '.join(violations)}"})
        domain.transition_to(OrderStatus.COMPLETED)
        order.status = domain.status
        db.flush()

        # 8. 显式联动：InventoryEngine 出库 + 生成会计凭证
        if cmd.deduct_inventory:
            for item in order.items:
                product = get_product(db, cmd.account_id, item.product_id)
                if product.track_inventory:
                    unit_cost = InventoryEngine(db).outbound(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        source_type="sale_order",
                        source_id=order.id,
                        operator=cmd.operator,
                    )
                    item.set_calculated_cost(unit_cost)
                else:
                    item.set_calculated_cost(Decimal("0"))
            FinanceEngine(db, cmd.account_id).record_sale(order)

        # 9. 事件（仅日志）
        emit("sale_order.created", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        # 10. 操作日志
        _log(db, cmd.account_id, "create", "sale_order", order.id,
             f"创建销售单 {order_no}: {len(cmd.items)}项商品, 总价={total}", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 2. CancelSaleOrder — 取消销售单
# ═══════════════════════════════════════════════════════════

@dataclass
class CancelSaleOrder(Command):
    order_id: int = 0


@register(CancelSaleOrder)
class CancelSaleOrderHandler(CommandHandler):
    def handle(self, cmd: CancelSaleOrder, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        old_status = order.status

        # Domain 状态机校验 + 转换
        domain = SaleOrderDomain.from_orm(order)
        violations = domain.validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"销售单校验失败: {'; '.join(violations)}"})
        domain.transition_to(OrderStatus.CANCELLED)
        order.status = domain.status

        # 显式联动：InventoryEngine 回补库存（BR-7: StockMove 真相源）
        eng = InventoryEngine(db)
        for item in order.items:
            eng.reverse(
                account_id=cmd.account_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_cost=Decimal(str(item.unit_cost)) if item.unit_cost else Decimal('0'),
                source_type="sale_order",
                source_id=order.id,
                operator=cmd.operator,
            )

        # 显式联动：冲销收款记录 + 银行流水
        reverse_receipts(db, cmd.account_id, cmd.order_id)

        # 显式联动：冲红会计凭证
        FinanceEngine(db, cmd.account_id).reverse_sale(order.id)

        # 事件（仅日志）
        emit("sale_order.cancelled", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator, old_status=old_status)

        # 操作日志
        _log(db, cmd.account_id, "update", "sale_order", cmd.order_id,
             f"取消销售单 {order.order_no}: 状态={old_status}->cancelled", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 2b. ReturnSaleOrder — 销售退货（部分冲红，保留原单）
# ═══════════════════════════════════════════════════════════

@dataclass
class ReturnSaleOrder(Command):
    order_id: int = 0
    return_date: str = ""
    reason: str = ""
    items: List[dict] = field(default_factory=list)  # [{product_id, quantity}]


@register(ReturnSaleOrder)
class ReturnSaleOrderHandler(CommandHandler):
    def handle(self, cmd: ReturnSaleOrder, db: Any) -> Any:
        from finance_integration import post_journal
        # StockMove 定义在 models.py（库存真相源），不在 models_finance.py
        StockMove = models.StockMove

        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                                data={"order_type": "销售单", "order_id": cmd.order_id})
        if order.status != OrderStatus.COMPLETED:
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE,
                                data={"status": order.status, "action": "退货"})

        if not cmd.return_date:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message="退货日期不能为空，请提供业务发生日期",
                                ai_instruction="STOP_RETRYING. return_date 字段必填。")
        if not cmd.items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS,
                                data={"order_type": "销售退货单"})

        # 1. 校验退货数量不超原销售数量
        original_qty_map = {item.product_id: item.quantity for item in order.items}
        for ret in cmd.items:
            pid = ret['product_id']
            if pid not in original_qty_map:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND,
                                    data={"product_id": pid, "details": "商品不在原销售单中"})
            if ret['quantity'] > original_qty_map[pid]:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"退货数量 {ret['quantity']} 超过原销售数量 {original_qty_map[pid]}",
                    ai_instruction=f"STOP_RETRYING. 商品 ID={pid} 原销售 {original_qty_map[pid]} 件，退货不能超过此数量。"
                )

        # 2. 获取账本配置
        account = db.query(models.Account).filter(models.Account.id == cmd.account_id).first()
        taxpayer_type = account.taxpayer_type if account else "general"

        # 3. 库存回补 + 按行计算退货金额
        total_with_tax_ret = Decimal("0")
        total_without_tax_ret = Decimal("0")
        tax_amount_ret = Decimal("0")
        cost_return = Decimal("0")
        eng = InventoryEngine(db)
        return_id = int(time.time() * 1000)  # 部分退货唯一标识，支持多次部分退货

        for ret in cmd.items:
            pid = ret['product_id']
            qty_ret = Decimal(str(ret['quantity']))
            # 找到原销售明细
            orig_item = next((it for it in order.items if it.product_id == pid), None)
            if not orig_item:
                continue

            # 3a. 库存回补（InventoryEngine.reverse 自动从原 StockMove 取 unit_cost）
            product = db.query(models.Product).filter(
                models.Product.id == pid,
                models.Product.account_id == cmd.account_id,
            ).first()
            if product and product.track_inventory:
                eng.reverse(
                    account_id=cmd.account_id,
                    product_id=pid,
                    quantity=int(qty_ret),
                    unit_cost=Decimal("0"),  # 自动从原 StockMove 取
                    source_type="sale_order",
                    source_id=order.id,
                    operator=cmd.operator,
                    source_id_override=return_id,  # 避免与整单冲销的幂等冲突
                )
                # 取 unit_cost 计算成本冲红
                move = db.query(StockMove).filter(
                    StockMove.source_type == "sale_order",
                    StockMove.source_id == order.id,
                    StockMove.product_id == pid,
                ).first()
                unit_cost = move.unit_cost if move and move.unit_cost else Decimal("0")
                cost_return += (qty_ret * unit_cost).quantize(Q2)

            # 3b. 收入/税额按比例计算
            line_total = Decimal(str(orig_item.total_price))
            ratio = qty_ret / Decimal(str(orig_item.quantity))
            revenue_ret = (line_total * ratio).quantize(Q2)

            # 税额：小规模纳税人按账本税率，一般纳税人按行税率
            rate = orig_item.tax_rate
            if taxpayer_type == "small_scale" and rate and rate > 0:
                # 小规模实际征收率
                rate = Decimal("0.01")  # 小规模 1% 征收率
            tax_ret = (revenue_ret * Decimal(str(rate))).quantize(Q2) if rate else Decimal("0")

            total_without_tax_ret += revenue_ret
            tax_amount_ret += tax_ret
            total_with_tax_ret += (revenue_ret + tax_ret).quantize(Q2)

        total_with_tax_ret = total_with_tax_ret.quantize(Q2)
        total_without_tax_ret = total_without_tax_ret.quantize(Q2)
        tax_amount_ret = tax_amount_ret.quantize(Q2)
        cost_return = cost_return.quantize(Q2)

        # 4. 过账部分冲红凭证（return_id 已在上方生成，作 source_id 避免幂等冲突，支持多次部分退货）
        post_journal(db, cmd.account_id, "sale_return", {
            "partner_id": order.customer_id or 0,
            "total_with_tax": total_with_tax_ret,
            "total_without_tax": total_without_tax_ret,
            "tax_amount": tax_amount_ret,
            "cost_return": cost_return,
            "taxpayer_type": taxpayer_type,
            "source_model": "sale_return",
            "source_id": return_id,
            "date": cmd.return_date,
        })

        # 5. 事件 + 日志
        emit("sale_order.returned", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator, return_amount=total_with_tax_ret)
        _log(db, cmd.account_id, "return", "sale_order", cmd.order_id,
             f"销售退货 {order.order_no}: 退货金额={total_with_tax_ret}, 原因={cmd.reason or '未提供'}",
             operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 3. RestoreSaleOrder — 恢复销售单（取消→完成）
# ═══════════════════════════════════════════════════════════

@dataclass
class RestoreSaleOrder(Command):
    order_id: int = 0


@register(RestoreSaleOrder)
class RestoreSaleOrderHandler(CommandHandler):
    def handle(self, cmd: RestoreSaleOrder, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        if order.status != OrderStatus.CANCELLED:
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": order.status, "action": "恢复"})

        old_status = order.status

        # Domain 状态机校验 + 转换
        domain = SaleOrderDomain.from_orm(order)
        violations = domain.validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"销售单校验失败: {'; '.join(violations)}"})
        domain.transition_to(OrderStatus.COMPLETED)
        order.status = domain.status

        # 显式联动：InventoryEngine 出库 + 生成会计凭证（BR-7/BR-8）
        # 使用 force_outbound 跳过幂等（source_id 复用原单，cancel 时已有出库流水）
        # record_sale(force=True) 同理跳过幂等，重建销售凭证
        # 弃用 sale_deduct（直接改 inv.quantity，不写 StockMove，违背 BR-7）
        eng = InventoryEngine(db)
        for item in order.items:
            product = get_product(db, cmd.account_id, item.product_id)
            if product.track_inventory:
                unit_cost = eng.force_outbound(
                    account_id=cmd.account_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    source_type="sale_order",
                    source_id=order.id,
                    operator=cmd.operator,
                )
                item.set_calculated_cost(unit_cost)
            else:
                item.set_calculated_cost(Decimal("0"))
        FinanceEngine(db, cmd.account_id).record_sale(order, force=True)

        # 事件（仅日志）
        emit("sale_order.restored", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator, old_status=old_status)

        # 操作日志
        _log(db, cmd.account_id, "update", "sale_order", cmd.order_id,
             f"恢复销售单 {order.order_no}: 状态={old_status}->completed", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 4. DeleteSaleOrder — 删除销售单
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteSaleOrder(Command):
    order_id: int = 0


@register(DeleteSaleOrder)
class DeleteSaleOrderHandler(CommandHandler):
    def handle(self, cmd: DeleteSaleOrder, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        # Domain 校验是否可删除
        domain = SaleOrderDomain.from_orm(order)
        if not domain.can_delete():
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": order.status, "action": "删除"})

        # 显式联动：InventoryEngine 回补库存（BR-7: StockMove 真相源）
        if order.status == OrderStatus.COMPLETED:
            eng = InventoryEngine(db)
            for item in order.items:
                eng.reverse(
                    account_id=cmd.account_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=Decimal(str(item.unit_cost)) if item.unit_cost else Decimal('0'),
                    source_type="sale_order",
                    source_id=order.id,
                    operator=cmd.operator,
                )

        # 显式联动：冲销收款记录 + 银行流水
        reverse_receipts(db, cmd.account_id, cmd.order_id)

        # 显式联动：冲红会计凭证
        if order.status == OrderStatus.COMPLETED:
            FinanceEngine(db, cmd.account_id).reverse_sale(order.id)

        # 事件（仅日志）
        emit("sale_order.deleted", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator, old_status=order.status)

        # 操作日志
        _log(db, cmd.account_id, "delete", "sale_order", cmd.order_id,
             f"删除销售单 {order.order_no}: 状态={order.status}", operator=cmd.operator)

        # 删除
        db.delete(order)
        db.flush()
        return True


# ═══════════════════════════════════════════════════════════
# 5. UpdateSaleOrderItems — 更新销售单明细（全量替换）
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateSaleOrderItems(Command):
    order_id: int = 0
    items: List[dict] = field(default_factory=list)
    total_price: Optional[Decimal] = None


@register(UpdateSaleOrderItems)
class UpdateSaleOrderItemsHandler(CommandHandler):
    def handle(self, cmd: UpdateSaleOrderItems, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        # 商品重复校验
        if cmd.items:
            product_ids = [it['product_id'] for it in cmd.items]
            dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
            if dup_pids:
                raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT, data={"product_ids": dup_pids})

        old_status = order.status

        # 记录旧行数据（含 unit_cost，用于红冲）
        old_items = [
            {'product_id': item.product_id, 'quantity': item.quantity,
             'unit_cost': Decimal(str(item.unit_cost)) if item.unit_cost else Decimal('0')}
            for item in order.items
        ]

        # 旧行冲红：InventoryEngine 红冲 + FinanceEngine 冲红凭证（BR-7/BR-8）
        # force=True：跳过幂等检查 + 取最近正向流水/凭证，支持反复更新
        if old_status == OrderStatus.COMPLETED:
            eng = InventoryEngine(db)
            for item_data in old_items:
                eng.reverse(
                    account_id=cmd.account_id,
                    product_id=item_data['product_id'],
                    quantity=item_data['quantity'],
                    unit_cost=item_data['unit_cost'],
                    source_type="sale_order",
                    source_id=order.id,
                    operator=cmd.operator,
                    force=True,
                )
            FinanceEngine(db, cmd.account_id).reverse_sale(order.id, force=True)

        # 删除旧行
        for item in order.items[:]:
            db.delete(item)
        db.flush()

        # 新 items 为空 → 删除整个销售单（旧行已在上文冲红）
        if len(cmd.items) == 0:
            _log(db, cmd.account_id, "delete", "sale_order", cmd.order_id,
                 f"删除销售单 {order.order_no}（商品行数归零自动删除）", operator=cmd.operator)
            db.delete(order)
            db.flush()
            return None

        # 创建新行 + 自定义金额分配
        items_data = []
        total = Decimal('0')
        for it in cmd.items:
            product = get_product(db, cmd.account_id, it['product_id'])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": it['product_id']})
            line_total = (Decimal(str(it['quantity'])) * _d(it['unit_price'])).quantize(Q2)
            items_data.append({
                'product_id': it['product_id'],
                'quantity': it['quantity'],
                'unit_price': it['unit_price'],
                'tax_rate': it.get('tax_rate', Decimal('0.01')),
                'total_price': line_total,
            })
            total += line_total

        if cmd.total_price is not None:
            _distribute_total_price(items_data, cmd.total_price)

        for it in items_data:
            new_item = models.SaleItem(
                order_id=order.id,
                product_id=it['product_id'],
                quantity=it['quantity'],
                unit_price=it['unit_price'],
                tax_rate=it['tax_rate'],
                total_price=it['total_price'],
            )
            db.add(new_item)

        final_total = sum(_d(it['total_price']) for it in items_data)
        order.total_price = _d(cmd.total_price) if cmd.total_price is not None else final_total.quantize(Q2)

        db.flush()

        # 新行扣减：InventoryEngine 出库 + 生成会计凭证（BR-7/BR-8）
        # 旧行已在删除前通过 InventoryEngine.reverse + reverse_sale 冲红
        # 新行使用 force_outbound 跳过幂等（source_id 复用原单），record_sale 同理
        if order.status == OrderStatus.COMPLETED:
            eng = InventoryEngine(db)
            for item in order.items:
                product = get_product(db, cmd.account_id, item.product_id)
                if product.track_inventory:
                    unit_cost = eng.force_outbound(
                        account_id=cmd.account_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        source_type="sale_order",
                        source_id=order.id,
                        operator=cmd.operator,
                    )
                    item.set_calculated_cost(unit_cost)
                else:
                    item.set_calculated_cost(Decimal("0"))
            FinanceEngine(db, cmd.account_id).record_sale(order, force=True)

        # 事件（仅日志）
        emit("sale_order.items_updated", db=db, account_id=cmd.account_id, order=order,
             operator=cmd.operator)

        # 操作日志
        _log(db, cmd.account_id, "update", "sale_order", cmd.order_id,
             f"更新销售单明细 {order.order_no}", operator=cmd.operator)
        db.flush()
        return order


# ═══════════════════════════════════════════════════════════
# 6. UpdateSaleOrderFields — 更新销售单普通字段
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateSaleOrderFields(Command):
    order_id: int = 0
    customer_id: Optional[int] = None
    payment_status: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


@register(UpdateSaleOrderFields)
class UpdateSaleOrderFieldsHandler(CommandHandler):
    def handle(self, cmd: UpdateSaleOrderFields, db: Any) -> Any:
        order = get_sale_order(db, cmd.account_id, cmd.order_id)
        if not order:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": cmd.order_id})

        field_map = {
            'customer_id': cmd.customer_id,
            'payment_status': cmd.payment_status,
            'notes': cmd.notes,
            'image_url': cmd.image_url,
            'status': cmd.status,
        }
        for k, v in field_map.items():
            if v is not None:
                setattr(order, k, v)

        # 事件（仅日志）
        emit("sale_order.fields_updated", db=db, account_id=cmd.account_id, order=order, operator=cmd.operator)

        # 操作日志
        _log(db, cmd.account_id, "update", "sale_order", cmd.order_id,
             f"更新销售单字段 {order.order_no}", operator=cmd.operator)
        db.flush()
        return order