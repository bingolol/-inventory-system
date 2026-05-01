"""采购单 + 销售单 CRUD（含事务包裹和金额精度）"""

import logging
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
import models, schemas

from .base import _generate_order_no, _log, get_or_create_inventory
from .products import get_product
from .linkage import sale_create_income, sale_delete_income, sale_deduct_inventory, sale_restore_inventory
from utils import update_project_summary

logger = logging.getLogger("inventory")

# Decimal 量化工具：精确到分
Q2 = Decimal('0.01')
Q6 = Decimal('0.000001')

def _d(val):
    """安全转换为 Decimal：float→str→Decimal，Decimal直接返回"""
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def _distribute_total_price(items_data: list, target_total):
    """将自定义总额与明细合计的差额分配到各行单价

    策略：
    - 优先分配给 unit_price==0 的行（按数量加权）
    - 所有行都有单价时按金额比例分配（整体打折/加价）
    - 尾差给最后一行，确保合计精确
    """
    raw_total = sum(_d(it['total_price']) for it in items_data)
    target_total = _d(target_total)
    if raw_total == target_total:
        return  # 无需分配
    diff = target_total - raw_total

    zero_price_indices = [i for i, it in enumerate(items_data) if _d(it['unit_price']) == 0]
    if zero_price_indices:
        # 按数量加权分配给单价为0的行
        zero_qty_sum = sum(Decimal(str(items_data[i]['quantity'])) for i in zero_price_indices)
        if zero_qty_sum > 0:
            for idx in zero_price_indices[:-1]:
                qty = Decimal(str(items_data[idx]['quantity']))
                share = (diff * qty / zero_qty_sum).quantize(Q2)
                items_data[idx]['unit_price'] = (share / qty).quantize(Q6)
                items_data[idx]['total_price'] = share
            # 尾差给最后一行
            last_idx = zero_price_indices[-1]
            last_share = (target_total - sum(_d(it['total_price']) for i, it in enumerate(items_data) if i != last_idx)).quantize(Q2)
            items_data[last_idx]['unit_price'] = (last_share / Decimal(str(items_data[last_idx]['quantity']))).quantize(Q6)
            items_data[last_idx]['total_price'] = last_share
    else:
        # 按金额比例分配（整体打折/加价）
        if raw_total > 0:
            for idx in range(len(items_data) - 1):
                ratio = _d(items_data[idx]['total_price']) / raw_total
                new_line = (target_total * ratio).quantize(Q2)
                items_data[idx]['unit_price'] = (new_line / Decimal(str(items_data[idx]['quantity']))).quantize(Q6)
                items_data[idx]['total_price'] = new_line
            last_idx = len(items_data) - 1
            last_line = (target_total - sum(_d(it['total_price']) for i, it in enumerate(items_data) if i != last_idx)).quantize(Q2)
            items_data[last_idx]['unit_price'] = (last_line / Decimal(str(items_data[last_idx]['quantity']))).quantize(Q6)
            items_data[last_idx]['total_price'] = last_line


# ── 采购单 ──

def list_purchase_orders(db: Session, account_id: int, skip: int = 0, limit: int = 100, start_date: str = None, end_date: str = None, status: str = None, keyword: str = None):
    q = db.query(models.PurchaseOrder).filter(models.PurchaseOrder.account_id == account_id)
    if start_date:
        q = q.filter(models.PurchaseOrder.purchase_date >= start_date)
    if end_date:
        q = q.filter(models.PurchaseOrder.purchase_date <= end_date + " 23:59:59")
    if status:
        q = q.filter(models.PurchaseOrder.status == status)
    if keyword:
        q = q.filter(
            models.PurchaseOrder.order_no.contains(keyword) |
            models.PurchaseOrder.project_name.contains(keyword) |
            models.PurchaseOrder.supplier.has(models.Supplier.name.contains(keyword))
        )
    total = q.count()
    items = q.order_by(models.PurchaseOrder.purchase_date.desc()).offset(skip).limit(limit).all()
    return total, items


def get_purchase_order(db: Session, account_id: int, order_id: int):
    return db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.id == order_id
    ).first()


