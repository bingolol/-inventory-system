"""前置条件检查接口 - 让端侧Agent在操作前检查是否可行"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal

from database import get_db
from models import Product, Supplier, Customer, Inventory, Expense
from account_dep import get_account_id
from errors import BusinessError, ErrorCode
from utils import _d

router = APIRouter()


@router.get("/sale")
def check_sale(
    product_id: int = Query(..., description="商品ID"),
    quantity: int = Query(..., gt=0, description="销售数量"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """检查销售操作是否可行"""
    warnings = []
    suggestions = []
    can_proceed = True

    # 检查商品是否存在
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.account_id == account_id
    ).first()
    if not product:
        return {
            "can_proceed": False,
            "warnings": [f"商品不存在: ID={product_id}"],
            "suggestions": ["请检查商品ID是否正确"],
            "ai_instruction": "STOP_RETRYING. 商品不存在，请检查商品ID或名称是否正确。"
        }

    # 检查库存是否充足
    inventory = db.query(Inventory).filter(
        Inventory.product_id == product_id,
        Inventory.account_id == account_id
    ).first()
    current_stock = inventory.quantity if inventory else 0
    if current_stock < quantity:
        can_proceed = False
        warnings.append(f"库存不足: 当前库存{current_stock}，需要{quantity}")
        suggestions.append("请先采购入库")
        suggestions.append("或减少销售数量")

    return {
        "can_proceed": can_proceed,
        "warnings": warnings,
        "suggestions": suggestions,
        "ai_instruction": "STOP_RETRYING. 库存不足，请向用户确认：是否先采购入库？还是减少销售数量？" if not can_proceed else "操作可行，可以继续。"
    }


@router.get("/purchase")
def check_purchase(
    supplier_id: int = Query(..., description="供应商ID"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """检查采购操作是否可行"""
    warnings = []
    suggestions = []
    can_proceed = True

    # 检查供应商是否存在
    supplier = db.query(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.account_id == account_id
    ).first()
    if not supplier:
        can_proceed = False
        warnings.append(f"供应商不存在: ID={supplier_id}")
        suggestions.append("请检查供应商ID是否正确")

    return {
        "can_proceed": can_proceed,
        "warnings": warnings,
        "suggestions": suggestions,
        "ai_instruction": "STOP_RETRYING. 供应商不存在，请检查供应商ID或名称是否正确。" if not can_proceed else "操作可行，可以继续。"
    }


@router.get("/expense")
def check_expense(
    category: str = Query(..., description="费用类别"),
    amount: Decimal = Query(..., gt=0, description="费用金额"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db)
):
    """检查费用操作是否可行"""
    from enums import EXPENSE_CATEGORIES
    warnings = []
    suggestions = []
    can_proceed = True

    # 检查费用类别是否合法
    if category not in EXPENSE_CATEGORIES:
        can_proceed = False
        warnings.append(f"费用类别不合法: {category}")
        suggestions.append(f"合法类别: {EXPENSE_CATEGORIES}")

    return {
        "can_proceed": can_proceed,
        "warnings": warnings,
        "suggestions": suggestions,
        "ai_instruction": f"STOP_RETRYING. 费用类别不合法，请使用正确的类别: {EXPENSE_CATEGORIES}" if not can_proceed else "操作可行，可以继续。"
    }
