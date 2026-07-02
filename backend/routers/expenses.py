from fastapi import APIRouter, Depends, Query
from errors import BusinessError, ErrorCode
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Expense
from schemas import ExpenseCreate, ExpenseUpdate, PaginatedResponse
from account_dep import get_account_id, get_operator
from enums import EXPENSE_CATEGORIES
import crud
from crud.invoice_linkage import bulk_has_invoice
from uow import unit_of_work
from commands.base import dispatch
from commands.cash_commands import CreateExpense, UpdateExpense, ReverseExpense, DeleteExpense

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def get_expenses(
    category: Optional[str] = None,
    year: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取费用列表，支持筛选"""
    query = db.query(Expense).filter(Expense.account_id == account_id)
    
    if category:
        query = query.filter(Expense.category == category)
    if year:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)
        query = query.filter(Expense.expense_date_l1 >= start_date, Expense.expense_date_l1 < end_date)
    
    total = query.count()
    expenses = query.offset(skip).limit(limit).all()
    
    # 批量派生查询:哪些费用有发票关联(单一真相源,取代 ORM has_invoice 列)
    invoiced_ids = bulk_has_invoice(db, account_id, "expense", [e.id for e in expenses])

    # 转换为响应模型
    expense_outs = []
    for expense in expenses:
        expense_outs.append({
            "id": expense.id,
            "account_id": expense.account_id,
            "category": expense.category,
            "functional_category": expense.functional_category,
            "amount": float(expense.amount_l1),
            "expense_date": expense.expense_date_l1.isoformat() if expense.expense_date_l1 else None,
            "has_invoice": (expense.id in invoiced_ids),
            "payment_method": expense.payment_method,
            "payment_status": expense.payment_status,
            "description": expense.description,
            "image_url": expense.image_url or "",
            "created_at": expense.created_at.isoformat() if expense.created_at else None,
        })
    
    return PaginatedResponse(total=total, items=expense_outs)


@router.post("")
async def create_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """创建费用"""
    if expense.category not in EXPENSE_CATEGORIES:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"费用类别 '{expense.category}' 不合法，合法值: {EXPENSE_CATEGORIES}"})

    with unit_of_work(db):
        result = dispatch(CreateExpense(account_id=account_id, operator=operator, expense=expense), db)
    return result


@router.put("/{expense_id}")
async def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """更新费用（已付款费用禁止修改）"""
    if expense_update.category is not None and expense_update.category not in EXPENSE_CATEGORIES:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": f"费用类别 '{expense_update.category}' 不合法，合法值: {EXPENSE_CATEGORIES}"})

    with unit_of_work(db):
        result = dispatch(UpdateExpense(account_id=account_id, operator=operator, expense_id=expense_id, expense_update=expense_update), db)
    return result


@router.post("/{expense_id}/reverse")
async def reverse_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """红冲费用：冲红总账凭证 + 标记费用为已冲红（不物理删除，保留审计轨迹）"""
    with unit_of_work(db):
        result = dispatch(ReverseExpense(account_id=account_id, operator=operator, expense_id=expense_id), db)
    return result


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """删除费用"""
    with unit_of_work(db):
        result = dispatch(DeleteExpense(account_id=account_id, operator=operator, expense_id=expense_id), db)
    return result
