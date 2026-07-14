"""TDD: 销售单创建 → 自动生成会计凭证 + 库存出库流水

架构改造后，销售单必须由销项发票驱动创建（CreateInvoice direction='out',
sale_order_action='auto_create'），禁止直接 CreateOrder。
"""
import pytest
from datetime import datetime
from decimal import Decimal

from models import Account, Product, SaleOrder, SaleItem, Inventory, StockMove
from models_finance import (
    Ledger, LedgerAccount, AccountMove, AccountMoveLine,
)
from commands.base import dispatch
from commands.orders import CreateInvoice
from enums import OrderStatus


@pytest.fixture
def account(db):
    a = Account(id=1, name="测试", type="company", code="test",
                taxpayer_type_l3="general")
    db.add(a)
    db.commit()
    return a


@pytest.fixture
def ledger(db, account):
    l = Ledger(id=1, name="测试", type="company", code="test")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def accts(db, ledger):
    seed = [
        ("1122", "应收账款", "asset"),
        ("1405", "库存商品", "asset"),
        ("222101", "应交增值税-销项税额", "liability"),
        ("6001", "主营业务收入", "income"),
        ("6401", "主营业务成本", "expense"),
    ]
    for code, name, atype in seed:
        db.add(LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True))
    db.commit()


@pytest.fixture
def product(db):
    p = Product(id=1, account_id=1, name="测试商品", sku="T-001",
                purchase_price_l3=Decimal("8"), sale_price_l3=Decimal("20"),
                track_inventory_l3=True)
    db.add(p)
    db.flush()
    inv = Inventory(account_id=1, product_id=1, quantity_l4=100,
                    average_cost_l4=Decimal("8.00"), total_value_l4=Decimal("800.00"))
    db.add(inv)
    db.flush()
    # AS-03: 库存真相源为 StockMove，需保留期初流水
    db.add(StockMove(
        account_id=1, product_id=1,
        quantity_l1=Decimal("100"), unit_cost_l2=Decimal("8.00"),
        total_cost_l2=Decimal("800.00"), source_type="inventory_adjustment",
        source_id=0, move_date_l1=datetime(2026, 1, 1),
    ))
    db.commit()
    return p


class TestSaleCreateTriggersAccounting:
    """创建销售单（发票驱动）→ 会计凭证 + 库存出库"""

    def test_creates_revenue_and_cogs_journal(self, db, account, accts, product):
        invoice = dispatch(CreateInvoice(
            account_id=1,
            operator="test",
            invoice_no="TEST-INV-SALE-001",
            direction="out",
            invoice_type="ordinary",
            tax_rate=Decimal("0.13"),
            amount_without_tax=Decimal("200.00"),
            tax_amount=Decimal("26.00"),
            amount_with_tax=Decimal("226.00"),
            counterparty_name="测试客户",
            issue_date="2026-06-01",
            sale_order_action="auto_create",
            items=[{
                "product_id": 1,
                "quantity": 10,
                "unit_price": "20.00",
                "tax_rate": "0.13",
            }],
        ), db)
        db.flush()
        order = db.query(SaleOrder).filter(
            SaleOrder.id == invoice.related_order_id
        ).first()

        moves = db.query(AccountMove).filter(
            AccountMove.source_model == "sale_order",
            AccountMove.source_id == order.id,
        ).all()
        assert len(moves) == 1, "创建销售单后应生成 1 条会计凭证"
        move = moves[0]

        lines = db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == move.id
        ).order_by(AccountMoveLine.id).all()
        assert len(lines) == 5, "一般纳税人销售应有 5 行分录（收入+税+成本+库存）"

        codes = {}
        for line in lines:
            la = db.query(LedgerAccount).filter(
                LedgerAccount.id == line.ledger_account_id
            ).first()
            codes[la.code] = {"debit": line.debit_l2, "credit": line.credit_l2}

        assert codes["1122"]["debit"] == Decimal("226.00"), "应收账款借(含税): 226"
        assert codes["6001"]["credit"] == Decimal("200.00"), "主营业务收入贷(不含税): 200"
        assert codes["222101"]["credit"] == Decimal("26.00"), "销项税额贷: 26"
        assert codes["6401"]["debit"] == Decimal("80.00"), "主营业务成本借: 80"
        assert codes["1405"]["credit"] == Decimal("80.00"), "库存商品贷: 80"

        from models import StockMove
        sm = db.query(StockMove).filter(
            StockMove.source_type == "sale_order",
            StockMove.source_id == order.id,
        ).first()
        assert sm is not None, "销售出库应生成 StockMove"
        assert sm.quantity_l1 == -10
        assert sm.unit_cost_l2 == Decimal("8.00")
