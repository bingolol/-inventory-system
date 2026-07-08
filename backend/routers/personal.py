from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from decimal import Decimal
from database import get_db
from account_dep import get_account_id, get_operator
from models import PersonalTransaction
from image_utils import delete_old_image
from enums import PERSONAL_EXPENSE_CATEGORIES, PERSONAL_INCOME_CATEGORIES
import schemas, crud
from commands import dispatch, CreatePersonalTransaction, UpdatePersonalTransaction, DeletePersonalTransaction
from uow import unit_of_work
from utils import _d, Q2
from errors import BusinessError, ErrorCode

router = APIRouter()


def _validate_personal_category(type: str, category: str):
    """校验个人流水分类是否在对应枚举中"""
    if not category:
        return
    allowed = PERSONAL_INCOME_CATEGORIES if type == "income" else PERSONAL_EXPENSE_CATEGORIES
    if category not in allowed:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message=f"category '{category}' 不合法，'{type}' 的合法值: {allowed}")


@router.get("/category_summary")
def get_category_summary(
    type: str = None, start_date: str = None, end_date: str = None,
    account_id: int = Depends(get_account_id), db: Session = Depends(get_db)
):
    return crud.get_personal_category_summary(
        db, account_id, type=type, start_date=start_date, end_date=end_date
    )


@router.get("/monthly_summary")
def get_monthly_summary(
    type: str = None, months: int = 12,
    account_id: int = Depends(get_account_id), db: Session = Depends(get_db)
):
    return crud.get_personal_monthly_summary(db, account_id, type=type, months=months)


@router.get("/summary")
def get_summary(account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    return crud.get_personal_summary(db, account_id)


@router.get("")
def list_transactions(
    page: int = 1, page_size: int = 20,
    type: str = None, category: str = None, start_date: str = None, end_date: str = None,
    account_id: int = Depends(get_account_id), db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size
    total, items, sum_income, sum_expense = crud.list_personal_transactions(
        db, account_id, skip=skip, limit=page_size, type=type, category=category, start_date=start_date, end_date=end_date
    )
    return {
        "total": total,
        "items": [schemas.PersonalTransactionOut.model_validate(item) for item in items],
        "sum_income": sum_income,
        "sum_expense": sum_expense,
        "sum_balance": (_d(sum_income) - _d(sum_expense)).quantize(Q2)
    }


@router.post("", response_model=schemas.PersonalTransactionOut)
def create_transaction(data: schemas.PersonalTransactionCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    _validate_personal_category(data.type, data.category)
    with unit_of_work(db):
        tx = dispatch(CreatePersonalTransaction(
            account_id=account_id,
            operator=operator,
            type=data.type,
            amount=data.amount,
            category=data.category,
            description=data.description,
            image_url=data.image_url or "",
            date=data.date,
        ), db)
    db.refresh(tx)
    return tx


@router.put("/{tx_id}", response_model=schemas.PersonalTransactionOut)
def update_transaction(tx_id: int, data: schemas.PersonalTransactionUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    # 先查原记录，用于校验和确定 type
    tx = db.query(PersonalTransaction).filter(
        PersonalTransaction.id == tx_id,
        PersonalTransaction.account_id == account_id
    ).first()
    if not tx:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "个人流水记录", "order_id": tx_id})

    # 确定最终 type（若传了新 type 则用新的，否则保持原 type）
    final_type = data.type if data.type is not None else tx.type
    # 若传了 category，则用最终 type 校验其合法性
    if data.category is not None:
        _validate_personal_category(final_type, data.category)

    with unit_of_work(db):
        tx = dispatch(UpdatePersonalTransaction(
            account_id=account_id,
            operator=operator,
            tx_id=tx_id,
            type=data.type,
            amount=data.amount,
            category=data.category,
            description=data.description,
            image_url=data.image_url,
            date=data.date,
        ), db)
    if not tx:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "个人流水记录", "order_id": tx_id})
    db.refresh(tx)
    return tx


@router.delete("/{tx_id}")
def delete_transaction(tx_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    # 先查记录获取image_url
    tx = db.query(PersonalTransaction).filter(
        PersonalTransaction.id == tx_id,
        PersonalTransaction.account_id == account_id
    ).first()
    if not tx:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "个人流水记录", "order_id": tx_id})
    # 删除关联图片文件
    if tx.image_url:
        delete_old_image(tx.image_url)
    with unit_of_work(db):
        if not dispatch(DeletePersonalTransaction(
            account_id=account_id,
            operator=operator,
            tx_id=tx_id,
        ), db):
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "个人流水记录", "order_id": tx_id})
    return {"message": "已删除"}
