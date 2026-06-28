"""收款路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Receipt, SaleOrder, BankAccount, BankTransaction
from schemas.receipt import ReceiptCreate, ReceiptOut
from schemas import PaginatedResponse
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.base import _log
from crud.finance import list_receipts, get_receipt
from utils import _d
from operation_result import OperationResult, EntityType, OperationType
from finance_integration import post_journal

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
def get_receipts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取收款记录列表"""
    items = list_receipts(db, account_id, skip=skip, limit=limit)
    total = len(items)
    return PaginatedResponse(total=total, items=[ReceiptOut.model_validate(r) for r in items])


@router.get("/{receipt_id}", response_model=ReceiptOut)
def get_receipt_by_id(
    receipt_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取单条收款记录"""
    r = get_receipt(db, account_id, receipt_id)
    if not r:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"receipt_id": receipt_id})
    return ReceiptOut.model_validate(r)


@router.post("")
def create_receipt(
    data: ReceiptCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """创建收款记录"""
    with unit_of_work(db):
        # 创建收款记录
        receipt = Receipt(
            account_id=account_id,
            receipt_type=data.receipt_type,
            related_entity_type=data.related_entity_type,
            related_entity_id=data.related_entity_id,
            amount=_d(data.amount),
            receipt_method=data.receipt_method,
            receipt_date=data.receipt_date,
            bank_account_id=data.bank_account_id,
            description=data.description
        )
        db.add(receipt)
        db.flush()

        # 如果没有指定银行账户，自动关联第一个银行账户
        if not data.bank_account_id:
            default_bank = db.query(BankAccount).filter(
                BankAccount.account_id == account_id
            ).first()
            if default_bank:
                data.bank_account_id = default_bank.id

        # 如果有银行账户，创建银行流水并更新余额
        if data.bank_account_id:
            # 添加行锁防止并发问题
            bank_account = db.query(BankAccount).filter(
                BankAccount.id == data.bank_account_id,
                BankAccount.account_id == account_id
            ).with_for_update().first()
            if not bank_account:
                raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND, data={"bank_account_id": data.bank_account_id})

            # 计算交易后余额
            new_balance = _d(bank_account.balance) + _d(data.amount)

            # 创建银行流水
            bank_transaction = BankTransaction(
                account_id=account_id,
                bank_account_id=data.bank_account_id,
                transaction_type="inflow",
                amount=_d(data.amount),
                balance_after=new_balance,
                transaction_date=data.receipt_date,
                description=f"收款: {data.description}",
                flow_category="operating",
                related_entity_type="receipt",
                related_entity_id=receipt.id
            )
            db.add(bank_transaction)
            db.flush()

            # 更新银行账户余额
            bank_account.balance = new_balance

            # 回写银行流水ID到收款记录
            receipt.bank_transaction_id = bank_transaction.id

        # 更新关联的销售单状态
        if data.related_entity_type == "sale_order":
            sale_order = db.query(SaleOrder).filter(
                SaleOrder.id == data.related_entity_id,
                SaleOrder.account_id == account_id
            ).first()
            if sale_order:
                sale_order.payment_status = "paid"

        # 生成会计凭证：借:1002 贷:1122
        post_journal(db, account_id, "receipt", {
            "amount": _d(data.amount),
            "date": data.receipt_date.strftime("%Y-%m-%d"),
            "partner_id": data.related_entity_id,
            "bank_account_id": data.bank_account_id,
        })

        db.flush()
        _log(db, account_id, "create", "receipt", receipt.id,
             f"创建收款: {data.receipt_type} {data.amount}", operator=operator)

    db.refresh(receipt)
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.RECEIPT,
        entity_id=receipt.id,
        summary=f"收款成功，金额 {data.amount}，类型 {data.receipt_type}",
        ai_hint="收款已完成，银行余额已增加。",
        data=ReceiptOut.model_validate(receipt).model_dump(),
        changes={"cash": {"amount": f"+{data.amount}"}}
    )
    return result.to_dict()