def create_purchase_order(db: Session, account_id: int, data: schemas.PurchaseOrderCreate, operator: str = "user"):
    if not data.items:
        raise ValueError("采购单至少包含1个商品")
    # ★ 校验：同一订单内商品不可重复
    product_ids = [item.product_id for item in data.items]
    dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
    if dup_pids:
        raise ValueError(f"同一商品不可重复添加，重复商品ID: {dup_pids}，请合并到一行")
    order_no = _generate_order_no(db, "PO")
    # ★ project_name 自动填充：如果传了 project_id 但未传 project_name，从 Project 表反查
    project_name = data.project_name
    if data.project_id and not project_name:
        project_name = db.query(models.Project.name).filter(
            models.Project.id == data.project_id
        ).scalar()

    order = models.PurchaseOrder(
        account_id=account_id,
        order_no=order_no,
        supplier_id=data.supplier_id,
        project_id=data.project_id,       # ★ 新增
        project_name=project_name,         # ★ 自动填充
        has_invoice=data.has_invoice,
        payment_method=data.payment_method,
        status="completed",
        notes=data.notes,
        total_price=0
    )
    db.add(order)
    db.flush()

    total = Decimal('0')
    for item_data in data.items:
        product = get_product(db, account_id, item_data.product_id)
        if not product:
            raise ValueError(f"商品不存在: ID={item_data.product_id}")
        line_total = (Decimal(str(item_data.quantity)) * _d(item_data.unit_price)).quantize(Q2)
        item = models.PurchaseItem(
            order_id=order.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            tax_rate=item_data.tax_rate if hasattr(item_data, 'tax_rate') else Decimal('0.13'),
            total_price=line_total
        )
        db.add(item)
        inv = get_or_create_inventory(db, account_id, item_data.product_id)
        inv.quantity += item_data.quantity
        total += line_total

    order.total_price = total.quantize(Q2)

    # ★ 统一重算项目汇总（不变量 III）
    if data.project_id:
        update_project_summary(db, data.project_id)

    _log(db, account_id, "create", "purchase_order", order.id, f"创建采购单 {order_no}: {len(data.items)}项商品, 总价={total}", operator=operator)
    db.flush()
    return order


