"""核心机制测试 — ORM 转换 + 事件注册"""
import pytest
from decimal import Decimal
from domain.inventory import InventoryDomain
from domain.sale_order import SaleOrderDomain, SaleOrderLine
from domain.purchase_order import PurchaseOrderDomain, PurchaseOrderLine
from domain.money import Money
from enums import OrderStatus, PaymentMethod, PaymentStatus, InvoiceStatus

import handlers  # 触发 handler 注册
from events import get_handlers


# ========== ORM 转换测试 ==========

class FakeInventoryORM:
    id = 1
    account_id = 2
    product_id = 3
    quantity = 50


class FakeSaleItemORM:
    def __init__(self, product_id=1, quantity=2, unit_price=10, tax_rate=0.13, total_price=20):
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.tax_rate = tax_rate
        self.total_price = total_price


class FakeSaleOrderORM:
    def __init__(self):
        self.id = 10
        self.order_no = "SO-001"
        self.customer_id = 5
        self.total_price = 20
        self.has_invoice = False
        self.payment_status = "unpaid"
        self.status = "completed"
        self.notes = ""
        self.items = [FakeSaleItemORM()]


class FakePurchaseItemORM:
    def __init__(self, product_id=1, quantity=5, unit_price=10, tax_rate=0.13, total_price=50):
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.tax_rate = tax_rate
        self.total_price = total_price


class FakePurchaseOrderORM:
    def __init__(self):
        self.id = 20
        self.account_id = 1
        self.order_no = "PO-001"
        self.supplier_id = 3
        self.status = "pending"
        self.payment_status = "unpaid"
        self.payment_method = "company"
        self.has_invoice = False
        self.purchase_date = None
        self.notes = ""
        self.total_price = 50
        self.items = [FakePurchaseItemORM()]


class TestInventoryFromOrm:
    def test_from_orm(self):
        inv = InventoryDomain.from_orm(FakeInventoryORM())
        assert inv.id == 1
        assert inv.account_id == 2
        assert inv.product_id == 3
        assert inv.quantity == 50


class TestSaleOrderFromOrm:
    def test_from_orm(self):
        order = SaleOrderDomain.from_orm(FakeSaleOrderORM())
        assert order.id == 10
        assert order.order_no == "SO-001"
        assert order.customer_id == 5
        assert order.status == "completed"
        assert len(order.items) == 1
        assert order.items[0].product_id == 1


class TestPurchaseOrderFromOrm:
    def test_from_orm(self):
        order = PurchaseOrderDomain.from_orm(FakePurchaseOrderORM())
        assert order.id == 20
        assert order.account_id == 1
        assert order.supplier_id == 3
        assert order.status == "pending"
        assert len(order.items) == 1


# ========== 事件注册测试 ==========

class TestHandlerRegistration:
    """验证关键事件至少有一个 handler"""

    @pytest.mark.parametrize("event_name", [
        "sale_order.created",
        "sale_order.cancelled",
        "sale_order.deleted",
    ])
    def test_event_has_handlers(self, event_name):
        hs = get_handlers(event_name)
        assert len(hs) > 0, f"{event_name} should have at least one handler"

    def test_handler_has_priority(self):
        """每个 handler 应有 priority 属性"""
        for evt in ["sale_order.created", "sale_order.cancelled"]:
            for h in get_handlers(evt):
                assert hasattr(h, "priority"), f"Handler {h.name} missing priority"
