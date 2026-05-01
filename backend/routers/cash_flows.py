from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
import schemas, crud
from uow import unit_of_work

router = APIRouter()


@router.get("/statement")
def get_cash_flow_statement(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    try:
        return crud.generate_cash_flow_statement(db, account_id, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成现金流量表失败: {str(e)}")


@router.post("/transactions", response_model=schemas.CashFlowTransactionOut)
def create_cash_transaction(
    data: schemas.CashFlowTransactionCreate,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    try:
        with unit_of_work(db):
            tx = crud.create_cash_flow_transaction(db, account_id, data)
        db.refresh(tx)
        return tx
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建现金流水失败: {str(e)}")


@router.get("/transactions")
def list_cash_transactions(
    skip: int = 0,
    limit: int = 100,
    start_date: str = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(None, description="结束日期 (YYYY-MM-DD)"),
    flow_category: str = Query(None, description="现金流量分类"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    total, items = crud.list_cash_flow_transactions(db, account_id, skip, limit, start_date, end_date, flow_category)
    return {"total": total, "items": items}


@router.put("/transactions/{transaction_id}", response_model=schemas.CashFlowTransactionOut)
def update_cash_transaction(
    transaction_id: int,
    data: schemas.CashFlowTransactionUpdate,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    with unit_of_work(db):
        transaction = crud.update_cash_flow_transaction(db, account_id, transaction_id, data)
    if not transaction:
        raise HTTPException(status_code=404, detail="现金流水不存在")
    db.refresh(transaction)
    return transaction

@router.delete("/transactions/{transaction_id}")
def delete_cash_transaction(
    transaction_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    with unit_of_work(db):
        success = crud.delete_cash_flow_transaction(db, account_id, transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="现金流水不存在")
    return {"result": "现金流水已删除"}
