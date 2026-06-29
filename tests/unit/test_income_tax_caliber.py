"""所得税引擎测试 — 税务口径（发票说话）

测试 routers/income_tax.py 和 crud/finance.py 的所得税计算：
- 收入取销项发票不含税金额
- 成本取 SaleItem.unit_cost（移动加权平均出库成本，单一真相源）
- 费用区分有票/无票
"""
import pytest
from decimal import Decimal
from datetime import datetime

import models
from crud.finance import generate_income_tax_prepayment


@pytest.fixture
def seed_data(db):
    """创建测试基础数据"""
    account = models.Account(
        id=1, name="测试账本", type="company", code="test",
        taxpayer_type="small_scale"
    )
    db.add(account)

    # 销售单
    sale = models.SaleOrder(
        id=100, account_id=1, order_no="SO-001",
        total_price=Decimal("11300"),  # 含税
        status="completed",
        sale_date=datetime(2026, 1, 15)
    )
    db.add(sale)

    # 销售明细
    sale_item = models.SaleItem(
        order_id=100, product_id=1, quantity=10,
        unit_price=Decimal("1130"), tax_rate=Decimal("0.13"),
        total_price=Decimal("11300")
    )
    db.add(sale_item)

    # 商品（进价用于计算成本）
    product = models.Product(
        id=1, account_id=1, name="测试商品",
        purchase_price=Decimal("500"), sale_price=Decimal("1000")
    )
    db.add(product)

    # 销项发票（收入取数来源）
    invoice_out = models.Invoice(
        account_id=1, invoice_no="INV-OUT-001", direction="out",
        invoice_type="ordinary", tax_rate=Decimal("0.13"),
        amount_without_tax=Decimal("10000"),  # 不含税
        tax_amount=Decimal("1300"),
        amount_with_tax=Decimal("11300"),
        counterparty_name="客户A", issue_date=datetime(2026, 1, 15),
        related_order_type="sale_order", related_order_id=100,
    )
    db.add(invoice_out)

    # 费用（有票）
    expense = models.Expense(
        id=200, account_id=1, category="房租",
        amount=Decimal("2000"), expense_date=datetime(2026, 2, 1)
    )
    db.add(expense)

    # 费用发票
    expense_invoice = models.Invoice(
        account_id=1, invoice_no="INV-EXP-001", direction="in",
        invoice_type="ordinary", tax_rate=Decimal("0.06"),
        amount_without_tax=Decimal("1886.79"),
        tax_amount=Decimal("113.21"),
        amount_with_tax=Decimal("2000"),
        counterparty_name="房东", issue_date=datetime(2026, 2, 1),
        related_order_type="expense", related_order_id=200,
    )
    db.add(expense_invoice)

    # 无票费用
    expense_no_invoice = models.Expense(
        id=201, account_id=1, category="办公用品",
        amount=Decimal("500"), expense_date=datetime(2026, 2, 15)
    )
    db.add(expense_no_invoice)

    db.flush()
    # 设置销售成本（实际由 InventoryEngine.outbound 写入，此处用进价模拟）
    sale_item.set_calculated_cost(product.purchase_price)
    db.flush()
    return {"account_id": 1, "sale_id": 100, "expense_id": 200}


class TestIncomeTaxCaliber:
    def test_tax_caliber_uses_invoices(self, db, seed_data):
        """税务口径：收入取发票不含税金额"""
        from routers.income_tax import get_income_tax_report
        import asyncio

        report = asyncio.run(get_income_tax_report(
            year=2026, quarter=None, db=db, account_id=1
        ))
        # 收入 = 销项发票不含税 = 10000
        assert report.total_revenue == Decimal("10000.00")
        # 成本 = 进项发票不含税 = 1886.79（费用发票 direction=in 被计入）
        assert report.total_cost == Decimal("1886.79")

    def test_prepayment_revenue_uses_invoices(self, db, seed_data):
        """预缴表：收入取销项发票不含税金额（取消经营口径后统一发票说话）"""
        result = generate_income_tax_prepayment(db, 1, 2026, 1)
        # 营业收入 = 销项发票不含税 = 10000
        assert result["operating_revenue"] == Decimal("10000.00")
        # 营业成本 = quantity * unit_cost = 10 * 500 = 5000
        assert result["operating_cost"] == Decimal("5000.00")

    def test_tax_caliber_expenses_only_invoiced(self, db, seed_data):
        """税务口径：费用仅有票费用可税前扣除"""
        from routers.income_tax import get_income_tax_report
        import asyncio

        report = asyncio.run(get_income_tax_report(
            year=2026, quarter=None, db=db, account_id=1
        ))
        # 有票费用 = 2000
        assert report.invoiced_expenses == Decimal("2000.00")
        # 无票费用 = 500
        assert report.non_invoice_expenses == Decimal("500.00")
        # operating_expenses = 有票费用 = 2000
        assert report.operating_expenses == Decimal("2000.00")

    def test_prepayment_all_expenses(self, db, seed_data):
        """预缴表：所有费用都计入"""
        result = generate_income_tax_prepayment(db, 1, 2026, 1)
        # 营业费用 = 所有费用 = 2000 + 500 = 2500
        assert result["operating_expenses"] == Decimal("2500.00")
