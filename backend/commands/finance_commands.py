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
from crud.base import log_op
from errors import BusinessError, ErrorCode
from lineage import writes, TIER_L1, TIER_L2, TIER_L4
from utils import to_decimal


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
    @writes("BankAccount.balance_l4", tier=TIER_L4, source="derived")
    @writes("OpeningBalance.date_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.cash_balance_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.bank_balance_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.accounts_receivable_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.inventory_value_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.fixed_assets_original_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.accumulated_depreciation_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.intangible_assets_original_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.accumulated_amortization_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.accounts_payable_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.tax_payable_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.long_term_borrowings_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.paid_in_capital_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.retained_earnings_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: CreateOpeningBalance, db: Any) -> Any:
        # 1. 校验：日期不能重复
        ob_date = datetime.strptime(cmd.date, "%Y-%m-%d").date()
        existing = db.query(models.OpeningBalance).filter(
            models.OpeningBalance.account_id == cmd.account_id,
            models.OpeningBalance.date_l1 == ob_date,
        ).first()
        if existing:
            raise BusinessError(code=ErrorCode.BALANCE_ALREADY_EXISTS, data={"date": cmd.date})

        # 2. 校验：资产 = 负债 + 权益（含非流动资产/负债）
        total_assets = (to_decimal(cmd.cash_balance) + to_decimal(cmd.bank_balance)
                        + to_decimal(cmd.accounts_receivable) + to_decimal(cmd.inventory_value)
                        + to_decimal(cmd.fixed_assets_original) - to_decimal(cmd.accumulated_depreciation)
                        + to_decimal(cmd.intangible_assets_original) - to_decimal(cmd.accumulated_amortization))
        total_liabilities = to_decimal(cmd.accounts_payable) + to_decimal(cmd.tax_payable) + to_decimal(cmd.long_term_borrowings)
        total_equity = to_decimal(cmd.paid_in_capital) + to_decimal(cmd.retained_earnings)
        if total_assets != total_liabilities + total_equity:
            raise BusinessError(
                code=ErrorCode.BALANCE_SHEET_UNBALANCED,
                data={"assets": total_assets, "liabilities": total_liabilities + total_equity}
            )

        # 3. 创建 ORM 对象
        opening_balance = models.OpeningBalance(
            account_id=cmd.account_id,
            date_l1=ob_date,
            cash_balance_l1=cmd.cash_balance,
            bank_balance_l1=cmd.bank_balance,
            accounts_receivable_l1=cmd.accounts_receivable,
            inventory_value_l1=cmd.inventory_value,
            fixed_assets_original_l1=cmd.fixed_assets_original,
            accumulated_depreciation_l1=cmd.accumulated_depreciation,
            intangible_assets_original_l1=cmd.intangible_assets_original,
            accumulated_amortization_l1=cmd.accumulated_amortization,
            accounts_payable_l1=cmd.accounts_payable,
            tax_payable_l1=cmd.tax_payable,
            long_term_borrowings_l1=cmd.long_term_borrowings,
            paid_in_capital_l1=cmd.paid_in_capital,
            retained_earnings_l1=cmd.retained_earnings,
        )
        db.add(opening_balance)
        db.flush()

        # 4. 过账到总账
        lines = []
        for code, field in [("1001", "cash_balance"), ("1002", "bank_balance"),
                            ("1122", "accounts_receivable"), ("1405", "inventory_value"),
                            ("1601", "fixed_assets_original"), ("1701", "intangible_assets_original")]:
            val = to_decimal(getattr(cmd, field, 0))
            if val > 0:
                lines.append({"account_code": code, "debit": val, "credit": Decimal("0")})
        for code, field in [("1602", "accumulated_depreciation"), ("1702", "accumulated_amortization"),
                            ("2202", "accounts_payable"), ("2221", "tax_payable"),
                            ("2501", "long_term_borrowings"), ("3001", "paid_in_capital"),
                            ("4104", "retained_earnings")]:
            val = to_decimal(getattr(cmd, field, 0))
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
        bank_balance_val = to_decimal(cmd.bank_balance)
        if bank_balance_val > 0:
            bank_account = db.query(models.BankAccount).filter(
                models.BankAccount.account_id == cmd.account_id,
            ).order_by(models.BankAccount.id.asc()).first()
            if bank_account:
                bank_account.balance_l4 = (Decimal(str(bank_account.balance_l4)) + bank_balance_val).quantize(Decimal("0.01"))
            else:
                # 没有银行账户时记录日志（不影响期初余额过账本身）
                import logging
                logging.getLogger("inventory").warning(
                    "[OpeningBalance] 账本 %s 期初银行余额 %s 但无关联 BankAccount，"
                    "请后续手动创建 BankAccount 后通过启动同步对齐",
                    cmd.account_id, bank_balance_val,
                )

        # 5. 日志
        log_op(db, cmd.account_id, "create", "opening_balance", opening_balance.id,
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
    @writes("BankAccount.balance_l4", tier=TIER_L4, source="derived")
    @writes("OpeningBalance.date_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.cash_balance_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.bank_balance_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.accounts_receivable_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.inventory_value_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.fixed_assets_original_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.accumulated_depreciation_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.intangible_assets_original_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.accumulated_amortization_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.accounts_payable_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.tax_payable_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.long_term_borrowings_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.paid_in_capital_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.retained_earnings_l1", tier=TIER_L1, source="external")
    @writes("OpeningBalance.is_reversed", tier=TIER_L1, source="external")
    def handle(self, cmd: UpdateOpeningBalance, db: Any) -> Any:
        # 1. 查旧记录
        old_ob = db.query(models.OpeningBalance).filter(
            models.OpeningBalance.id == cmd.opening_balance_id,
            models.OpeningBalance.account_id == cmd.account_id,
            models.OpeningBalance.is_reversed == False,
        ).first()
        if not old_ob:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "期初余额", "order_id": cmd.opening_balance_id})

        # 2. 用旧值兜底，组装新值
        def _new(old_val, cmd_val):
            return cmd_val if cmd_val is not None else old_val

        new_date = _new(old_ob.date_l1.isoformat(), cmd.date)
        new_cash = _new(old_ob.cash_balance_l1, cmd.cash_balance)
        new_bank = _new(old_ob.bank_balance_l1, cmd.bank_balance)
        new_ar = _new(old_ob.accounts_receivable_l1, cmd.accounts_receivable)
        new_inv = _new(old_ob.inventory_value_l1, cmd.inventory_value)
        new_fa = _new(old_ob.fixed_assets_original_l1, cmd.fixed_assets_original)
        new_dep = _new(old_ob.accumulated_depreciation_l1, cmd.accumulated_depreciation)
        new_ia = _new(old_ob.intangible_assets_original_l1, cmd.intangible_assets_original)
        new_amort = _new(old_ob.accumulated_amortization_l1, cmd.accumulated_amortization)
        new_ap = _new(old_ob.accounts_payable_l1, cmd.accounts_payable)
        new_tax = _new(old_ob.tax_payable_l1, cmd.tax_payable)
        new_ltb = _new(old_ob.long_term_borrowings_l1, cmd.long_term_borrowings)
        new_pic = _new(old_ob.paid_in_capital_l1, cmd.paid_in_capital)
        new_re = _new(old_ob.retained_earnings_l1, cmd.retained_earnings)

        # 3. 校验：资产 = 负债 + 权益
        total_assets = (to_decimal(new_cash) + to_decimal(new_bank) + to_decimal(new_ar) + to_decimal(new_inv)
                        + to_decimal(new_fa) - to_decimal(new_dep) + to_decimal(new_ia) - to_decimal(new_amort))
        total_liabilities = to_decimal(new_ap) + to_decimal(new_tax) + to_decimal(new_ltb)
        total_equity = to_decimal(new_pic) + to_decimal(new_re)
        if total_assets != total_liabilities + total_equity:
            raise BusinessError(
                code=ErrorCode.BALANCE_SHEET_UNBALANCED,
                data={"assets": total_assets, "liabilities": total_liabilities + total_equity}
            )

        # 4. 冲红旧凭证（force=True 允许同一 source_id 反复更新后重建）
        from finance_integration import reverse_journal
        reverse_journal(db, cmd.account_id, "opening_balance", old_ob.id, force=True)

        # 5. 标记旧记录作废
        old_ob.is_reversed = True

        # 6. 创建新记录
        ob_date = datetime.strptime(new_date, "%Y-%m-%d").date()
        new_ob = models.OpeningBalance(
            account_id=cmd.account_id,
            date_l1=ob_date,
            cash_balance_l1=new_cash,
            bank_balance_l1=new_bank,
            accounts_receivable_l1=new_ar,
            inventory_value_l1=new_inv,
            fixed_assets_original_l1=new_fa,
            accumulated_depreciation_l1=new_dep,
            intangible_assets_original_l1=new_ia,
            accumulated_amortization_l1=new_amort,
            accounts_payable_l1=new_ap,
            tax_payable_l1=new_tax,
            long_term_borrowings_l1=new_ltb,
            paid_in_capital_l1=new_pic,
            retained_earnings_l1=new_re,
        )
        db.add(new_ob)
        db.flush()

        # 7. 重新过账
        lines = []
        for code, field in [("1001", new_cash), ("1002", new_bank), ("1122", new_ar),
                            ("1405", new_inv), ("1601", new_fa), ("1701", new_ia)]:
            val = to_decimal(field)
            if val > 0:
                lines.append({"account_code": code, "debit": val, "credit": Decimal("0")})
        for code, field in [("1602", new_dep), ("1702", new_amort), ("2202", new_ap),
                            ("2221", new_tax), ("2501", new_ltb), ("3001", new_pic),
                            ("4104", new_re)]:
            val = to_decimal(field)
            if val > 0:
                lines.append({"account_code": code, "debit": Decimal("0"), "credit": val})
        from finance_integration import post_journal
        post_journal(db, cmd.account_id, "opening_balance", {
            "lines": lines,
            "date": new_date,
            "source_model": "opening_balance",
            "source_id": new_ob.id,
        })

        # 8. 同步 BankAccount：扣回旧银行余额，加上新银行余额
        bank_account = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == cmd.account_id,
        ).order_by(models.BankAccount.id.asc()).first()
        if bank_account:
            old_bank_val = to_decimal(old_ob.bank_balance_l1)
            new_bank_val = to_decimal(new_bank)
            bank_account.balance_l4 = (Decimal(str(bank_account.balance_l4)) - old_bank_val + new_bank_val).quantize(Decimal("0.01"))

        # 9. 日志
        log_op(db, cmd.account_id, "update", "opening_balance", new_ob.id,
             f"更新期初余额: {new_date}（原记录 {old_ob.id} 已冲红）", operator=cmd.operator)
        db.flush()
        return new_ob


