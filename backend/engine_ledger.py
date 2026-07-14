from decimal import Decimal
from sqlalchemy import func, select, union_all
from sqlalchemy.orm import Session
from models_finance import (
    LedgerAccount, LedgerAccountBalance, AccountMoveLine, AccountMove,
)
from accounting_engine import AccountingError, AccountingErrorCode
from lineage import derives, TIER_L2, TIER_L4


class LedgerEngine:
    """科目余额引擎 - 由 JournalEngine 内部调用"""

    def __init__(self, db: Session):
        self.db = db

    def _get_descendant_leaf_ids(self, ledger_account_id: int) -> list[int]:
        base = select(
            LedgerAccount.id,
            LedgerAccount.parent_id,
            LedgerAccount.is_leaf,
        ).where(LedgerAccount.id == ledger_account_id)

        cte = base.cte(name="account_tree", recursive=True)
        cte_alias = cte.alias()

        recursive = select(
            LedgerAccount.id,
            LedgerAccount.parent_id,
            LedgerAccount.is_leaf,
        ).where(LedgerAccount.parent_id == cte_alias.c.id)

        combined = cte.union_all(recursive)

        stmt = select(combined.c.id).where(combined.c.is_leaf == True)
        rows = self.db.execute(stmt).all()
        return [row[0] for row in rows]

    def _ensure_balance_row(self, ledger_account_id: int):
        balance_row = self.db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == ledger_account_id
        ).with_for_update().first()

        if not balance_row:
            balance_row = LedgerAccountBalance(
                ledger_account_id=ledger_account_id,
                balance_l4=Decimal("0"),
                debit_total_l4=Decimal("0"),
                credit_total_l4=Decimal("0"),
            )
            self.db.add(balance_row)
            self.db.flush()

        return balance_row

    @derives("LedgerAccountBalance.balance_l4",
             from_fields=["AccountMoveLine.debit_l2", "AccountMoveLine.credit_l2"])
    @derives("LedgerAccountBalance.debit_total_l4",
             from_fields=["AccountMoveLine.debit_l2"])
    @derives("LedgerAccountBalance.credit_total_l4",
             from_fields=["AccountMoveLine.credit_l2"])
    def update_balance(self, line: AccountMoveLine):
        account = self.db.query(LedgerAccount).filter(
            LedgerAccount.id == line.ledger_account_id
        ).with_for_update().first()

        if not account:
            raise AccountingError(AccountingErrorCode.ACCOUNT_NOT_FOUND,
                f"科目不存在: {line.ledger_account_id}")

        if not account.is_leaf:
            raise AccountingError(AccountingErrorCode.NON_LEAF_ACCOUNT,
                f"科目 {account.code}({account.name}) 不是叶子科目，不能直接记账。"
                f"请改用其子科目。如确认需使用此科目，请在科目表中设 is_leaf=True。")

        balance_row = self._ensure_balance_row(account.id)
        delta = Decimal(str(line.debit_l2)) - Decimal(str(line.credit_l2))

        if account.code == "1001" and balance_row.balance_l4 + delta < 0:
            raise AccountingError(AccountingErrorCode.INSUFFICIENT_BALANCE,
                f"库存现金余额不足。当前余额: {balance_row.balance_l4}，"
                f"扣减: {abs(delta) if delta < 0 else delta}")

        balance_row.balance_l4 += delta
        balance_row.debit_total_l4 += line.debit_l2
        balance_row.credit_total_l4 += line.credit_l2

    def get_balance(self, ledger_account_id: int, date: str = None) -> Decimal:
        account = self.db.query(LedgerAccount).filter(
            LedgerAccount.id == ledger_account_id
        ).first()

        if not account:
            raise AccountingError(AccountingErrorCode.ACCOUNT_NOT_FOUND,
                f"科目不存在: {ledger_account_id}")

        if date:
            if account.is_leaf:
                target_ids = [account.id]
            else:
                target_ids = self._get_descendant_leaf_ids(account.id)

            if not target_ids:
                return Decimal("0")

            result = self.db.query(
                func.coalesce(func.sum(AccountMoveLine.debit_l2), 0),
                func.coalesce(func.sum(AccountMoveLine.credit_l2), 0),
            ).filter(
                AccountMoveLine.ledger_account_id.in_(target_ids),
                AccountMoveLine.move_id.in_(
                    self.db.query(AccountMove.id).filter(AccountMove.date_l1 <= date)
                ),
            ).first()

            debit = result[0]
            credit = result[1]
            if account.account_type.startswith("asset") or account.account_type.startswith("expense"):
                return Decimal(str(debit)) - Decimal(str(credit))
            else:
                return Decimal(str(credit)) - Decimal(str(debit))
        else:
            if account.is_leaf:
                balance_row = self.db.query(LedgerAccountBalance).filter(
                    LedgerAccountBalance.ledger_account_id == account.id
                ).first()
                return balance_row.balance_l4 if balance_row else Decimal("0")
                # NOTE: 叶子科目无 balance_l4 缓存时可能是未初始化，但报表查询不应中断。
                # 若需严格校验，调用方应预先检查 LedgerAccountBalance 表。
            else:
                leaf_ids = self._get_descendant_leaf_ids(account.id)
                if not leaf_ids:
                    return Decimal("0")

                result = self.db.query(
                    func.coalesce(func.sum(LedgerAccountBalance.balance_l4), 0)
                ).filter(
                    LedgerAccountBalance.ledger_account_id.in_(leaf_ids)
                ).first()
                return result[0]

    def get_trial_balance(self, ledger_id: int, date: str) -> dict:
        line_totals = self.db.query(
            AccountMoveLine.ledger_account_id,
            func.coalesce(func.sum(AccountMoveLine.debit_l2), 0).label("total_debit"),
            func.coalesce(func.sum(AccountMoveLine.credit_l2), 0).label("total_credit"),
        ).filter(
            AccountMoveLine.move_id.in_(
                self.db.query(AccountMove.id).filter(AccountMove.date_l1 <= date)
            ),
        ).group_by(AccountMoveLine.ledger_account_id).subquery()

        results = self.db.query(
            LedgerAccount.code,
            LedgerAccount.name,
            LedgerAccount.account_type,
            func.coalesce(line_totals.c.total_debit, 0).label("debit"),
            func.coalesce(line_totals.c.total_credit, 0).label("credit"),
        ).outerjoin(
            line_totals,
            LedgerAccount.id == line_totals.c.ledger_account_id,
        ).filter(
            LedgerAccount.ledger_id == ledger_id,
            LedgerAccount.is_leaf == True,
            LedgerAccount.is_active == True,
        ).order_by(LedgerAccount.code).all()

        rows = []
        total_debit = Decimal("0")
        total_credit = Decimal("0")

        for code, name, acct_type, debit_val, credit_val in results:
            debit = Decimal(str(debit_val))
            credit = Decimal(str(credit_val))

            if debit != 0 or credit != 0:
                rows.append({"code": code, "name": name, "debit": debit, "credit": credit})
                total_debit += debit
                total_credit += credit

        return {
            "rows": rows,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balanced": total_debit == total_credit,
        }
