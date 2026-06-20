"""银行流水路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import BankAccount, BankTransaction
from schemas.bank import BankTransactionCreate, BankTransactionOut
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.base import _log
from utils import _d

router = APIRouter()


@router.post("", response_model=BankTransactionOut)
def create_bank_transaction(
    data: BankTransactionCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """录入银行流水"""
    with unit_of_work(db):
        # 查询银行账户（添加行锁防止并发问题）
        bank_account = db.query(BankAccount).filter(
            BankAccount.id == data.bank_account_id,
            BankAccount.account_id == account_id
        ).with_for_update().first()
        if not bank_account:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="银行账户不存在")

        # 计算交易后余额
        amount = _d(data.amount)
        if data.transaction_type == "inflow":
            new_balance = _d(bank_account.balance) + amount
        else:
            new_balance = _d(bank_account.balance) - amount

        # 创建银行流水
        transaction = BankTransaction(
            account_id=account_id,
            bank_account_id=data.bank_account_id,
            transaction_type=data.transaction_type,
            amount=amount,
            balance_after=new_balance,
            transaction_date=data.transaction_date,
            description=data.description,
            reference_no=data.reference_no
        )
        db.add(transaction)

        # 更新银行账户余额
        bank_account.balance = new_balance

        db.flush()
        _log(db, account_id, "create", "bank_transaction", transaction.id,
             f"录入银行流水: {data.transaction_type} {amount}", operator=operator)

    db.refresh(transaction)
    return BankTransactionOut.model_validate(transaction)
