"""TDD: 销售单创建 → 自动生成会计凭证 + 库存出库流水"""
import pytest
from datetime import datetime
from decimal import Decimal

from models import Account, Product, SaleOrder, SaleItem, Inventory
from models_finance import (
    Ledger, LedgerAccount, AccountMove, AccountMoveLine,
)
from commands.base import dispatch
from commands.sale_commands import CreateSaleOrder
from enums import OrderStatus


@pytest.fixture
def account(db):
    a = Account(id=1, name="测试", type="company", code="test",
                taxpayer_type="general")
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
        ("5001", "主营业务收入", "income"),
        ("5401", "主营业务成本", "expense"),
    ]
    for code, name, atype in seed:
        db.add(LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True))
    db.commit()


@pytest.fixture
def product(db):
    p = Product(id=1, account_id=1, name="测试商品", sku="T-001",
                purchase_price=Decimal("8"), sale_price=Decimal("20"),
                track_inventory=True)
    db.add(p)
    db.flush()
    inv = Inventory(account_id=1, product_id=1, quantity=100,
                    average_cost=Decimal("8.00"), total_value=Decimal("800.00"))
    db.add(inv)
    db.commit()
    return p


class TestSaleCreateTriggersAccounting:
    """创建销售单 → 会计凭证 + 库存出库"""

    def test_creates_revenue_and_cogs_journal(self, db, account, accts, product):
        cmd = CreateSaleOrder(
            account_id=1,
            operator="test",
            customer_id=1,
            items=[{
                "product_id": 1,
                "quantity": 10,
                "unit_price": "20.00",
                "tax_rate": "0.13",
            }],
        )
        order = dispatch(cmd, db)
        db.flush()

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
            codes[la.code] = {"debit": line.debit, "credit": line.credit}

        assert codes["1122"]["debit"] == Decimal("200.00"), "应收账款借: 200"
        assert codes["5001"]["credit"] == Decimal("176.99"), "主营业务收入贷(不含税): 176.99"
        assert codes["222101"]["credit"] == Decimal("23.01"), "销项税额贷: 23.01"
        assert codes["5401"]["debit"] == Decimal("80.00"), "主营业务成本借: 80"
        assert codes["1405"]["credit"] == Decimal("80.00"), "库存商品贷: 80"

        from models import StockMove
        sm = db.query(StockMove).filter(
            StockMove.source_type == "sale_order",
            StockMove.source_id == order.id,
        ).first()
        assert sm is not None, "销售出库应生成 StockMove"
        assert sm.quantity == -10
        assert sm.unit_cost == Decimal("8.00")
