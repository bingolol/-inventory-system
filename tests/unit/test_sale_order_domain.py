"""SaleOrderDomain 单元测试 — 状态机 + 不变量 + 业务规则"""
import pytest
from decimal import Decimal
from domain.sale_order import SaleOrderDomain, SaleOrderLine, VALID_TRANSITIONS
from domain.money import Money
from enums import OrderStatus, OrderType


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
        with pytest.raises(ValueError, match="非法状态转换"):
            d.transition_to(OrderStatus.CANCELLED)

    def test_completed_to_completed_blocked(self):
        d = SaleOrderDomain(status=OrderStatus.COMPLETED)
        with pytest.raises(ValueError, match="非法状态转换"):
            d.transition_to(OrderStatus.COMPLETED)

    def test_pending_to_pending_blocked(self):
        d = SaleOrderDomain(status=OrderStatus.PENDING)
        with pytest.raises(ValueError, match="非法状态转换"):
            d.transition_to(OrderStatus.PENDING)

    def test_can_transition_to(self):
        d = SaleOrderDomain(status=OrderStatus.PENDING)
        assert d.can_transition_to(OrderStatus.COMPLETED) is True
        assert d.can_transition_to(OrderStatus.CANCELLED) is True
        assert d.can_transition_to(OrderStatus.PENDING) is False


class TestSaleOrderBusinessRules:
    """业务规则测试"""

    def test_is_retail(self):
        assert SaleOrderDomain(deduct_inventory=True).is_retail() is True
        assert SaleOrderDomain(deduct_inventory=False).is_retail() is False

    def test_is_project_sale_with_order_type(self):
        assert SaleOrderDomain(order_type=OrderType.PROJECT).is_project_sale() is True

    def test_is_project_sale_retail_type(self):
        assert SaleOrderDomain(order_type=OrderType.RETAIL).is_project_sale() is False

    def test_is_project_sale_no_project(self):
        assert SaleOrderDomain().is_project_sale() is False

    def test_should_deduct_inventory_retail(self):
        """零售单：deduct_inventory=True, 无项目 → 应扣库存"""
        d = SaleOrderDomain(deduct_inventory=True, project_id=None)
        assert d.should_deduct_inventory() is True

    def test_should_deduct_inventory_project_sale(self):
        """项目型销售单（完结生成）：order_type=PROJECT → 不扣库存"""
        d = SaleOrderDomain(deduct_inventory=False, order_type=OrderType.PROJECT)
        assert d.should_deduct_inventory() is False

    def test_should_deduct_inventory_no_deduct(self):
        """不扣库存单：deduct_inventory=False → 不扣"""
        d = SaleOrderDomain(deduct_inventory=False, project_id=None)
        assert d.should_deduct_inventory() is False

    def test_can_delete_completed(self):
        assert SaleOrderDomain(status=OrderStatus.COMPLETED).can_delete() is True

    def test_can_delete_cancelled(self):
        assert SaleOrderDomain(status=OrderStatus.CANCELLED).can_delete() is True

    def test_can_delete_pending_blocked(self):
        assert SaleOrderDomain(status=OrderStatus.PENDING).can_delete() is False


class TestSaleOrderValidate:
    """不变量校验测试"""

    def test_project_sale_with_deduct_violation(self):
        """项目型销售单 + 扣库存 → 违规"""
        d = SaleOrderDomain(deduct_inventory=True, project_id=1, order_type=OrderType.PROJECT)
        violations = d.validate()
        assert len(violations) > 0
        assert any("项目销售" in v for v in violations)

    def test_retail_with_deduct_ok(self):
        """零售 + 扣库存 → 合法"""
        d = SaleOrderDomain(deduct_inventory=True, project_id=None)
        assert d.validate() == []

    def test_item_quantity_zero_violation(self):
        """行项数量为0 → 违规"""
        items = [SaleOrderLine(
            product_id=1, quantity=0,
            unit_price=Money("10.00"), tax_rate=Decimal("0.13"),
            total_price=Money("0.00"),
        )]
        d = SaleOrderDomain(items=items)
        violations = d.validate()
        assert any("数量必须大于0" in v for v in violations)

    def test_item_negative_unit_price_violation(self):
        """行项单价为负 → 违规"""
        items = [SaleOrderLine(
            product_id=1, quantity=1,
            unit_price=Money("-5.00"), tax_rate=Decimal("0.13"),
            total_price=Money("-5.00"),
        )]
        d = SaleOrderDomain(items=items)
        violations = d.validate()
        assert any("单价不能为负" in v for v in violations)

    def test_item_negative_total_price_violation(self):
        """行项小计为负 → 违规"""
        items = [SaleOrderLine(
            product_id=1, quantity=1,
            unit_price=Money("5.00"), tax_rate=Decimal("0.13"),
            total_price=Money("-5.00"),
        )]
        d = SaleOrderDomain(items=items)
        violations = d.validate()
        assert any("小计不能为负" in v for v in violations)

    def test_valid_order_no_violations(self):
        """合法订单 → 无违规"""
        items = [SaleOrderLine(
            product_id=1, quantity=2,
            unit_price=Money("10.00"), tax_rate=Decimal("0.13"),
            total_price=Money("20.00"),
        )]
        d = SaleOrderDomain(deduct_inventory=True, project_id=None, items=items)
        assert d.validate() == []