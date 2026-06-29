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
from crud.base import _log
from errors import BusinessError, ErrorCode
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
    fixed_assets_original: Any = None       # Decimal (非流动资产)
    accumulated_depreciation: Any = None    # Decimal (累计折旧)
    intangible_assets_original: Any = None  # Decimal (无形资产原值)
    accumulated_amortization: Any = None    # Decimal (累计摊销)
    accounts_payable: Any = None            # Decimal
    tax_payable: Any = None                 # Decimal
    long_term_borrowings: Any = None        # Decimal (非流动负债)
    paid_in_capital: Any = None             # Decimal
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
            raise BusinessError(code=ErrorCode.BALANCE_ALREADY_EXISTS, data={"date": cmd.date})

        # 2. 校验：资产 = 负债 + 权益（含非流动资产/负债）
        total_assets = (_d(cmd.cash_balance) + _d(cmd.bank_balance)
                        + _d(cmd.accounts_receivable) + _d(cmd.inventory_value)
                        + _d(cmd.fixed_assets_original) - _d(cmd.accumulated_depreciation)
                        + _d(cmd.intangible_assets_original) - _d(cmd.accumulated_amortization))
        total_liabilities = _d(cmd.accounts_payable) + _d(cmd.tax_payable) + _d(cmd.long_term_borrowings)
        total_equity = _d(cmd.paid_in_capital) + _d(cmd.retained_earnings)
        if total_assets != total_liabilities + total_equity:
            raise BusinessError(
                code=ErrorCode.BALANCE_SHEET_UNBALANCED,
                data={"assets": total_assets, "liabilities": total_liabilities + total_equity}
            )

        # 3. 创建 ORM 对象
        opening_balance = models.OpeningBalance(
            account_id=cmd.account_id,
            date=ob_date,
            cash_balance=cmd.cash_balance,
            bank_balance=cmd.bank_balance,
            accounts_receivable=cmd.accounts_receivable,
            inventory_value=cmd.inventory_value,
            fixed_assets_original=cmd.fixed_assets_original,
            accumulated_depreciation=cmd.accumulated_depreciation,
            intangible_assets_original=cmd.intangible_assets_original,
            accumulated_amortization=cmd.accumulated_amortization,
            accounts_payable=cmd.accounts_payable,
            tax_payable=cmd.tax_payable,
            long_term_borrowings=cmd.long_term_borrowings,
            paid_in_capital=cmd.paid_in_capital,
            retained_earnings=cmd.retained_earnings,
        )
        db.add(opening_balance)
        db.flush()

        # 4. 过账到总账
        lines = []
        for code, field in [("1001", "cash_balance"), ("1002", "bank_balance"),
                            ("1122", "accounts_receivable"), ("1405", "inventory_value"),
                            ("1601", "fixed_assets_original"), ("1701", "intangible_assets_original")]:
            val = _d(getattr(cmd, field, 0))
            if val > 0:
                lines.append({"account_code": code, "debit": val, "credit": Decimal("0")})
        for code, field in [("1602", "accumulated_depreciation"), ("1702", "accumulated_amortization"),
                            ("2202", "accounts_payable"), ("2221", "tax_payable"),
                            ("2501", "long_term_borrowings"), ("3001", "paid_in_capital"),
                            ("4104", "retained_earnings")]:
            val = _d(getattr(cmd, field, 0))
            if val > 0:
                lines.append({"account_code": code, "debit": Decimal("0"), "credit": val})
        from finance_integration import post_journal
        post_journal(db, cmd.account_id, "opening_balance", {
            "lines": lines,
            "date": cmd.date,
            "source_model": "opening_balance",
            "source_id": opening_balance.id,
        })

        # 5. 同步 BankAccount.balance 与 1002 科目余额
        #    防止期初余额进总账但 BankAccount.balance 未更新导致后续付款/收款校验出错
        #    若账本下有多个 BankAccount，按"第一个"作为主账户累计（与日常付款/收款用 BankAccount 一致）
        bank_balance_val = _d(cmd.bank_balance)
        if bank_balance_val > 0:
            bank_account = db.query(models.BankAccount).filter(
                models.BankAccount.account_id == cmd.account_id,
            ).order_by(models.BankAccount.id.asc()).first()
            if bank_account:
                bank_account.balance = (Decimal(str(bank_account.balance)) + bank_balance_val).quantize(Decimal("0.01"))
            else:
                # 没有银行账户时记录日志（不影响期初余额过账本身）
                import logging
                logging.getLogger("inventory").warning(
                    "[OpeningBalance] 账本 %s 期初银行余额 %s 但无关联 BankAccount，"
                    "请后续手动创建 BankAccount 后通过启动同步对齐",
                    cmd.account_id, bank_balance_val,
                )

        # 5. 日志
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
    fixed_assets_original: Any = None       # Optional[Decimal]
    accumulated_depreciation: Any = None    # Optional[Decimal]
    intangible_assets_original: Any = None  # Optional[Decimal]
    accumulated_amortization: Any = None    # Optional[Decimal]
    accounts_payable: Any = None            # Optional[Decimal]
    tax_payable: Any = None                 # Optional[Decimal]
    long_term_borrowings: Any = None        # Optional[Decimal]
    paid_in_capital: Any = None             # Optional[Decimal]
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
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "期初余额", "order_id": cmd.opening_balance_id})

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
        if cmd.fixed_assets_original is not None:
            opening_balance.fixed_assets_original = cmd.fixed_assets_original
        if cmd.accumulated_depreciation is not None:
            opening_balance.accumulated_depreciation = cmd.accumulated_depreciation
        if cmd.intangible_assets_original is not None:
            opening_balance.intangible_assets_original = cmd.intangible_assets_original
        if cmd.accumulated_amortization is not None:
            opening_balance.accumulated_amortization = cmd.accumulated_amortization
        if cmd.accounts_payable is not None:
            opening_balance.accounts_payable = cmd.accounts_payable
        if cmd.tax_payable is not None:
            opening_balance.tax_payable = cmd.tax_payable
        if cmd.long_term_borrowings is not None:
            opening_balance.long_term_borrowings = cmd.long_term_borrowings
        if cmd.paid_in_capital is not None:
            opening_balance.paid_in_capital = cmd.paid_in_capital
        if cmd.retained_earnings is not None:
            opening_balance.retained_earnings = cmd.retained_earnings

        # 3. 校验：更新后资产 = 负债 + 权益（含非流动资产/负债）
        total_assets = (_d(opening_balance.cash_balance) + _d(opening_balance.bank_balance)
                        + _d(opening_balance.accounts_receivable) + _d(opening_balance.inventory_value)
                        + _d(opening_balance.fixed_assets_original) - _d(opening_balance.accumulated_depreciation)
                        + _d(opening_balance.intangible_assets_original) - _d(opening_balance.accumulated_amortization))
        total_liabilities = (_d(opening_balance.accounts_payable) + _d(opening_balance.tax_payable)
                             + _d(opening_balance.long_term_borrowings))
        total_equity = _d(opening_balance.paid_in_capital) + _d(opening_balance.retained_earnings)
        if total_assets != total_liabilities + total_equity:
            raise BusinessError(
                code=ErrorCode.BALANCE_SHEET_UNBALANCED,
                data={"assets": total_assets, "liabilities": total_liabilities + total_equity}
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
    counter_account_code: str = "2202"      # 对方科目编码
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

        # 2. 过账到总账
        from finance_integration import post_journal
        counter_account = cmd.counter_account_code
        if not counter_account or counter_account == "2202":
            # 按 flow_category 映射默认对方科目
            mapping = {
                ("operating", "inflow"): "6001",
                ("operating", "outflow"): "6602",
                ("investing", "inflow"): "6111",
                ("investing", "outflow"): "1601",
                ("financing", "inflow"): "2001",
                ("financing", "outflow"): "2501",
            }
            counter_account = mapping.get((cmd.flow_category, cmd.type), "2202")
        post_journal(db, cmd.account_id, "cash_flow", {
            "amount": cmd.amount,
            "direction": cmd.type,
            "flow_category": cmd.flow_category,
            "counter_account": counter_account,
            "date": cmd.transaction_date,
            "source_model": "cash_flow",
            "source_id": transaction.id,
        })

        # 3. 日志
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
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "现金流水", "order_id": cmd.transaction_id})

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
                raise BusinessError(code=ErrorCode.INVOICE_INVALID_DATE, data={"date": cmd.transaction_date})
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
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "现金流水", "order_id": cmd.transaction_id})

        # 2. 日志 + 删除
        _log(db, cmd.account_id, "delete", "cash_flow", cmd.transaction_id,
             f"删除现金流水: {transaction.type} {transaction.amount}", operator=cmd.operator)

        db.delete(transaction)
        db.flush()
        return True