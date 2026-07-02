"""付款路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Payment
from schemas.payment import PaymentCreate, PaymentOut
from schemas import PaginatedResponse
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.finance import list_payments, get_payment
from commands.base import dispatch
from commands.cash_commands import CreatePayment, ReversePayment

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取付款记录列表"""
    items = list_payments(db, account_id, skip=skip, limit=limit)
    total = len(items)
    return PaginatedResponse(total=total, items=[PaymentOut.model_validate(p) for p in items])


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment_by_id(
    payment_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取单条付款记录"""
    p = get_payment(db, account_id, payment_id)
    if not p:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"payment_id": payment_id})
    return PaymentOut.model_validate(p)


@router.post("")
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """创建付款记录"""
    if data.withholding_tax_amount > 0 and data.payment_type != "salary":
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
            message=f"withholding_tax_amount 仅 payment_type=salary 可用,当前 payment_type={data.payment_type}",
            ai_instruction="STOP_RETRYING. 代扣个税只在发工资时使用,其他付款类型不应传 withholding_tax_amount。")

    with unit_of_work(db):
        result = dispatch(CreatePayment(account_id=account_id, operator=operator, data=data), db)
    return result


@router.post("/{payment_id}/reverse")
def reverse_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """红冲付款"""
    with unit_of_work(db):
        result = dispatch(ReversePayment(account_id=account_id, operator=operator, payment_id=payment_id), db)
    return result
