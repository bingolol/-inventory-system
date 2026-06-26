"""单元测试：采购单命令 (commands/purchase_commands.py)"""
import pytest
from decimal import Decimal
from commands.base import dispatch
from commands.purchase_commands import (
    CreatePurchaseOrder, CancelPurchaseOrder, DeletePurchaseOrder,
    UpdatePurchaseOrderItems, UpdatePurchaseOrderFields,
)
from errors import BusinessError
from models import Product, PurchaseOrder, PurchaseItem, StockMove
from helpers import get_account_id
from factories import make_product, make_supplier


def _make_supplier(db):
    from models import Supplier
    s = Supplier(account_id=1, name="测试供应商", contact="测试", phone="13800138000")
    db.add(s)
    db.flush()
    return s


class TestCreatePurchaseOrder:
    def test_empty_items(self, db):
        with pytest.raises(BusinessError, match="ORDER_EMPTY_ITEMS|采购单"):
            dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=[]), db)

    def test_duplicate_products(self, db):
        p = make_product(db, 1, track_inventory=False)
        items = [{"product_id": p.id, "quantity": 1, "unit_price": 10},
                 {"product_id": p.id, "quantity": 2, "unit_price": 10}]
        with pytest.raises(BusinessError, match="ORDER_DUPLICATE_PRODUCT|重复"):
            dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items), db)

    def test_product_not_found(self, db):
        items = [{"product_id": 99999, "quantity": 1, "unit_price": 10}]
        with pytest.raises(BusinessError, match="PRODUCT_NOT_FOUND|不存在"):
            dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items), db)

    def test_create_success(self, db):
        p = make_product(db, 1, track_inventory=True, purchase_price=Decimal("10"))
        s = _make_supplier(db)
        items = [{"product_id": p.id, "quantity": 5, "unit_price": 10}]
        order = dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items, supplier_id=s.id), db)
        assert order.total_price == Decimal("50.00")
        assert order.status == "completed"
        moves = db.query(StockMove).filter(StockMove.source_id == order.id).all()
        assert len(moves) > 0


class TestCancelPurchaseOrder:
    def test_cancel_not_found(self, db):
        with pytest.raises(BusinessError, match="ORDER_NOT_FOUND|不存在"):
            dispatch(CancelPurchaseOrder(account_id=1, operator="test", order_id=99999), db)

    def test_cancel_already_cancelled(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = _make_supplier(db)
        items = [{"product_id": p.id, "quantity": 1, "unit_price": 10}]
        order = dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items, supplier_id=s.id), db)
        dispatch(CancelPurchaseOrder(account_id=1, operator="test", order_id=order.id), db)
        with pytest.raises(BusinessError):
            dispatch(CancelPurchaseOrder(account_id=1, operator="test", order_id=order.id), db)

    def test_cancel_success(self, db):
        p = make_product(db, 1, track_inventory=False, purchase_price=Decimal("10"))
        s = _make_supplier(db)
        items = [{"product_id": p.id, "quantity": 3, "unit_price": 10}]
        order = dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items, supplier_id=s.id), db)
        result = dispatch(CancelPurchaseOrder(account_id=1, operator="test", order_id=order.id), db)
        assert result.status == "cancelled"


class TestDeletePurchaseOrder:
    def test_delete_not_found(self, db):
        with pytest.raises(BusinessError, match="ORDER_NOT_FOUND|不存在"):
            dispatch(DeletePurchaseOrder(account_id=1, operator="test", order_id=99999), db)

    def test_delete_success(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = _make_supplier(db)
        items = [{"product_id": p.id, "quantity": 1, "unit_price": 10}]
        order = dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items, supplier_id=s.id), db)
        result = dispatch(DeletePurchaseOrder(account_id=1, operator="test", order_id=order.id), db)
        assert result is True


class TestUpdatePurchaseOrderItems:
    def test_update_not_found(self, db):
        with pytest.raises(BusinessError, match="ORDER_NOT_FOUND|不存在"):
            dispatch(UpdatePurchaseOrderItems(account_id=1, operator="test", order_id=99999, items=[]), db)

    def test_update_duplicate_products(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = _make_supplier(db)
        items = [{"product_id": p.id, "quantity": 1, "unit_price": 10}]
        order = dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items, supplier_id=s.id), db)
        dupe_items = [{"product_id": p.id, "quantity": 1, "unit_price": 10},
                      {"product_id": p.id, "quantity": 2, "unit_price": 10}]
        with pytest.raises(BusinessError, match="ORDER_DUPLICATE_PRODUCT|重复"):
            dispatch(UpdatePurchaseOrderItems(account_id=1, operator="test", order_id=order.id, items=dupe_items), db)

    def test_update_to_empty_deletes_order(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = _make_supplier(db)
        items = [{"product_id": p.id, "quantity": 1, "unit_price": 10}]
        order = dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items, supplier_id=s.id), db)
        result = dispatch(UpdatePurchaseOrderItems(account_id=1, operator="test", order_id=order.id, items=[]), db)
        assert result is None
        deleted = db.query(PurchaseOrder).filter(PurchaseOrder.id == order.id).first()
        assert deleted is None

    def test_update_success(self, db):
        p1 = make_product(db, 1, track_inventory=False, purchase_price=Decimal("10"))
        p2 = make_product(db, 1, track_inventory=False, purchase_price=Decimal("20"))
        s = _make_supplier(db)
        items = [{"product_id": p1.id, "quantity": 2, "unit_price": 10}]
        order = dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items, supplier_id=s.id), db)
        new_items = [{"product_id": p2.id, "quantity": 3, "unit_price": 20}]
        result = dispatch(UpdatePurchaseOrderItems(account_id=1, operator="test", order_id=order.id, items=new_items), db)
        assert result is not None
        assert result.total_price == Decimal("60.00")
        assert len(result.items) == 1
        assert result.items[0].product_id == p2.id


class TestUpdatePurchaseOrderFields:
    def test_update_not_found(self, db):
        with pytest.raises(BusinessError, match="ORDER_NOT_FOUND|不存在"):
            dispatch(UpdatePurchaseOrderFields(account_id=1, operator="test", order_id=99999, notes="test"), db)

    def test_update_fields(self, db):
        p = make_product(db, 1, track_inventory=False)
        s = _make_supplier(db)
        items = [{"product_id": p.id, "quantity": 1, "unit_price": 10}]
        order = dispatch(CreatePurchaseOrder(account_id=1, operator="test", items=items, supplier_id=s.id), db)
        result = dispatch(UpdatePurchaseOrderFields(
            account_id=1, operator="test", order_id=order.id,
            notes="更新备注", payment_status="paid",
        ), db)
        assert result.notes == "更新备注"
        assert result.payment_status == "paid"
