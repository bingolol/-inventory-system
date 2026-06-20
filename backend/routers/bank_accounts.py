"""银行账户路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
import models
from models import BankAccount
from schemas.bank import BankAccountCreate, BankAccountUpdate, BankAccountOut, BankAccountList
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.base import _log

router = APIRouter()


@router.get("", response_model=BankAccountList)
def list_bank_accounts(
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """查询银行账户列表"""
    accounts = db.query(BankAccount).filter(
        BankAccount.account_id == account_id
    ).all()
    return BankAccountList(
        total=len(accounts),
        items=[BankAccountOut.model_validate(a) for a in accounts]
    )


@router.post("", response_model=BankAccountOut)
def create_bank_account(
    data: BankAccountCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """创建银行账户"""
    with unit_of_work(db):
        bank_account = BankAccount(
            account_id=account_id,
            bank_name=data.bank_name,
            account_number=data.account_number,
            balance=data.balance,
            description=data.description
        )
        db.add(bank_account)
        db.flush()
        _log(db, account_id, "create", "bank_account", bank_account.id,
             f"创建银行账户: {data.bank_name} {data.account_number}", operator=operator)
    db.refresh(bank_account)
    return BankAccountOut.model_validate(bank_account)


@router.put("/{bank_account_id}", response_model=BankAccountOut)
def update_bank_account(
    bank_account_id: int,
    data: BankAccountUpdate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """更新银行账户"""
    with unit_of_work(db):
        bank_account = db.query(BankAccount).filter(
            BankAccount.id == bank_account_id,
            BankAccount.account_id == account_id
        ).first()
        if not bank_account:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="银行账户不存在")

        if data.bank_name is not None:
            bank_account.bank_name = data.bank_name
        if data.account_number is not None:
            bank_account.account_number = data.account_number
        # 注意：余额不能直接编辑，只能通过银行流水调整
        # if data.balance is not None:
        #     bank_account.balance = data.balance
        if data.description is not None:
            bank_account.description = data.description

        db.flush()
        _log(db, account_id, "update", "bank_account", bank_account.id,
             f"更新银行账户: {bank_account.bank_name}", operator=operator)
    db.refresh(bank_account)
    return BankAccountOut.model_validate(bank_account)


@router.delete("/{bank_account_id}")
def delete_bank_account(
    bank_account_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """删除银行账户（有关联数据时不能删除）"""
    with unit_of_work(db):
        bank_account = db.query(BankAccount).filter(
            BankAccount.id == bank_account_id,
            BankAccount.account_id == account_id
        ).first()
        if not bank_account:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="银行账户不存在")

        # 检查关联数据
        transactions_count = db.query(models.BankTransaction).filter(
            models.BankTransaction.bank_account_id == bank_account_id
        ).count()
        payments_count = db.query(models.Payment).filter(
            models.Payment.bank_account_id == bank_account_id
        ).count()
        receipts_count = db.query(models.Receipt).filter(
            models.Receipt.bank_account_id == bank_account_id
        ).count()

        if transactions_count + payments_count + receipts_count > 0:
            raise BusinessError(
                code=ErrorCode.DUPLICATE_ENTRY,
                message=f"该银行账户存在关联的银行流水({transactions_count})、付款({payments_count})、收款({receipts_count})记录，无法删除",
                ai_instruction="STOP_RETRYING. 该银行账户有关联数据，无法删除。如需删除，请先清理关联的银行流水、付款、收款记录。"
            )

        _log(db, account_id, "delete", "bank_account", bank_account.id,
             f"删除银行账户: {bank_account.bank_name}", operator=operator)
        db.delete(bank_account)
        db.flush()
    return {"message": "银行账户已删除"}
