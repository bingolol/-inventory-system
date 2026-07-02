"""银行流水路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import BankAccount, BankTransaction
from schemas.bank import BankTransactionCreate, BankTransactionOut
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.base import _log
from crud.reversal import reverse_bank_transaction
from utils import _d

router = APIRouter()


@router.get("")
def list_bank_transactions(
    bank_account_id: int = Query(..., description="银行账户ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """查询银行流水"""
    query = db.query(BankTransaction).filter(
        BankTransaction.bank_account_id == bank_account_id,
        BankTransaction.account_id == account_id
    ).order_by(BankTransaction.transaction_date_l1.desc(), BankTransaction.id.desc())
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    try:
        return {"total": total, "items": [BankTransactionOut.model_validate(t) for t in items]}
    except Exception as e:
        from errors import BusinessError, ErrorCode
        raise BusinessError(code=ErrorCode.INTERNAL_ERROR, message=f"银行流水数据格式异常: {str(e)}", ai_instruction="STOP_RETRYING. 银行流水数据异常，请检查数据库记录完整性")


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
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND, data={"bank_account_id": data.bank_account_id})

        # 计算交易后余额
        amount = _d(data.amount)
        if data.transaction_type == "inflow":
            new_balance = _d(bank_account.balance_l4) + amount
        else:
            new_balance = _d(bank_account.balance_l4) - amount
            # 余额校验：禁止银行账户透支（防止负资产）
            if new_balance < 0:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"银行账户余额不足: 当前余额 {bank_account.balance_l4}，"
                            f"支出金额 {amount}，超额 {abs(new_balance)}",
                    ai_instruction=f"STOP_RETRYING. 银行账户 {bank_account.bank_name} 余额仅 "
                                   f"{bank_account.balance_l4}，不足以支出 {amount}。"
                                   f"请减少金额或先充值。"
                )

        # 创建银行流水
        transaction = BankTransaction(
            account_id=account_id,
            bank_account_id=data.bank_account_id,
            transaction_type=data.transaction_type,
            amount_l2=amount,
            balance_after_l4=new_balance,
            transaction_date_l1=data.transaction_date,
            description=data.description,
            reference_no=data.reference_no
        )
        db.add(transaction)

        # 更新银行账户余额
        bank_account.balance_l4 = new_balance

        db.flush()
        _log(db, account_id, "create", "bank_transaction", transaction.id,
             f"录入银行流水: {data.transaction_type} {amount}", operator=operator)

    db.refresh(transaction)
    return BankTransactionOut.model_validate(transaction)

