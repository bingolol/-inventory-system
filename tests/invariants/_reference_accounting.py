"""独立参考计算器 — 消除"量体裁衣"的独立真相源

核心问题（阶段1 Mutation Test 发现）：
- 测试期望值不能从系统自己的计算逻辑里推出来，否则 mutation 改了系统代码，
  期望值也跟着变，测试永远通过（M5 mutation 无效就是这个原因）。
- 测试期望值也不能硬编码数字，否则无法验证计算逻辑的正确性（只是验证形状）。

解决：本模块独立实现会计计算，不 import 任何 engine_*/accounting_engine 模块。
每个函数基于会计准则（非系统代码）实现，作为系统计算的独立参照。

实现依据：
- 《小企业会计准则》
- 财税〔2008〕151号、2023年第12号
- memory 硬约束（project_memory.md）
"""
from decimal import Decimal, ROUND_HALF_UP

Q2 = Decimal("0.01")


def _q2(value: Decimal) -> Decimal:
    """保留两位小数，四舍五入"""
    return Decimal(str(value)).quantize(Q2, rounding=ROUND_HALF_UP)


# ──────────────────────────────────────────────────────────────
# 采购入库
# ──────────────────────────────────────────────────────────────

def purchase_inventory_cost(unit_price, qty, enable_vat_deduction: bool) -> Decimal:
    """采购入库库存成本（进 1405 的金额）

    一般纳税人（enable_vat_deduction=True）：
        不含税金额进成本 = qty × unit_price（unit_price 视为不含税）
    小规模纳税人（enable_vat_deduction=False）：
        价税合计进成本 = qty × unit_price（unit_price 视为含税，全额进成本）

    依据：memory 硬约束 — 小规模 unit_price 视为含税价全额进成本，不分离税额
    """
    return _q2(Decimal(str(qty)) * Decimal(str(unit_price)))


def purchase_input_tax(unit_price, qty, tax_rate, enable_vat_deduction: bool) -> Decimal:
    """采购进项税额（进 222102 的金额，仅一般纳税人）

    一般纳税人：tax = qty × unit_price × tax_rate
    小规模纳税人：0（不抵扣进项税）
    """
    if not enable_vat_deduction:
        return Decimal("0")
    rate = Decimal(str(tax_rate)) if tax_rate else Decimal("0")
    return _q2(Decimal(str(qty)) * Decimal(str(unit_price)) * rate)


def purchase_payable(unit_price, qty, tax_rate, enable_vat_deduction: bool) -> Decimal:
    """采购应付账款（进 2202 的金额，价税合计）

    一般纳税人：qty × unit_price × (1 + tax_rate)
    小规模纳税人：qty × unit_price（unit_price 已含税）
    """
    base = Decimal(str(qty)) * Decimal(str(unit_price))
    if enable_vat_deduction:
        rate = Decimal(str(tax_rate)) if tax_rate else Decimal("0")
        return _q2(base * (1 + rate))
    return _q2(base)


# ──────────────────────────────────────────────────────────────
# 销售出库
# ──────────────────────────────────────────────────────────────

def sale_cogs(sale_item_unit_cost, qty) -> Decimal:
    """销售 COGS = SaleItem.unit_cost × qty（锁定成本）

    依据（memory 硬约束 + audit-truth-source skill）：
    COGS 必须用 SaleItem.unit_cost（销售时锁定的加权平均成本），
    不能用 Product.purchase_price 或当前 Inventory.average_cost
    """
    return _q2(Decimal(str(qty)) * Decimal(str(sale_item_unit_cost)))


def sale_revenue(unit_price, qty) -> Decimal:
    """销售收入（进 6001 的不含税金额）= qty × unit_price"""
    return _q2(Decimal(str(qty)) * Decimal(str(unit_price)))


