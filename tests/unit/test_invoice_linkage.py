"""InvoiceLinkage 单元测试 — 单一真相源派生查询

测试 crud/invoice_linkage.py 的 4 个公共函数：
- has_invoice: 单条派生查询
- bulk_has_invoice: 批量派生查询
- list_invoices: 关联发票列表
- validate_link_target: 防孤儿校验
"""
import pytest
from decimal import Decimal
from datetime import datetime

import models
from crud.invoice_linkage import has_invoice, bulk_has_invoice, list_invoices, validate_link_target
from errors import BusinessError


@pytest.fixture
def seed_data(db):
    """创建测试基础数据：账本 + 销售单 + 采购单 + 费用"""
    account = models.Account(id=1, name="测试账本", type="company", code="test", taxpayer_type="small_scale")
    db.add(account)

    sale = models.SaleOrder(id=100, account_id=1, order_no="SO-001", total_price=Decimal("1000"))
    purchase = models.PurchaseOrder(id=200, account_id=1, order_no="PO-001", total_price=Decimal("500"))
    expense = models.Expense(id=300, account_id=1, category="房租", amount=Decimal("2000"), expense_date=datetime.now())
    db.add_all([sale, purchase, expense])
    db.flush()
    return {"sale_id": 100, "purchase_id": 200, "expense_id": 300}


class TestHasInvoice:
    def test_no_invoice_returns_false(self, db, seed_data):
        assert has_invoice(db, 1, "sale_order", 100) is False

    def test_with_invoice_returns_true(self, db, seed_data):
        inv = models.Invoice(
            account_id=1, invoice_no="INV-001", direction="out", invoice_type="ordinary",
            tax_rate=Decimal("0.13"), amount_without_tax=Decimal("1000"),
            tax_amount=Decimal("130"), amount_with_tax=Decimal("1130"),
            counterparty_name="客户A", issue_date=datetime.now(),
            related_order_type="sale_order", related_order_id=100,
        )
        db.add(inv)
        db.flush()
        assert has_invoice(db, 1, "sale_order", 100) is True

    def test_different_type_returns_false(self, db, seed_data):
        inv = models.Invoice(
            account_id=1, invoice_no="INV-002", direction="out", invoice_type="ordinary",
            tax_rate=Decimal("0.13"), amount_without_tax=Decimal("1000"),
            tax_amount=Decimal("130"), amount_with_tax=Decimal("1130"),
            counterparty_name="客户A", issue_date=datetime.now(),
            related_order_type="sale_order", related_order_id=100,
        )
        db.add(inv)
        db.flush()
        assert has_invoice(db, 1, "purchase_order", 100) is False

    def test_invalid_type_returns_false(self, db, seed_data):
        assert has_invoice(db, 1, "invalid_type", 100) is False

    def test_expense_has_invoice(self, db, seed_data):
        inv = models.Invoice(
            account_id=1, invoice_no="INV-003", direction="in", invoice_type="ordinary",
            tax_rate=Decimal("0.06"), amount_without_tax=Decimal("2000"),
            tax_amount=Decimal("120"), amount_with_tax=Decimal("2120"),
            counterparty_name="房东", issue_date=datetime.now(),
            related_order_type="expense", related_order_id=300,
        )
        db.add(inv)
        db.flush()
        assert has_invoice(db, 1, "expense", 300) is True


class TestBulkHasInvoice:
    def test_empty_ids_returns_empty(self, db, seed_data):
        assert bulk_has_invoice(db, 1, "sale_order", []) == set()

    def test_no_invoices_returns_empty(self, db, seed_data):
        assert bulk_has_invoice(db, 1, "sale_order", [100]) == set()

    def test_returns_correct_ids(self, db, seed_data):
        sale2 = models.SaleOrder(id=101, account_id=1, order_no="SO-002", total_price=Decimal("500"))
        db.add(sale2)
        db.flush()

        inv = models.Invoice(
            account_id=1, invoice_no="INV-004", direction="out", invoice_type="ordinary",
            tax_rate=Decimal("0.13"), amount_without_tax=Decimal("1000"),
            tax_amount=Decimal("130"), amount_with_tax=Decimal("1130"),
            counterparty_name="客户A", issue_date=datetime.now(),
            related_order_type="sale_order", related_order_id=100,
        )
        db.add(inv)
        db.flush()

        result = bulk_has_invoice(db, 1, "sale_order", [100, 101])
        assert result == {100}

    def test_invalid_type_returns_empty(self, db, seed_data):
        assert bulk_has_invoice(db, 1, "invalid_type", [100]) == set()


class TestListInvoices:
    def test_no_invoices_returns_empty(self, db, seed_data):
        assert list_invoices(db, 1, "sale_order", 100) == []

    def test_returns_related_invoices(self, db, seed_data):
        inv = models.Invoice(
            account_id=1, invoice_no="INV-005", direction="out", invoice_type="ordinary",
            tax_rate=Decimal("0.13"), amount_without_tax=Decimal("1000"),
            tax_amount=Decimal("130"), amount_with_tax=Decimal("1130"),
            counterparty_name="客户A", issue_date=datetime.now(),
            related_order_type="sale_order", related_order_id=100,
        )
        db.add(inv)
        db.flush()

        result = list_invoices(db, 1, "sale_order", 100)
        assert len(result) == 1
        assert result[0].invoice_no == "INV-005"


class TestValidateLinkTarget:
    def test_valid_target_passes(self, db, seed_data):
        validate_link_target(db, 1, "sale_order", 100)

    def test_nonexistent_target_raises(self, db, seed_data):
        with pytest.raises(BusinessError) as exc:
            validate_link_target(db, 1, "sale_order", 999)
        assert exc.value.code.name == "ORDER_NOT_FOUND"

    def test_invalid_type_raises(self, db, seed_data):
        with pytest.raises(BusinessError) as exc:
            validate_link_target(db, 1, "invalid_type", 100)
        assert exc.value.code.name == "VALIDATION_ERROR"

    def test_none_type_skips(self, db, seed_data):
        validate_link_target(db, 1, None, None)
        validate_link_target(db, 1, "", 100)
