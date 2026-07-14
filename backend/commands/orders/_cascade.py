"""冲红级联策略 — ReverseInvoice 的级联分支提取为可注册策略

每个策略实现 cascade(db, account_id, operator, invoice, red_invoice, reason) -> list[str]。
resolve_reversal 通过策略注册表分发，新增级联类型无需修改 dispatcher。
"""

import time as _time
from decimal import Decimal
from typing import Any, Callable, Dict, List

import models
from enums import OrderStatus, InvoiceType
from operation_result import EntityType
from utils import to_decimal, Q2
from errors import BusinessError, ErrorCode
from policy.entity_profile import build_profile
from lineage import reads, writes, TIER_L1, TIER_L3

from sqlalchemy import func as sqlfunc


CascadeStrategy = Callable[[Any, int, str, Any, Any, str], List[str]]
_reversal_strategies: Dict[str, CascadeStrategy] = {}


def register_cascade_strategy(related_type: str) -> Callable[[CascadeStrategy], CascadeStrategy]:
    """注册冲红级联策略装饰器。

    用法::

        @register_cascade_strategy("sale_order")
        def _cascade_sale(db, account_id, operator, invoice, red_invoice, reason):
            ...
    """
    def decorator(fn: CascadeStrategy) -> CascadeStrategy:
        _reversal_strategies[related_type] = fn
        return fn
    return decorator


def resolve_reversal(db, account_id, operator, invoice, red_invoice, reason) -> List[str]:
    """分发到对应策略 — 替代原 ReverseInvoiceHandler 中的 if-else 树。"""
    related_type = invoice.related_order_type
    related_id = invoice.related_order_id

    if related_type and related_id and related_type in _reversal_strategies:
        return _reversal_strategies[related_type](
            db, account_id, operator, invoice, red_invoice, reason
        )

    return ["独立发票（无级联冲红）"]


