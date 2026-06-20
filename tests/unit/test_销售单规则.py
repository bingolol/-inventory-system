"""SaleOrderDomain 单元测试 — 状态机 + 不变量 + 业务规则"""
import pytest
from decimal import Decimal
from domain.sale_order import SaleOrderDomain, SaleOrderLine, VALID_TRANSITIONS
from domain.money import Money
from enums import OrderStatus, OrderType
from errors import BusinessError


class TestSaleOrderStateMachine:
    """状态机转换测试"""

    def test_pending_to_completed(self):
        d = SaleOrderDomain(status=OrderStatus.PENDING)
        d.transition_to(OrderStatus.COMPLETED)
        assert d.status == OrderStatus.COMPLETED

    def test_pending_to_cancelled(self):
        d = SaleOrderDomain(status=OrderStatus.PENDING)
        d.transition_to(OrderStatus.CANCELLED)
        assert d.status == OrderStatus.CANCELLED

    def test_completed_to_cancelled(self):
        d = SaleOrderDomain(status=OrderStatus.COMPLETED)
        d.transition_to(OrderStatus.CANCELLED)
        assert d.status == OrderStatus.CANCELLED

    def test_cancelled_to_completed_restore(self):
        d = SaleOrderDomain(status=OrderStatus.CANCELLED)
        d.transition_to(OrderStatus.COMPLETED)
        assert d.status == OrderStatus.COMPLETED

    def test_cancelled_to_cancelled_blocked(self):
        d = SaleOrderDomain(status=OrderStatus.CANCELLED)
        with pytest.raises(BusinessError):
            d.transition_to(OrderStatus.CANCELLED)

    def test_completed_to_completed_blocked(self):
        d = SaleOrderDomain(status=OrderStatus.COMPLETED)
        with pytest.raises(BusinessError):
            d.transition_to(OrderStatus.COMPLETED)

    def test_pending_to_pending_blocked(self):
        d = SaleOrderDomain(status=OrderStatus.PENDING)
        with pytest.raises(BusinessError):
            d.transition_to(OrderStatus.PENDING)

    def test_can_transition_to(self):
        d = SaleOrderDomain(status=OrderStatus.PENDING)
        assert d.can_transition_to(OrderStatus.COMPLETED) is True
        assert d.can_transition_to(OrderStatus.CANCELLED) is True
        assert d.can_transition_to(OrderStatus.PENDING) is False


class TestSaleOrderBusinessRules:
    """业务规则测试"""

    def test_can_delete_completed(self):
        assert SaleOrderDomain(status=OrderStatus.COMPLETED).can_delete() is True

    def test_can_delete_cancelled(self):
        assert SaleOrderDomain(status=OrderStatus.CANCELLED).can_delete() is True

    def test_can_delete_pending_blocked(self):
        assert SaleOrderDomain(status=OrderStatus.PENDING).can_delete() is False


class TestSaleOrderValidate:
    """不变量校验测试"""

    def test_item_quantity_zero_violation(self):
        """行项数量为0 → 违规"""
        items = [SaleOrderLine(
            product_id=1, quantity=0,
            unit_price=Decimal("10.00"), tax_rate=Decimal("0.13"),
            total_price=Money("0.00"),
        )]
        d = SaleOrderDomain(items=items)
        violations = d.validate()
        assert any("数量必须>0" in v for v in violations)

    def test_item_negative_unit_price_violation(self):
        """行项单价为负 → 违规"""
        items = [SaleOrderLine(
            product_id=1, quantity=1,
            unit_price=Decimal("-5.00"), tax_rate=Decimal("0.13"),
            total_price=Money("-5.00"),
        )]
        d = SaleOrderDomain(items=items)
        violations = d.validate()
        assert any("单价不能为负" in v for v in violations)

    def test_item_negative_total_price_violation(self):
        """行项小计为负 → 违规"""
        items = [SaleOrderLine(
            product_id=1, quantity=1,
            unit_price=Decimal("5.00"), tax_rate=Decimal("0.13"),
            total_price=Money("-5.00"),
        )]
        d = SaleOrderDomain(items=items)
        violations = d.validate()
        assert any("小计不能为负" in v for v in violations)

    def test_valid_order_no_violations(self):
        """合法订单 → 无违规"""
        items = [SaleOrderLine(
            product_id=1, quantity=2,
            unit_price=Decimal("10.00"), tax_rate=Decimal("0.13"),
            total_price=Money("20.00"),
        )]
        d = SaleOrderDomain(items=items)
        assert d.validate() == []
