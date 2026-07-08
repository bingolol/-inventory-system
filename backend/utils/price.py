"""统一价税分离 + ROUND_HALF_UP 舍入工具

所有涉及含税/不含税转换的业务代码必须通过此模块。
"""
from decimal import Decimal, ROUND_HALF_UP
from utils import Q2


def _d(v):
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def quantize(x):
    """统一精确保存：ROUND_HALF_UP"""
    return _d(x).quantize(Q2, rounding=ROUND_HALF_UP)


def without_tax_from(amount_with_tax: Decimal, tax_amount: Decimal) -> Decimal:
    """含税金额 - 税额 → 不含税金额（BR-27 合规）"""
    a = _d(amount_with_tax)
    t = _d(tax_amount)
    return (a - t).quantize(Q2, rounding=ROUND_HALF_UP)
