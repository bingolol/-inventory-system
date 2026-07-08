# handlers.py — 事件处理器注册（声明式）

"""事件 handler 注册模块。

设计：Emit-as-Log（单一 seam）
- 写操作的日志由 Command 通过 emit() 触发
- 本模块是 OperationLog 的唯一写入点
- 使用声明式 EVENT_LOG_RULES 替代 12 个重复的 2 行 handler 函数
"""

from events import on
from crud.base import log_op


def _emit_log(order, default_action: str, entity_type: str, default_detail: str, **kw):
    entity_id = order.id if order is not None else kw.get('entity_id')
    log_op(
        kw['db'], kw['account_id'],
        kw.get('log_action', default_action),
        entity_type,
        entity_id,
        kw.get('log_detail', default_detail),
        operator=kw.get('operator', 'user'),
    )


EVENT_LOG_RULES = [
    ("sale_order.created",       "create", "sale_order",    "销售单创建"),
    ("sale_order.cancelled",     "update", "sale_order",    "销售单取消"),
    ("sale_order.returned",      "return", "sale_order",    "销售退货"),
    ("sale_order.restored",      "update", "sale_order",    "销售单恢复"),
    ("sale_order.deleted",       "delete", "sale_order",    "销售单删除"),
    ("sale_order.items_updated", "update", "sale_order",    "更新销售单明细"),
    ("sale_order.fields_updated","update", "sale_order",    "更新销售单字段"),
    ("purchase_order.created",   "create", "purchase_order","采购单创建"),
    ("purchase_order.updated",   "update", "purchase_order","采购单更新"),
    ("purchase_order.returned",  "return", "purchase_order","采购退货"),
    ("purchase_order.deleted",   "delete", "purchase_order","采购单删除"),
]


def _register():
    for event_name, action, entity_type, label in EVENT_LOG_RULES:
        def _handler(order, _action=action, _etype=entity_type, _label=label, **kw):
            _emit_log(order, _action, _etype, f"{_label}: {order.order_no}", **kw)
        _handler.__name__ = f"_log_{event_name.replace('.', '_')}"
        on(event_name, priority=10, name=_handler.__name__)(_handler)


_register()