def update_purchase_order(db: Session, account_id: int, order_id: int, data: schemas.PurchaseOrderUpdate, operator: str = "user"):
    order = get_purchase_order(db, account_id, order_id)
    if not order:
        return None
    # ★ 校验：同一订单内商品不可重复
    if data.items:
        product_ids = [item.product_id for item in data.items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise ValueError(f"同一商品不可重复添加，重复商品ID: {dup_pids}，请合并到一行")
    old_status = order.status
    old_project_id = order.project_id
    project_ids_to_update = set()  # ★ 收集所有需要重算的项目ID

    # ── 处理 items 全量替换 ──
    if data.items is not None:
        # 1a. 旧行库存回补（仅已完成状态的采购单）
        if old_status == "completed":
            for item in order.items:
                inv = get_or_create_inventory(db, account_id, item.product_id)
                inv.quantity -= item.quantity

        # 1b. 记录旧项目（删除旧行前保存）
        if old_project_id:
            project_ids_to_update.add(old_project_id)

        # 1c. 删除旧行
        for item in order.items[:]:
            db.delete(item)
        db.flush()

        # 1d. 新 items 为空 → 删除整个采购单
        if len(data.items) == 0:
            _log(db, account_id, "delete", "purchase_order", order_id,
                 f"删除采购单 {order.order_no}（商品行数归零自动删除）", operator=operator)
            db.delete(order)
            for pid in project_ids_to_update:
                update_project_summary(db, pid)
            db.flush()
            return None  # 表示采购单已删除

        # ★ 先更新普通字段（含 status），确保 new_status 已知
        for k, v in data.model_dump(exclude_unset=True).items():
            if k not in ("items",):
                setattr(order, k, v)
        new_status = order.status

        # 1e. 创建新行 + 库存扣减（基于 new_status）
        total = Decimal('0')
        for item_data in data.items:
            product = get_product(db, account_id, item_data.product_id)
            if not product:
                raise ValueError(f"商品不存在: ID={item_data.product_id}")
            line_total = (Decimal(str(item_data.quantity)) * _d(item_data.unit_price)).quantize(Q2)
            new_item = models.PurchaseItem(
                order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                tax_rate=item_data.tax_rate if hasattr(item_data, 'tax_rate') else Decimal('0.13'),
                total_price=line_total
            )
            db.add(new_item)
            if new_status == "completed":
                inv = get_or_create_inventory(db, account_id, item_data.product_id)
                inv.quantity += item_data.quantity
            total += line_total

        order.total_price = total.quantize(Q2)

    else:
        # ── 不改 items：处理普通字段更新 ──
        for k, v in data.model_dump(exclude_unset=True).items():
            if k != "items":
                setattr(order, k, v)
        new_status = order.status

        # ── 状态切换库存处理（仅不改 items 时生效）──
        if old_status == "completed" and new_status == "cancelled":
            for item in order.items:
                inv = get_or_create_inventory(db, account_id, item.product_id)
                inv.quantity -= item.quantity
        elif old_status == "cancelled" and new_status == "completed":
            for item in order.items:
                inv = get_or_create_inventory(db, account_id, item.product_id)
                inv.quantity += item.quantity

    # ★ 收集新项目ID（项目可能通过 setattr 被修改）
    if order.project_id:
        project_ids_to_update.add(order.project_id)

    # ★ 统一重算所有受影响项目的汇总（不变量 III）
    for pid in project_ids_to_update:
        update_project_summary(db, pid)

    _log(db, account_id, "update", "purchase_order", order_id,
         f"更新采购单 {order.order_no}: 状态={old_status}->{new_status}", operator=operator)
    db.flush()
    return order


def delete_purchase_order(db: Session, account_id: int, order_id: int, operator: str = "user"):
    order = get_purchase_order(db, account_id, order_id)
    if not order:
        return False
    project_id = order.project_id  # ★ 先保存

    if order.status == "completed":
        for item in order.items:
            inv = get_or_create_inventory(db, account_id, item.product_id)
            inv.quantity -= item.quantity
    _log(db, account_id, "delete", "purchase_order", order_id, f"删除采购单 {order.order_no}: 状态={order.status}", operator=operator)
    db.delete(order)

    # ★ 统一重算项目汇总（不变量 III）
    if project_id:
        update_project_summary(db, project_id)

    db.flush()
    return True


# ── 销售单 ──

def list_sale_orders(db: Session, account_id: int, skip: int = 0, limit: int = 100, start_date: str = None, end_date: str = None, status: str = None):
    q = db.query(models.SaleOrder).filter(models.SaleOrder.account_id == account_id)
    if start_date:
        q = q.filter(models.SaleOrder.sale_date >= start_date)
    if end_date:
        q = q.filter(models.SaleOrder.sale_date <= end_date + " 23:59:59")
    if status:
        q = q.filter(models.SaleOrder.status == status)
    total = q.count()
    items = q.order_by(models.SaleOrder.sale_date.desc()).offset(skip).limit(limit).all()
    return total, items


def get_sale_order(db: Session, account_id: int, order_id: int):
    return db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.id == order_id
    ).first()


def create_sale_order(db: Session, account_id: int, data: schemas.SaleOrderCreate, operator: str = "user"):
    if not data.items:
        raise ValueError("销售单至少包含1个商品")
    # ★ 校验：同一订单内商品不可重复
    product_ids = [item.product_id for item in data.items]
    dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
    if dup_pids:
        raise ValueError(f"同一商品不可重复添加，重复商品ID: {dup_pids}，请合并到一行")
    order_no = _generate_order_no(db, "SO")
    # ★ project_name 自动填充：如果传了 project_id 但未传 project_name，从 Project 表反查
    project_name = data.project_name
    if data.project_id and not project_name:
        project_name = db.query(models.Project.name).filter(
            models.Project.id == data.project_id
        ).scalar()

    # 项目业务禁止销售单扣库存（避免双扣）
    if data.project_id and data.deduct_inventory:
        raise ValueError("项目销售单不支持直接扣库存，请走项目领料/材料成本出库")

    order = models.SaleOrder(
        account_id=account_id,
        order_no=order_no,
        customer_id=data.customer_id,
        project_id=data.project_id,         # ★ 显式赋值
        project_name=project_name,           # ★ 自动填充
        deduct_inventory=bool(data.deduct_inventory) if data.deduct_inventory is not None else False,
        has_invoice=data.has_invoice,
        payment_status=data.payment_status,
        status="completed",
        notes=data.notes,
        total_price=0
    )
    db.add(order)
    db.flush()

    # ★ 计算明细合计，构建 item_data 列表
    items_data = []
    total = Decimal('0')
    for item_data in data.items:
        product = get_product(db, account_id, item_data.product_id)
        if not product:
            raise ValueError(f"商品不存在: ID={item_data.product_id}")
        line_total = (Decimal(str(item_data.quantity)) * _d(item_data.unit_price)).quantize(Q2)
        items_data.append({
            'product_id': item_data.product_id,
            'quantity': item_data.quantity,
            'unit_price': item_data.unit_price,
            'tax_rate': item_data.tax_rate if hasattr(item_data, 'tax_rate') else Decimal('0.01'),
            'total_price': line_total,
        })
        total += line_total

    # ★ 自定义金额：将差额分配到各行单价
    if data.total_price is not None:
        _distribute_total_price(items_data, data.total_price)

    # ★ 创建 SaleItem 行
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

    # 最终总额
    final_total = sum(_d(it['total_price']) for it in items_data)
    order.total_price = _d(data.total_price) if data.total_price is not None else final_total.quantize(Q2)
    db.flush()  # ★ 确保 order.items 关系可被遍历（零售扣库存/项目收入联动依赖）

    # ★ 零售扣库存：deduct_inventory=true 且 project_id为空 且 status=completed
    sale_deduct_inventory(db, account_id, order, operator)

    # ★ 联动：自动生成项目收入（不变量 II，幂等）
    sale_create_income(db, account_id, order, operator)

    # ★ 统一重算项目汇总（不变量 III，在 commit 之前）
    if data.project_id:
        update_project_summary(db, data.project_id)

    _log(db, account_id, "create", "sale_order", order.id, f"创建销售单 {order_no}: {len(data.items)}项商品, 总价={total}", operator=operator)
    db.flush()
    return order


