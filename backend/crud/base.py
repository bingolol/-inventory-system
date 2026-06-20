"""公共函数：订单号生成、操作日志、库存查询"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
import models
from errors import BusinessError, ErrorCode

logger = logging.getLogger("inventory")


def _generate_order_no(db, prefix):
    """生成订单号：{中文前缀}{年}—{月}-{日}-{时}:{分}-{序号}，如 CG2026—2-17-20:01-01"""
    # 前缀映射：英文缩写 → 中文首字母大写
    prefix_map = {"PO": "CG", "PL": "RG", "SO": "XS", "PS": "XS"}
    cn_prefix = prefix_map.get(prefix, prefix)

    now = datetime.now()
    date_part = f"{now.year}—{now.month}-{now.day}"
    time_part = f"{now.hour:02d}:{now.minute:02d}"
    # LIKE 匹配需注意中文破折号
    pattern = f"{cn_prefix}{now.year}—{now.month}-{now.day}-{now.hour:02d}:{now.minute:02d}-%"
    model = models.PurchaseOrder if prefix in ("PO", "PL") else models.SaleOrder
    count = db.query(model).filter(model.order_no.like(pattern)).count()
    return f"{cn_prefix}{date_part}-{time_part}-{count + 1:02d}"


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


def update_account(db: Session, account_id: int, name: str):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        return None
    account.name = name
    db.flush()
    return account


def create_account(db: Session, name: str, type: str = "company", code: str = "", taxpayer_type: str = "small_scale"):
    """创建新账本，自动生成唯一 code"""
    if not code:
        # 自动生成 code：取名字拼音首字母或用递增数字
        import time
        code = f"acc_{int(time.time() * 1000) % 1000000}"
    account = models.Account(name=name, type=type, code=code, taxpayer_type=taxpayer_type)
    db.add(account)
    db.flush()
    return account


def delete_account(db: Session, account_id: int) -> bool:
    """删除账本，仅允许删除无业务数据的空账本"""
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        return False

    # 检查各关联表是否还有数据
    checks = [
        (models.Product, "商品"),
        (models.Supplier, "供应商"),
        (models.Customer, "客户"),
        (models.PurchaseOrder, "采购单"),
        (models.SaleOrder, "销售单"),
        (models.Invoice, "发票"),
        (models.Expense, "费用"),
        (models.PersonalTransaction, "个人流水"),
        (models.OpeningBalance, "期初余额"),
        (models.Inventory, "库存"),
        (models.OperationLog, "操作日志"),
        (models.CashFlowTransaction, "现金流"),
        (models.BankAccount, "银行账户"),
        (models.BankTransaction, "银行流水"),
        (models.Payment, "付款记录"),
        (models.Receipt, "收款记录"),
        (models.FixedAsset, "固定资产"),
        (models.IntangibleAsset, "无形资产"),
    ]
    for model, label in checks:
        if hasattr(model, 'account_id'):
            count = db.query(model).filter(model.account_id == account_id).count()
            if count > 0:
                raise BusinessError(code=ErrorCode.PRODUCT_HAS_TRANSACTIONS, data={"count": count, "label": label})

    db.delete(account)
    db.flush()
    return True