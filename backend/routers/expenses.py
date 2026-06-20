from fastapi import APIRouter, Depends, Query
from errors import BusinessError, ErrorCode, ActionType
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
from crud.invoice_linkage import bulk_has_invoice, has_invoice as linkage_has_invoice
from uow import unit_of_work
from operation_result import OperationResult, EntityType, OperationType

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
            "amount": float(expense.amount),
            "expense_date": expense.expense_date.isoformat() if expense.expense_date else None,
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
    # 校验费用类别
    if expense.category not in EXPENSE_CATEGORIES:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message=f"category '{expense.category}' not in {EXPENSE_CATEGORIES}")
    # 创建费用
    db_expense = Expense(
        account_id=account_id,
        category=expense.category,
        functional_category=expense.functional_category or "管理费用",
        amount=expense.amount,
        expense_date=expense.expense_date,
        payment_method=expense.payment_method,
        payment_status="unpaid",  # 权责发生制：费用发生时未付款
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
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.EXPENSE,
        entity_id=db_expense.id,
        summary=f"费用创建成功，类别：{db_expense.category}，金额 {db_expense.amount}",
        ai_hint="费用已创建，状态为未付款。如需付款，请调用 POST /api/payments。",
        data={
            "id": db_expense.id,
            "account_id": db_expense.account_id,
            "category": db_expense.category,
            "functional_category": db_expense.functional_category,
            "amount": float(db_expense.amount),
            "expense_date": db_expense.expense_date.isoformat() if db_expense.expense_date else None,
            "has_invoice": linkage_has_invoice(db, account_id, "expense", db_expense.id),
            "payment_method": db_expense.payment_method,
            "payment_status": db_expense.payment_status,
            "description": db_expense.description,
            "image_url": db_expense.image_url or "",
            "created_at": db_expense.created_at.isoformat() if db_expense.created_at else None,
        },
        changes={
            "payable": {"amount": f"+{db_expense.amount}"}
        }
    )
    return result.to_dict()


@router.put("/{expense_id}")
async def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """更新费用（已付款费用禁止修改）"""
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.account_id == account_id
    ).first()
    
    if not expense:
        raise BusinessError(code=ErrorCode.EXPENSE_NOT_FOUND, data={"expense_id": expense_id})
    
    # 检查是否已付款
    if expense.payment_status == "paid":
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message="已付款费用禁止修改",
            ai_instruction="STOP_RETRYING. 该费用已付款，禁止修改。如需调整，请创建新的费用记录。"
        )
    
    # 更新费用
    update_data = expense_update.model_dump(exclude_unset=True)
    if expense_update.category is not None and expense_update.category not in EXPENSE_CATEGORIES:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message=f"category '{expense_update.category}' not in {EXPENSE_CATEGORIES}")
    with unit_of_work(db):
        for field, value in update_data.items():
            setattr(expense, field, value)
        crud._log(db, account_id, "update", "expense", expense.id,
                  f"更新费用:{expense.category} {expense.amount}", operator=operator)
    db.refresh(expense)
    
    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.EXPENSE,
        entity_id=expense.id,
        summary=f"费用更新成功，类别：{expense.category}，金额 {expense.amount}",
        ai_hint="费用已更新。",
        data={"id": expense.id, "category": expense.category, "amount": float(expense.amount)}
    )
    return result.to_dict()


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
        raise BusinessError(code=ErrorCode.EXPENSE_NOT_FOUND, data={"expense_id": expense_id})
    
    # 删除关联图片文件
    if expense.image_url:
        delete_old_image(expense.image_url)
    
    # 删除费用
    with unit_of_work(db):
        db.delete(expense)
        crud._log(db, account_id, "delete", "expense", expense.id,
                  f"删除费用:{expense.category} {expense.amount}", operator=operator)
    
    result = OperationResult(
        operation=OperationType.DELETE,
        entity_type=EntityType.EXPENSE,
        entity_id=expense_id,
        summary=f"费用删除成功，类别：{expense.category}，金额 {expense.amount}",
        ai_hint="费用已删除。",
        data={"expense_id": expense_id, "category": expense.category}
    )
    return result.to_dict()
