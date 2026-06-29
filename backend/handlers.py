# handlers.py — 事件处理器注册（Emit-as-Log 单一写入点）

"""事件 handler 注册模块。

import handlers 即完成所有事件注册（模块加载时自动执行装饰器）。

设计：Emit-as-Log（单一 seam）
- 写操作的日志由 Command 通过 emit() 触发，emit 携带 log_action / log_detail
  元数据；本模块的 handler 是 OperationLog 的唯一写入点。
- 历史问题：Command 既 emit 又直接 _log，handler 再 _log → 同一操作 2 条日志。
  现已移除 Command 中的直接 _log，日志只在此处写一次。

注册事件（sale_order / purchase_order 全生命周期）：
  sale_order.created / cancelled / returned / restored / deleted / items_updated / fields_updated
  purchase_order.created / updated / returned / deleted
"""

from events import on
from crud.base import _log


def _emit_log(order, default_action: str, entity_type: str, default_detail: str, **kw):
    """通用日志写入：优先用 emit 携带的 log_action / log_detail，否则用默认值。

    - order: 事件携带的订单对象（emit 必传，由 handler 签名提取后显式传入），
      用于取 entity_id
    - log_action: 操作类型（create/update/delete/return），由 emit 传入或回退默认
    - log_detail: 日志详情，由 emit 传入（携带业务上下文）或回退默认文案
    这是 OperationLog 的唯一写入入口，确保每个操作恰好 1 条日志。
    """
    entity_id = order.id if order is not None else kw.get('entity_id')
    _log(
        kw['db'], kw['account_id'],
        kw.get('log_action', default_action),
        entity_type,
        entity_id,
        kw.get('log_detail', default_detail),
        operator=kw.get('operator', 'user'),
    )


# ── sale_order ────────────────────────────────────────────

@on('sale_order.created', priority=10, name='log_sale_created')
def _log_sale_created(order, **kw):
    _emit_log(order, 'create', 'sale_order', f'销售单创建: {order.order_no}', **kw)


@on('sale_order.cancelled', priority=10, name='log_sale_cancelled')
def _log_sale_cancelled(order, **kw):
    _emit_log(order, 'update', 'sale_order', f'销售单取消: {order.order_no}', **kw)


@on('sale_order.returned', priority=10, name='log_sale_returned')
def _log_sale_returned(order, **kw):
    _emit_log(order, 'return', 'sale_order', f'销售退货: {order.order_no}', **kw)


@on('sale_order.restored', priority=10, name='log_sale_restored')
def _log_sale_restored(order, **kw):
    _emit_log(order, 'update', 'sale_order', f'销售单恢复: {order.order_no}', **kw)


@on('sale_order.deleted', priority=10, name='log_sale_deleted')
def _log_sale_deleted(order, **kw):
    _emit_log(order, 'delete', 'sale_order', f'销售单删除: {order.order_no}', **kw)


@on('sale_order.items_updated', priority=10, name='log_sale_items_updated')
def _log_sale_items_updated(order, **kw):
    _emit_log(order, 'update', 'sale_order', f'更新销售单明细: {order.order_no}', **kw)


@on('sale_order.fields_updated', priority=10, name='log_sale_fields_updated')
def _log_sale_fields_updated(order, **kw):
    _emit_log(order, 'update', 'sale_order', f'更新销售单字段: {order.order_no}', **kw)


# ── purchase_order ────────────────────────────────────────

@on('purchase_order.created', priority=10, name='log_purchase_created')
def _log_purchase_created(order, **kw):
    _emit_log(order, 'create', 'purchase_order', f'采购单创建: {order.order_no}', **kw)


@on('purchase_order.updated', priority=10, name='log_purchase_updated')
def _log_purchase_updated(order, **kw):
    _emit_log(order, 'update', 'purchase_order', f'采购单更新: {order.order_no}', **kw)


@on('purchase_order.returned', priority=10, name='log_purchase_returned')
def _log_purchase_returned(order, **kw):
    _emit_log(order, 'return', 'purchase_order', f'采购退货: {order.order_no}', **kw)


@on('purchase_order.deleted', priority=10, name='log_purchase_deleted')
def _log_purchase_deleted(order, **kw):
    _emit_log(order, 'delete', 'purchase_order', f'采购单删除: {order.order_no}', **kw)
