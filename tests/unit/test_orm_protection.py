"""ORM 防护测试 — before_update 事件 + @property 只读"""
import pytest
from decimal import Decimal
from datetime import datetime, date

import models
from models_finance import AccountMove, AccountMoveLine, Ledger
from errors import BusinessError


class TestBeforeUpdateStockMove:
    def test_cannot_update_stock_move(self, db):
        db.add(models.Account(id=1, name="test", type="company", code="t1"))
        db.add(models.Product(id=1, account_id=1, name="p1", purchase_price=Decimal("10")))
        db.flush()

        move = models.StockMove(
            account_id=1, product_id=1, quantity=10,
            unit_cost=Decimal("5"), total_cost=Decimal("50"),
            source_type="purchase_order", source_id=100,
        )
        db.add(move)
        db.flush()

        move.quantity = 20
        with pytest.raises(BusinessError):
            db.flush()


class TestBeforeUpdateFixedAssetDepreciation:
    def test_cannot_update_depreciation(self, db):
        db.add(models.Account(id=1, name="test", type="company", code="t1"))
        db.add(models.FixedAsset(
            id=1, account_id=1, name="asset1", original_value=Decimal("10000"),
            salvage_rate=Decimal("0.05"), useful_life=60,
            start_date=date(2025, 1, 1),
        ))
        db.flush()

        dep = models.FixedAssetDepreciation(
            asset_id=1, account_id=1, period="2025-01",
            amount=Decimal("158.33"),
        )
        db.add(dep)
        db.flush()

        dep.amount = Decimal("200")
        with pytest.raises(BusinessError):
            db.flush()


class TestBeforeUpdateAccountMove:
    def test_cannot_update_account_move(self, db):
        from database import Base
        Base.metadata.create_all(bind=db.bind)

        db.add(models.Account(id=1, name="test", type="company", code="t1"))
        db.flush()

        ledger = Ledger(id=1, name="test", type="company", code="t1")
        db.add(ledger)
        db.flush()

        move = AccountMove(
            id=1, ledger_id=1, move_type="manual",
            date=date.today(), ref="test",
        )
        db.add(move)
        db.flush()

        move.ref = "changed"
        with pytest.raises(BusinessError):
            db.flush()


class TestPropertySaleItemUnitCost:
    def test_cannot_direct_assign_unit_cost(self, db):
        item = models.SaleItem(
            order_id=0, product_id=0, quantity=1,
            unit_price=Decimal("10"), tax_rate=Decimal("0.13"),
            total_price=Decimal("11.30"),
        )
        with pytest.raises(AttributeError):
            item.unit_cost = Decimal("100")

    def test_can_set_via_method(self, db):
        item = models.SaleItem(
            order_id=0, product_id=0, quantity=1,
            unit_price=Decimal("10"), tax_rate=Decimal("0.13"),
            total_price=Decimal("11.30"),
        )
        item.set_calculated_cost(Decimal("100"))
        assert item.unit_cost == Decimal("100")
