from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id, get_operator
import schemas, crud
from uow import unit_of_work
from commands.base import dispatch
from commands.finance_commands import CreateOpeningBalance, UpdateOpeningBalance
from errors import BusinessError, ErrorCode
from operation_result import OperationResult, EntityType, OperationType

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
        "fixed_assets_original": opening_balance.fixed_assets_original,
        "accumulated_depreciation": opening_balance.accumulated_depreciation,
        "intangible_assets_original": opening_balance.intangible_assets_original,
        "accumulated_amortization": opening_balance.accumulated_amortization,
        "accounts_payable": opening_balance.accounts_payable,
        "tax_payable": opening_balance.tax_payable,
        "long_term_borrowings": opening_balance.long_term_borrowings,
        "paid_in_capital": opening_balance.paid_in_capital,
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
                fixed_assets_original=data.fixed_assets_original,
                accumulated_depreciation=data.accumulated_depreciation,
                intangible_assets_original=data.intangible_assets_original,
                accumulated_amortization=data.accumulated_amortization,
                accounts_payable=data.accounts_payable,
                tax_payable=data.tax_payable,
                long_term_borrowings=data.long_term_borrowings,
                paid_in_capital=data.paid_in_capital,
                retained_earnings=data.retained_earnings,
            )
            opening_balance = dispatch(cmd, db)
    except ValueError:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "创建期初余额失败，请检查输入数据"})
    db.refresh(opening_balance)
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.OPENING_BALANCE,
        entity_id=opening_balance.id,
        summary=f"期初余额创建成功，日期 {opening_balance.date}",
        ai_hint="期初余额已创建。可以开始录入业务数据。",
        data=_build_ob_out(opening_balance)
    )
    return result.to_dict()


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
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "期初余额", "order_id": 0})
    return _build_ob_out(opening_balance)


@router.get("/{opening_balance_id}")
def get_opening_balance(opening_balance_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """获取指定期初余额"""
    opening_balance = crud.get_opening_balance(db, account_id, opening_balance_id)
    if not opening_balance:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "期初余额", "order_id": opening_balance_id})
    return _build_ob_out(opening_balance)


@router.put("/{opening_balance_id}")
def update_opening_balance(opening_balance_id: int, data: schemas.OpeningBalanceUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    """更新期初余额（存在业务数据时禁止修改）"""
    # 检查是否存在业务数据
    from models import PurchaseOrder, SaleOrder, Expense
    has_business_data = (
        db.query(PurchaseOrder).filter(PurchaseOrder.account_id == account_id).first() is not None or
        db.query(SaleOrder).filter(SaleOrder.account_id == account_id).first() is not None or
        db.query(Expense).filter(Expense.account_id == account_id).first() is not None
    )
    if has_business_data:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message="已存在业务数据（采购单/销售单/费用），禁止修改期初余额",
            ai_instruction="STOP_RETRYING. 期初余额已被锁定，存在业务数据后禁止修改。如需修改，请先清除所有业务数据。"
        )

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
                fixed_assets_original=data.fixed_assets_original,
                accumulated_depreciation=data.accumulated_depreciation,
                intangible_assets_original=data.intangible_assets_original,
                accumulated_amortization=data.accumulated_amortization,
                accounts_payable=data.accounts_payable,
                tax_payable=data.tax_payable,
                long_term_borrowings=data.long_term_borrowings,
                paid_in_capital=data.paid_in_capital,
                retained_earnings=data.retained_earnings,
            )
            opening_balance = dispatch(cmd, db)
    except ValueError:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "更新期初余额失败，请检查输入数据"})
    db.refresh(opening_balance)
    return _build_ob_out(opening_balance)


@router.delete("/{opening_balance_id}")
def delete_opening_balance(opening_balance_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    """删除期初余额（存在业务数据时禁止删除）"""
    # 检查是否存在业务数据
    from models import PurchaseOrder, SaleOrder, Expense
    has_business_data = (
        db.query(PurchaseOrder).filter(PurchaseOrder.account_id == account_id).first() is not None or
        db.query(SaleOrder).filter(SaleOrder.account_id == account_id).first() is not None or
        db.query(Expense).filter(Expense.account_id == account_id).first() is not None
    )
    if has_business_data:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message="已存在业务数据（采购单/销售单/费用），禁止删除期初余额",
            ai_instruction="STOP_RETRYING. 期初余额已被锁定，存在业务数据后禁止删除。如需删除，请先清除所有业务数据。"
        )

    with unit_of_work(db):
        if not crud.delete_opening_balance(db, account_id, opening_balance_id, operator=operator):
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "期初余额", "order_id": opening_balance_id})
    return {"message": "期初余额已删除"}