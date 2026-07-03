"""TDD: 报表口径 — 一般纳税人收入用不含税，小规模用含税"""
import pytest
from datetime import datetime, date
from decimal import Decimal

from models import Account, SaleOrder, SaleItem, Product
from enums import OrderStatus, PaymentStatus
from crud.finance import generate_income_statement
from finance_integration import post_journal


@pytest.fixture
def general_account(db):
    a = Account(id=10, name="一般纳税人", type="company", code="general_test",
                taxpayer_type_l3="general")
    db.add(a)
    db.commit()
    return a


@pytest.fixture
def small_account(db):
    a = Account(id=11, name="小规模", type="company", code="small_test2",
                taxpayer_type_l3="small_scale")
    db.add(a)
    db.commit()
    return a


def _make_sale(db, account_id, total_price, items_data):
    """创建完成的销售单"""
    so = SaleOrder(
        account_id=account_id,
        order_no=f"T-{datetime.now().timestamp()}",
        total_price_l1=total_price,
        status=OrderStatus.COMPLETED,
        sale_date_l1=datetime(2026, 6, 1),
    )
    db.add(so)
    db.flush()
    for it in items_data:
        si = SaleItem(
            order_id=so.id,
            product_id=it["product_id"],
            quantity_l1=it["quantity"],
            unit_price_l1=it["unit_price"],
            tax_rate_l1=it["tax_rate"],
            total_price_l1=it["total_price"],
        )
        db.add(si)
    db.commit()
    return so


class TestIncomeStatementRevenueCaliber:
    """利润表收入口径：一般纳税人不含税，小规模含税"""

    def test_general_taxpayer_revenue_is_without_tax(self, db, general_account):
        """一般纳税人：收入=不含税金额"""
        prod = Product(id=100, account_id=10, name="商品G", sku="G-100",
                       purchase_price_l3=Decimal("10"), track_inventory_l3=False)
        db.add(prod)
        db.commit()

        so = _make_sale(db, 10, Decimal("226.00"), [
            {"product_id": 100, "quantity": 10, "unit_price": Decimal("20.00"),
             "tax_rate": Decimal("0.13"), "total_price": Decimal("226.00")},
        ])

        post_journal(db, 10, "sale_order", {
            "partner_id": 1,
            "partner_type": "customer",
            "total_with_tax": Decimal("226.00"),
            "total_without_tax": Decimal("200.00"),
            "tax_amount": Decimal("26.00"),
            "items": [{"product_id": 100, "quantity": 10, "unit_cost": Decimal("0")}],
            "date": datetime(2026, 6, 1),
            "source_model": "sale_order",
            "source_id": so.id,
        })
        db.commit()

        result = generate_income_statement(db, 10, "2026-01-01", "2026-12-31")
        revenue = result["revenue"]
        # 226 / 1.13 = 200.00
        assert revenue == Decimal("200.00"), f"一般纳税人收入应不含税: 预期200, 实际{revenue}"

    def test_small_scale_revenue_is_with_tax(self, db, small_account):
        """小规模：收入=含税金额"""
        prod = Product(id=101, account_id=11, name="商品S", sku="S-101",
                       purchase_price_l3=Decimal("10"), track_inventory_l3=False)
        db.add(prod)
        db.commit()

        so = _make_sale(db, 11, Decimal("200.00"), [
            {"product_id": 101, "quantity": 10, "unit_price": Decimal("20.00"),
             "tax_rate": Decimal("0.01"), "total_price": Decimal("200.00")},
        ])

        post_journal(db, 11, "sale_order", {
            "partner_id": 1,
            "partner_type": "customer",
            "total_with_tax": Decimal("200.00"),
            "total_without_tax": Decimal("200.00"),
            "tax_amount": Decimal("0.00"),
            "items": [{"product_id": 101, "quantity": 10, "unit_cost": Decimal("0")}],
            "date": datetime(2026, 6, 1),
            "source_model": "sale_order",
            "source_id": so.id,
            "account_config": {"taxpayer_type": "small_scale"},
        })
        db.commit()

        result = generate_income_statement(db, 11, "2026-01-01", "2026-12-31")
        revenue = result["revenue"]
        assert revenue == Decimal("200.00"), f"小规模收入应含税: 预期200, 实际{revenue}"
