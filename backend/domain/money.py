"""Money 值对象 —— 封装 Decimal，自动 quantize 到 2 位小数。"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Union

TWO_PLACES = Decimal("0.01")


class Money:
    """金额值对象，所有运算结果自动保留两位小数（四舍五入）。"""

    __slots__ = ("_amount",)

    def __init__(self, value: Union[int, float, str, Decimal] = 0) -> None:
        self._amount = Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    # ── 属性 ──────────────────────────────────────────────
    @property
    def amount(self) -> Decimal:
        """内部 Decimal 值（已 quantize）。"""
        return self._amount

    # ── 算术运算 ──────────────────────────────────────────
    def __add__(self, other: Money) -> Money:  # type: ignore[override]
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self._amount + other._amount)

    def __sub__(self, other: Money) -> Money:  # type: ignore[override]
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self._amount - other._amount)

    def __mul__(self, other: Union[int, float, str, Decimal]) -> Money:
        return Money(self._amount * Decimal(str(other)))

    def __rmul__(self, other: Union[int, float, str, Decimal]) -> Money:
        return self.__mul__(other)

    # ── 比较运算 ──────────────────────────────────────────
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount == other._amount

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount < other._amount

    def __le__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount <= other._amount

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount > other._amount

    def __ge__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount >= other._amount

    # ── 对象协议 ──────────────────────────────────────────
    def __hash__(self) -> int:
        return hash(self._amount)

    def __repr__(self) -> str:
        return f"Money('{self._amount}')"

    def __bool__(self) -> bool:
        return self._amount != 0

    # ── ORM 桥接 ─────────────────────────────────────────
    def to_float(self) -> float:
        """仅用于 ORM 写入数据库，业务层禁止使用。"""
        return float(self._amount)

    # ── 类方法 ────────────────────────────────────────────
    @classmethod
    def zero(cls) -> Money:
        return cls(0)

    @classmethod
    def sum(cls, items: Iterable[Money]) -> Money:
        """对 Money 可迭代对象求和，空迭代返回 zero()。"""
        total = cls.zero()
        for item in items:
            total = total + item
        return total