def sale_output_tax(unit_price, qty, tax_rate, general_taxpayer: bool = True,
                    is_special_invoice: bool = False,
                    quarterly_revenue=0) -> Decimal:
    """销售销项税额

    Args:
        general_taxpayer: 纳税人开关。True=一般纳税人（开），False=小规模纳税人（闭）
        tax_rate: 销项税税率（来自上传发票，反映税务局现行政策，不硬编码）
        is_special_invoice: 是否专用发票（仅小规模纳税人使用）
            - 小规模专用发票：按 tax_rate 征收，不享受免税
            - 小规模普通发票：季度销售额≤30万免税，>30万按 tax_rate
        quarterly_revenue: 本笔前的季度累计不含税销售额，用于判定免税

    依据（memory 硬约束 + 财税2023年第12号 + 单一真相源原则§8）：
    - 一般纳税人：qty × unit_price × tax_rate
    - 小规模纳税人：专票必征；普票看季度累计（≤30万免税，>30万按 tax_rate 征收）
    - 税率来自上传发票，系统不硬编码征收率
    """
    rate = Decimal(str(tax_rate)) if tax_rate else Decimal("0")

    if general_taxpayer:
        return _q2(Decimal(str(qty)) * Decimal(str(unit_price)) * rate)

    # 小规模纳税人
    Q30 = Decimal("300000")  # 季度免税阈值
    this_sale = Decimal(str(qty)) * Decimal(str(unit_price))
    cumulative = Decimal(str(quarterly_revenue)) + this_sale

    # 专用发票：按 tax_rate 征收（税率来自上传发票），不享受免税
    if is_special_invoice:
        return _q2(this_sale * rate)

    # 普通发票：季度累计≤30万免税，>30万按 tax_rate
    if cumulative <= Q30:
        return Decimal("0")
    return _q2(this_sale * rate)


def sale_receivable(unit_price, qty, tax_rate, general_taxpayer: bool = True,
                    is_special_invoice: bool = False,
                    quarterly_revenue=0) -> Decimal:
    """销售应收账款（进 1122 的价税合计）

    Args:
        general_taxpayer: 纳税人开关。True=一般纳税人（开），False=小规模纳税人（闭）
    """
    revenue = sale_revenue(unit_price, qty)
    output_tax_l1 = sale_output_tax(unit_price, qty, tax_rate, general_taxpayer,
                                  is_special_invoice, quarterly_revenue)
    return _q2(revenue + output_tax_l1)


# ──────────────────────────────────────────────────────────────
# 采购退货
# ──────────────────────────────────────────────────────────────

def purchase_return_inventory_cost(orig_unit_price, qty_ret, enable_vat_deduction: bool) -> Decimal:
    """采购退货库存退回（贷 1405 的金额）

    依据（memory 硬约束 + audit-truth-source skill）：
    必须用原发票单价 orig_item.unit_price，不能用 StockMove.unit_cost（移动加权平均成本）
    """
    return _q2(Decimal(str(qty_ret)) * Decimal(str(orig_unit_price)))


def purchase_return_tax(orig_unit_price, qty_ret, tax_rate, enable_vat_deduction: bool) -> Decimal:
    """采购退货进项税额转出（贷 222102，仅一般纳税人）"""
    if not enable_vat_deduction:
        return Decimal("0")
    rate = Decimal(str(tax_rate)) if tax_rate else Decimal("0")
    return _q2(Decimal(str(qty_ret)) * Decimal(str(orig_unit_price)) * rate)


def purchase_return_payable(orig_unit_price, qty_ret, tax_rate, enable_vat_deduction: bool) -> Decimal:
    """采购退货冲减应付（借 2202，原发票价税合计）"""
    base = Decimal(str(qty_ret)) * Decimal(str(orig_unit_price))
    if enable_vat_deduction:
        rate = Decimal(str(tax_rate)) if tax_rate else Decimal("0")
        return _q2(base * (1 + rate))
    return _q2(base)


# ──────────────────────────────────────────────────────────────
# 销售退货
# ──────────────────────────────────────────────────────────────

def sale_return_cogs(orig_stock_move_unit_cost, qty_ret) -> Decimal:
    """销售退货 COGS 冲回（贷 6401 的金额）

    依据（memory 硬约束）：
    必须用原销售时锁定的 StockMove.unit_cost，不用当前 Inventory.average_cost
    """
    return _q2(Decimal(str(qty_ret)) * Decimal(str(orig_stock_move_unit_cost)))


def sale_return_revenue(orig_unit_price, qty_ret, orig_qty=None, orig_total_price=None) -> Decimal:
    """销售退货冲减收入（借 6001）

    优先用原单价 × 退货数量（与系统销售退货收入冲减逻辑一致）。
    若仅提供 orig_total_price，则按比例分摊。

    revenue_ret = orig_unit_price × qty_ret
    """
    if orig_unit_price is not None:
        return _q2(Decimal(str(qty_ret)) * Decimal(str(orig_unit_price)))
    # 兼容：仅提供 orig_total_price 时按比例分摊
    if orig_qty is None or Decimal(str(orig_qty)) == 0:
        return Decimal("0")
    ratio = Decimal(str(qty_ret)) / Decimal(str(orig_qty))
    return _q2(Decimal(str(orig_total_price)) * ratio)


# ──────────────────────────────────────────────────────────────
# 月结税
# ──────────────────────────────────────────────────────────────

