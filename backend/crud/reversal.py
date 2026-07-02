"""冲销模块 — 取消/删除订单时反转收款/付款/银行流水

设计原则：
- 生成反向分录（非删除），保留审计痕迹
- 银行余额同步回滚
- 重置关联订单的付款状态
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

import models
from utils import _d


def reverse_receipts(db: Session, account_id: int, sale_order_id: int) -> None:
    """冲销销售单关联的所有收款记录。

    1. 查找该销售单的所有正向收款记录
    2. 为每笔收款生成反向收款（负金额）
    3. 生成反向银行流水（outflow）
    4. 回滚银行余额
    5. 重置销售单付款状态为 unpaid

    幂等性：通过 description 前缀 "冲销收款 #{原receipt.id}" 判断原 Receipt
    是否已被红冲过，避免重复冲红（与 reverse_bank_transaction 的幂等设计一致）。
    场景：先调用 /api/receipts/{id}/reverse 红冲单笔收款，
    后续 /api/sales/{id}/cancel 取消整单时不应再次冲红同一笔收款。
    """
    receipts = db.query(models.Receipt).filter(
        models.Receipt.account_id == account_id,
        models.Receipt.related_entity_type == "sale_order",
        models.Receipt.related_entity_id == sale_order_id,
    ).all()

    for receipt in receipts:
        # 跳过已冲销的反向收款（负金额）
<<<<<<< Updated upstream
        if _d(receipt.amount) < 0:
=======
        if _d(receipt.amount_l1) < 0:
>>>>>>> Stashed changes
            continue

        # 幂等检查：原 Receipt 是否已被红冲过（description 匹配 "冲销收款 #{原id}"）
        existing_reversal = db.query(models.Receipt).filter(
            models.Receipt.account_id == account_id,
            models.Receipt.related_entity_type == "sale_order",
            models.Receipt.related_entity_id == sale_order_id,
<<<<<<< Updated upstream
            models.Receipt.amount < 0,
=======
            models.Receipt.amount_l1 < 0,
>>>>>>> Stashed changes
            models.Receipt.description == f"冲销收款 #{receipt.id}",
        ).first()
        if existing_reversal:
            continue

<<<<<<< Updated upstream
        original_amount = _d(receipt.amount)
=======
        original_amount = _d(receipt.amount_l1)
>>>>>>> Stashed changes

        # 生成反向收款记录
        reversal_receipt = models.Receipt(
            account_id=account_id,
            receipt_type=receipt.receipt_type,
            related_entity_type="sale_order",
            related_entity_id=sale_order_id,
            amount_l1=-original_amount,
            receipt_method=receipt.receipt_method,
            receipt_date_l1=datetime.now(),
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
                new_balance = _d(bank_account.balance_l4) - original_amount

                reversal_tx = models.BankTransaction(
                    account_id=account_id,
                    bank_account_id=receipt.bank_account_id,
                    transaction_type="outflow",
                    amount_l2=original_amount,
                    balance_after_l4=new_balance,
                    transaction_date_l1=datetime.now(),
                    description=f"冲销收款: {reversal_receipt.description}",
                    related_entity_type="receipt",
                    related_entity_id=reversal_receipt.id,
                )
                db.add(reversal_tx)
                db.flush()

                bank_account.balance_l4 = new_balance
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

    1. 查找该采购单的所有正向付款记录
    2. 为每笔付款生成反向付款（负金额）
    3. 生成反向银行流水（inflow）
    4. 回滚银行余额
    5. 重置采购单付款状态为 unpaid

    幂等性：通过 description 匹配 "冲销付款 #{原payment.id}" 判断原 Payment
    是否已被红冲过，避免重复冲红（与 reverse_receipts 一致）。
    """
    payments = db.query(models.Payment).filter(
        models.Payment.account_id == account_id,
        models.Payment.related_entity_type == "purchase_order",
        models.Payment.related_entity_id == purchase_order_id,
    ).all()

    for payment in payments:
        # 跳过已冲销的反向付款（负金额）
<<<<<<< Updated upstream
        if _d(payment.amount) < 0:
=======
        if _d(payment.amount_l1) < 0:
