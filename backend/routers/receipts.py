"""收款路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Receipt
from schemas.receipt import ReceiptCreate, ReceiptOut
from schemas import PaginatedResponse
from account_dep import get_account_id, get_operator
from dependencies import Pagination
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.finance import list_receipts, get_receipt
from commands.base import dispatch
from commands.cash_commands import CreateReceipt, ReverseReceipt

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
def get_receipts(
    pag: Pagination = Depends(),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取收款记录列表"""
    items = list_receipts(db, account_id, skip=pag.skip, limit=pag.limit)
    total = len(items)
    return PaginatedResponse(total=total, items=[ReceiptOut.model_validate(r) for r in items])


@router.get("/{receipt_id}", response_model=ReceiptOut)
def get_receipt_by_id(
    receipt_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取单条收款记录"""
    return ReceiptOut.model_validate(get_receipt(db, account_id, receipt_id))


@router.post("")
def create_receipt(
    data: ReceiptCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """创建收款记录"""
    with unit_of_work(db):
        result = dispatch(CreateReceipt(account_id=account_id, operator=operator, data=data), db)
    return result


@router.post("/{receipt_id}/reverse")
def reverse_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """红冲收款"""
    with unit_of_work(db):
        result = dispatch(ReverseReceipt(account_id=account_id, operator=operator, receipt_id=receipt_id), db)
    return result
