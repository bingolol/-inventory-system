"""应收应付引擎"""
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from models_finance import (
    LedgerAccount, AccountMove, AccountMoveLine, AccountPartialReconcile,
    AccountingError,
)


class ReceivableEngine:
    """应收应付引擎 - 由 JournalEngine 内部调用"""

    def __init__(self, db: Session):
        self.db = db

    def reconcile(self, ledger_id: int, debit_line_id: int, credit_line_id: int, amount: Decimal):
        debit_line = self.db.query(AccountMoveLine).join(AccountMove).filter(
            AccountMoveLine.id == debit_line_id,
            AccountMove.ledger_id == ledger_id,
        ).first()

        credit_line = self.db.query(AccountMoveLine).join(AccountMove).filter(
            AccountMoveLine.id == credit_line_id,
            AccountMove.ledger_id == ledger_id,
        ).first()

        if not debit_line or not credit_line:
            raise AccountingError("LINE_NOT_FOUND",
                "核销行不存在或不属于当前账本")

        reconcile = AccountPartialReconcile(
            ledger_id=ledger_id,
            debit_move_id=debit_line_id,
            credit_move_id=credit_line_id,
            amount=amount,
        )
        self.db.add(reconcile)

        debit_line.amount_residual -= amount
        credit_line.amount_residual -= amount

        if debit_line.amount_residual <= 0:
            debit_line.reconciled = True
        if credit_line.amount_residual <= 0:
            credit_line.reconciled = True

    def get_partner_balance(self, partner_id: int, partner_type: str,
                            account_type: str = None, as_of: str = None) -> Decimal:
        query = self.db.query(
            func.coalesce(func.sum(AccountMoveLine.debit), 0),
            func.coalesce(func.sum(AccountMoveLine.credit), 0),
        ).filter(
            AccountMoveLine.partner_id == partner_id,
            AccountMoveLine.partner_type == partner_type,
        )

        if account_type:
            query = query.join(LedgerAccount).filter(
                LedgerAccount.account_type == account_type
            )

        if as_of:
            query = query.filter(
                AccountMoveLine.move_id.in_(
                    self.db.query(AccountMove.id).filter(AccountMove.date <= as_of)
                )
            )

        debit, credit = query.first()
        return Decimal(str(debit)) - Decimal(str(credit))

    def get_aging_report(self, partner_id: int, partner_type: str,
                         as_of_date: str, account_type: str = "asset_receivable") -> dict:
        as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        d30 = as_of - timedelta(days=30)
        d60 = as_of - timedelta(days=60)
        d90 = as_of - timedelta(days=90)

        bucket = case(
            (AccountMove.date >= d30, "0-30"),
            (AccountMove.date >= d60, "31-60"),
            (AccountMove.date >= d90, "61-90"),
            else_="90+",
        )

        rows = self.db.query(
            bucket.label("bucket"),
            func.coalesce(func.sum(AccountMoveLine.amount_residual), 0).label("total"),
        ).join(
            AccountMove, AccountMove.id == AccountMoveLine.move_id,
        ).join(
            LedgerAccount, LedgerAccount.id == AccountMoveLine.ledger_account_id,
        ).filter(
            AccountMoveLine.partner_id == partner_id,
            AccountMoveLine.partner_type == partner_type,
            LedgerAccount.account_type == account_type,
            AccountMoveLine.reconciled == False,
            AccountMove.date <= as_of,
        ).group_by("bucket").all()

        aging = {
            "0-30": Decimal("0"),
            "31-60": Decimal("0"),
            "61-90": Decimal("0"),
            "90+": Decimal("0"),
        }
        for row in rows:
            aging[row.bucket] = Decimal(str(row.total))

        return aging
