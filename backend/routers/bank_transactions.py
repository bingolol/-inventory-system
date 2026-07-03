"""银行流水路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import BankTransaction
from schemas.bank import BankTransactionCreate, BankTransactionOut
from account_dep import get_account_id, get_operator
from uow import unit_of_work
from commands.base import dispatch
from commands.bank_commands import CreateBankTransaction

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
        return dispatch(CreateBankTransaction(
            account_id=account_id,
            operator=operator,
            data=data,
        ), db)
