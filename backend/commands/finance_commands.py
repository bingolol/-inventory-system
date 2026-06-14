"""财务 Command + Handler — 3个命令覆盖期初余额+现金流水业务操作

从 routers/opening_balances.py + routers/cash_flows.py 逻辑提取，Command 模式封装。
每个 Handler 包含：数据校验 → ORM 操作 → 日志记录。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import models

from .base import Command, CommandHandler, register
from .crud_compat import _log
from utils import _d


# ═══════════════════════════════════════════════════════════
# 1. CreateOpeningBalance — 创建期初余额
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateOpeningBalance(Command):
    date: str = ""                          # YYYY-MM-DD
    cash_balance: Any = None                # Decimal
    bank_balance: Any = None                # Decimal
    accounts_receivable: Any = None         # Decimal
    inventory_value: Any = None             # Decimal
    accounts_payable: Any = None            # Decimal
    tax_payable: Any = None                 # Decimal
    retained_earnings: Any = None           # Decimal


@register(CreateOpeningBalance)
class CreateOpeningBalanceHandler(CommandHandler):
    def handle(self, cmd: CreateOpeningBalance, db: Any) -> Any:
        # 1. 校验：日期不能重复
        ob_date = datetime.strptime(cmd.date, "%Y-%m-%d").date()
        existing = db.query(models.OpeningBalance).filter(
            models.OpeningBalance.account_id == cmd.account_id,
            models.OpeningBalance.date == ob_date,
        ).first()
        if existing:
            raise ValueError(f"该日期已存在期初余额: {cmd.date}")

        # 2. 校验：资产 = 负债 + 权益
        total_assets = _d(cmd.cash_balance) + _d(cmd.bank_balance) + _d(cmd.accounts_receivable) + _d(cmd.inventory_value)
        total_liabilities = _d(cmd.accounts_payable) + _d(cmd.tax_payable)
        total_equity = _d(cmd.retained_earnings)
        if total_assets != total_liabilities + total_equity:
            raise ValueError(
                f"资产负债表不平衡: 资产={total_assets}, 负债+权益={total_liabilities + total_equity}"
            )

        # 3. 创建 ORM 对象
        opening_balance = models.OpeningBalance(
            account_id=cmd.account_id,
            date=ob_date,
            cash_balance=cmd.cash_balance,
            bank_balance=cmd.bank_balance,
            accounts_receivable=cmd.accounts_receivable,
            inventory_value=cmd.inventory_value,
            accounts_payable=cmd.accounts_payable,
            tax_payable=cmd.tax_payable,
            retained_earnings=cmd.retained_earnings,
        )
        db.add(opening_balance)
        db.flush()

        # 4. 日志
        _log(db, cmd.account_id, "create", "opening_balance", opening_balance.id,
             f"创建期初余额: {cmd.date}", operator=cmd.operator)
        db.flush()
        return opening_balance


# ═══════════════════════════════════════════════════════════
# 2. UpdateOpeningBalance — 更新期初余额
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateOpeningBalance(Command):
    opening_balance_id: int = 0
    date: Optional[str] = None              # YYYY-MM-DD
    cash_balance: Any = None                # Optional[Decimal]
    bank_balance: Any = None                # Optional[Decimal]
    accounts_receivable: Any = None         # Optional[Decimal]
    inventory_value: Any = None             # Optional[Decimal]
    accounts_payable: Any = None            # Optional[Decimal]
    tax_payable: Any = None                 # Optional[Decimal]
    retained_earnings: Any = None           # Optional[Decimal]


@register(UpdateOpeningBalance)
class UpdateOpeningBalanceHandler(CommandHandler):
    def handle(self, cmd: UpdateOpeningBalance, db: Any) -> Any:
        # 1. 查记录
        opening_balance = db.query(models.OpeningBalance).filter(
            models.OpeningBalance.id == cmd.opening_balance_id,
            models.OpeningBalance.account_id == cmd.account_id,
        ).first()
        if not opening_balance:
            raise ValueError("期初余额不存在")

        # 2. 更新字段
        if cmd.date is not None:
            opening_balance.date = datetime.strptime(cmd.date, "%Y-%m-%d").date()
        if cmd.cash_balance is not None:
            opening_balance.cash_balance = cmd.cash_balance
        if cmd.bank_balance is not None:
            opening_balance.bank_balance = cmd.bank_balance
        if cmd.accounts_receivable is not None:
            opening_balance.accounts_receivable = cmd.accounts_receivable
        if cmd.inventory_value is not None:
            opening_balance.inventory_value = cmd.inventory_value
        if cmd.accounts_payable is not None:
            opening_balance.accounts_payable = cmd.accounts_payable
        if cmd.tax_payable is not None:
            opening_balance.tax_payable = cmd.tax_payable
        if cmd.retained_earnings is not None:
            opening_balance.retained_earnings = cmd.retained_earnings

        # 3. 校验：更新后资产 = 负债 + 权益
        total_assets = (_d(opening_balance.cash_balance) + _d(opening_balance.bank_balance)
                        + _d(opening_balance.accounts_receivable) + _d(opening_balance.inventory_value))
        total_liabilities = _d(opening_balance.accounts_payable) + _d(opening_balance.tax_payable)
        total_equity = _d(opening_balance.retained_earnings)
        if total_assets != total_liabilities + total_equity:
            raise ValueError(
                f"资产负债表不平衡: 资产={total_assets}, 负债+权益={total_liabilities + total_equity}"
            )

        # 4. 日志
        db.flush()
        _log(db, cmd.account_id, "update", "opening_balance", opening_balance.id,
             f"更新期初余额: {opening_balance.date}", operator=cmd.operator)
        db.flush()
        return opening_balance


# ═══════════════════════════════════════════════════════════
# 3. CreateCashFlowTransaction — 创建现金流水
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateCashFlowTransaction(Command):
    type: str = ""                          # inflow / outflow
    amount: Any = None                      # Decimal
    flow_category: str = "operating"        # operating / investing / financing
    description: str = ""
    transaction_date: str = ""              # YYYY-MM-DD
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


@register(CreateCashFlowTransaction)
class CreateCashFlowTransactionHandler(CommandHandler):
    def handle(self, cmd: CreateCashFlowTransaction, db: Any) -> Any:
        # 1. 创建 ORM 对象
        transaction = models.CashFlowTransaction(
            account_id=cmd.account_id,
            type=cmd.type,
            amount=cmd.amount,
            flow_category=cmd.flow_category,
            description=cmd.description,
            transaction_date=datetime.strptime(cmd.transaction_date, "%Y-%m-%d"),
            related_entity_type=cmd.related_entity_type,
            related_entity_id=cmd.related_entity_id,
        )
        db.add(transaction)
        db.flush()

        # 2. 日志
        _log(db, cmd.account_id, "create", "cash_flow", transaction.id,
             f"创建现金流水: {cmd.type} {cmd.amount}", operator=cmd.operator)
        db.flush()
        return transaction


# ═══════════════════════════════════════════════════════════
# 4. UpdateCashFlowTransaction — 更新现金流水
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateCashFlowTransaction(Command):
    transaction_id: int = 0
    type: Optional[str] = None
    amount: Any = None                      # Optional[Decimal]
    flow_category: Optional[str] = None
    description: Optional[str] = None
    transaction_date: Optional[str] = None  # YYYY-MM-DD
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


@register(UpdateCashFlowTransaction)
class UpdateCashFlowTransactionHandler(CommandHandler):
    def handle(self, cmd: UpdateCashFlowTransaction, db: Any) -> Any:
        # 1. 查记录
        transaction = db.query(models.CashFlowTransaction).filter(
            models.CashFlowTransaction.id == cmd.transaction_id,
            models.CashFlowTransaction.account_id == cmd.account_id,
        ).first()
        if not transaction:
            raise ValueError("现金流水不存在")

        # 2. 更新字段
        if cmd.type is not None:
            transaction.type = cmd.type
        if cmd.amount is not None:
            transaction.amount = cmd.amount
        if cmd.flow_category is not None:
            transaction.flow_category = cmd.flow_category
        if cmd.description is not None:
            transaction.description = cmd.description
        if cmd.transaction_date is not None:
            try:
                transaction.transaction_date = datetime.strptime(cmd.transaction_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"日期格式无效: {cmd.transaction_date}，应为 YYYY-MM-DD")
        if cmd.related_entity_type is not None:
            transaction.related_entity_type = cmd.related_entity_type
        if cmd.related_entity_id is not None:
            transaction.related_entity_id = cmd.related_entity_id

        # 3. 日志
        _log(db, cmd.account_id, "update", "cash_flow", cmd.transaction_id,
             f"更新现金流水: {transaction.type} {transaction.amount}", operator=cmd.operator)
        db.flush()
        return transaction


# ═══════════════════════════════════════════════════════════
# 5. DeleteCashFlowTransaction — 删除现金流水
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteCashFlowTransaction(Command):
    transaction_id: int = 0


@register(DeleteCashFlowTransaction)
class DeleteCashFlowTransactionHandler(CommandHandler):
    def handle(self, cmd: DeleteCashFlowTransaction, db: Any) -> Any:
        # 1. 查记录
        transaction = db.query(models.CashFlowTransaction).filter(
            models.CashFlowTransaction.id == cmd.transaction_id,
            models.CashFlowTransaction.account_id == cmd.account_id,
        ).first()
        if not transaction:
            raise ValueError("现金流水不存在")

        # 2. 日志 + 删除
        _log(db, cmd.account_id, "delete", "cash_flow", cmd.transaction_id,
             f"删除现金流水: {transaction.type} {transaction.amount}", operator=cmd.operator)

        db.delete(transaction)
        db.flush()
        return True