@register_cascade_strategy("sale_order")
def _cascade_sale(db, account_id, operator, invoice, red_invoice, reason) -> List[str]:
    """销项发票冲红级联 — 销售凭证冲红 + 库存回退（支持部分退货）

    BR-REV: 必须先级联冲红关联收款，否则收款凭证残留、银行余额不回滚、BS 应收/银行不符。
    """
    from engine_finance import FinanceEngine
    from engine_inventory import InventoryEngine
    from finance_integration import post_journal

    lines = []
    sale_order = db.query(models.SaleOrder).filter(
        models.SaleOrder.id == invoice.related_order_id,
        models.SaleOrder.account_id == account_id,
    ).first()

    # ── 级联冲红关联收款 ──
    # project_memory 约束：reverse_invoice must check associated receipts。
    # 若有未冲红收款，自动级联冲红（与销售凭证/库存自动冲红风格一致）。
    # Receipt 无 is_reversed 字段，冲红后 amount_l1 为负数，用 amount_l1 > 0 筛选未冲红收款。
    if sale_order:
        unreversed_receipts = db.query(models.Receipt).filter(
            models.Receipt.account_id == account_id,
            models.Receipt.related_entity_type == EntityType.SALE_ORDER,
            models.Receipt.related_entity_id == sale_order.id,
            models.Receipt.amount_l1 > 0,
        ).all()
        if unreversed_receipts:
            from commands.reversal_ops import reverse_receipts
            reverse_receipts(db, account_id, sale_order.id)
            lines.append(f"级联冲红收款 {len(unreversed_receipts)} 笔")

    if sale_order and sale_order.status == OrderStatus.CANCELLED:
        lines.append("销售单已取消（凭证库存已冲红，跳过）")
        return lines

    if sale_order and sale_order.status == OrderStatus.COMPLETED:
        reversed_qty_map = {}
        reversal_moves = db.query(
            models.StockMove.product_id,
            sqlfunc.sum(models.StockMove.quantity_l1).label('rev_qty')
        ).filter(
            models.StockMove.source_type == "sale_order_reversal",
            models.StockMove.account_id == account_id,
            models.StockMove.ref_source_id == sale_order.id,
        ).group_by(models.StockMove.product_id).all()
        for row in reversal_moves:
            reversed_qty_map[row.product_id] = abs(int(row.rev_qty))

        remaining_items = []
        for item in sale_order.items:
            already_reversed = reversed_qty_map.get(item.product_id, 0)
            remaining_qty = item.quantity_l1 - already_reversed
            if remaining_qty > 0:
                remaining_items.append((item, remaining_qty))

        if not remaining_items:
            FinanceEngine(db, account_id).reverse_sale(sale_order.id)
            lines.append("冲红销售凭证（库存已全部退货）")
        else:
            has_partial_return = any(v > 0 for v in reversed_qty_map.values())
            if has_partial_return:
                from finance_integration import post_journal as _pj
                account = db.query(models.Account).filter(models.Account.id == account_id).first()
                taxpayer_type = build_profile(account).vat_type if account else "general"
                total_wt_ret = Decimal("0")
                total_wot_ret = Decimal("0")
                tax_ret = Decimal("0")
                cost_ret = Decimal("0")
                eng_inv = InventoryEngine(db)
                red_return_id = int(_time.time() * 1000)
                for item, rem_qty in remaining_items:
                    product = db.query(models.Product).filter(
                        models.Product.id == item.product_id,
                        models.Product.account_id == account_id,
                    ).first()
                    if product and product.track_inventory_l3:
                        eng_inv.reverse(
                            account_id=account_id, product_id=item.product_id,
                            quantity=rem_qty, unit_cost=Decimal("0"),
                            source_type="sale_order", source_id=sale_order.id,
                            operator=operator, source_id_override=red_return_id,
                        )
                        move = db.query(models.StockMove).filter(
                            models.StockMove.source_type == "sale_order",
                            models.StockMove.source_id == sale_order.id,
                            models.StockMove.product_id == item.product_id,
                        ).first()
                        uc = move.unit_cost_l2 if move and move.unit_cost_l2 else Decimal("0")
                        cost_ret += (Decimal(str(rem_qty)) * uc).quantize(Q2)
                    line_total = to_decimal(item.total_price_l1)
                    denom = to_decimal(item.quantity_l1)
                    if denom <= 0:
                        raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                            data={"product_id": item.product_id, "msg": "冲红时商品数量为0或负数"})
                    ratio = to_decimal(rem_qty) / denom
                    rev_ret = line_total * ratio
                    total_wt_ret += rev_ret
                total_wt_ret = total_wt_ret.quantize(Q2)
                order_tax = Decimal(str(sale_order.tax_amount_l1 or 0))
                order_total = Decimal(str(sale_order.total_price_l1 or 0))
                if order_tax and order_total and order_total != Decimal('0'):
                    cascade_ratio = total_wt_ret / order_total
                    cascade_tax = (order_tax * cascade_ratio).quantize(Q2)
                else:
                    cascade_tax = Decimal('0')
                cascade_wot = (total_wt_ret - cascade_tax).quantize(Q2)
                _pj(db, account_id, "sale_return", {
                    "partner_id": sale_order.customer_id or 0,
                    "total_with_tax": total_wt_ret,
                    "total_without_tax": cascade_wot,
                    "tax_amount": cascade_tax,
                    "cost_return": cost_ret.quantize(Q2),
                    "taxpayer_type": taxpayer_type,
                    "source_model": "sale_return",
                    "source_id": red_return_id,
                    "date": red_invoice.issue_date_l1,
                })
                lines.append(f"冲红剩余销售部分({len(remaining_items)}项，已扣减部分退货)")
            else:
                FinanceEngine(db, account_id).reverse_sale(sale_order.id)
                lines.append("冲红销售凭证")
                eng_inv = InventoryEngine(db)
                for item in sale_order.items:
                    unit_cost = to_decimal(item.unit_cost_l2) if item.unit_cost_l2 else Decimal('0')
                    eng_inv.reverse(
                        account_id=account_id, product_id=item.product_id,
                        quantity=item.quantity_l1, unit_cost=unit_cost,
                        source_type="sale_order", source_id=sale_order.id,
                        operator=operator,
                    )
                lines.append(f"库存回退({len(sale_order.items)}项)")
    else:
        lines.append("销售单状态异常，跳过级联冲红")

    return lines


