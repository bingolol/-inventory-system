"""公共函数：订单号生成、操作日志、库存查询"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
import models

logger = logging.getLogger("inventory")


def _generate_order_no(db, prefix):
    """生成订单号：{前缀}{日期}-{时分秒}-{序号}，如 PO20260428-143025-001"""
    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    pattern = f"{prefix}{date_part}-{time_part}-%"
    model = models.PurchaseOrder if prefix == "PO" else models.SaleOrder
    count = db.query(model).filter(model.order_no.like(pattern)).count()
    return f"{prefix}{date_part}-{time_part}-{count + 1:03d}"


def _log(db, account_id, operation, entity_type, entity_id, detail="", operator="user"):
    """写入操作日志（只 add+flush，由调用方统一 commit）"""
    log = models.OperationLog(
        account_id=account_id,
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        operator=operator
    )
    db.add(log)
    db.flush()


def get_or_create_inventory(db: Session, account_id: int, product_id: int) -> models.Inventory:
    """获取或创建库存记录"""
    inv = db.query(models.Inventory).filter(
        models.Inventory.account_id == account_id,
        models.Inventory.product_id == product_id
    ).first()
    if not inv:
        inv = models.Inventory(account_id=account_id, product_id=product_id, quantity=0)
        db.add(inv)
        db.flush()
    return inv


# ── Account ──

def list_accounts(db: Session):
    return db.query(models.Account).all()


def get_account(db: Session, account_id: int):
    return db.query(models.Account).filter(models.Account.id == account_id).first()