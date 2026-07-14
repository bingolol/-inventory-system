"""小企业会计准则纯计算引擎（会计准则语言版）

不依赖 backend 代码，只用 Python 标准库和 Decimal。
用于为黄金测试提供独立的期望值：给定业务事实，输出报表关键指标。

设计原则：
- 所有输入必须是“独立会计师能从原始凭证和银行对账单中确认的事实”。
- 不使用系统内部概念（科目代码、单据类型、API 字段名）。
- 用权责发生制确认收入、费用、资产、负债；用现金收付制确认银行存款。
- 两条线并行推导，最终用资产负债表和利润表勾稽校验。
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List


TWO_PLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    """保留两位小数（四舍五入）。"""
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class Purchase:
    """采购入库（取得商品所有权）。

    一般纳税人：unit_price 为不含税单价；
    小规模纳税人：unit_price 为含税单价（由 Facts.enable_vat_deduction 控制）。
    """
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal = Decimal("0.13")


@dataclass
class Sale:
    """销售出库（转移商品所有权）。

    一般纳税人：unit_price 为不含税单价；
    小规模纳税人：unit_price 为含税单价。
    """
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal = Decimal("0.13")


@dataclass
class Return:
    """退货。

    direction: "purchase" 或 "sale"
    - 采购退货：按采购价扣减存货和进项税（一般纳税人才有进项税）。
    - 销售退货：按销售价扣减收入和销项税，按成本恢复存货并冲减成本。
    """
    direction: str
    quantity: Decimal
    unit_price: Decimal          # 采购退货=采购价；销售退货=销售价
    unit_cost: Decimal = Decimal("0")  # 销售退货必填，用于恢复存货成本
    tax_rate: Decimal = Decimal("0.13")


@dataclass
class FixedAsset:
    """固定资产（直线法折旧）。

    original_value: 不含税原值
    periods_depreciated: 已计提折旧期数（默认 1 期）
    tax_rate: 进项税率，默认 0；需要价税分离时传 0.13
    salvage_rate: 残值率，默认 0
    paid: 是否已现金支付（默认 False=赊购）；
          True=已付现，减少银行存款，不形成应付账款
    """
    original_value: Decimal
    useful_life_months: int
    periods_depreciated: int = 1
    tax_rate: Decimal = Decimal("0")
    salvage_rate: Decimal = Decimal("0")
    paid: bool = False


@dataclass
class CashFlow:
    """期间内实际收付款（来自银行对账单的事实）。"""
    purchase_payment: Decimal = Decimal("0")   # 支付采购款
    sale_receipt: Decimal = Decimal("0")       # 收到销售款


@dataclass
class Expense:
    """期间费用。

    按权责发生制确认费用；按是否现金支付决定银行存款影响。
    paid=True:  已现金支付，减少银行存款，不形成应付账款；
    paid=False: 挂账，形成应付账款。
    """
    amount: Decimal
    paid: bool = False


@dataclass
class SupplierOverpayment:
    """对供应商多付款（预付/应收供应商款项）。

    典型场景：已付款费用被冲红，原费用和付款都被撤销，
    净效果是企业对供应商享有债权（银行存款已付，费用不再确认）。
    """
    amount: Decimal


@dataclass
class EmployeeFundedExpense:
    """员工垫付费用。

    员工先代企业支付费用，企业后报销。
    语义示例：amount=1000, reimbursed=1000, reversed_reimbursement=1000
    表示"员工垫付 1000 → 企业报销 1000 → 红冲报销 1000"
    净效果：费用仍确认 1000，企业仍欠员工 1000（报销被红冲），
    银行存款无净流出（报销付款被红冲抵销）。

    净效果（一般情况）：
    - 费用 += amount
    - 其他应付款（对员工） += amount - reimbursed + reversed_reimbursement
    - 银行存款 -= reimbursed - reversed_reimbursement
    """
    amount: Decimal
    reimbursed: Decimal = Decimal("0")              # 已报销金额
    reversed_reimbursement: Decimal = Decimal("0")  # 红冲的报销金额


@dataclass
class TaxesAndSurcharges:
    """税金及附加（由税务局核定，手工录入）。"""
    urban_construction: Decimal = Decimal("0")   # 城建税
    education: Decimal = Decimal("0")            # 教育费附加
    local_education: Decimal = Decimal("0")      # 地方教育附加

    @property
    def total(self) -> Decimal:
        return self.urban_construction + self.education + self.local_education


@dataclass
class BalanceSheet:
    """资产负债表关键字段。"""
    monetary_funds: Decimal
    accounts_receivable: Decimal
    inventory: Decimal
    prepaid_tax: Decimal
    prepayments: Decimal
    fixed_assets_original: Decimal
    accumulated_depreciation: Decimal
    fixed_assets_net: Decimal
    total_assets: Decimal

    accounts_payable: Decimal
    other_payable: Decimal
    vat_payable_l1: Decimal
    tax_surcharge_payable: Decimal
    income_tax_liability: Decimal
    total_liabilities: Decimal

    paid_in_capital: Decimal
    retained_earnings: Decimal
    total_equity: Decimal

    total_liabilities_and_equity: Decimal


@dataclass
class IncomeStatement:
    """利润表关键字段。"""
    revenue: Decimal
    cost_of_goods_sold: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    taxes_and_surcharges: Decimal
    depreciation_expense: Decimal
    financial_expenses: Decimal
    profit_before_tax: Decimal
    income_tax: Decimal
    net_profit: Decimal


@dataclass
class ExpectedReports:
    """报表预期结果。"""
    balance_sheet: BalanceSheet
    income_statement: IncomeStatement

    # 内部勾稽校验结果
    interlock_ok: bool
    interlock_messages: List[str] = field(default_factory=list)


@dataclass
class Facts:
    """业务事实输入。

    所有字段都是独立会计师能从原始凭证、银行对账单、税务局核定单中确认的事实，
    不依赖系统的科目设置或内部表结构。
    """
    opening_bank: Decimal
    opening_paid_in_capital: Decimal
    opening_retained_earnings: Decimal = Decimal("0")

    # 期初存货（数量和金额，用于加权平均）
    opening_inventory_qty: Decimal = Decimal("0")
    opening_inventory_value: Decimal = Decimal("0")

    # 增值税模式
    enable_vat_deduction: bool = True  # True=一般纳税人；False=小规模纳税人

    purchases: List[Purchase] = field(default_factory=list)
    sales: List[Sale] = field(default_factory=list)
    returns: List[Return] = field(default_factory=list)
    fixed_assets: List[FixedAsset] = field(default_factory=list)

    # 除折旧、附加税、银行手续费外的经营费用
    expenses: List[Expense] = field(default_factory=list)

    # 员工垫付费用
    employee_funded_expenses: List[EmployeeFundedExpense] = field(default_factory=list)

    # 对供应商多付款（预付/应收供应商）
    supplier_overpayments: List[SupplierOverpayment] = field(default_factory=list)

    # 银行手续费（对账生成凭证等）
    bank_fees: Decimal = Decimal("0")

    # 附加税
    taxes_and_surcharges: TaxesAndSurcharges = field(default_factory=TaxesAndSurcharges)

    # 期间内实际收付款
    cash_flows: CashFlow = field(default_factory=CashFlow)

    # 小微企业所得税实际税负（默认 5%）
    income_tax_rate: Decimal = Decimal("0.05")


def calculate(facts: Facts) -> ExpectedReports:
    """根据业务事实计算预期报表。"""
    inv_qty = facts.opening_inventory_qty
    inv_value = facts.opening_inventory_value

    revenue = Decimal("0")
    cogs = Decimal("0")
    input_tax_l1 = Decimal("0")
    output_tax_l1 = Decimal("0")
    accounts_payable = Decimal("0")
    accounts_receivable = Decimal("0")

    # ═══ 采购：存货增加，应付增加（一般纳税人另确认进项税）═══
    # 依据：§1.3 存货按采购成本入账；一般纳税人进项税单独核算。
    for p in facts.purchases:
        amount = _q(p.quantity * p.unit_price)
        if facts.enable_vat_deduction:
            tax = _q(amount * p.tax_rate)
            inv_value += amount
            input_tax_l1 += tax
            accounts_payable += amount + tax
        else:
            # 小规模纳税人：价税合一全额入库存，无进项税
            inv_value += amount
            accounts_payable += amount
        inv_qty += p.quantity

    # ═══ 采购退货：冲减存货、进项税、应付账款═══
    for r in facts.returns:
        if r.direction != "purchase":
            continue
        amount = _q(r.quantity * r.unit_price)
        if facts.enable_vat_deduction:
            tax = _q(amount * r.tax_rate)
            inv_value -= amount
            input_tax_l1 -= tax
            accounts_payable -= amount + tax
        else:
            inv_value -= amount
            accounts_payable -= amount
        inv_qty -= r.quantity

    # ═══ 销售：确认收入、销项税、应收账款；同时结转成本═══
    # 依据：§5.1 收入确认；§7.1 加权平均法结转成本。
    for s in facts.sales:
        amount = _q(s.quantity * s.unit_price)
        if facts.enable_vat_deduction:
            tax = _q(amount * s.tax_rate)
            revenue += amount
            output_tax_l1 += tax
            accounts_receivable += amount + tax
        else:
            # 小规模纳税人：收入为含税全额，无销项税
            revenue += amount
            accounts_receivable += amount
        if inv_qty <= 0:
            raise ValueError(f"销售 {s.quantity} 件时库存不足，当前 {inv_qty}")
        avg_cost = inv_value / inv_qty
        sale_cost = _q(s.quantity * avg_cost)
        cogs += sale_cost
        inv_qty -= s.quantity
        inv_value -= sale_cost

    # ═══ 销售退货：冲减收入、销项税、应收账款；恢复存货成本═══
    for r in facts.returns:
        if r.direction != "sale":
            continue
        amount = _q(r.quantity * r.unit_price)
        if facts.enable_vat_deduction:
            tax = _q(amount * r.tax_rate)
            revenue -= amount
            output_tax_l1 -= tax
            accounts_receivable -= amount + tax
        else:
            revenue -= amount
            accounts_receivable -= amount
        if r.unit_cost:
            restore_cost = _q(r.quantity * r.unit_cost)
        else:
            avg_cost = inv_value / inv_qty if inv_qty else Decimal("0")
            restore_cost = _q(r.quantity * avg_cost)
        cogs -= restore_cost
        inv_qty += r.quantity
        inv_value += restore_cost

    # ═══ 固定资产：确认资产原值、进项税、应付账款；计提折旧═══
    # 依据：§31 固定资产按年限平均法计提折旧。
    fixed_assets_original = Decimal("0")
    accumulated_depreciation = Decimal("0")
    depreciation_expense = Decimal("0")
    cash_fa_payment = Decimal("0")  # 现金购买固定资产的支出
    for fa in facts.fixed_assets:
        fixed_assets_original += fa.original_value

        # 进项税与应付（默认赊购；paid=True 时为现金购买）
        if facts.enable_vat_deduction:
            fa_tax = _q(fa.original_value * fa.tax_rate)
            input_tax_l1 += fa_tax
            if fa.paid:
                cash_fa_payment += fa.original_value + fa_tax  # 现金支付
            else:
                accounts_payable += fa.original_value + fa_tax  # 赊购
        else:
            if fa.paid:
                cash_fa_payment += fa.original_value
            else:
                accounts_payable += fa.original_value

        # 直线法折旧：原值×(1-残值率)÷使用年限
        monthly = _q(fa.original_value * (Decimal("1") - fa.salvage_rate) / Decimal(str(fa.useful_life_months)))
        accumulated_depreciation += monthly * fa.periods_depreciated
        depreciation_expense += monthly * fa.periods_depreciated

    # ═══ 收付款：应付/应收减少（现金收付制影响见下方银行存款）═══
    accounts_payable -= facts.cash_flows.purchase_payment
    accounts_receivable -= facts.cash_flows.sale_receipt

    # ═══ 费用：权责发生制确认费用；现金支付同时减少银行存款═══
    # 依据：§6.1 费用按权责发生制确认；已付现金不形成负债。
    operating_expenses = Decimal("0")
    cash_expenses = Decimal("0")
    for e in facts.expenses:
        operating_expenses += e.amount
        if e.paid:
            cash_expenses += e.amount  # 现金支付，减少银行存款
        else:
            accounts_payable += e.amount  # 挂账，形成应付账款

    # ═══ 对供应商多付款：银行存款已付，但费用/采购不确认，形成预付账款（资产）═══
    # 依据：小企业会计准则 1123 预付账款是独立资产科目，不应塞进应付账款做负数。
    prepayments = Decimal("0")
    for sop in facts.supplier_overpayments:
        prepayments += sop.amount

    # ═══ 员工垫付费用：费用已发生，负债对象为员工，报销时减少银行存款═══
    other_payable = Decimal("0")
    employee_reimbursement = Decimal("0")
    for efe in facts.employee_funded_expenses:
        operating_expenses += efe.amount
        other_payable += efe.amount - efe.reimbursed + efe.reversed_reimbursement
        employee_reimbursement += efe.reimbursed - efe.reversed_reimbursement

    # ═══ 银行手续费：财务费用，减少银行存款═══
    financial_expenses = facts.bank_fees

    # ═══ 附加税：税金及附加，形成负债═══
    taxes_and_surcharges = facts.taxes_and_surcharges.total
    tax_surcharge_payable = taxes_and_surcharges

    # ═══ 银行存款（现金收付制）═══
    monetary_funds = (
        facts.opening_bank
        - facts.cash_flows.purchase_payment
        + facts.cash_flows.sale_receipt
        - cash_expenses
        - employee_reimbursement
        - cash_fa_payment
        - sum(sop.amount for sop in facts.supplier_overpayments)
        - facts.bank_fees
    )

    # ═══ 增值税：销项税 - 进项税═══
    # 依据：§3 应交增值税 = 销项税额 - 进项税额。
    if facts.enable_vat_deduction:
        vat_net = output_tax_l1 - input_tax_l1
        vat_payable_l1 = max(vat_net, Decimal("0"))
        prepaid_tax = max(-vat_net, Decimal("0"))
    else:
        vat_payable_l1 = Decimal("0")
        prepaid_tax = Decimal("0")

    # ═══ 所得税：利润总额 × 税率（小微企业实际税负）═══
    # 依据：§7.1 所得税费用按应纳税所得额与实际税负计算。
    # 小微企业优惠：利润≤300万适用 5%（或 10%）实际税负；超过 300万按 25%。
    # 独立会计师应从税务局核定单确认实际税负，不应依赖默认值。
    #
    # 符号约定：本独立引擎中 depreciation_expense/financial_expenses 等费用类字段
    # 均为正数（累加后从收入中减去），与系统报表中费用显示为负数的约定相反。
    # 两种约定对 net_profit 的计算结果一致，对照表生成时需对费用类字段取绝对值比较。
    profit_before_tax = _q(
        revenue - cogs - operating_expenses - depreciation_expense
        - taxes_and_surcharges - financial_expenses
    )
    income_tax = _q(profit_before_tax * facts.income_tax_rate) if profit_before_tax > 0 else Decimal("0")
    net_profit = _q(profit_before_tax - income_tax)

    # 超限警告：利润超过 300 万但税率仍是默认 5%，提示可能不适用小微企业优惠
    _tax_warnings = []
    if profit_before_tax > Decimal("3000000") and facts.income_tax_rate == Decimal("0.05"):
        _tax_warnings.append(
            f"利润总额 {profit_before_tax} 超过 300 万，默认 5% 小微税率可能不适用，"
            "应按 25% 税率重新计算（独立会计师需从税务局核定单确认）"
        )

    # ═══ 资产负债表═══
    fixed_assets_net = fixed_assets_original - accumulated_depreciation
    total_assets = (
        monetary_funds
        + max(accounts_receivable, Decimal("0"))
        + inv_value
        + prepaid_tax
        + prepayments
        + fixed_assets_net
    )

    total_liabilities = (
        accounts_payable
        + max(other_payable, Decimal("0"))
        + vat_payable_l1
        + tax_surcharge_payable
        + income_tax
    )

    retained_earnings = facts.opening_retained_earnings + net_profit
    total_equity = facts.opening_paid_in_capital + retained_earnings
    total_liabilities_and_equity = total_liabilities + total_equity

    bs = BalanceSheet(
        monetary_funds=_q(monetary_funds),
        accounts_receivable=_q(max(accounts_receivable, Decimal("0"))),
        inventory=_q(inv_value),
        prepaid_tax=_q(prepaid_tax),
        prepayments=_q(prepayments),
        fixed_assets_original=_q(fixed_assets_original),
        accumulated_depreciation=_q(accumulated_depreciation),
        fixed_assets_net=_q(fixed_assets_net),
        total_assets=_q(total_assets),
        accounts_payable=_q(accounts_payable),
        other_payable=_q(max(other_payable, Decimal("0"))),
        vat_payable_l1=_q(vat_payable_l1),
        tax_surcharge_payable=_q(tax_surcharge_payable),
        income_tax_liability=_q(income_tax),
        total_liabilities=_q(total_liabilities),
        paid_in_capital=facts.opening_paid_in_capital,
        retained_earnings=_q(retained_earnings),
        total_equity=_q(total_equity),
        total_liabilities_and_equity=_q(total_liabilities_and_equity),
    )

    pl = IncomeStatement(
        revenue=_q(revenue),
        cost_of_goods_sold=_q(cogs),
        gross_profit=_q(revenue - cogs),
        operating_expenses=_q(operating_expenses),
        taxes_and_surcharges=_q(taxes_and_surcharges),
        depreciation_expense=_q(depreciation_expense),
        financial_expenses=_q(financial_expenses),
        profit_before_tax=profit_before_tax,
        income_tax=income_tax,
        net_profit=net_profit,
    )

    # ═══ 勾稽校验：资产 = 负债 + 权益；净利润 = 留存收益增加额═══
    # 依据：§84 资产负债表平衡公式；利润表净利润 = 留存收益本期增加。
    messages = list(_tax_warnings)  # 先装入税率超限警告（非阻塞）
    ok = True
    if bs.total_assets != bs.total_liabilities_and_equity:
        ok = False
        messages.append(
            f"资产负债表不平衡: 资产 {bs.total_assets} != 负债+权益 {bs.total_liabilities_and_equity}"
        )
    if pl.net_profit != retained_earnings - facts.opening_retained_earnings:
        ok = False
        messages.append(
            f"利润与留存收益勾稽不一致: 净利润 {pl.net_profit} != 留存收益增加 {retained_earnings - facts.opening_retained_earnings}"
        )

    return ExpectedReports(
        balance_sheet=bs,
        income_statement=pl,
        interlock_ok=ok,
        interlock_messages=messages,
    )