@register_cascade_strategy("purchase_order")
def _cascade_purchase(db, account_id, operator, invoice, red_invoice, reason) -> List[str]:
    """进项发票冲红级联 — 采购凭证冲红 + 库存退回（支持部分退货，与 _cascade_sale 对称）"""
    from engine_finance import FinanceEngine
    from engine_inventory import InventoryEngine
    from finance_integration import post_journal as _pj

    lines = []
    purchase_order = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.id == invoice.related_order_id,
        models.PurchaseOrder.account_id == account_id,
    ).first()

    if purchase_order and purchase_order.status == OrderStatus.CANCELLED:
        lines.append("采购单已取消（凭证库存已冲红，跳过）")
        return lines

    if purchase_order and purchase_order.status == OrderStatus.COMPLETED:
        # 统计已部分退货数量（与 _cascade_sale 对称）
        reversed_qty_map = {}
        reversal_moves = db.query(
            models.StockMove.product_id,
            sqlfunc.sum(models.StockMove.quantity_l1).label('rev_qty')
        ).filter(
            models.StockMove.source_type == "purchase_order_reversal",
            models.StockMove.account_id == account_id,
            models.StockMove.ref_source_id == purchase_order.id,
        ).group_by(models.StockMove.product_id).all()
        for row in reversal_moves:
            reversed_qty_map[row.product_id] = abs(int(row.rev_qty))

        # 计算剩余未退货数量
        remaining_items = []
        for item in purchase_order.items:
            already_reversed = reversed_qty_map.get(item.product_id, 0)
            remaining_qty = item.quantity_l1 - already_reversed
            if remaining_qty > 0:
                remaining_items.append((item, remaining_qty))

        if not remaining_items:
            # 已全部退货：直接冲红采购凭证
            FinanceEngine(db, account_id).reverse_purchase(purchase_order.id)
            lines.append("冲红采购凭证（库存已全部退货）")
        else:
            has_partial_return = any(v > 0 for v in reversed_qty_map.values())
            if has_partial_return:
                # 部分退货场景：冲红剩余部分，与 _cascade_sale 对称
                account = db.query(models.Account).filter(models.Account.id == account_id).first()
                taxpayer_type = build_profile(account).vat_type if account else "general"
                total_wt_ret = Decimal("0")
                cost_ret = Decimal("0")
                eng_inv = InventoryEngine(db)
                red_return_id = int(_time.time() * 1000)
                for item, rem_qty in remaining_items:
                    product = db.query(models.Product).filter(
                        models.Product.id == item.product_id,
                        models.Product.account_id == account_id,
                    ).first()
                    if product and product.track_inventory_l3:
                        eng_inv.reverse(
                            account_id=account_id, product_id=item.product_id,
                            quantity=rem_qty, unit_cost=Decimal("0"),
                            source_type="purchase_order", source_id=purchase_order.id,
                            operator=operator, source_id_override=red_return_id,
                        )
                        move = db.query(models.StockMove).filter(
                            models.StockMove.source_type == "purchase_order",
                            models.StockMove.source_id == purchase_order.id,
                            models.StockMove.product_id == item.product_id,
                        ).first()
                        uc = move.unit_cost_l2 if move and move.unit_cost_l2 else Decimal("0")
                        cost_ret += (Decimal(str(rem_qty)) * uc).quantize(Q2)
                    line_total = to_decimal(item.total_price_l1)
                    denom = to_decimal(item.quantity_l1)
                    if denom <= 0:
                        raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                            data={"product_id": item.product_id, "msg": "冲红时商品数量为0或负数"})
                    ratio = to_decimal(rem_qty) / denom
                    rev_ret = line_total * ratio
                    total_wt_ret += rev_ret
                total_wt_ret = total_wt_ret.quantize(Q2)
                order_tax = Decimal(str(purchase_order.tax_amount_l1 or 0))
                order_total = Decimal(str(purchase_order.total_price_l1 or 0))
                if order_tax and order_total and order_total != Decimal('0'):
                    cascade_ratio = total_wt_ret / order_total
                    cascade_tax = (order_tax * cascade_ratio).quantize(Q2)
                else:
                    cascade_tax = Decimal('0')
                cascade_wot = (total_wt_ret - cascade_tax).quantize(Q2)
                _pj(db, account_id, "purchase_return", {
                    "partner_id": purchase_order.supplier_id or 0,
                    "total_with_tax": total_wt_ret,
                    "total_without_tax": cascade_wot,
                    "tax_amount": cascade_tax,
                    "cost_return": cost_ret.quantize(Q2),
                    "taxpayer_type": taxpayer_type,
                    "source_model": "purchase_return",
                    "source_id": red_return_id,
                    "date": red_invoice.issue_date_l1,
                })
                lines.append(f"冲红剩余采购部分({len(remaining_items)}项，已扣减部分退货)")
            else:
                # 无部分退货：全额冲红
                FinanceEngine(db, account_id).reverse_purchase(purchase_order.id)
                lines.append("冲红采购凭证")
                eng_inv = InventoryEngine(db)
                for item in purchase_order.items:
                    unit_cost = to_decimal(item.unit_price_l1)
                    eng_inv.reverse(
                        account_id=account_id, product_id=item.product_id,
                        quantity=item.quantity_l1, unit_cost=unit_cost,
                        source_type="purchase_order", source_id=purchase_order.id,
                        operator=operator,
                    )
                lines.append(f"库存退回({len(purchase_order.items)}项)")
    else:
        lines.append("采购单状态异常，跳过级联冲红")

    return lines


