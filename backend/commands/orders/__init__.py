"""orders — 订单/发票命令包

公开接口：所有 Command 类在此导出，路由层统一从 commands.orders 导入。
内部模块前缀 _ 表示私有，不直接引用。
"""

# 导入各模块以触发 @register 装饰器
from . import _order  # noqa: F401
from . import _invoice  # noqa: F401

# 参数化订单命令（通过 order_type 区分 sale/purchase）
from ._order import (
    CreateOrder,
    CancelOrder,
    ReturnOrder,
    DeleteOrder,
    UpdateOrderItems,
    UpdateOrderFields,
    RestoreOrder,
)

# 发票专有命令
from ._invoice import (
    CreateInvoice,
    UpdateInvoice,
    CertifyInvoice,
    CreateInvoiceWithFixedAsset,
    ReverseInvoice,
    UpdateAssetWithInvoice,
)

__all__ = [
    # 参数化订单命令
    "CreateOrder",
    "CancelOrder",
    "ReturnOrder",
    "DeleteOrder",
    "UpdateOrderItems",
    "UpdateOrderFields",
    "RestoreOrder",
    # 发票命令
    "CreateInvoice",
    "UpdateInvoice",
    "CertifyInvoice",
    "CreateInvoiceWithFixedAsset",
    "ReverseInvoice",
    "UpdateAssetWithInvoice",
]
