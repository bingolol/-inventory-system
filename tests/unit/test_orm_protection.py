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
        db.add(models.Product(id=1, account_id=1, name="p1", purchase_price_l3=Decimal("10")))
        db.flush()

        move = models.StockMove(
            account_id=1, product_id=1, quantity_l1=10,
            unit_cost_l2=Decimal("5"), total_cost_l2=Decimal("50"),
            source_type="purchase_order", source_id=100,
        )
        db.add(move)
        db.flush()

        move.quantity_l1 = 20
        with pytest.raises(BusinessError):
            db.flush()


class TestBeforeUpdateFixedAssetDepreciation:
    def test_cannot_update_depreciation(self, db):
        db.add(models.Account(id=1, name="test", type="company", code="t1"))
        db.add(models.FixedAsset(
            id=1, account_id=1, name="asset1", original_value_l1=Decimal("10000"),
            salvage_rate_l3=Decimal("0.05"), useful_life_l3=60,
            start_date_l1=date(2025, 1, 1),
        ))
        db.flush()

        dep = models.FixedAssetDepreciation(
            asset_id=1, account_id=1, period="2025-01",
            amount_l2=Decimal("158.33"),
        )
        db.add(dep)
        db.flush()

        dep.amount_l2 = Decimal("200")
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
            date_l1=date.today(), ref="test",
        )
        db.add(move)
        db.flush()

        move.ref = "changed"
        with pytest.raises(BusinessError):
            db.flush()


class TestPropertySaleItemUnitCost:
    def test_direct_assign_does_not_affect_column(self, db):
        item = models.SaleItem(
            order_id=0, product_id=0, quantity_l1=1,
            unit_price_l1=Decimal("10"), tax_rate_l1=Decimal("0.13"),
            total_price_l1=Decimal("11.30"),
        )
        item.unit_cost = Decimal("100")
        assert item.unit_cost_l2 is None

    def test_can_set_via_method(self, db):
        item = models.SaleItem(
            order_id=0, product_id=0, quantity_l1=1,
            unit_price_l1=Decimal("10"), tax_rate_l1=Decimal("0.13"),
            total_price_l1=Decimal("11.30"),
        )
        item.set_calculated_cost(Decimal("100"))
        assert item.unit_cost_l2 == Decimal("100")
