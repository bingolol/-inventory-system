"""Money 值对象单元测试"""
import pytest
from decimal import Decimal
from domain.money import Money


class TestMoneyConstruction:
    """Money 构造与基本属性"""

    def test_from_int(self):
        m = Money(100)
        assert m.amount == Decimal("100.00")

    def test_from_float(self):
        m = Money(99.9)
        assert m.amount == Decimal("99.90")

    def test_from_str(self):
        m = Money("123.456")
        assert m.amount == Decimal("123.46")  # 四舍五入

    def test_from_decimal(self):
        m = Money(Decimal("50.125"))
        assert m.amount == Decimal("50.13")

    def test_default_zero(self):
        m = Money()
        assert m.amount == Decimal("0.00")

    def test_zero_classmethod(self):
        m = Money.zero()
        assert m.amount == Decimal("0.00")


class TestMoneyArithmetic:
    """Money 算术运算"""

    def test_add(self):
        assert (Money("10.00") + Money("20.00")).amount == Decimal("30.00")

    def test_sub(self):
        assert (Money("50.00") - Money("20.00")).amount == Decimal("30.00")

    def test_mul_int(self):
        assert (Money("10.00") * 3).amount == Decimal("30.00")

    def test_rmul_int(self):
        assert (3 * Money("10.00")).amount == Decimal("30.00")

    def test_mul_float(self):
        assert (Money("100.00") * 0.5).amount == Decimal("50.00")

    def test_sum_empty(self):
        assert Money.sum([]) == Money.zero()

    def test_sum_multiple(self):
        result = Money.sum([Money("10.00"), Money("20.00"), Money("30.00")])
        assert result.amount == Decimal("60.00")


class TestMoneyComparison:
    """Money 比较运算"""

    def test_eq(self):
        assert Money("10.00") == Money(10)

    def test_lt(self):
        assert Money("5.00") < Money("10.00")

    def test_le(self):
        assert Money("5.00") <= Money("5.00")

    def test_gt(self):
        assert Money("10.00") > Money("5.00")

    def test_ge(self):
        assert Money("10.00") >= Money("10.00")

    def test_hash_equal(self):
        assert hash(Money("10.00")) == hash(Money(10))


class TestMoneyObjectProtocol:
    """Money 对象协议"""

    def test_repr(self):
        assert repr(Money("10.00")) == "Money('10.00')"

    def test_bool_nonzero(self):
        assert bool(Money("10.00")) is True

    def test_bool_zero(self):
        assert bool(Money.zero()) is False

    def test_to_float(self):
        assert Money("123.45").to_float() == 123.45