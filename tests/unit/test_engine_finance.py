"""FinanceEngine 单元测试 — 验证会计凭证正确生成"""
import pytest
from datetime import datetime
from decimal import Decimal
from models import Account, Product, PurchaseOrder, PurchaseItem, SaleOrder, SaleItem
from models_finance import (
    Ledger, LedgerAccount, AccountMove, AccountMoveLine,
)
from engine_finance import FinanceEngine
from enums import OrderStatus, PaymentMethod


@pytest.fixture
def account(db):
    a = Account(id=1, name="测试", type="company", code="test",
                taxpayer_type="general")
    db.add(a)
    db.commit()
    return a


@pytest.fixture
def ledger(db, account):
    l = Ledger(id=1, name="测试账本", type="company", code="test")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def accts(db, ledger):
    """创建科目"""
    seed = [
        ("1002", "银行存款", "asset"),
        ("1122", "应收账款", "asset"),
        ("1405", "库存商品", "asset"),
        ("2202", "应付账款", "liability"),
        ("222101", "应交增值税-销项税额", "liability"),
        ("222102", "应交增值税-进项税额", "liability"),
        ("6001", "主营业务收入", "income"),
        ("6401", "主营业务成本", "expense"),
    ]
    result = {}
    for code, name, atype in seed:
        a = LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True)
        db.add(a)
        db.flush()
        result[code] = a
    db.commit()
    return result


@pytest.fixture
def product(db):
    p = Product(id=1, account_id=1, name="测试商品", sku="T-001",
                purchase_price=Decimal("10"), sale_price=Decimal("20"))
    db.add(p)
    db.commit()
    return p


class TestRecordPurchase:
    def test_creates_purchase_journal(self, db, account, accts, product):
        po = PurchaseOrder(
            account_id=1, order_no="PO-TEST-001", supplier_id=1,
            total_price=Decimal("113.00"),
            status=OrderStatus.COMPLETED,
            payment_method=PaymentMethod.COMPANY,
            purchase_date=datetime.now(),
        )
        db.add(po)
        db.flush()
        pi = PurchaseItem(
            order_id=po.id, product_id=product.id,
            quantity=10, unit_price=Decimal("10.00"),
            tax_rate=Decimal("0.13"), total_price=Decimal("113.00"),
        )
        db.add(pi)
        db.commit()

        fin = FinanceEngine(db, account_id=1)
        fin.record_purchase(po)
        db.flush()

        moves = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == po.id,
        ).all()
        assert len(moves) == 1
        move = moves[0]

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 3

        codes = {}
        for line in lines:
            la = db.query(LedgerAccount).filter(
                LedgerAccount.id == line.ledger_account_id
            ).first()
            codes[la.code] = {"debit": line.debit, "credit": line.credit}

        assert codes["1405"]["debit"] == Decimal("100.00")
        assert codes["222102"]["debit"] == Decimal("13.00")
        assert codes["2202"]["credit"] == Decimal("113.00")

    def test_idempotent_duplicate_call(self, db, account, accts, product):
        po = PurchaseOrder(
            account_id=1, order_no="PO-TEST-002", supplier_id=1,
            total_price=Decimal("56.50"),
            status=OrderStatus.COMPLETED,
            payment_method=PaymentMethod.COMPANY,
            purchase_date=datetime.now(),
        )
        db.add(po)
        db.flush()
        pi = PurchaseItem(
            order_id=po.id, product_id=product.id,
            quantity=5, unit_price=Decimal("10.00"),
            tax_rate=Decimal("0.13"), total_price=Decimal("56.50"),
        )
        db.add(pi)
        db.commit()

        fin = FinanceEngine(db, account_id=1)
        fin.record_purchase(po)
        db.flush()
        fin.record_purchase(po)
        db.flush()

        count = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == po.id,
        ).count()
        assert count == 1


class TestRecordSale:
    def test_creates_revenue_and_cogs_journal(self, db, account, accts, product):
        so = SaleOrder(
            account_id=1, order_no="SO-TEST-001", customer_id=1,
            total_price=Decimal("200.00"),
            status=OrderStatus.COMPLETED,
            sale_date=datetime.now(),
        )
        db.add(so)
        db.flush()
        si = SaleItem(
            order_id=so.id, product_id=product.id,
            quantity=10, unit_price=Decimal("20.00"),
            tax_rate=Decimal("0.13"), total_price=Decimal("200.00"),
        )
        si.set_calculated_cost(Decimal("10.00"))
        db.add(si)
        db.commit()

        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()

        moves = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.source_id == so.id,
        ).all()
        assert len(moves) == 1
        move = moves[0]

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()

        codes = {}
        for line in lines:
            la = db.query(LedgerAccount).filter(
                LedgerAccount.id == line.ledger_account_id
            ).first()
            codes[la.code] = {"debit": line.debit, "credit": line.credit}

        assert codes["1122"]["debit"] == Decimal("226.00")
        assert codes["6001"]["credit"] == Decimal("200.00")
        assert codes["222101"]["credit"] == Decimal("26.00")
        assert codes["6401"]["debit"] == Decimal("100.00")
        assert codes["1405"]["credit"] == Decimal("100.00")


class TestReverse:
    def test_reverse_purchase(self, db, account, accts, product):
        po = PurchaseOrder(
            account_id=1, order_no="PO-TEST-003", supplier_id=1,
            total_price=Decimal("113.00"),
            status=OrderStatus.COMPLETED,
            payment_method=PaymentMethod.COMPANY,
            purchase_date=datetime.now(),
        )
        db.add(po)
        db.flush()
        pi = PurchaseItem(
            order_id=po.id, product_id=product.id,
            quantity=10, unit_price=Decimal("10.00"),
            tax_rate=Decimal("0.13"), total_price=Decimal("113.00"),
        )
        db.add(pi)
        db.commit()

        fin = FinanceEngine(db, account_id=1)
        fin.record_purchase(po)
        db.flush()
        fin.reverse_purchase(po.id)
        db.flush()

        reversals = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == po.id,
            AccountMove.is_reversal == True,
        ).all()
        assert len(reversals) == 1

        original = db.query(AccountMove).filter(
            AccountMove.source_model == "purchase_order",
            AccountMove.source_id == po.id,
            AccountMove.is_reversal == False,
        ).first()

        rev_lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == reversals[0].id
        ).order_by(AccountMoveLine.id).all()
        orig_lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == original.id
        ).order_by(AccountMoveLine.id).all()

        for rl, ol in zip(rev_lines, orig_lines):
            assert rl.debit == ol.credit
            assert rl.credit == ol.debit

    def test_reverse_sale(self, db, account, accts, product):
        so = SaleOrder(
            account_id=1, order_no="SO-TEST-002", customer_id=1,
            total_price=Decimal("200.00"),
            status=OrderStatus.COMPLETED,
            sale_date=datetime.now(),
        )
        db.add(so)
        db.flush()
        si = SaleItem(
            order_id=so.id, product_id=product.id,
            quantity=10, unit_price=Decimal("20.00"),
            tax_rate=Decimal("0.13"), total_price=Decimal("200.00"),
        )
        si.set_calculated_cost(Decimal("10.00"))
        db.add(si)
        db.commit()

        fin = FinanceEngine(db, account_id=1)
        fin.record_sale(so)
        db.flush()
        fin.reverse_sale(so.id)
        db.flush()

        reversals = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.source_id == so.id,
            AccountMove.is_reversal == True,
        ).all()
        assert len(reversals) == 1
