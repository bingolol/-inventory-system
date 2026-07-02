"""银行引擎 — BankAccount.balance_l4 唯一更新入口

BankAccount.balance_l4 仅为缓存，财务真相源在 LedgerAccountBalance（科目 1002）。
"""
from decimal import Decimal
from sqlalchemy.orm import Session
from models import BankAccount
from errors import BusinessError, ErrorCode
from lineage import writes, derives, reads, TIER_L1, TIER_L2, TIER_L4


class BankEngine:
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id

    @derives("BankAccount.balance_l4", from_fields=["BankTransaction.amount_l2"])
    def update_balance(self, bank_account_id: int, amount: Decimal,
                       transaction_type: str) -> BankAccount:
        bank_account = self.db.query(BankAccount).filter(
            BankAccount.id == bank_account_id,
            BankAccount.account_id == self.account_id,
        ).with_for_update().first()
        if not bank_account:
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND, data={"bank_account_id": bank_account_id})

        if transaction_type == "inflow":
            bank_account.balance_l4 = Decimal(str(bank_account.balance_l4)) + amount
        else:
            bank_account.balance_l4 = Decimal(str(bank_account.balance_l4)) - amount

        self.db.flush()
        return bank_account
