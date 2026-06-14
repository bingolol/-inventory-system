from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import Expense
from schemas import ExpenseCreate, ExpenseUpdate, ExpenseOut, PaginatedResponse
from account_dep import get_account_id, get_operator
from image_utils import delete_old_image
from enums import EXPENSE_CATEGORIES
import crud
from uow import unit_of_work

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
        query = query.filter(Expense.expense_date >= start_date, Expense.expense_date < end_date)
    
    total = query.count()
    expenses = query.offset(skip).limit(limit).all()
    
    # 转换为响应模型
    expense_outs = []
    for expense in expenses:
        expense_out = ExpenseOut(
            id=expense.id,
            account_id=expense.account_id,
            category=expense.category,
            amount=expense.amount,
            expense_date=expense.expense_date,
            has_invoice=expense.has_invoice,
            payment_method=expense.payment_method,
            description=expense.description,
            image_url=expense.image_url or "",
            created_at=expense.created_at
        )
        expense_outs.append(expense_out)
    
    return PaginatedResponse(total=total, items=expense_outs)


@router.post("", response_model=ExpenseOut)
async def create_expense(
    expense: ExpenseCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """创建费用"""
    # 校验费用类别
    if expense.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"category '{expense.category}' not in {EXPENSE_CATEGORIES}")
    # 创建费用
    db_expense = Expense(
        account_id=account_id,
        category=expense.category,
        amount=expense.amount,
        expense_date=expense.expense_date,
        has_invoice=expense.has_invoice,
        payment_method=expense.payment_method,
        description=expense.description,
        image_url=expense.image_url or ""
    )
    with unit_of_work(db):
        db.add(db_expense)
        db.flush()  # 确保 db_expense.id 可用于日志
        # 记录操作日志
        crud._log(db, account_id, "create", "expense", db_expense.id,
                  f"创建费用:{db_expense.category} {db_expense.amount}", operator=operator)
    db.refresh(db_expense)
    
    # 转换为响应模型
    return ExpenseOut(
        id=db_expense.id,
        account_id=db_expense.account_id,
        category=db_expense.category,
        amount=db_expense.amount,
        expense_date=db_expense.expense_date,
        has_invoice=db_expense.has_invoice,
        payment_method=db_expense.payment_method,
        description=db_expense.description,
        image_url=db_expense.image_url or "",
        created_at=db_expense.created_at
    )


@router.put("/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """更新费用"""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.account_id == account_id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="费用不存在")
    
    # 更新费用
    update_data = expense_update.model_dump(exclude_unset=True)
    # 校验费用类别（仅当修改了 category 时）
    if expense_update.category is not None and expense_update.category not in EXPENSE_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"category '{expense_update.category}' not in {EXPENSE_CATEGORIES}")
    with unit_of_work(db):
        for field, value in update_data.items():
            setattr(expense, field, value)
        # 记录操作日志
        crud._log(db, account_id, "update", "expense", expense.id,
                  f"更新费用:{expense.category} {expense.amount}", operator=operator)
    db.refresh(expense)
    return ExpenseOut(
        id=expense.id,
        account_id=expense.account_id,
        category=expense.category,
        amount=expense.amount,
        expense_date=expense.expense_date,
        has_invoice=expense.has_invoice,
        payment_method=expense.payment_method,
        description=expense.description,
        image_url=expense.image_url or "",
        created_at=expense.created_at
    )


@router.delete("/{expense_id}")
async def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """删除费用"""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.account_id == account_id
    ).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="费用不存在")
    
    # 删除关联图片文件
    if expense.image_url:
        delete_old_image(expense.image_url)
    
    # 删除费用
    with unit_of_work(db):
        db.delete(expense)
        # 记录操作日志（与业务数据同一事务）
        crud._log(db, account_id, "delete", "expense", expense.id,
                  f"删除费用:{expense.category} {expense.amount}", operator=operator)
    
    return {"message": "费用删除成功"}
