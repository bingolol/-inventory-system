import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from domain.inventory import InventoryDomain
from errors import BusinessError


def test_sale_deduct_prevents_negative_inventory():
    """销售扣减不应允许库存变为负数"""
    inv = InventoryDomain(account_id=1, product_id=5, quantity=5)
    with pytest.raises(BusinessError, match="库存不足"):
        inv.deduct(10)


def test_deduct_rejects_negative_amount():
    """deduct 不应接受负数"""
    inv = InventoryDomain(account_id=1, product_id=1, quantity=10)
    with pytest.raises(BusinessError, match="不能为负"):
        inv.deduct(-5)


def test_deduct_success():
    """正常扣减应成功"""
    inv = InventoryDomain(account_id=1, product_id=1, quantity=10)
    inv.deduct(3)
    assert inv.quantity == 7


def test_deduct_boundary_exact_amount():
    """扣减量恰好等于库存应成功"""
    inv = InventoryDomain(account_id=1, product_id=1, quantity=5)
    inv.deduct(5)
    assert inv.quantity == 0


def test_is_available_delegates_to_can_deduct():
    """is_available 委托给 can_deduct"""
    inv = InventoryDomain(account_id=1, product_id=1, quantity=5)
    assert inv.is_available(5) == inv.can_deduct(5)
    assert inv.is_available(6) == inv.can_deduct(6)
