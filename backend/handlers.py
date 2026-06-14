# handlers.py — 事件处理器注册（v7 精简版）

"""事件 handler 注册模块。

import handlers 即完成所有事件注册（模块加载时自动执行装饰器）。

v7 重构后：移除项目模块，handlers 只保留日志 handler。
库存/收入联动已移至 Command Handler 显式调用。

注册事件：
  sale_order.created       → log(10)
  sale_order.cancelled     → log(10)
  sale_order.deleted       → log(10)
  sale_order.restored      → log(10)
  sale_order.items_updated → log(10)

  purchase_order.created → log(10)
  purchase_order.updated → log(10)
  purchase_order.deleted → log(10)
"""

from events import on
from crud.base import _log


# ── sale_order.created ────────────────────────────────────

@on('sale_order.created', priority=10, name='log_sale_created')
def _log_sale_created(order, **kw):
    _log(kw['db'], kw['account_id'], 'create', 'sale_order', order.id,
         f'销售单创建: {order.order_no}', operator=kw.get('operator', 'user'))


# ── sale_order.cancelled ──────────────────────────────────

@on('sale_order.cancelled', priority=10, name='log_sale_cancelled')
def _log_sale_cancelled(order, **kw):
    _log(kw['db'], kw['account_id'], 'update', 'sale_order', order.id,
         f'销售单取消: {order.order_no}', operator=kw.get('operator', 'user'))


# ── sale_order.deleted ────────────────────────────────────

@on('sale_order.deleted', priority=10, name='log_sale_deleted')
def _log_sale_deleted(order, **kw):
    _log(kw['db'], kw['account_id'], 'delete', 'sale_order', order.id,
         f'销售单删除: {order.order_no}', operator=kw.get('operator', 'user'))


# ── sale_order.restored ──────────────────────────────────

@on('sale_order.restored', priority=10, name='log_sale_restored')
def _log_sale_restored(order, **kw):
    _log(kw['db'], kw['account_id'], 'update', 'sale_order', order.id,
         f'销售单恢复: {order.order_no}', operator=kw.get('operator', 'user'))


# ── sale_order.items_updated ─────────────────────────────

@on('sale_order.items_updated', priority=10, name='log_sale_items_updated')
def _log_sale_items_updated(order, **kw):
    _log(kw['db'], kw['account_id'], 'update', 'sale_order', order.id,
         f'销售单明细更新: {order.order_no}', operator=kw.get('operator', 'user'))


# ── purchase_order.created ────────────────────────────────

@on('purchase_order.created', priority=10, name='log_purchase_created')
def _log_purchase_created(order, **kw):
    _log(kw['db'], kw['account_id'], 'create', 'purchase_order', order.id,
         f'采购单创建: {order.order_no}', operator=kw.get('operator', 'user'))


# ── purchase_order.updated ────────────────────────────────

@on('purchase_order.updated', priority=10, name='log_purchase_updated')
def _log_purchase_updated(order, **kw):
    _log(kw['db'], kw['account_id'], 'update', 'purchase_order', order.id,
         f'采购单更新: {order.order_no}', operator=kw.get('operator', 'user'))


# ── purchase_order.deleted ────────────────────────────────

@on('purchase_order.deleted', priority=10, name='log_purchase_deleted')
def _log_purchase_deleted(order, **kw):
    _log(kw['db'], kw['account_id'], 'delete', 'purchase_order', order.id,
         f'采购单删除: {order.order_no}', operator=kw.get('operator', 'user'))