>>>>>>> Stashed changes
            continue

        # 幂等检查：原 Payment 是否已被红冲过（description 匹配 "冲销付款 #{原id}"）
        existing_reversal = db.query(models.Payment).filter(
            models.Payment.account_id == account_id,
            models.Payment.related_entity_type == "purchase_order",
            models.Payment.related_entity_id == purchase_order_id,
<<<<<<< Updated upstream
            models.Payment.amount < 0,
=======
            models.Payment.amount_l1 < 0,
>>>>>>> Stashed changes
            models.Payment.description == f"冲销付款 #{payment.id}",
        ).first()
        if existing_reversal:
            continue

<<<<<<< Updated upstream
        original_amount = _d(payment.amount)
=======
        original_amount = _d(payment.amount_l1)
>>>>>>> Stashed changes

        # 生成反向付款记录
        reversal_payment = models.Payment(
            account_id=account_id,
            payment_type=payment.payment_type,
            related_entity_type="purchase_order",
            related_entity_id=purchase_order_id,
            amount_l1=-original_amount,
            payment_method=payment.payment_method,
            payment_date_l1=datetime.now(),
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
                new_balance = _d(bank_account.balance_l4) + original_amount

                reversal_tx = models.BankTransaction(
                    account_id=account_id,
                    bank_account_id=payment.bank_account_id,
                    transaction_type="inflow",
                    amount_l2=original_amount,
                    balance_after_l4=new_balance,
                    transaction_date_l1=datetime.now(),
                    description=f"冲销付款: {reversal_payment.description}",
                    related_entity_type="payment",
                    related_entity_id=reversal_payment.id,
                )
                db.add(reversal_tx)
                db.flush()

                bank_account.balance_l4 = new_balance
                reversal_payment.bank_transaction_id = reversal_tx.id

    # 重置采购单付款状态
    purchase_order = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.id == purchase_order_id,
        models.PurchaseOrder.account_id == account_id,
    ).first()
    if purchase_order:
        purchase_order.payment_status = "unpaid"

    db.flush()


def reverse_single_receipt(db: Session, account_id: int, receipt_id: int) -> models.Receipt:
    """红冲单笔收款：生成反向收款 + 反向银行流水 + 回滚余额

    幂等性：通过 description 匹配 "冲销收款 #{原receipt.id}" 判断原 Receipt
    是否已被红冲过，避免重复冲红（与 reverse_receipts 一致）。
    场景：先调用 /api/sales/{id}/cancel 取消整单（级联红冲收款），
    后续 /api/receipts/{id}/reverse 红冲同一笔收款时不应再次冲红。
    """

    receipt = db.query(models.Receipt).filter(
        models.Receipt.id == receipt_id,
        models.Receipt.account_id == account_id,
    ).first()
    if not receipt:
        return None

    original_amount = _d(receipt.amount_l1)
    if original_amount <= 0:
        return None  # already reversed

    # 幂等检查：原 Receipt 是否已被红冲过（description 匹配 "冲销收款 #{原id}"）
    existing_reversal = db.query(models.Receipt).filter(
        models.Receipt.account_id == account_id,
<<<<<<< Updated upstream
        models.Receipt.amount < 0,
=======
        models.Receipt.amount_l1 < 0,
>>>>>>> Stashed changes
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
        receipt_date_l1=datetime.now(),
        bank_account_id=receipt.bank_account_id,
        description=f"冲销收款 #{receipt.id}",
    )
    db.add(reversal)
    db.flush()

    if receipt.bank_account_id:
        bank = db.query(models.BankAccount).filter(
            models.BankAccount.id == receipt.bank_account_id,
            models.BankAccount.account_id == account_id,
        ).with_for_update().first()
        if bank:
            new_balance = _d(bank.balance_l4) - original_amount
            reversal_tx = models.BankTransaction(
                account_id=account_id,
                bank_account_id=receipt.bank_account_id,
                transaction_type="outflow",
                amount_l2=original_amount,
                balance_after_l4=new_balance,
                transaction_date_l1=datetime.now(),
                description=f"冲销收款: {reversal.description}",
                related_entity_type="receipt",
                related_entity_id=reversal.id,
            )
            db.add(reversal_tx)
            db.flush()
            bank.balance_l4 = new_balance
            reversal.bank_transaction_id = reversal_tx.id

        # 生成冲销凭证
        from finance_integration import reverse_journal
        reverse_journal(db, account_id, "receipt", receipt.id)

    # 重置关联订单付款状态
    if receipt.related_entity_type == "sale_order":
        sale = db.query(models.SaleOrder).filter(
            models.SaleOrder.id == receipt.related_entity_id,
            models.SaleOrder.account_id == account_id,
        ).first()
        if sale:
            sale.payment_status = "unpaid"

    db.flush()
    return reversal


