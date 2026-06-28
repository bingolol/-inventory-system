from fastapi import APIRouter, Depends, Query
from errors import BusinessError, ErrorCode, ActionType
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id, get_operator
import schemas, crud
from uow import unit_of_work
from commands.base import dispatch
from commands.finance_commands import (
    CreateCashFlowTransaction, UpdateCashFlowTransaction, DeleteCashFlowTransaction,
)

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
        raise BusinessError(code=ErrorCode.INTERNAL_ERROR, message=f"生成现金流量表失败: {str(e)}")


@router.post("/transactions", response_model=schemas.CashFlowTransactionOut)
def create_cash_transaction(
    data: schemas.CashFlowTransactionCreate,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db)
):
    try:
        with unit_of_work(db):
            cmd = CreateCashFlowTransaction(
                account_id=account_id,
                operator=operator,
                type=data.type,
                amount=data.amount,
                flow_category=data.flow_category,
                description=data.description,
                transaction_date=data.transaction_date,
                counter_account_code=data.counter_account_code,
                related_entity_type=getattr(data, 'related_entity_type', None),
                related_entity_id=getattr(data, 'related_entity_id', None),
            )
            tx = dispatch(cmd, db)
    except ValueError:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "创建现金流水失败，请检查输入数据"})
    except Exception:
        raise BusinessError(code=ErrorCode.INTERNAL_ERROR, data={"details": "创建现金流水失败"})
    db.refresh(tx)
    return tx


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
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db)
):
    try:
        with unit_of_work(db):
            update_kwargs = {}
            for k in ('type', 'amount', 'flow_category', 'description',
                      'transaction_date', 'related_entity_type', 'related_entity_id'):
                v = getattr(data, k, None)
                if v is not None:
                    update_kwargs[k] = v
            cmd = UpdateCashFlowTransaction(
                account_id=account_id,
                operator=operator,
                transaction_id=transaction_id,
                **update_kwargs
            )
            transaction = dispatch(cmd, db)
    except ValueError as e:
        if "不存在" in str(e):
            raise BusinessError(code=ErrorCode.CASH_FLOW_NOT_FOUND, data={"transaction_id": transaction_id})
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "更新现金流水失败，请检查输入数据"})
    db.refresh(transaction)
    return transaction

@router.delete("/transactions/{transaction_id}")
def delete_cash_transaction(
    transaction_id: int,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db)
):
    try:
        with unit_of_work(db):
            dispatch(DeleteCashFlowTransaction(
                account_id=account_id,
                operator=operator,
                transaction_id=transaction_id,
            ), db)
    except ValueError as e:
        if "不存在" in str(e):
            raise BusinessError(code=ErrorCode.CASH_FLOW_NOT_FOUND, data={"transaction_id": transaction_id})
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "删除现金流水失败，请检查输入数据"})
    return {"result": "现金流水已删除"}