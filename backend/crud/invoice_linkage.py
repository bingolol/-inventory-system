# crud/invoice_linkage.py — 发票关联领域服务(单一真相源)

"""发票与订单/采购/费用的关联查询,作为"是否有发票"的唯一真相源。

方案1:删除 SaleOrder/PurchaseOrder/Expense 的 has_invoice 布尔字段后,
所有"该记录是否有发票"的判断改走本模块派生查询,从 Invoice 表的
related_order_id + related_order_type 推导。

设计参考:crud/inventory_ops.py(领域服务,handler 调用,非纯查询也非独立命令)。
关联的写操作(设置 related_order_id/type)由 CreateInvoiceHandler 在 ORM 上完成,
本模块只提供:派生查询 + 防孤儿校验 + 对账查询。
"""

from typing import Set, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import exists as sa_exists

import models
from errors import BusinessError, ErrorCode
from operation_result import EntityType

VALID_ORDER_TYPES = (EntityType.SALE_ORDER, EntityType.PURCHASE_ORDER, EntityType.EXPENSE, EntityType.FIXED_ASSET)

_TARGET_MODEL = {
    EntityType.SALE_ORDER: models.SaleOrder,
    EntityType.PURCHASE_ORDER: models.PurchaseOrder,
    EntityType.EXPENSE: models.Expense,
    EntityType.FIXED_ASSET: models.FixedAsset,
}


def has_invoice(db: Session, account_id: int, order_type: str, order_id: int) -> bool:
    """派生查询:指定记录是否有发票关联(单一真相源)。

    替代读 SaleOrder/PurchaseOrder/Expense.has_invoice 字段。
    用于:详情页、对账、所得税税务口径筛有票费用等单条查询场景。
    """
    if order_type not in VALID_ORDER_TYPES:
        return False
    return db.query(
        sa_exists().where(
            models.Invoice.account_id == account_id,
            models.Invoice.related_order_type == order_type,
            models.Invoice.related_order_id == order_id,
        )
    ).scalar()


def bulk_has_invoice(db: Session, account_id: int, order_type: str, ids: List[int]) -> Set[int]:
    """批量派生查询:返回这批 id 中有发票关联的 id 集合。

    用于列表页,避免 N+1 查询。一次 SQL 查出该类型下所有关联到 ids 的发票,
    取 related_order_id 的 distinct 集合。
    """
    if not ids or order_type not in VALID_ORDER_TYPES:
        return set()
    rows = db.query(models.Invoice.related_order_id).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.related_order_type == order_type,
        models.Invoice.related_order_id.in_(ids),
    ).distinct().all()
    return {r[0] for r in rows}


def list_invoices(db: Session, account_id: int, order_type: str, order_id: int) -> List[models.Invoice]:
    """查指定记录关联的发票列表。

    用于对账:取代 reconciliations.py 的 counterparty_name 字符串模糊匹配,
    改为按 related_order_id 精确查询。
    """
    if order_type not in VALID_ORDER_TYPES:
        return []
    return db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.related_order_type == order_type,
        models.Invoice.related_order_id == order_id,
    ).all()


def validate_link_target(db: Session, account_id: int, order_type: str, order_id: int) -> None:
    """校验关联目标存在(防孤儿引用)。

    在 CreateInvoiceHandler 内、设置 ORM related_order_id 之前调用。
    若 order_type 合法但 order_id 在对应表不存在,抛 BusinessError。
    order_type 为 None/空时跳过(允许无关联发票)。
    """
    if not order_type or not order_id:
        return
    if order_type not in VALID_ORDER_TYPES:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"非法的关联类型: {order_type},合法值: {list(VALID_ORDER_TYPES)}",
            data={"order_type": order_type, "valid_types": list(VALID_ORDER_TYPES)},
        )
    model_cls = _TARGET_MODEL[order_type]
    found = db.query(model_cls.id).filter(
        model_cls.id == order_id,
        model_cls.account_id == account_id,
    ).first()
    if not found:
        raise BusinessError(
            code=ErrorCode.ORDER_NOT_FOUND,
            message=f"关联目标不存在: {order_type} #{order_id}",
            data={"order_type": order_type, "order_id": order_id},
        )
