"""银行账户 / 银行流水 / 银行对账杂项 Command + Handler

原 routers/bank_accounts.py、routers/bank_transactions.py、routers/bank_reconcile.py
中的直接写端点下沉到本模块，router 只负责 HTTP 解析 + dispatch。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from commands.base import Command, CommandHandler, register
from crud.base import log_op
from engine_bank import BankEngine
from errors import BusinessError, ErrorCode
from finance_integration import post_journal
from lineage import writes, TIER_L1, TIER_L4
from models import BankAccount, BankTransaction
from operation_result import EntityType, OperationResult, OperationType
from schemas.bank import (
    BankAccountCreate,
    BankAccountUpdate,
    BankTransactionCreate,
    BankAccountOut,
    BankTransactionOut,
)
from utils import _d


# ═══════════════════════════════════════════════════════════
# BankAccount Commands
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateBankAccount(Command):
    data: Optional[BankAccountCreate] = None


@register(CreateBankAccount)
class CreateBankAccountHandler(CommandHandler):
    @writes("BankAccount.bank_name", tier=TIER_L1, source="external")
    @writes("BankAccount.account_number", tier=TIER_L1, source="external")
    @writes("BankAccount.balance_l4", tier=TIER_L4, source="engine")
    def handle(self, cmd: CreateBankAccount, db: Any) -> Any:
        import models as _models

        data = cmd.data
        if data.balance is not None and data.balance > 0:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="开户时不支持直接录入期初余额。请先创建银行账户（余额为0），"
                        "再通过「期初余额」功能录入银行存款期初，系统会自动过账到总账 1002 科目。",
                ai_instruction="STOP_RETRYING. 期初余额必须走 OpeningBalance 流程，不能在开户时直接录入。"
            )

        bank_account = BankAccount(
            account_id=cmd.account_id,
            bank_name=data.bank_name,
            account_number=data.account_number,
            balance_l4=Decimal('0'),
            description=data.description
        )
        db.add(bank_account)
        db.flush()

        # 反向同步：若账本已有期初余额中的 bank_balance 但此前无银行账户导致未同步
        latest_ob = db.query(_models.OpeningBalance).filter(
            _models.OpeningBalance.account_id == cmd.account_id,
        ).order_by(_models.OpeningBalance.date_l1.desc()).first()
        if latest_ob and latest_ob.bank_balance_l1 and latest_ob.bank_balance_l1 > 0:
            bank_account.balance_l4 = Decimal(str(latest_ob.bank_balance_l1)).quantize(Decimal("0.01"))

        log_op(db, cmd.account_id, "create", "bank_account", bank_account.id,
               f"创建银行账户: {data.bank_name} {data.account_number}", operator=cmd.operator)

        db.refresh(bank_account)
        return BankAccountOut.model_validate(bank_account)


@dataclass
class UpdateBankAccount(Command):
    bank_account_id: int = 0
    data: Optional[BankAccountUpdate] = None


@register(UpdateBankAccount)
class UpdateBankAccountHandler(CommandHandler):
    @writes("BankAccount.bank_name", tier=TIER_L1, source="external")
    @writes("BankAccount.account_number", tier=TIER_L1, source="external")
    @writes("BankAccount.description", tier=TIER_L1, source="external")
    def handle(self, cmd: UpdateBankAccount, db: Any) -> Any:
        data = cmd.data
        bank_account = db.query(BankAccount).filter(
            BankAccount.id == cmd.bank_account_id,
            BankAccount.account_id == cmd.account_id,
        ).first()
        if not bank_account:
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND,
                                data={"bank_account_id": cmd.bank_account_id})

        if data.bank_name is not None:
            bank_account.bank_name = data.bank_name
        if data.account_number is not None:
            bank_account.account_number = data.account_number
        if data.description is not None:
            bank_account.description = data.description

        db.flush()
        log_op(db, cmd.account_id, "update", "bank_account", bank_account.id,
               f"更新银行账户: {bank_account.bank_name}", operator=cmd.operator)

        db.refresh(bank_account)
        return BankAccountOut.model_validate(bank_account)


@dataclass
class DeleteBankAccount(Command):
    bank_account_id: int = 0


@register(DeleteBankAccount)
class DeleteBankAccountHandler(CommandHandler):
    def handle(self, cmd: DeleteBankAccount, db: Any) -> Any:
        import models as _models

        bank_account = db.query(BankAccount).filter(
            BankAccount.id == cmd.bank_account_id,
            BankAccount.account_id == cmd.account_id,
        ).first()
        if not bank_account:
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND,
                                data={"bank_account_id": cmd.bank_account_id})

        transactions_count = db.query(BankTransaction).filter(
            BankTransaction.bank_account_id == cmd.bank_account_id
        ).count()
        payments_count = db.query(_models.Payment).filter(
            _models.Payment.bank_account_id == cmd.bank_account_id
        ).count()
        receipts_count = db.query(_models.Receipt).filter(
            _models.Receipt.bank_account_id == cmd.bank_account_id
        ).count()

        if transactions_count + payments_count + receipts_count > 0:
            raise BusinessError(
                code=ErrorCode.DUPLICATE_ENTRY,
                message=f"该银行账户存在关联的银行流水({transactions_count})、付款({payments_count})、收款({receipts_count})记录，无法删除",
                ai_instruction="STOP_RETRYING. 该银行账户有关联数据，无法删除。如需删除，请先清理关联的银行流水、付款、收款记录。"
            )

        log_op(db, cmd.account_id, "delete", "bank_account", bank_account.id,
               f"删除银行账户: {bank_account.bank_name}", operator=cmd.operator)
        db.delete(bank_account)
        db.flush()
        return {"message": "银行账户已删除"}


# ═══════════════════════════════════════════════════════════
# BankTransaction Commands
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateBankTransaction(Command):
    data: Optional[BankTransactionCreate] = None


@register(CreateBankTransaction)
class CreateBankTransactionHandler(CommandHandler):
    # BankTransaction 字段实际由 BankEngine.record_transaction 写入，
    # 已在 engine_bank.py 声明 @writes；Handler 仅做编排，不再重复声明。
    def handle(self, cmd: CreateBankTransaction, db: Any) -> Any:
        data = cmd.data
        transaction = BankEngine(db, cmd.account_id).record_transaction(
            bank_account_id=data.bank_account_id,
            transaction_type=data.transaction_type,
            amount=data.amount,
            transaction_date=data.transaction_date,
            description=data.description,
            reference_no=data.reference_no,
        )

        log_op(db, cmd.account_id, "create", "bank_transaction", transaction.id,
               f"录入银行流水: {data.transaction_type} {transaction.amount_l2}", operator=cmd.operator)

        db.refresh(transaction)
        return BankTransactionOut.model_validate(transaction)


# ═══════════════════════════════════════════════════════════
# Bank Entry Commands（利息收入 / 手续费）
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateBankEntry(Command):
    entry_type: str = ""           # "interest_income" | "bank_fee"
    amount: float = 0.0
    transaction_date: str = ""     # YYYY-MM-DD
    description: str = ""


@register(CreateBankEntry)
class CreateBankEntryHandler(CommandHandler):
    # BankTransaction 由 BankEngine.record_transaction 写入；
    # AccountMove 由 post_journal / JournalEngine.post 写入；Handler 仅编排。
    def handle(self, cmd: CreateBankEntry, db: Any) -> Any:
        import models as _models

        if cmd.entry_type not in ("interest_income", "bank_fee"):
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"无效 entry_type: {cmd.entry_type}，仅支持 interest_income / bank_fee"
            )

        amt = _d(cmd.amount)
        dt = datetime.strptime(cmd.transaction_date, "%Y-%m-%d")
        direction = "in" if cmd.entry_type == "interest_income" else "out"

        ba = db.query(_models.BankAccount).filter(
            _models.BankAccount.account_id == cmd.account_id,
        ).first()
        if not ba:
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND)

        tx = BankEngine(db, cmd.account_id).record_transaction(
            bank_account_id=ba.id,
            transaction_type="inflow" if direction == "in" else "outflow",
            amount=amt,
            transaction_date=dt,
            description=cmd.description or cmd.entry_type,
            flow_category="operating",
        )
        tx_id = tx.id

        post_journal(db, cmd.account_id, "bank_fee_entry", {
            "amount": amt,
            "direction": direction,
            "date": cmd.transaction_date,
            "source_model": "bank_entry",
            "source_id": tx_id,
        })

        entry_label = "利息收入" if cmd.entry_type == "interest_income" else "手续费"
        log_op(db, cmd.account_id, "create", "bank_entry", tx_id,
               f"{entry_label}: {cmd.amount}", operator=cmd.operator)

        changes = {"cash": {"amount": f"+{cmd.amount}" if direction == "in" else f"-{cmd.amount}"}}

        return OperationResult(
            operation=OperationType.CREATE,
            entity_type=EntityType.BANK_ENTRY,
            entity_id=tx_id,
            summary=f"{entry_label}录入成功，金额 {cmd.amount}",
            ai_hint=f"{entry_label}已录入，银行存款余额已更新。",
            changes=changes,
        ).to_dict()
