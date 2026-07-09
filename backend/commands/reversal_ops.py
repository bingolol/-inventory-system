"""冲销操作 — 取消/删除订单时反转收款/付款/银行流水

本模块提供模块级函数：
- reverse_receipts / reverse_payments — 批量冲销（被 order_lifecycle 调用）
- reverse_single_receipt / reverse_single_payment — 单笔冲销（被 cash_commands Handler 调用）
- reverse_bank_transaction — 单笔银行流水冲销（被 personal_advance_commands 调用）

设计原则：
- 生成反向分录（非删除），保留审计痕迹
- 银行余额同步回滚
- 重置关联订单的付款状态

call_reverse_journal 参数说明：
- 单笔红冲（call_reverse_journal=True）：同时冲红收款/付款凭证
- 批量红冲（call_reverse_journal=False）：跳过凭证冲红，由上层调用方统一处理
  例如 order_lifecycle 取消销售单时：先逐笔反向收款/银行流水，再集中调
  FinanceEngine.reverse_sale() 冲红销售凭证。收款凭证本身不在此流程中被冲红
  —— 这是已知不对称（与 BR-6 一致），批量场景的收款/付款凭证冲红在整体订单
  凭证冲红中间接体现，不单独逐笔 reverse_journal。
"""

from datetime import datetime
from typing import Optional

import models
from engine_bank import BankEngine
from enums import PaymentStatus, TransactionType
from finance_integration import reverse_journal
from operation_result import EntityType
from utils import _d


def reverse_single_receipt(db, account_id: int, receipt_id: int, call_reverse_journal: bool = True, date: Optional[datetime] = None):
    """红冲单笔收款：生成反向收款 + 反向银行流水 + 回滚余额 + 可选冲红凭证。

    幂等性：通过 description 匹配 "冲销收款 #{原id}" 判断是否已被红冲过。
    call_reverse_journal=False 用于批量场景（order_lifecycle 统一处理凭证冲红）。

    date: 冲销业务日期，默认取原始收款的 receipt_date_l1（BR-21：禁止用 datetime.now() 回退）。
    """

    receipt = db.query(models.Receipt).filter(
        models.Receipt.id == receipt_id,
        models.Receipt.account_id == account_id,
    ).first()
    if not receipt:
        return None

    original_amount = _d(receipt.amount_l1)
    if original_amount <= 0:
        return None

    existing_reversal = db.query(models.Receipt).filter(
        models.Receipt.account_id == account_id,
        models.Receipt.amount_l1 < 0,
        models.Receipt.description == f"冲销收款 #{receipt.id}",
    ).first()
    if existing_reversal:
        return existing_reversal

    reversal = models.Receipt(
        account_id=account_id,
        receipt_type=receipt.receipt_type,
        related_entity_type=receipt.related_entity_type,
        related_entity_id=receipt.related_entity_id,
        amount_l1=-original_amount,
        receipt_method=receipt.receipt_method,
        receipt_date_l1=date or receipt.receipt_date_l1,
        bank_account_id=receipt.bank_account_id,
        description=f"冲销收款 #{receipt.id}",
    )
    db.add(reversal)
    db.flush()

    if receipt.bank_account_id:
        reversal_tx = BankEngine(db, account_id).record_transaction(
            bank_account_id=receipt.bank_account_id,
            transaction_type=TransactionType.OUTFLOW,
            amount=original_amount,
            transaction_date=date or receipt.receipt_date_l1,
            description=f"冲销收款: {reversal.description}",
            related_entity_type=EntityType.RECEIPT,
            related_entity_id=reversal.id,
            allow_overdraft=True,
        )
        reversal.bank_transaction_id = reversal_tx.id

        if call_reverse_journal:
            reverse_journal(db, account_id, EntityType.RECEIPT, receipt.id)

    if receipt.related_entity_type == EntityType.SALE_ORDER:
        sale = db.query(models.SaleOrder).filter(
            models.SaleOrder.id == receipt.related_entity_id,
            models.SaleOrder.account_id == account_id,
        ).first()
        if sale:
            sale.payment_status = PaymentStatus.UNPAID

    db.flush()
    return reversal


