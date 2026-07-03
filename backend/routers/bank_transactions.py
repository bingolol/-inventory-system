"""银行流水路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import BankTransaction
from schemas.bank import BankTransactionCreate, BankTransactionOut
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.base import log_op
from crud.reversal import reverse_bank_transaction
from engine_bank import BankEngine

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
        # 经 BankEngine.record_transaction 统一入口写入（含行锁、透支校验、余额同步）
        transaction = BankEngine(db, account_id).record_transaction(
            bank_account_id=data.bank_account_id,
            transaction_type=data.transaction_type,
            amount=data.amount,
            transaction_date=data.transaction_date,
            description=data.description,
            reference_no=data.reference_no,
        )
        log_op(db, account_id, "create", "bank_transaction", transaction.id,
             f"录入银行流水: {data.transaction_type} {transaction.amount_l2}", operator=operator)

    db.refresh(transaction)
    return BankTransactionOut.model_validate(transaction)

