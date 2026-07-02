"""冲销逻辑测试 — 取消/删除订单时反转收款/付款/银行流水

测试 crud/reversal.py 的冲销函数：
- reverse_receipts: 冲销收款记录 + 银行流水 + 余额
- reverse_payments: 冲销付款记录 + 银行流水 + 余额
"""
import pytest
from decimal import Decimal
from datetime import datetime

import models
from crud.reversal import reverse_receipts, reverse_payments


@pytest.fixture
def seed_sale_with_receipt(db):
    """创建已收款的销售单"""
    account = models.Account(id=1, name="测试账本", type="company", code="test", taxpayer_type_l3="small_scale")
    db.add(account)

    bank_account = models.BankAccount(id=1, account_id=1, bank_name="测试银行", account_number="123456", balance_l4=Decimal("11300"))
    db.add(bank_account)

    sale = models.SaleOrder(id=100, account_id=1, order_no="SO-001", total_price_l1=Decimal("11300"), payment_status="paid", status="completed", sale_date_l1=datetime(2026, 1, 15))
    db.add(sale)

    receipt = models.Receipt(id=1, account_id=1, receipt_type="sale", related_entity_type="sale_order", related_entity_id=100, amount_l1=Decimal("11300"), receipt_method="company", receipt_date_l1=datetime(2026, 1, 16), bank_account_id=1, bank_transaction_id=1)
    db.add(receipt)

    bank_tx = models.BankTransaction(id=1, account_id=1, bank_account_id=1, transaction_type="inflow", amount_l2=Decimal("11300"), balance_after_l4=Decimal("11300"), transaction_date_l1=datetime(2026, 1, 16), description="收款", related_entity_type="receipt", related_entity_id=1)
    db.add(bank_tx)

    db.flush()
    return {"account_id": 1, "sale_id": 100, "receipt_id": 1, "bank_account_id": 1, "bank_tx_id": 1}


@pytest.fixture
def seed_purchase_with_payment(db):
    """创建已付款的采购单"""
    account = models.Account(id=1, name="测试账本", type="company", code="test", taxpayer_type_l3="small_scale")
    db.add(account)

    bank_account = models.BankAccount(id=1, account_id=1, bank_name="测试银行", account_number="123456", balance_l4=Decimal("0"))
    db.add(bank_account)

    purchase = models.PurchaseOrder(id=200, account_id=1, order_no="PO-001", total_price_l1=Decimal("5650"), payment_status="paid", status="completed", purchase_date_l1=datetime(2026, 2, 1))
    db.add(purchase)

    payment = models.Payment(id=1, account_id=1, payment_type="purchase", related_entity_type="purchase_order", related_entity_id=200, amount_l1=Decimal("5650"), payment_method="company", payment_date_l1=datetime(2026, 2, 2), bank_account_id=1, bank_transaction_id=2)
    db.add(payment)

    bank_tx = models.BankTransaction(id=2, account_id=1, bank_account_id=1, transaction_type="outflow", amount_l2=Decimal("5650"), balance_after_l4=Decimal("0"), transaction_date_l1=datetime(2026, 2, 2), description="付款", related_entity_type="payment", related_entity_id=1)
    db.add(bank_tx)

    db.flush()
    return {"account_id": 1, "purchase_id": 200, "payment_id": 1, "bank_account_id": 1, "bank_tx_id": 2}


class TestReverseReceipts:
    def test_creates_reversal_receipt(self, db, seed_sale_with_receipt):
        """冲销收款：生成反向收款记录"""
        reverse_receipts(db, 1, 100)
        receipts = db.query(models.Receipt).filter(
            models.Receipt.account_id == 1,
            models.Receipt.related_entity_type == "sale_order",
            models.Receipt.related_entity_id == 100,
        ).all()
        # 原收款 + 冲销 = 2 条
        assert len(receipts) == 2
        reversal = [r for r in receipts if r.amount_l1 < 0]
        assert len(reversal) == 1
        assert reversal[0].amount_l1 == Decimal("-11300")

    def test_creates_reversal_bank_transaction(self, db, seed_sale_with_receipt):
        """冲销收款：生成反向银行流水"""
        reverse_receipts(db, 1, 100)
        txs = db.query(models.BankTransaction).filter(
            models.BankTransaction.account_id == 1,
            models.BankTransaction.related_entity_type == "receipt",
        ).all()
        # 原流水 + 冲销 = 2 条
        assert len(txs) == 2
        reversal = [t for t in txs if t.transaction_type == "outflow"]
        assert len(reversal) == 1
        assert reversal[0].amount_l2 == Decimal("11300")

    def test_reverses_bank_balance(self, db, seed_sale_with_receipt):
        """冲销收款：银行余额回滚"""
        reverse_receipts(db, 1, 100)
        bank_account = db.query(models.BankAccount).get(1)
        assert bank_account.balance_l4 == Decimal("0")

    def test_resets_payment_status(self, db, seed_sale_with_receipt):
        """冲销收款：重置销售单付款状态"""
        reverse_receipts(db, 1, 100)
        sale = db.query(models.SaleOrder).get(100)
        assert sale.payment_status == "unpaid"


class TestReversePayments:
    def test_creates_reversal_payment(self, db, seed_purchase_with_payment):
        """冲销付款：生成反向付款记录"""
        reverse_payments(db, 1, 200)
        payments = db.query(models.Payment).filter(
            models.Payment.account_id == 1,
            models.Payment.related_entity_type == "purchase_order",
            models.Payment.related_entity_id == 200,
        ).all()
        # 原付款 + 冲销 = 2 条
        assert len(payments) == 2
        reversal = [p for p in payments if p.amount_l1 < 0]
        assert len(reversal) == 1
        assert reversal[0].amount_l1 == Decimal("-5650")

    def test_creates_reversal_bank_transaction(self, db, seed_purchase_with_payment):
        """冲销付款：生成反向银行流水"""
        reverse_payments(db, 1, 200)
        txs = db.query(models.BankTransaction).filter(
            models.BankTransaction.account_id == 1,
            models.BankTransaction.related_entity_type == "payment",
        ).all()
        # 原流水 + 冲销 = 2 条
        assert len(txs) == 2
        reversal = [t for t in txs if t.transaction_type == "inflow"]
        assert len(reversal) == 1
        assert reversal[0].amount_l2 == Decimal("5650")

    def test_reverses_bank_balance(self, db, seed_purchase_with_payment):
        """冲销付款：银行余额回滚"""
        reverse_payments(db, 1, 200)
        bank_account = db.query(models.BankAccount).get(1)
        assert bank_account.balance_l4 == Decimal("5650")

    def test_resets_payment_status(self, db, seed_purchase_with_payment):
        """冲销付款：重置采购单付款状态"""
        reverse_payments(db, 1, 200)
        purchase = db.query(models.PurchaseOrder).get(200)
        assert purchase.payment_status == "unpaid"
