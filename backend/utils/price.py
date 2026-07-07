"""统一价税分离 + ROUND_HALF_UP 舍入工具

所有涉及含税/不含税转换的业务代码必须通过此模块，
消除历史上多套公式和不同 rounding 策略的不一致。
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


def split(amount_with_tax, tax_rate):
    """含税金额 → (不含税金额, 税额)

    Formula A：不含税 = 含税 / (1+税率), 税额 = 含税 - 不含税
    适用：发票开票、采购结算、费用报销等"先有含税总额"的场景。
    """
    a = _d(amount_with_tax)
    r = _d(tax_rate)
    without_tax = (a / (Decimal("1") + r)).quantize(Q2, rounding=ROUND_HALF_UP)
    tax = (a - without_tax).quantize(Q2, rounding=ROUND_HALF_UP)
    return without_tax, tax


def combine(amount_without_tax, tax_rate):
    """不含税金额 → (税额, 含税金额)

    Formula B：税额 = 不含税 × 税率, 含税 = 不含税 + 税额
    适用：销售出库、收入确认等"先有不含税单价"的场景。
    """
    b = _d(amount_without_tax)
    r = _d(tax_rate)
    tax = (b * r).quantize(Q2, rounding=ROUND_HALF_UP)
    with_tax = (b + tax).quantize(Q2, rounding=ROUND_HALF_UP)
    return tax, with_tax


def without_tax_from(amount_with_tax: Decimal, tax_amount: Decimal) -> Decimal:
    """含税金额 - 税额 → 不含税金额（BR-27 合规）"""
    a = _d(amount_with_tax)
    t = _d(tax_amount)
    return (a - t).quantize(Q2, rounding=ROUND_HALF_UP)


def with_tax_from(amount_without_tax: Decimal, tax_amount: Decimal) -> Decimal:
    """不含税金额 + 税额 → 含税金额（BR-27 合规）"""
    b = _d(amount_without_tax)
    t = _d(tax_amount)
    return (b + t).quantize(Q2, rounding=ROUND_HALF_UP)