@register_cascade_strategy("fixed_asset")
def _cascade_fixed_asset(db, account_id, operator, invoice, red_invoice, reason) -> List[str]:
    """固定资产发票冲红 — 冲红总账凭证 + 资产卡片标记已冲红"""
    from finance_integration import reverse_journal

    lines = []
    asset_id = invoice.related_order_id
    asset = db.query(models.FixedAsset).filter(
        models.FixedAsset.id == asset_id,
        models.FixedAsset.account_id == account_id,
    ).first()
    if asset:
        if asset.status == "已冲红":
            lines.append("资产卡片已冲红，跳过")
        else:
            reverse_journal(db, account_id, "fixed_asset_purchase", asset_id, force=True)
            asset.status = "已冲红"
            lines.append(f"冲红固定资产凭证 + 资产卡片 #{asset_id} 标记已冲红")
    else:
        lines.append(f"资产卡片 #{asset_id} 不存在，跳过")
    return lines


@register_cascade_strategy("expense")
def _cascade_expense(db, account_id, operator, invoice, red_invoice, reason) -> List[str]:
    """费用发票冲红 — 冲红费用凭证 + 标记 Expense.is_reversed=True

    BR-REV: 修复前仅日志记录不冲红凭证，留下 dangling AccountMove 导致 BS 不平。
    """
    from finance_integration import reverse_journal
    from datetime import datetime

    lines = []
    expense_id = invoice.related_order_id
    expense = db.query(models.Expense).filter(
        models.Expense.id == expense_id,
        models.Expense.account_id == account_id,
    ).first()
    if expense:
        if expense.is_reversed:
            lines.append(f"费用 #{expense_id} 已冲红，跳过")
        else:
            reverse_journal(db, account_id, "expense", expense_id, force=True)
            expense.is_reversed = True
            expense.reversed_at = datetime.now()
            lines.append(f"冲红费用凭证 + Expense #{expense_id} 标记已冲红")
    else:
        lines.append(f"费用 #{expense_id} 不存在，跳过")
    return lines
