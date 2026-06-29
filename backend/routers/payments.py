"""付款路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Payment, Expense, BankAccount, BankTransaction, PurchaseOrder
from schemas.payment import PaymentCreate, PaymentOut
from schemas import PaginatedResponse
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.base import _log
from crud.finance import list_payments, get_payment
from crud.reversal import reverse_single_payment
from utils import _d
from operation_result import OperationResult, EntityType, OperationType
from finance_integration import post_journal

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取付款记录列表"""
    items = list_payments(db, account_id, skip=skip, limit=limit)
    total = len(items)
    return PaginatedResponse(total=total, items=[PaymentOut.model_validate(p) for p in items])


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment_by_id(
    payment_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取单条付款记录"""
    p = get_payment(db, account_id, payment_id)
    if not p:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"payment_id": payment_id})
    return PaymentOut.model_validate(p)


@router.post("")
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """创建付款记录"""
    with unit_of_work(db):
        # 创建付款记录
        payment = Payment(
            account_id=account_id,
            payment_type=data.payment_type,
            related_entity_type=data.related_entity_type,
            related_entity_id=data.related_entity_id,
            amount=_d(data.amount),
            payment_method=data.payment_method,
            payment_date=data.payment_date,
            bank_account_id=data.bank_account_id,
            description=data.description
        )
        db.add(payment)
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
            new_balance = _d(bank_account.balance) - _d(data.amount)

            # 余额校验：禁止银行账户透支（防止负资产）
            if new_balance < 0:
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"银行账户余额不足: 当前余额 {bank_account.balance}，"
                            f"付款金额 {data.amount}，超额 {abs(new_balance)}",
                    ai_instruction=f"STOP_RETRYING. 银行账户 {bank_account.bank_name} 余额仅 "
                                   f"{bank_account.balance}，不足以支付 {data.amount}。"
                                   f"请减少付款金额或先充值。"
                )

            # 创建银行流水
            bank_transaction = BankTransaction(
                account_id=account_id,
                bank_account_id=data.bank_account_id,
                transaction_type="outflow",
                amount=_d(data.amount),
                balance_after=new_balance,
                transaction_date=data.payment_date,
                description=f"付款: {data.description}",
                flow_category="operating",
                related_entity_type="payment",
                related_entity_id=payment.id
            )
            db.add(bank_transaction)
            db.flush()

            # 更新银行账户余额
            bank_account.balance = new_balance

            # 回写银行流水ID到付款记录
            payment.bank_transaction_id = bank_transaction.id

        # 更新关联的费用状态
        if data.related_entity_type == "expense":
            expense = db.query(Expense).filter(
                Expense.id == data.related_entity_id,
                Expense.account_id == account_id
            ).first()
            if expense:
                expense.payment_status = "paid"
                expense.payment_id = payment.id

        # 更新关联的采购单状态
        if data.related_entity_type == "purchase_order":
            purchase_order = db.query(PurchaseOrder).filter(
                PurchaseOrder.id == data.related_entity_id,
                PurchaseOrder.account_id == account_id
            ).first()
            if purchase_order:
                purchase_order.payment_status = "paid"

        # 确定冲销科目：工资→2211，个人垫付→2241，缴税→2221，其他→2202
        if data.payment_type == "salary":
            debit_code = "2211"
        elif data.payment_type == "tax":
            debit_code = "2221"
        elif data.payment_type == "expense" and data.related_entity_type == "expense":
            adv = db.query(Expense).filter(Expense.id == data.related_entity_id).first()
            debit_code = "2241" if adv and adv.payment_method == "private_advance" else "2202"
        else:
            debit_code = "2202"
        post_journal(db, account_id, "payment", {
            "amount": _d(data.amount),
            "date": data.payment_date.strftime("%Y-%m-%d"),
            "debit_account_code": debit_code,
            "partner_id": data.related_entity_id,
            "partner_type": "supplier",
            "bank_account_id": data.bank_account_id,
        })

        db.flush()
        _log(db, account_id, "create", "payment", payment.id,
             f"创建付款: {data.payment_type} {data.amount}", operator=operator)

    db.refresh(payment)
    
    # 构建变化信息
    changes = {"cash": {"amount": f"-{data.amount}"}}
    if data.related_entity_type == "expense":
        changes["payable"] = {"amount": f"-{data.amount}"}
    elif data.related_entity_type == "purchase_order":
        changes["payable"] = {"amount": f"-{data.amount}"}
    elif data.related_entity_type == "tax_payable":
        # 缴税:清偿应交税费负债,不碰利润表(增值税属价外税/负债)
        changes["tax_payable"] = {"amount": f"-{data.amount}"}
        changes["note"] = "缴税:借应交税费,贷银行存款,清负债不碰利润表"

    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.PAYMENT,
        entity_id=payment.id,
        summary=f"付款成功，金额 {data.amount}，类型 {data.payment_type}",
        ai_hint="付款已完成，银行余额已减少。",
        data=PaymentOut.model_validate(payment).model_dump(),
        changes=changes
    )
    return result.to_dict()


@router.post("/{payment_id}/reverse")
def reverse_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator)
):
    """红冲付款"""
    with unit_of_work(db):
        reversal = reverse_single_payment(db, account_id, payment_id)
        if not reversal:
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"payment_id": payment_id})
        _log(db, account_id, "reverse", "payment", payment_id,
             f"红冲付款: {reversal.amount}", operator=operator)
    return {"status": "reversed", "reversal_id": reversal.id}