def reverse_bank_transaction(db: Session, account_id: int, tx_id: int) -> Optional[models.BankTransaction]:
    """红冲单笔银行交易：reverse_journal 红冲原始凭证 → 反向流水

    凭证锚点设计：BankTransaction.id 即原始凭证的 source_id，
    reverse_journal(source_model="bank_entry", source_id=tx_id) 借贷互换红冲原始凭证。
    旧数据（source_id 为纳秒时间戳）找不到原始凭证时，reverse_journal 返回 None，
    不影响银行余额回滚，只是总账中凭证不会被红冲（合理降级）。
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

    # 幂等：已冲销过则直接返回旧记录
    existing = db.query(models.BankTransaction).filter(
        models.BankTransaction.related_entity_type == "reversal",
        models.BankTransaction.related_entity_id == tx_id,
        models.BankTransaction.account_id == account_id,
    ).first()
    if existing:
        return existing

    bank = db.query(models.BankAccount).filter(
        models.BankAccount.id == tx.bank_account_id,
        models.BankAccount.account_id == account_id,
    ).with_for_update().first()
    if not bank:
        return None

    # 红冲原始凭证：借贷互换（reverse_journal 自带幂等，已红冲过返回 None）
    from finance_integration import reverse_journal
    reverse_journal(db, account_id, "bank_entry", tx_id)

    # 反向流水
    reversal = models.BankTransaction(
        account_id=account_id,
        bank_account_id=tx.bank_account_id,
        transaction_type="outflow" if tx.transaction_type == "inflow" else "inflow",
        amount_l2=original_amount,
        balance_after_l4=_d(bank.balance_l4) + (original_amount if tx.transaction_type == "outflow" else -original_amount),
        transaction_date_l1=datetime.now(),
        description=f"冲销银行交易 #{tx.id}",
        flow_category_l2=tx.flow_category_l2,
        related_entity_type="reversal",
        related_entity_id=tx_id,
    )
    db.add(reversal)
    bank.balance_l4 = reversal.balance_after_l4
    db.flush()
    return reversal


def reverse_single_payment(db: Session, account_id: int, payment_id: int) -> models.Payment:
    """红冲单笔付款：生成反向付款 + 反向银行流水 + 回滚余额

    幂等性：通过 description 匹配 "冲销付款 #{原payment.id}" 判断原 Payment
    是否已被红冲过，避免重复冲红（与 reverse_single_receipt 一致）。
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

    # 幂等检查：原 Payment 是否已被红冲过（description 匹配 "冲销付款 #{原id}"）
    existing_reversal = db.query(models.Payment).filter(
        models.Payment.account_id == account_id,
<<<<<<< Updated upstream
        models.Payment.amount < 0,
=======
        models.Payment.amount_l1 < 0,
>>>>>>> Stashed changes
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
        payment_date_l1=datetime.now(),
        bank_account_id=payment.bank_account_id,
        description=f"冲销付款 #{payment.id}",
    )
    db.add(reversal)
    db.flush()

    if payment.bank_account_id:
        bank = db.query(models.BankAccount).filter(
            models.BankAccount.id == payment.bank_account_id,
            models.BankAccount.account_id == account_id,
        ).with_for_update().first()
        if bank:
            new_balance = _d(bank.balance_l4) + original_amount
            reversal_tx = models.BankTransaction(
                account_id=account_id,
                bank_account_id=payment.bank_account_id,
                transaction_type="inflow",
                amount_l2=original_amount,
                balance_after_l4=new_balance,
                transaction_date_l1=datetime.now(),
                description=f"冲销付款: {reversal.description}",
                related_entity_type="payment",
                related_entity_id=reversal.id,
            )
            db.add(reversal_tx)
            db.flush()
            bank.balance_l4 = new_balance
            reversal.bank_transaction_id = reversal_tx.id

        from finance_integration import reverse_journal
        reverse_journal(db, account_id, "payment", payment.id)

    if payment.related_entity_type == "purchase_order":
        po = db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.id == payment.related_entity_id,
            models.PurchaseOrder.account_id == account_id,
        ).first()
        if po:
            po.payment_status = "unpaid"

    db.flush()
    return reversal