def update_sale_order(db: Session, account_id: int, order_id: int, data: schemas.SaleOrderUpdate, operator: str = "user"):
    order = get_sale_order(db, account_id, order_id)
    if not order:
        return None
    # ★ 校验：同一订单内商品不可重复
    if data.items:
        product_ids = [item.product_id for item in data.items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise ValueError(f"同一商品不可重复添加，重复商品ID: {dup_pids}，请合并到一行")
    old_status = order.status
    old_project_id = order.project_id
    old_deduct_inventory = bool(order.deduct_inventory) if order.deduct_inventory is not None else False
    project_ids_to_update = set()  # ★ 收集所有需要重算的项目ID

    # ── 处理 items 全量替换 ──
    if data.items is not None:
        # 1a. 旧行库存回补（已完成的零售单才扣了库存）
        if old_status == "completed" and old_deduct_inventory and not old_project_id:
            sale_restore_inventory(db, account_id, order, operator)

        # 1b. 删除旧的项目收入（如有）
        if old_project_id:
            sale_delete_income(db, account_id, order_id, operator)
            project_ids_to_update.add(old_project_id)

        # 1c. 删除旧行
        for item in order.items[:]:
            db.delete(item)
        db.flush()

        # 1d. 新 items 为空 → 删除整个销售单
        if len(data.items) == 0:
            _log(db, account_id, "delete", "sale_order", order_id,
                 f"删除销售单 {order.order_no}（商品行数归零自动删除）", operator=operator)
            db.delete(order)
            for pid in project_ids_to_update:
                update_project_summary(db, pid)
            db.flush()
            return None

        # 1e. 校验项目单不允许扣库存
        if data.project_id and data.deduct_inventory:
            raise ValueError("项目销售单不支持直接扣库存，请走项目领料/材料成本出库")

        # 1f. 创建新行 + 自定义金额分配
        items_data = []
        total = Decimal('0')
        for item_data in data.items:
            product = get_product(db, account_id, item_data.product_id)
            if not product:
                raise ValueError(f"商品不存在: ID={item_data.product_id}")
            line_total = (Decimal(str(item_data.quantity)) * _d(item_data.unit_price)).quantize(Q2)
            items_data.append({
                'product_id': item_data.product_id,
                'quantity': item_data.quantity,
                'unit_price': item_data.unit_price,
                'tax_rate': item_data.tax_rate if hasattr(item_data, 'tax_rate') else Decimal('0.01'),
                'total_price': line_total,
            })
            total += line_total

        # ★ 自定义金额：将差额分配到各行单价
        if data.total_price is not None:
            _distribute_total_price(items_data, data.total_price)

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
        order.total_price = _d(data.total_price) if data.total_price is not None else final_total.quantize(Q2)

        # 1g. 新行扣库存（已完成的零售单）
        new_deduct_inventory = bool(data.deduct_inventory) if data.deduct_inventory is not None else old_deduct_inventory
        new_project_id = data.project_id if data.project_id is not None else old_project_id
        if old_status == "completed" and new_deduct_inventory and not new_project_id:
            sale_deduct_inventory(db, account_id, order, operator)

        # 1h. 重新生成项目收入（如有项目ID）
        if old_status == "completed" and new_project_id:
            sale_create_income(db, account_id, order, operator)
            project_ids_to_update.add(new_project_id)

    # ── 处理普通字段更新（排除 items 和 total_price）──
    # total_price 已在 items 处理逻辑中正确设置，此处不应覆盖
    for k, v in data.model_dump(exclude_unset=True).items():
        if k not in ("items", "total_price"):
            setattr(order, k, v)

    new_status = order.status
    new_deduct_inventory = bool(order.deduct_inventory) if order.deduct_inventory is not None else False

    # ── 状态切换库存处理（仅无 items 替换时生效）──
    if data.items is None:
        # 项目业务禁止销售单扣库存
        if order.project_id and (order.deduct_inventory is True):
            raise ValueError("项目销售单不支持直接扣库存，请走项目领料/材料成本出库")

        if old_status == "completed" and new_status == "cancelled" and old_deduct_inventory:
            sale_restore_inventory(db, account_id, order, operator)
        elif old_status == "cancelled" and new_status == "completed" and new_deduct_inventory:
            sale_deduct_inventory(db, account_id, order, operator)

        # 联动1：取消时删除项目收入
        if new_status == "cancelled" and order.project_id:
            deleted_pid = sale_delete_income(db, account_id, order_id, operator)
            if deleted_pid:
                project_ids_to_update.add(deleted_pid)

        # 联动2：恢复时重新生成项目收入
        if old_status == "cancelled" and new_status == "completed" and order.project_id:
            sale_create_income(db, account_id, order, operator)
            project_ids_to_update.add(order.project_id)

        # ★ 联动3：project_id 变更时，删除旧项目收入 + 创建新项目收入
        if data.project_id is not None and data.project_id != old_project_id:
            # 删除旧项目收入（如旧项目有收入）
            if old_project_id and new_status == "completed":
                deleted_pid = sale_delete_income(db, account_id, order_id, operator)
                if deleted_pid:
                    project_ids_to_update.add(deleted_pid)
            # 创建新项目收入（如新项目存在且状态为已完成）
            if data.project_id and new_status == "completed":
                sale_create_income(db, account_id, order, operator)
                project_ids_to_update.add(data.project_id)

        # ★ 只改总额不改明细时，重新分配各行单价
        if data.total_price is not None:
            order.total_price = _d(data.total_price)
            # 将差额分配到现有明细行
            items_data = [{
                'product_id': item.product_id,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'tax_rate': item.tax_rate,
                'total_price': item.total_price,
            } for item in order.items]
            _distribute_total_price(items_data, data.total_price)
            for item, it in zip(order.items, items_data):
                item.unit_price = it['unit_price']
                item.total_price = it['total_price']

    # ★ 统一重算所有受影响项目的汇总
    for pid in project_ids_to_update:
        update_project_summary(db, pid)

    _log(db, account_id, "update", "sale_order", order_id,
         f"更新销售单 {order.order_no}: 状态={old_status}->{new_status}", operator=operator)
    db.flush()
    return order


def delete_sale_order(db: Session, account_id: int, order_id: int, operator: str = "user"):
    order = get_sale_order(db, account_id, order_id)
    if not order:
        return False
    # ★ 零售扣库存：删除已完成零售单时回补库存
    sale_restore_inventory(db, account_id, order, operator)

    # ★ 联动：删除自动生成的项目收入（不变量 II）
    project_id_for_summary = sale_delete_income(db, account_id, order_id, operator)
    # 如果 sale_delete_income 没返回 project_id，用 order.project_id
    if not project_id_for_summary and order.project_id:
        project_id_for_summary = order.project_id

    _log(db, account_id, "delete", "sale_order", order_id, f"删除销售单 {order.order_no}: 状态={order.status}", operator=operator)
    db.delete(order)

    # ★ 统一重算项目汇总（不变量 III）
    if project_id_for_summary:
        update_project_summary(db, project_id_for_summary)

    db.flush()
    return True