from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id, get_operator
import schemas, crud
from uow import unit_of_work
from commands.base import dispatch
from commands.finance_commands import CreateOpeningBalance, UpdateOpeningBalance

router = APIRouter()


def _build_ob_out(opening_balance):
    """OpeningBalance ORM 对象 → 响应字典"""
    return {
        "id": opening_balance.id,
        "account_id": opening_balance.account_id,
        "date": opening_balance.date.isoformat() if opening_balance.date else None,
        "cash_balance": opening_balance.cash_balance,
        "bank_balance": opening_balance.bank_balance,
        "accounts_receivable": opening_balance.accounts_receivable,
        "inventory_value": opening_balance.inventory_value,
        "accounts_payable": opening_balance.accounts_payable,
        "tax_payable": opening_balance.tax_payable,
        "retained_earnings": opening_balance.retained_earnings,
        "created_at": opening_balance.created_at.isoformat() if opening_balance.created_at else None,
        "updated_at": opening_balance.updated_at.isoformat() if opening_balance.updated_at else None
    }


@router.post("")
def create_opening_balance(data: schemas.OpeningBalanceCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    """创建期初余额"""
    try:
        with unit_of_work(db):
            cmd = CreateOpeningBalance(
                account_id=account_id,
                operator=operator,
                date=data.date,
                cash_balance=data.cash_balance,
                bank_balance=data.bank_balance,
                accounts_receivable=data.accounts_receivable,
                inventory_value=data.inventory_value,
                accounts_payable=data.accounts_payable,
                tax_payable=data.tax_payable,
                retained_earnings=data.retained_earnings,
            )
            opening_balance = dispatch(cmd, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(opening_balance)
    return _build_ob_out(opening_balance)


@router.get("")
def list_opening_balances(account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """获取所有期初余额"""
    balances = crud.list_opening_balances(db, account_id)
    result = []
    for balance in balances:
        result.append(_build_ob_out(balance))
    return result


@router.get("/latest")
def get_latest_opening_balance(date: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """获取最新的期初余额（指定日期之前最新的）"""
    opening_balance = crud.get_latest_opening_balance(db, account_id, date)
    if not opening_balance:
        raise HTTPException(status_code=404, detail="未找到期初余额")
    return _build_ob_out(opening_balance)


@router.get("/{opening_balance_id}")
def get_opening_balance(opening_balance_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """获取指定期初余额"""
    opening_balance = crud.get_opening_balance(db, account_id, opening_balance_id)
    if not opening_balance:
        raise HTTPException(status_code=404, detail="期初余额不存在")
    return _build_ob_out(opening_balance)


@router.put("/{opening_balance_id}")
def update_opening_balance(opening_balance_id: int, data: schemas.OpeningBalanceUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    """更新期初余额"""
    try:
        with unit_of_work(db):
            cmd = UpdateOpeningBalance(
                account_id=account_id,
                operator=operator,
                opening_balance_id=opening_balance_id,
                date=data.date,
                cash_balance=data.cash_balance,
                bank_balance=data.bank_balance,
                accounts_receivable=data.accounts_receivable,
                inventory_value=data.inventory_value,
                accounts_payable=data.accounts_payable,
                tax_payable=data.tax_payable,
                retained_earnings=data.retained_earnings,
            )
            opening_balance = dispatch(cmd, db)
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(opening_balance)
    return _build_ob_out(opening_balance)


@router.delete("/{opening_balance_id}")
def delete_opening_balance(opening_balance_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    """删除期初余额"""
    with unit_of_work(db):
        if not crud.delete_opening_balance(db, account_id, opening_balance_id, operator=operator):
            raise HTTPException(status_code=404, detail="期初余额不存在")
    return {"message": "期初余额已删除"}