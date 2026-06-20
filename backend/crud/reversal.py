"""冲销模块 — 取消/删除订单时反转收款/付款/银行流水

设计原则：
- 生成反向分录（非删除），保留审计痕迹
- 银行余额同步回滚
- 重置关联订单的付款状态
"""

from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

import models
from utils import _d


def reverse_receipts(db: Session, account_id: int, sale_order_id: int) -> None:
    """冲销销售单关联的所有收款记录。

    1. 查找该销售单的所有收款记录
    2. 为每笔收款生成反向收款（负金额）
    3. 生成反向银行流水（outflow）
    4. 回滚银行余额
    5. 重置销售单付款状态为 unpaid
    """
    receipts = db.query(models.Receipt).filter(
        models.Receipt.account_id == account_id,
        models.Receipt.related_entity_type == "sale_order",
        models.Receipt.related_entity_id == sale_order_id,
    ).all()

    for receipt in receipts:
        # 跳过已冲销的（负金额）
        if _d(receipt.amount) < 0:
            continue

        original_amount = _d(receipt.amount)

        # 生成反向收款记录
        reversal_receipt = models.Receipt(
            account_id=account_id,
            receipt_type=receipt.receipt_type,
            related_entity_type="sale_order",
            related_entity_id=sale_order_id,
            amount=-original_amount,
            receipt_method=receipt.receipt_method,
            receipt_date=datetime.now(),
            bank_account_id=receipt.bank_account_id,
            description=f"冲销收款 #{receipt.id}",
        )
        db.add(reversal_receipt)
        db.flush()

        # 如果有银行账户，生成反向银行流水并回滚余额
        if receipt.bank_account_id:
            bank_account = db.query(models.BankAccount).filter(
                models.BankAccount.id == receipt.bank_account_id,
                models.BankAccount.account_id == account_id,
            ).with_for_update().first()

            if bank_account:
                new_balance = _d(bank_account.balance) - original_amount

                reversal_tx = models.BankTransaction(
                    account_id=account_id,
                    bank_account_id=receipt.bank_account_id,
                    transaction_type="outflow",
                    amount=original_amount,
                    balance_after=new_balance,
                    transaction_date=datetime.now(),
                    description=f"冲销收款: {reversal_receipt.description}",
                    related_entity_type="receipt",
                    related_entity_id=reversal_receipt.id,
                )
                db.add(reversal_tx)
                db.flush()

                bank_account.balance = new_balance
                reversal_receipt.bank_transaction_id = reversal_tx.id

    # 重置销售单付款状态
    sale_order = db.query(models.SaleOrder).filter(
        models.SaleOrder.id == sale_order_id,
        models.SaleOrder.account_id == account_id,
    ).first()
    if sale_order:
        sale_order.payment_status = "unpaid"

    db.flush()


def reverse_payments(db: Session, account_id: int, purchase_order_id: int) -> None:
    """冲销采购单关联的所有付款记录。

    1. 查找该采购单的所有付款记录
    2. 为每笔付款生成反向付款（负金额）
    3. 生成反向银行流水（inflow）
    4. 回滚银行余额
    5. 重置采购单付款状态为 unpaid
    """
    payments = db.query(models.Payment).filter(
        models.Payment.account_id == account_id,
        models.Payment.related_entity_type == "purchase_order",
        models.Payment.related_entity_id == purchase_order_id,
    ).all()

    for payment in payments:
        # 跳过已冲销的（负金额）
        if _d(payment.amount) < 0:
            continue

        original_amount = _d(payment.amount)

        # 生成反向付款记录
        reversal_payment = models.Payment(
            account_id=account_id,
            payment_type=payment.payment_type,
            related_entity_type="purchase_order",
            related_entity_id=purchase_order_id,
            amount=-original_amount,
            payment_method=payment.payment_method,
            payment_date=datetime.now(),
            bank_account_id=payment.bank_account_id,
            description=f"冲销付款 #{payment.id}",
        )
        db.add(reversal_payment)
        db.flush()

        # 如果有银行账户，生成反向银行流水并回滚余额
        if payment.bank_account_id:
            bank_account = db.query(models.BankAccount).filter(
                models.BankAccount.id == payment.bank_account_id,
                models.BankAccount.account_id == account_id,
            ).with_for_update().first()

            if bank_account:
                new_balance = _d(bank_account.balance) + original_amount

                reversal_tx = models.BankTransaction(
                    account_id=account_id,
                    bank_account_id=payment.bank_account_id,
                    transaction_type="inflow",
                    amount=original_amount,
                    balance_after=new_balance,
                    transaction_date=datetime.now(),
                    description=f"冲销付款: {reversal_payment.description}",
                    related_entity_type="payment",
                    related_entity_id=reversal_payment.id,
                )
                db.add(reversal_tx)
                db.flush()

                bank_account.balance = new_balance
                reversal_payment.bank_transaction_id = reversal_tx.id

    # 重置采购单付款状态
    purchase_order = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.id == purchase_order_id,
        models.PurchaseOrder.account_id == account_id,
    ).first()
    if purchase_order:
        purchase_order.payment_status = "unpaid"

    db.flush()
