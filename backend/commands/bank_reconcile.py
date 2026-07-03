"""银行对账 Command — 导入对账单、执行对账、强制匹配、生成凭证、确认"""

from dataclasses import dataclass
from typing import Any, List, Optional

from .base import Command, CommandHandler, register
from crud.base import log_op
from engine_bank_reconcile import BankReconcileEngine
from errors import BusinessError, ErrorCode


@dataclass
class ImportBankStatement(Command):
    period_start: str = ""      # YYYY-MM-DD
    period_end: str = ""        # YYYY-MM-DD
    opening_balance: float = 0
    closing_balance: float = 0
    lines: List[dict] = None    # [{transaction_date, amount, description}]


@register(ImportBankStatement)
class ImportBankStatementHandler(CommandHandler):
    def handle(self, cmd: ImportBankStatement, db: Any):
        import models, models_bank
        from datetime import datetime

        ba = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == cmd.account_id,
        ).first()
        if not ba:
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND,
                                data={"details": "未找到银行账户"})

        stmt = models_bank.BankStatement(
            bank_account_id=ba.id, account_id=cmd.account_id,
            period_start=datetime.strptime(cmd.period_start, "%Y-%m-%d").date(),
            period_end=datetime.strptime(cmd.period_end, "%Y-%m-%d").date(),
            opening_balance_l1=cmd.opening_balance, closing_balance_l1=cmd.closing_balance,
        )
        db.add(stmt); db.flush()

        for line in cmd.lines or []:
            db.add(models_bank.BankStatementLine(
                statement_id=stmt.id,
                transaction_date_l1=datetime.strptime(line["transaction_date"], "%Y-%m-%d").date(),
                amount_l1=line.get("amount", 0), description=line.get("description", ""),
            ))

        log_op(db, cmd.account_id, "import", "bank_statement", stmt.id,
             f"导入对账单 {cmd.period_start}~{cmd.period_end}", operator=cmd.operator)
        db.flush()
        return {"id": stmt.id, "status": "imported"}


@dataclass
class ReconcileBank(Command):
    period: str = ""            # YYYY-MM
    seed: List[dict] = None     # 期初未达种子


@register(ReconcileBank)
class ReconcileBankHandler(CommandHandler):
    def handle(self, cmd: ReconcileBank, db: Any):
        import models, models_bank

        ba = db.query(models.BankAccount).filter(
            models.BankAccount.account_id == cmd.account_id,
        ).first()
        if not ba:
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND,
                                data={"details": "未找到银行账户"})

        engine = BankReconcileEngine(db, cmd.account_id, ba.id, cmd.period)
        rec = engine.create_reconciliation(cmd.seed or [])
        engine.run_matching()

        log_op(db, cmd.account_id, "reconcile", "bank_reconciliation", rec.id,
             f"银行对账 {cmd.period}", operator=cmd.operator)
        db.flush()

        return {
            "id": rec.id,
            "period": rec.period,
            "book_balance": float(rec.book_balance),
            "statement_balance": float(rec.statement_balance),
            "adjusted_book": float(rec.adjusted_book),
            "adjusted_statement": float(rec.adjusted_statement),
            "balanced": rec.balanced,
            "status": rec.status,
        }


@dataclass
class ForceMatchBankReconciliation(Command):
    reconciliation_id: int = 0
    stmt_line_ids: List[int] = None
    bank_tx_ids: List[int] = None
    reason: str = ""


@register(ForceMatchBankReconciliation)
class ForceMatchBankReconciliationHandler(CommandHandler):
    def handle(self, cmd: ForceMatchBankReconciliation, db: Any):
        import models, models_bank

        rec = db.query(models_bank.BankReconciliation).filter(
            models_bank.BankReconciliation.id == cmd.reconciliation_id,
            models_bank.BankReconciliation.account_id == cmd.account_id,
        ).first()
        if not rec:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "调节表"})

        engine = BankReconcileEngine(db, cmd.account_id, rec.bank_account_id, rec.period)
        engine.force_match(cmd.reconciliation_id, cmd.stmt_line_ids or [],
                           cmd.bank_tx_ids or [], cmd.reason)
        log_op(db, cmd.account_id, "force_match", "bank_reconciliation", cmd.reconciliation_id,
             f"强制匹配: {cmd.reason}", operator=cmd.operator)
        db.flush()
        return {"status": "matched"}


@dataclass
class ConfirmBankReconciliation(Command):
    reconciliation_id: int = 0


@register(ConfirmBankReconciliation)
class ConfirmBankReconciliationHandler(CommandHandler):
    def handle(self, cmd: ConfirmBankReconciliation, db: Any):
        import models, models_bank

        rec = db.query(models_bank.BankReconciliation).filter(
            models_bank.BankReconciliation.id == cmd.reconciliation_id,
            models_bank.BankReconciliation.account_id == cmd.account_id,
        ).first()
        if not rec:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "调节表"})

        engine = BankReconcileEngine(db, cmd.account_id, rec.bank_account_id, rec.period)
        engine.confirm(cmd.reconciliation_id, cmd.operator)

        log_op(db, cmd.account_id, "confirm", "bank_reconciliation", cmd.reconciliation_id,
             f"确认调节表 {rec.period}", operator=cmd.operator)
        db.flush()
        return {"status": rec.status}


@dataclass
class GenerateReconciliationEntry(Command):
    reconciliation_id: int = 0


@register(GenerateReconciliationEntry)
class GenerateReconciliationEntryHandler(CommandHandler):
    def handle(self, cmd: GenerateReconciliationEntry, db: Any):
        import models, models_bank

        rec = db.query(models_bank.BankReconciliation).filter(
            models_bank.BankReconciliation.id == cmd.reconciliation_id,
            models_bank.BankReconciliation.account_id == cmd.account_id,
        ).first()
        if not rec:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "调节表"})

        engine = BankReconcileEngine(db, cmd.account_id, rec.bank_account_id, rec.period)
        result = engine.generate_entries(cmd.reconciliation_id)

        log_op(db, cmd.account_id, "generate_entry", "bank_reconciliation", cmd.reconciliation_id,
             f"生成手续费凭证 {len(result)}笔", operator=cmd.operator)
        db.flush()
        return {"generated": len(result)}
