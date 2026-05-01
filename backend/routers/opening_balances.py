from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
import schemas, crud
from uow import unit_of_work

router = APIRouter()


@router.post("/")
def create_opening_balance(data: schemas.OpeningBalanceCreate, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """创建期初余额"""
    try:
        with unit_of_work(db):
            opening_balance = crud.create_opening_balance(db, account_id, data)
        db.refresh(opening_balance)
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
def list_opening_balances(account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """获取所有期初余额"""
    balances = crud.list_opening_balances(db, account_id)
    result = []
    for balance in balances:
        result.append({
            "id": balance.id,
            "account_id": balance.account_id,
            "date": balance.date.isoformat() if balance.date else None,
            "cash_balance": balance.cash_balance,
            "bank_balance": balance.bank_balance,
            "accounts_receivable": balance.accounts_receivable,
            "inventory_value": balance.inventory_value,
            "accounts_payable": balance.accounts_payable,
            "tax_payable": balance.tax_payable,
            "retained_earnings": balance.retained_earnings,
            "created_at": balance.created_at.isoformat() if balance.created_at else None,
            "updated_at": balance.updated_at.isoformat() if balance.updated_at else None
        })
    return result


@router.get("/latest")
def get_latest_opening_balance(date: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """获取最新的期初余额（指定日期之前最新的）"""
    opening_balance = crud.get_latest_opening_balance(db, account_id, date)
    if not opening_balance:
        raise HTTPException(status_code=404, detail="未找到期初余额")
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


@router.get("/{opening_balance_id}")
def get_opening_balance(opening_balance_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """获取指定期初余额"""
    opening_balance = crud.get_opening_balance(db, account_id, opening_balance_id)
    if not opening_balance:
        raise HTTPException(status_code=404, detail="期初余额不存在")
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


@router.put("/{opening_balance_id}")
def update_opening_balance(opening_balance_id: int, data: schemas.OpeningBalanceUpdate, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """更新期初余额"""
    try:
        with unit_of_work(db):
            opening_balance = crud.update_opening_balance(db, account_id, opening_balance_id, data)
        if not opening_balance:
            raise HTTPException(status_code=404, detail="期初余额不存在")
        db.refresh(opening_balance)
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{opening_balance_id}")
def delete_opening_balance(opening_balance_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """删除期初余额"""
    with unit_of_work(db):
        if not crud.delete_opening_balance(db, account_id, opening_balance_id):
            raise HTTPException(status_code=404, detail="期初余额不存在")
    return {"message": "期初余额已删除"}