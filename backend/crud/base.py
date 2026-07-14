"""公共函数：订单号生成、操作日志、库存查询"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
import models
from errors import BusinessError, ErrorCode
from utils.sequencer import next_order_no as gen_order_no
from utils.sequencer import next_advance_no, next_invoice_no

logger = logging.getLogger("inventory")


def log_op(db, account_id, operation, entity_type, entity_id, detail="", operator="user"):
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


def get_or_create_inventory(db: Session, account_id: int, product_id: int):
    """获取或创建库存记录(仅实物商品;服务类商品返回 None)

    服务类商品(track_inventory=False)无库存概念,不创建 Inventory 记录。
    此前无脑创建 quantity_l4=0 的空记录,违反 BR-7 并造成 AdjustInventory
    else 分支误改脏数据。现在统一通过 domain.product_kind 判断。
    """
    product = db.query(models.Product).filter(
        models.Product.id == product_id
    ).first()
    if product is not None:
        from domain.product_kind import should_track_inventory
        if not should_track_inventory(product):
            return None

    inv = db.query(models.Inventory).filter(
        models.Inventory.account_id == account_id,
        models.Inventory.product_id == product_id
    ).first()
    if not inv:
        inv = models.Inventory(account_id=account_id, product_id=product_id, quantity_l4=0)
        db.add(inv)
        db.flush()
    return inv


# ── Account ──

def list_accounts(db: Session):
    return db.query(models.Account).all()


def get_account(db: Session, account_id: int):
    return db.query(models.Account).filter(models.Account.id == account_id).first()


def update_account(db: Session, account_id: int, name: str, taxpayer_type: str = None):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        return None
    account.name = name
    if taxpayer_type is not None and taxpayer_type != account.taxpayer_type_l3:
        account.taxpayer_type_l3 = taxpayer_type
        effective_period = datetime.now().strftime("%Y-%m")
        db.add(models.TaxpayerTypeHistory(
            account_id=account_id,
            taxpayer_type_l3=taxpayer_type,
            effective_period=effective_period,
        ))
    db.flush()
    return account


def create_account(db: Session, name: str, type: str = "company", code: str = "", taxpayer_type: str = "small_scale"):
    """创建新账本，自动生成唯一 code"""
    if not code:
        # 自动生成 code：取名字拼音首字母或用递增数字
        import time
        code = f"acc_{int(time.time() * 1000) % 1000000}"
    account = models.Account(name=name, type=type, code=code, taxpayer_type_l3=taxpayer_type)
    db.add(account)
    db.flush()
    return account


def delete_account(db: Session, account_id: int, operator: str = "system") -> bool:
    """删除账本，仅允许删除无业务数据的空账本"""
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        return False

    # 检查各关联表是否还有数据
    # 注意：OperationLog 是元数据（delete_account 自身会写日志），必须放最后检查，
    # 否则会先于 BankAccount 等真实业务表触发，导致错误消息与实际阻塞原因不符。
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
        (models.CashFlowTransaction, "现金流"),
        (models.BankAccount, "银行账户"),
        (models.BankTransaction, "银行流水"),
        (models.Payment, "付款记录"),
        (models.Receipt, "收款记录"),
        (models.FixedAsset, "固定资产"),
        (models.IntangibleAsset, "无形资产"),
        (models.OperationLog, "操作日志"),
    ]
    for model, label in checks:
        if hasattr(model, 'account_id'):
            count = db.query(model).filter(model.account_id == account_id).count()
            if count > 0:
                raise BusinessError(
                    code=ErrorCode.ACCOUNT_HAS_BUSINESS_DATA,
                    message=f"账本存在 {count} 条{label}，无法删除",
                    data={"count": count, "label": label},
                )

    log_op(db, account_id, "delete", "account", account_id, f"删除账本: {account.name}", operator=operator)
    db.delete(account)
    db.flush()
    return True


def resolve_taxpayer_type_by_date(db: Session, account_id: int, target_date):
    """查询指定日期生效的纳税人类型"""
    from datetime import date as date_type
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    ref_period = target_date.strftime("%Y-%m") if hasattr(target_date, "strftime") else str(target_date)
    result = db.query(models.TaxpayerTypeHistory).filter(
        models.TaxpayerTypeHistory.account_id == account_id,
        models.TaxpayerTypeHistory.effective_period <= ref_period,
    ).order_by(models.TaxpayerTypeHistory.effective_period.desc()).first()
    if result:
        return result.taxpayer_type_l3
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    return account.taxpayer_type_l3 if account else "small_scale"