# ═══════════════════════════════════════════════════════════
# 2.5 DeleteOpeningBalance — 删除期初余额（冲红凭证 + 标记作废）
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteOpeningBalance(Command):
    opening_balance_id: int = 0


@register(DeleteOpeningBalance)
class DeleteOpeningBalanceHandler(CommandHandler):
    @writes("BankAccount.balance_l4", tier=TIER_L4, source="derived")
    @writes("OpeningBalance.is_reversed", tier=TIER_L1, source="external")
    def handle(self, cmd: DeleteOpeningBalance, db: Any) -> bool:
        ob = db.query(models.OpeningBalance).filter(
            models.OpeningBalance.id == cmd.opening_balance_id,
            models.OpeningBalance.account_id == cmd.account_id,
            models.OpeningBalance.is_reversed == False,
        ).first()
        if not ob:
            return False

        # 1. 冲红原凭证
        from finance_integration import reverse_journal
        reverse_journal(db, cmd.account_id, "opening_balance", ob.id, force=True)

        # 2. 扣回 BankAccount 已同步的银行余额
        bank_account = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == cmd.account_id,
        ).order_by(models.BankAccount.id.asc()).first()
        if bank_account:
            old_bank_val = to_decimal(ob.bank_balance_l1)
            bank_account.balance_l4 = (Decimal(str(bank_account.balance_l4)) - old_bank_val).quantize(Decimal("0.01"))

        # 3. 标记作废
        ob.is_reversed = True
        db.flush()

        log_op(db, cmd.account_id, "delete", "opening_balance", ob.id,
             f"删除期初余额: {ob.date_l1}（已冲红凭证）", operator=cmd.operator)
        db.flush()
        return True


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
    @writes("CashFlowTransaction.amount_l2", tier=TIER_L2, source="external")
    @writes("CashFlowTransaction.flow_category_l2", tier=TIER_L2, source="external")
    @writes("CashFlowTransaction.transaction_date_l1", tier=TIER_L1, source="external")
    def handle(self, cmd: CreateCashFlowTransaction, db: Any) -> Any:
        # 1. 创建 ORM 对象
        transaction = models.CashFlowTransaction(
            account_id=cmd.account_id,
            type=cmd.type,
            amount_l2=cmd.amount,
            flow_category_l2=cmd.flow_category,
            description=cmd.description,
            transaction_date_l1=datetime.strptime(cmd.transaction_date, "%Y-%m-%d"),
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
        log_op(db, cmd.account_id, "create", "cash_flow", transaction.id,
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

        if getattr(transaction, "is_reversed", False):
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"现金流水 #{cmd.transaction_id} 已冲红，禁止更新",
                ai_instruction="STOP_RETRYING. 已冲红的现金流水不能更新，如需调整请创建新记录。",
            )

        # 2. 冲红原总账凭证（不修改 AccountMove，只 INSERT 反向凭证）
        from finance_integration import reverse_journal, post_journal
        reverse_journal(db, cmd.account_id, "cash_flow", transaction.id)

        # 3. 更新业务字段
        if cmd.type is not None:
            transaction.type = cmd.type
        if cmd.amount is not None:
            transaction.amount_l2 = cmd.amount
        if cmd.flow_category is not None:
            transaction.flow_category_l2 = cmd.flow_category
        if cmd.description is not None:
            transaction.description = cmd.description
        if cmd.transaction_date is not None:
            try:
                transaction.transaction_date_l1 = datetime.strptime(cmd.transaction_date, "%Y-%m-%d")
            except ValueError:
                raise BusinessError(code=ErrorCode.INVOICE_INVALID_DATE, data={"date": cmd.transaction_date})
        if cmd.related_entity_type is not None:
            transaction.related_entity_type = cmd.related_entity_type
        if cmd.related_entity_id is not None:
            transaction.related_entity_id = cmd.related_entity_id

        # 4. 重新生成总账凭证
        counter_account = getattr(cmd, "counter_account_code", None) or "2202"
        if not counter_account or counter_account == "2202":
            mapping = {
                ("operating", "inflow"): "6001",
                ("operating", "outflow"): "6602",
                ("investing", "inflow"): "6111",
                ("investing", "outflow"): "1601",
                ("financing", "inflow"): "2001",
                ("financing", "outflow"): "2501",
            }
            counter_account = mapping.get((transaction.flow_category_l2, transaction.type), "2202")
        post_journal(db, cmd.account_id, "cash_flow", {
            "amount": transaction.amount_l2,
            "direction": transaction.type,
            "flow_category": transaction.flow_category_l2,
            "counter_account": counter_account,
            "date": transaction.transaction_date_l1.strftime("%Y-%m-%d"),
            "source_model": "cash_flow",
            "source_id": transaction.id,
        })

        # 5. 日志
        log_op(db, cmd.account_id, "update", "cash_flow", cmd.transaction_id,
             f"更新现金流水: {transaction.type} {transaction.amount_l2}", operator=cmd.operator)
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

        if getattr(transaction, "is_reversed", False):
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"现金流水 #{cmd.transaction_id} 已被冲红，不可重复操作",
                ai_instruction="STOP_RETRYING. 该现金流水已冲红。",
            )

        # 2. 冲红总账凭证 + 标记已冲红（不物理删除，保留审计轨迹）
        from finance_integration import reverse_journal
        from datetime import datetime
        reverse_journal(db, cmd.account_id, "cash_flow", transaction.id)
        transaction.is_reversed = True
        transaction.reversed_at = datetime.now()

        log_op(db, cmd.account_id, "delete", "cash_flow", cmd.transaction_id,
             f"删除(冲红)现金流水: {transaction.type} {transaction.amount_l2}", operator=cmd.operator)
        db.flush()
        return True

