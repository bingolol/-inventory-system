"""收款路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Receipt, SaleOrder, BankAccount, BankTransaction
from schemas.receipt import ReceiptCreate, ReceiptOut
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.base import _log
from utils import _d
from operation_result import OperationResult, EntityType, OperationType
from finance_integration import post_journal

router = APIRouter()


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

        # 如果有银行账户，创建银行流水并更新余额
        if data.bank_account_id:
            # 添加行锁防止并发问题
            bank_account = db.query(BankAccount).filter(
                BankAccount.id == data.bank_account_id,
                BankAccount.account_id == account_id
            ).with_for_update().first()
            if not bank_account:
                raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="银行账户不存在")

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
