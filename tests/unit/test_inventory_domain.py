"""InventoryDomain 单元测试 — 库存校验 + 不变量"""
import pytest
from domain.inventory import InventoryDomain


class TestInventoryBusinessRules:
    """业务规则测试"""

    def test_is_available_enough(self):
        inv = InventoryDomain(account_id=1, product_id=5, quantity=100)
        assert inv.is_available(50) is True

    def test_is_available_insufficient(self):
        inv = InventoryDomain(account_id=1, product_id=5, quantity=10)
        assert inv.is_available(15) is False

    def test_is_available_exact(self):
        inv = InventoryDomain(account_id=1, product_id=5, quantity=10)
        assert inv.is_available(10) is True

    def test_can_deduct_ok(self):
        inv = InventoryDomain(account_id=1, product_id=5, quantity=100)
        assert inv.can_deduct(50) is True

    def test_can_deduct_exceed(self):
        inv = InventoryDomain(account_id=1, product_id=5, quantity=10)
        assert inv.can_deduct(15) is False

    def test_can_deduct_exact(self):
        inv = InventoryDomain(account_id=1, product_id=5, quantity=10)
        assert inv.can_deduct(10) is True


class TestInventoryValidate:
    """不变量校验测试"""

    def test_valid_inventory(self):
        inv = InventoryDomain(account_id=1, product_id=5, quantity=100)
        assert inv.validate() == []

    def test_negative_quantity_violation(self):
        inv = InventoryDomain(account_id=1, product_id=5, quantity=-5)
        violations = inv.validate()
        assert any("不能为负" in v for v in violations)

    def test_zero_account_id_violation(self):
        inv = InventoryDomain(account_id=0, product_id=5, quantity=10)
        violations = inv.validate()
        assert any("account_id" in v for v in violations)

    def test_zero_product_id_violation(self):
        inv = InventoryDomain(account_id=1, product_id=0, quantity=10)
        violations = inv.validate()
        assert any("product_id" in v for v in violations)

    def test_zero_quantity_ok(self):
        """数量为0是合法的（库存清零但非负）"""
        inv = InventoryDomain(account_id=1, product_id=5, quantity=0)
        assert inv.validate() == []