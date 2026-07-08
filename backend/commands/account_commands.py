from dataclasses import dataclass
from typing import Any, Optional

import models

from .base import Command, CommandHandler, register
from crud.base import log_op
from errors import BusinessError, ErrorCode
from crud.base import get_account
from finance_integration import get_or_create_ledger_id
from lineage import writes, TIER_L3


@dataclass
class CreateAccount(Command):
    name: str = ""
    type: str = "company"
    code: str = ""
    taxpayer_type: str = "small_scale"


@register(CreateAccount)
class CreateAccountHandler(CommandHandler):
    @writes("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    def handle(self, cmd: CreateAccount, db: Any) -> Any:
        code = cmd.code
        if not code:
            import time
            code = f"acc_{int(time.time() * 1000) % 1000000}"
        account = models.Account(
            name=cmd.name, type=cmd.type, code=code,
            taxpayer_type_l3=cmd.taxpayer_type,
        )
        db.add(account)
        db.flush()
        get_or_create_ledger_id(db, account.id)
        return account


@dataclass
class UpdateAccount(Command):
    """更新账本名称（account_id 从基类继承）"""
    name: Optional[str] = None

    def __post_init__(self):
        if self.name is None:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="name is required")


@register(UpdateAccount)
class UpdateAccountHandler(CommandHandler):
    def handle(self, cmd: UpdateAccount, db: Any) -> Any:
        account = get_account(db, cmd.account_id)
        if not account:
            raise BusinessError(
                code=ErrorCode.ORDER_NOT_FOUND,
                data={"order_type": "账本"}
            )
        account.name = cmd.name
        db.flush()
        log_op(db, cmd.account_id, "update", "account", account.id,
             f"更新账本: {account.name}", operator=cmd.operator)
        return account


@dataclass
class DeleteAccount(Command):
    account_id: int = 0


@register(DeleteAccount)
class DeleteAccountHandler(CommandHandler):
    def handle(self, cmd: DeleteAccount, db: Any) -> Any:
        account = get_account(db, cmd.account_id)
        if not account:
            return False

        checks = [
            (models.Product, "商品"),
            (models.Supplier, "供应商"),
            (models.Customer, "客户"),
            (models.PurchaseOrder, "采购单"),
            (models.SaleOrder, "销售单"),
            (models.Invoice, "发票"),
            (models.Expense, "费用"),
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
                count = db.query(model).filter(model.account_id == cmd.account_id).count()
                if count > 0:
                    raise BusinessError(
                        code=ErrorCode.PRODUCT_HAS_TRANSACTIONS,
                        data={"count": count, "label": label}
                    )

        log_op(db, cmd.account_id, "delete", "account", account.id,
             f"删除账本: {account.name}", operator=cmd.operator)
        db.delete(account)
        db.flush()
        return True
