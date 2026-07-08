from fastapi import APIRouter, Depends, Query
from errors import BusinessError, ErrorCode, ActionType
from sqlalchemy.orm import Session
from utils import get_or_404
from database import get_db
from account_dep import get_account_id, get_operator
from dependencies import Pagination, DateRange
from schemas import PaginatedResponse
import schemas, crud
from uow import unit_of_work
from commands.base import dispatch, dispatch_safe
from commands.finance_commands import (
    CreateCashFlowTransaction, UpdateCashFlowTransaction, DeleteCashFlowTransaction,
)
from finance_integration import reverse_journal
from operation_result import OperationResult, EntityType, OperationType
from datetime import datetime

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
            tx = dispatch_safe(cmd, db, "创建现金流水失败，请检查输入数据")
    except Exception:
        raise BusinessError(code=ErrorCode.INTERNAL_ERROR, data={"details": "创建现金流水失败"})
    db.refresh(tx)
    return tx


@router.get("/transactions")
def list_cash_transactions(
    pag: Pagination = Depends(),
    date_range: DateRange = Depends(),
    flow_category: str = Query(None, description="现金流量分类"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    total, items = crud.list_cash_flow_transactions(db, account_id, pag.skip, pag.limit, date_range.start, date_range.end, flow_category)
    return PaginatedResponse(total=total, items=items)


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

@router.post("/transactions/{transaction_id}/reverse")
def reverse_cash_transaction(
    transaction_id: int,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """红冲现金流水：冲红总账凭证 + 标记为已冲红（不物理删除，保留审计轨迹）"""
    import models
    with unit_of_work(db):
        transaction = get_or_404(db, models.CashFlowTransaction, transaction_id, account_id)

        if transaction.is_reversed:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"现金流水 #{transaction_id} 已被冲红，不可重复操作",
                ai_instruction="STOP_RETRYING. 该现金流水已冲红。"
            )

        # 冲红总账凭证（reverse_journal 自带幂等）
        reverse_journal(db, account_id, "cash_flow", transaction_id)

        # 标记已冲红
        transaction.is_reversed = True
        transaction.reversed_at = datetime.now()

        crud.log_op(db, account_id, "reverse", "cash_flow", transaction_id,
                  f"红冲现金流水: {transaction.type} {transaction.amount_l2}", operator=operator)

    op = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.EXPENSE,
        entity_id=transaction_id,
        summary=f"现金流水 #{transaction_id} 已红冲",
        ai_hint="现金流水凭证已冲红，原记录保留（审计可追溯）。",
        data={"transaction_id": transaction_id, "is_reversed": True}
    )
    return op.to_dict()

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
