"""PurchaseOrderDomain 单元测试 — 状态机 + 不变量 + 业务规则"""
import pytest
from decimal import Decimal
from domain.purchase_order import PurchaseOrderDomain, PurchaseOrderLine
from domain.money import Money
from enums import OrderStatus, PaymentStatus, PaymentMethod


class TestPurchaseOrderStateMachine:
    """状态机转换测试"""

    def test_pending_to_completed(self):
        d = PurchaseOrderDomain(status=OrderStatus.PENDING)
        d.transition_to(OrderStatus.COMPLETED)
        assert d.status == OrderStatus.COMPLETED

    def test_pending_to_cancelled(self):
        d = PurchaseOrderDomain(status=OrderStatus.PENDING)
        d.transition_to(OrderStatus.CANCELLED)
        assert d.status == OrderStatus.CANCELLED

    def test_completed_to_cancelled(self):
        d = PurchaseOrderDomain(status=OrderStatus.COMPLETED)
        d.transition_to(OrderStatus.CANCELLED)
        assert d.status == OrderStatus.CANCELLED

    def test_cancelled_to_completed_restore(self):
        d = PurchaseOrderDomain(status=OrderStatus.CANCELLED)
        d.transition_to(OrderStatus.COMPLETED)
        assert d.status == OrderStatus.COMPLETED

    def test_illegal_transition_blocked(self):
        d = PurchaseOrderDomain(status=OrderStatus.COMPLETED)
        with pytest.raises(ValueError, match="非法状态转换"):
            d.transition_to(OrderStatus.COMPLETED)

    def test_can_transition_to(self):
        d = PurchaseOrderDomain(status=OrderStatus.PENDING)
        assert d.can_transition_to(OrderStatus.COMPLETED) is True
        assert d.can_transition_to(OrderStatus.PENDING) is False


class TestPurchaseOrderBusinessRules:
    """业务规则测试"""

    def test_is_completed(self):
        assert PurchaseOrderDomain(status=OrderStatus.COMPLETED).is_completed() is True
        assert PurchaseOrderDomain(status=OrderStatus.PENDING).is_completed() is False

    def test_is_cancelled(self):
        assert PurchaseOrderDomain(status=OrderStatus.CANCELLED).is_cancelled() is True
        assert PurchaseOrderDomain(status=OrderStatus.PENDING).is_cancelled() is False

    def test_affects_inventory_completed(self):
        assert PurchaseOrderDomain(status=OrderStatus.COMPLETED).affects_inventory() is True

    def test_affects_inventory_pending(self):
        assert PurchaseOrderDomain(status=OrderStatus.PENDING).affects_inventory() is False


class TestPurchaseOrderValidate:
    """不变量校验测试"""

    def test_completed_without_items_violation(self):
        """已完成采购单无商品明细 → 违规"""
        d = PurchaseOrderDomain(status=OrderStatus.COMPLETED, items=[])
        violations = d.validate()
        assert any("商品明细" in v for v in violations)

    def test_amount_mismatch_violation(self):
        """金额不一致 → 违规"""
        items = [PurchaseOrderLine(
            product_id=1, quantity=2,
            unit_price=Decimal("10.00"), tax_rate=Decimal("0.13"),
            total_price=Money("20.00"),
        )]
        d = PurchaseOrderDomain(
            status=OrderStatus.PENDING,
            total_price=Money("30.00"),
            items=items,
        )
        violations = d.validate()
        assert any("金额不一致" in v for v in violations)

    def test_amount_match_ok(self):
        """金额一致 → 合法"""
        items = [PurchaseOrderLine(
            product_id=1, quantity=2,
            unit_price=Decimal("10.00"), tax_rate=Decimal("0.13"),
            total_price=Money("20.00"),
        )]
        d = PurchaseOrderDomain(
            status=OrderStatus.PENDING,
            total_price=Money("20.00"),
            items=items,
        )
        assert d.validate() == []

    def test_item_quantity_zero_violation(self):
        """行项数量为0 → 违规"""
        items = [PurchaseOrderLine(
            product_id=1, quantity=0,
            unit_price=Decimal("10.00"), tax_rate=Decimal("0.13"),
            total_price=Money("0.00"),
        )]
        d = PurchaseOrderDomain(items=items)
        violations = d.validate()
        assert any("数量必须大于0" in v for v in violations)

    def test_invalid_payment_method_violation(self):
        """非法支付方式 → 违规"""
        d = PurchaseOrderDomain(payment_method="invalid_method")
        violations = d.validate()
        assert any("非法支付方式" in v for v in violations)

    def test_invalid_payment_status_violation(self):
        """非法付款状态 → 违规"""
        d = PurchaseOrderDomain(payment_status="unknown")
        violations = d.validate()
        assert any("非法付款状态" in v for v in violations)

    def test_valid_order_no_violations(self):
        """合法采购单 → 无违规"""
        items = [PurchaseOrderLine(
            product_id=1, quantity=5,
            unit_price=Decimal("10.00"), tax_rate=Decimal("0.13"),
            total_price=Money("50.00"),
        )]
        d = PurchaseOrderDomain(
            status=OrderStatus.PENDING,
            total_price=Money("50.00"),
            items=items,
        )
        assert d.validate() == []