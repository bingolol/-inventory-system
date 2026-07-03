"""银行账户路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import BankAccount
from schemas.bank import BankAccountCreate, BankAccountUpdate, BankAccountOut, BankAccountList
from account_dep import get_account_id, get_operator
from uow import unit_of_work
from commands.base import dispatch
from commands.bank_commands import CreateBankAccount, UpdateBankAccount, DeleteBankAccount

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
        return dispatch(CreateBankAccount(
            account_id=account_id,
            operator=operator,
            data=data,
        ), db)


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
        return dispatch(UpdateBankAccount(
            account_id=account_id,
            operator=operator,
            bank_account_id=bank_account_id,
            data=data,
        ), db)


@router.delete("/{bank_account_id}")
def delete_bank_account(
    bank_account_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """删除银行账户"""
    with unit_of_work(db):
        return dispatch(DeleteBankAccount(
            account_id=account_id,
            operator=operator,
            bank_account_id=bank_account_id,
        ), db)
