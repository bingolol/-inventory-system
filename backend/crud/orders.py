"""采购单 + 销售单 CRUD（含事务包裹和金额精度）

⚠️ 写操作警告：本模块禁止新增写操作函数。
所有写操作必须通过 Command 层执行，
以确保状态机校验和 EventBus 集成不被绕过。
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
import models

from .base import gen_order_no, log_op, get_or_create_inventory
from utils import to_decimal, Q2, get_or_404
from enums import OrderType

logger = logging.getLogger("inventory")

# Decimal 量化工具：精确到分
Q6 = Decimal('0.000001')


def _distribute_total_price(items_data: list, target_total):
    """将自定义总额与明细合计的差额分配到各行单价

    策略：
    - 优先分配给 unit_price==0 的行（按数量加权）
    - 所有行都有单价时按金额比例分配（整体打折/加价）
    - 尾差给最后一行，确保合计精确
    """
    raw_total = sum(to_decimal(it['total_price_l1']) for it in items_data)
    target_total = to_decimal(target_total)
    if raw_total == target_total:
        return  # 无需分配
    diff = target_total - raw_total

    zero_price_indices = [i for i, it in enumerate(items_data) if to_decimal(it['unit_price_l1']) == 0]
    if zero_price_indices:
        # 按数量加权分配给单价为0的行
        zero_qty_sum = sum(Decimal(str(items_data[i]['quantity_l1'])) for i in zero_price_indices)
        if zero_qty_sum > 0:
            for idx in zero_price_indices[:-1]:
                qty = Decimal(str(items_data[idx]['quantity_l1']))
                share = (diff * qty / zero_qty_sum).quantize(Q2)
                items_data[idx]['unit_price_l1'] = (share / qty).quantize(Q6)
                items_data[idx]['total_price_l1'] = share
            # 尾差给最后一行
            last_idx = zero_price_indices[-1]
            last_share = (target_total - sum(to_decimal(it['total_price_l1']) for i, it in enumerate(items_data) if i != last_idx)).quantize(Q2)
            items_data[last_idx]['unit_price_l1'] = (last_share / Decimal(str(items_data[last_idx]['quantity_l1']))).quantize(Q6)
            items_data[last_idx]['total_price_l1'] = last_share
    else:
        # 按金额比例分配（整体打折/加价）
        if raw_total > 0:
            for idx in range(len(items_data) - 1):
                ratio = to_decimal(items_data[idx]['total_price_l1']) / raw_total
                new_line = (target_total * ratio).quantize(Q2)
                items_data[idx]['unit_price_l1'] = (new_line / Decimal(str(items_data[idx]['quantity_l1']))).quantize(Q6)
                items_data[idx]['total_price_l1'] = new_line
            last_idx = len(items_data) - 1
            last_line = (target_total - sum(to_decimal(it['total_price_l1']) for i, it in enumerate(items_data) if i != last_idx)).quantize(Q2)
            items_data[last_idx]['unit_price_l1'] = (last_line / Decimal(str(items_data[last_idx]['quantity_l1']))).quantize(Q6)
            items_data[last_idx]['total_price_l1'] = last_line


# ── 采购单（只读） ──

def list_purchase_orders(db: Session, account_id: int, skip: int = 0, limit: int = 100, start_date: str = None, end_date: str = None, status: str = None, keyword: str = None, order_type: str = None):
    q = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.account_id == account_id)
    if order_type:
        q = q.filter(models.PurchaseOrder.order_type == order_type)
    if start_date:
        q = q.filter(models.PurchaseOrder.purchase_date_l1 >= start_date)
    if end_date:
        q = q.filter(models.PurchaseOrder.purchase_date_l1 <= end_date)
    if status:
        q = q.filter(models.PurchaseOrder.status == status)
    if keyword:
        q = q.filter(
            models.PurchaseOrder.order_no.contains(keyword) |
            models.PurchaseOrder.supplier.has(models.Supplier.name.contains(keyword))
        )
    total = q.count()
    items = q.order_by(models.PurchaseOrder.purchase_date_l1.desc()).offset(skip).limit(limit).all()
    return total, items


def get_purchase_order(db: Session, account_id: int, order_id: int):
    return get_or_404(db, models.PurchaseOrder, order_id, account_id)


# ── 销售单（只读） ──

def list_sale_orders(db: Session, account_id: int, skip: int = 0, limit: int = 100, start_date: str = None, end_date: str = None, status: str = None, order_type: str = None):
    q = db.query(models.SaleOrder).filter(models.SaleOrder.account_id == account_id)
    if order_type:
        q = q.filter(models.SaleOrder.order_type == order_type)
    if start_date:
        q = q.filter(models.SaleOrder.sale_date_l1 >= start_date)
    if end_date:
        q = q.filter(models.SaleOrder.sale_date_l1 <= end_date)
    if status:
        q = q.filter(models.SaleOrder.status == status)
    total = q.count()
    items = q.order_by(models.SaleOrder.sale_date_l1.desc()).offset(skip).limit(limit).all()
    return total, items


def get_sale_order(db: Session, account_id: int, order_id: int):
    return get_or_404(db, models.SaleOrder, order_id, account_id)