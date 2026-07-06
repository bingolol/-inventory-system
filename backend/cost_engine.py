"""成本引擎 — 内部计算真相源 (L2)

从原始凭证 (StockMove, L2) 计算移动加权平均成本。
产出为 L2 内部计算真相源，供 Inventory (L4 缓存) 和 AccountMove COGS 消费。

追溯链: Invoice(L1) → StockMove(L2) → CostEngine(L2) → AccountMove COGS
"""
from decimal import Decimal


def weighted_average(total_qty: Decimal, total_value: Decimal, precision: int = 6) -> Decimal:
    """计算加权平均成本 = total_value / total_qty。

    入参:
        total_qty: 当前库存量
        total_value: 当前库存总价值
        precision: 小数精度 (默认 6 位)

    出参:
        加权平均单位成本。qty <= 0 时返回 Decimal("0")。

    调用方职责: 入参 total_qty/total_value 由调用方从 StockMove 序列 ∑ 计算，
    出参可对照 Inventory 缓存或 AccountMove COGS 做独立验证。
    """
    if total_qty <= 0:
        return Decimal("0")
    return (total_value / total_qty).quantize(Decimal("0." + "0" * (precision - 1) + "1"))