def reverse_single_payment(db, account_id: int, payment_id: int, call_reverse_journal: bool = True, date: Optional[datetime] = None):
    """红冲单笔付款：生成反向付款 + 反向银行流水 + 回滚余额 + 可选冲红凭证。

    幂等性：通过 description 匹配 "冲销付款 #{原id}" 判断是否已被红冲过。
    call_reverse_journal=False 用于批量场景（order_lifecycle 统一处理凭证冲红）。

    date: 冲销业务日期，默认取原始付款的 payment_date_l1（BR-21：禁止用 datetime.now() 回退）。
    """

    payment = db.query(models.Payment).filter(
        models.Payment.id == payment_id,
        models.Payment.account_id == account_id,
    ).first()
    if not payment:
        return None

    original_amount = _d(payment.amount_l1)
    if original_amount <= 0:
        return None

    existing_reversal = db.query(models.Payment).filter(
        models.Payment.account_id == account_id,
        models.Payment.amount_l1 < 0,
        models.Payment.description == f"冲销付款 #{payment.id}",
    ).first()
    if existing_reversal:
        return existing_reversal

    reversal = models.Payment(
        account_id=account_id,
        payment_type=payment.payment_type,
        related_entity_type=payment.related_entity_type,
        related_entity_id=payment.related_entity_id,
        amount_l1=-original_amount,
        withholding_tax_amount_l1=-_d(payment.withholding_tax_amount_l1 or 0),
        payment_method=payment.payment_method,
        payment_date_l1=date or payment.payment_date_l1,
        bank_account_id=payment.bank_account_id,
        description=f"冲销付款 #{payment.id}",
    )
    db.add(reversal)
    db.flush()

    if payment.bank_account_id:
        reversal_tx = BankEngine(db, account_id).record_transaction(
            bank_account_id=payment.bank_account_id,
            transaction_type=TransactionType.INFLOW,
            amount=original_amount,
            transaction_date=date or payment.payment_date_l1,
            description=f"冲销付款: {reversal.description}",
            related_entity_type=EntityType.PAYMENT,
            related_entity_id=reversal.id,
            allow_overdraft=True,
        )
        reversal.bank_transaction_id = reversal_tx.id

        if call_reverse_journal:
            reverse_journal(db, account_id, EntityType.PAYMENT, payment.id)

    if payment.related_entity_type == EntityType.PURCHASE_ORDER:
        po = db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.id == payment.related_entity_id,
            models.PurchaseOrder.account_id == account_id,
        ).first()
        if po:
            po.payment_status = PaymentStatus.UNPAID

    db.flush()
    return reversal


def reverse_receipts(db, account_id: int, sale_order_id: int) -> None:
    """冲销销售单关联的所有收款记录，委托 reverse_single_receipt 逐笔处理。"""

    receipts = db.query(models.Receipt).filter(
        models.Receipt.account_id == account_id,
        models.Receipt.related_entity_type == EntityType.SALE_ORDER,
        models.Receipt.related_entity_id == sale_order_id,
    ).all()

    for receipt in receipts:
        if _d(receipt.amount_l1) < 0:
            continue
        reverse_single_receipt(db, account_id, receipt.id, call_reverse_journal=False)

    sale_order = db.query(models.SaleOrder).filter(
        models.SaleOrder.id == sale_order_id,
        models.SaleOrder.account_id == account_id,
    ).first()
    if sale_order:
        sale_order.payment_status = PaymentStatus.UNPAID

    db.flush()


def reverse_payments(db, account_id: int, purchase_order_id: int) -> None:
    """冲销采购单关联的所有付款记录，委托 reverse_single_payment 逐笔处理。"""

    payments = db.query(models.Payment).filter(
        models.Payment.account_id == account_id,
        models.Payment.related_entity_type == EntityType.PURCHASE_ORDER,
        models.Payment.related_entity_id == purchase_order_id,
    ).all()

    for payment in payments:
        if _d(payment.amount_l1) < 0:
            continue
        reverse_single_payment(db, account_id, payment.id, call_reverse_journal=False)

    purchase_order = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.id == purchase_order_id,
        models.PurchaseOrder.account_id == account_id,
    ).first()
    if purchase_order:
        purchase_order.payment_status = PaymentStatus.UNPAID

    db.flush()


def reverse_bank_transaction(db, account_id: int, tx_id: int, date: Optional[datetime] = None) -> Optional[models.BankTransaction]:
    """红冲单笔银行交易：reverse_journal 红冲原始凭证 → 反向流水

    date: 冲销业务日期，默认取原始流水的 transaction_date（BR-21：禁止用 datetime.now() 回退）。
    """

    tx = db.query(models.BankTransaction).filter(
        models.BankTransaction.id == tx_id,
        models.BankTransaction.account_id == account_id,
    ).first()
    if not tx:
        return None

    original_amount = _d(tx.amount_l2)
    if original_amount <= 0:
        return None

    existing = db.query(models.BankTransaction).filter(
        models.BankTransaction.related_entity_type == EntityType.REVERSAL,
        models.BankTransaction.related_entity_id == tx_id,
        models.BankTransaction.account_id == account_id,
    ).first()
    if existing:
        return existing

    bank = db.query(models.BankAccount).filter(
        models.BankAccount.id == tx.bank_account_id,
        models.BankAccount.account_id == account_id,
    ).first()
    if not bank:
        return None

    reverse_journal(db, account_id, EntityType.BANK_ENTRY, tx_id)

    reversal = BankEngine(db, account_id).record_transaction(
        bank_account_id=tx.bank_account_id,
        transaction_type=TransactionType.OUTFLOW if tx.transaction_type == TransactionType.INFLOW else TransactionType.INFLOW,
        amount=original_amount,
        transaction_date=date or tx.transaction_date_l1,
        description=f"冲销银行交易 #{tx.id}",
        flow_category=tx.flow_category_l2 or "operating",
        related_entity_type=EntityType.REVERSAL,
        related_entity_id=tx_id,
        allow_overdraft=True,
    )
    return reversal
