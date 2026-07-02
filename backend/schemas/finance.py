from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from schemas.invoice import InvoiceOut


# ── Opening Balance (期初余额) ──

class OpeningBalanceBase(BaseModel):
    date: str  # YYYY-MM-DD格式
    # 流动资产
    cash_balance: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    bank_balance: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    accounts_receivable: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    inventory_value: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    # 非流动资产
    fixed_assets_original: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    accumulated_depreciation: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    intangible_assets_original: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    accumulated_amortization: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    # 流动负债
    accounts_payable: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    tax_payable: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    # 非流动负债
    long_term_borrowings: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    # 权益
    paid_in_capital: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    retained_earnings: Decimal = Field(default=Decimal('0'), max_digits=12, decimal_places=2)


class OpeningBalanceCreate(OpeningBalanceBase):
    pass


class OpeningBalanceUpdate(BaseModel):
    date: Optional[str] = None
    cash_balance: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    bank_balance: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    accounts_receivable: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    inventory_value: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    fixed_assets_original: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    accumulated_depreciation: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    intangible_assets_original: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    accumulated_amortization: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    accounts_payable: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    tax_payable: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    long_term_borrowings: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    paid_in_capital: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    retained_earnings: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)


class OpeningBalanceOut(OpeningBalanceBase):
    id: int
    account_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
    
    @classmethod
    def model_validate(cls, obj):
        # 将 ORM 的 date_l1 字段映射到 Schema 的 date 字段
        if hasattr(obj, 'date_l1') and obj.date_l1:
            obj.date = obj.date_l1.isoformat()
        return super().model_validate(obj)


# ── Fixed Asset (固定资产) ──

class FixedAssetBase(BaseModel):
    asset_code: str = Field(..., max_length=50, description="资产编码")
    name: str = Field(..., max_length=100, description="资产名称")
    category: Optional[str] = Field(None, max_length=50, description="资产类别")
    original_value: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="原值")
    salvage_rate: Decimal = Field(default=Decimal('0.05'), ge=0, le=1, max_digits=5, decimal_places=2, description="残值率")
    useful_life: int = Field(..., gt=0, description="使用寿命(月)")
    depreciation_method: str = Field(default="年限平均法", description="折旧方法")
    start_date: str = Field(..., description="开始折旧日期(YYYY-MM-DD)")
    accumulated_depreciation: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2, description="累计折旧")
    status: str = Field(default="在用", description="在用/停用/报废")


class FixedAssetCreate(FixedAssetBase):
    pass


class FixedAssetUpdate(BaseModel):
    asset_code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    original_value: Optional[Decimal] = None
    salvage_rate: Optional[Decimal] = None
    useful_life: Optional[int] = None
    depreciation_method: Optional[str] = None
    start_date: Optional[str] = None
    accumulated_depreciation: Optional[Decimal] = None
    status: Optional[str] = None


class FixedAssetWithInvoiceUpdate(BaseModel):
    """固定资产更新（联动发票）"""
    original_value: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    name: Optional[str] = None
    category: Optional[str] = None
    salvage_rate: Optional[Decimal] = None
    useful_life: Optional[int] = None
    depreciation_method: Optional[str] = None
    start_date: Optional[str] = None
    status: Optional[str] = None


class FixedAssetOut(FixedAssetBase):
    id: int
    account_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
    
    @classmethod
    def model_validate(cls, obj):
        # 将 ORM 的 start_date_l1 字段映射到 Schema 的 start_date 字段
        if hasattr(obj, 'start_date_l1') and obj.start_date_l1:
            obj.start_date = obj.start_date_l1.isoformat()
        return super().model_validate(obj)


# ── Intangible Asset (无形资产) ──

class IntangibleAssetBase(BaseModel):
    asset_code: str = Field(..., max_length=50, description="资产编码")
    name: str = Field(..., max_length=100, description="资产名称")
    category: Optional[str] = Field(None, max_length=50, description="类别(专利/软件/商标等)")
    original_value: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="原值")
    useful_life: int = Field(..., gt=0, description="使用寿命(月)")
    start_date: str = Field(..., description="开始摊销日期(YYYY-MM-DD)")
    accumulated_amortization: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2, description="累计摊销")
    status: str = Field(default="使用中", description="使用中/已报废")


class IntangibleAssetCreate(IntangibleAssetBase):
    pass


class IntangibleAssetUpdate(BaseModel):
    asset_code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    original_value: Optional[Decimal] = None
    useful_life: Optional[int] = None
    start_date: Optional[str] = None
    accumulated_amortization: Optional[Decimal] = None
    status: Optional[str] = None


class IntangibleAssetOut(IntangibleAssetBase):
    id: int
    account_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
    
    @classmethod
    def model_validate(cls, obj):
        # 将 ORM 的 start_date_l1 字段映射到 Schema 的 start_date 字段
        if hasattr(obj, 'start_date_l1') and obj.start_date_l1:
            obj.start_date = obj.start_date_l1.isoformat()
        return super().model_validate(obj)


# ── TaxReport (增值税季度报表) ──

class TaxReport(BaseModel):
    year: int
    quarter: int
    period_start: str
    period_end: str
    taxpayer_type: str
    output_total: Decimal
    output_tax: Decimal
    input_total: Decimal
    input_tax: Decimal
    tax_payable: Decimal
    invoice_list: List[InvoiceOut]


class TaxReportMonth(BaseModel):
    year: int
    month: int
    period_start: str
    period_end: str
    taxpayer_type: str
    output_total: Decimal
    output_tax: Decimal
    input_total: Decimal
    input_tax: Decimal
    tax_payable: Decimal
    invoice_list: List[InvoiceOut]


# ── VAT Declaration (增值税纳税申报表 - 小规模纳税人) ──

class VATDeclaration(BaseModel):
    year: int
    quarter: int
    period_start: str
    period_end: str
    # 一、计税依据
    total_revenue: Decimal = Decimal('0')  # 应税不含税销售额
    tax_rate: Decimal = Decimal('0.03')    # 征收率
    tax_reduction: Decimal = Decimal('0')  # 减免税额
    # 二、税款计算
    tax_payable: Decimal = Decimal('0')    # 应纳税额
    tax_paid: Decimal = Decimal('0')       # 已预缴税额
    tax_supplement: Decimal = Decimal('0') # 本期应补(退)税额
    # 三、附加税费
    surcharge_education: Decimal = Decimal('0')      # 教育费附加
    surcharge_local_education: Decimal = Decimal('0') # 地方教育附加
    surcharge_urban_construction: Decimal = Decimal('0') # 城市维护建设税（7%）
    surcharge_total: Decimal = Decimal('0')           # 附加税费合计
    # 四、减免税明细
    reduction_item: str = ""  # 减免项目
    reduction_amount: Decimal = Decimal('0')  # 减免金额
    # 发票明细
    invoice_list: List[InvoiceOut] = []


# ── IncomeTaxReport (企业所得税年度报表) ──

class IncomeTaxReport(BaseModel):
    year: int
    quarter: Optional[int] = None
    account_id: int
    # ── 会计准则口径核心字段（利润表说话）──
    # 收入
    total_revenue: Decimal  # 利润表营业收入（总账 6001+6051 贷方净额）
    # 成本
    total_cost: Decimal     # 利润表营业成本（总账 6401 借方净额）
    # 费用
    operating_expenses: Decimal  # 利润表期间费用（6601+6602+6603，不含税金及附加）
    # 利润
    gross_profit: Decimal   # 营业毛利 = 营业收入 - 营业成本
    taxable_income: Decimal # 应纳税所得额 = 利润总额（简化，暂不处理纳税调整）
    # 税率
    tax_rate: Decimal       # 小微企业实际税率（如5%或更低）
    tax_amount: Decimal     # 应纳企业所得税 = taxable_income * tax_rate


# ── Income Tax Prepayment (企业所得税预缴申报表 - A类) ──

class IncomeTaxPrepayment(BaseModel):
    year: int
    quarter: int
    period_start: str
    period_end: str
    # 一、营业收入
    operating_revenue: Decimal = Decimal('0')  # 营业收入
    # 二、营业成本
    operating_cost: Decimal = Decimal('0')     # 营业成本
    # 三、利润总额
    gross_profit: Decimal = Decimal('0')       # 利润总额
    # 四、加：特定业务计算的应纳税所得额
    special_business_income: Decimal = Decimal('0')  # 特定业务
    # 五、减：免税收入、减计收入、加计扣除
    tax_exempt_income: Decimal = Decimal('0')  # 免税收入
    tax_deduction_income: Decimal = Decimal('0')  # 减计收入
    additional_deduction: Decimal = Decimal('0')  # 加计扣除
    # 六、减：减免所得额
    tax_reduction_income: Decimal = Decimal('0')  # 减免所得额
    # 七、实际利润额
    actual_profit: Decimal = Decimal('0')      # 实际利润额 = 利润总额 + 特定业务 - 免税 - 减计 - 加计扣除 - 减免
    # 八、税率
    tax_rate: Decimal = Decimal('0.25')        # 税率
    # 九、应纳所得税额
    tax_payable: Decimal = Decimal('0')        # 应纳所得税额 = 实际利润额 × 税率
    # 十、减：减免所得税额
    small_micro_discount: Decimal = Decimal('0')  # 小微企业减免
    # 十一、实际应纳所得税额
    actual_tax_payable: Decimal = Decimal('0') # 实际应纳所得税额
    # 十二、加：特定业务预缴所得税额
    special_business_prepaid: Decimal = Decimal('0')  # 特定业务预缴
    # 十三、减：已预缴所得税额
    prepaid_tax: Decimal = Decimal('0')        # 已预缴所得税额
    # 十四、本期应补(退)所得税额
    tax_supplement: Decimal = Decimal('0')     # 本期应补(退)所得税额


# ── Asset Depreciation Detail (资产加速折旧明细表 A201020) ──

class AssetDepreciationDetail(BaseModel):
    year: int
    quarter: int
    account_id: int
    # 资产明细列表
    assets: List[dict] = []  # 每项包含：资产名称、原值、折旧方法、本期折旧、累计折旧等
    # 汇总
    total_original_value: Decimal = Decimal('0')  # 资产原值合计
    total_depreciation: Decimal = Decimal('0')    # 本期折旧合计
    total_accumulated: Decimal = Decimal('0')     # 累计折旧合计


# ── Financial Reports (三大报表) ──

class BalanceSheet(BaseModel):
    """资产负债表 (会小企01表)"""
    date: str  # 报表日期
    # 资产
    monetary_funds: Decimal = Decimal('0')  # 货币资金
    accounts_receivable: Decimal = Decimal('0')  # 应收账款
    prepayments: Decimal = Decimal('0')  # 预付账款
    inventory: Decimal = Decimal('0')  # 存货
    total_current_assets: Decimal = Decimal('0')  # 流动资产合计
    fixed_assets_original: Decimal = Decimal('0')  # 固定资产原值
    accumulated_depreciation: Decimal = Decimal('0')  # 累计折旧
    fixed_assets_net: Decimal = Decimal('0')  # 固定资产净值
    intangible_assets_original: Decimal = Decimal('0')  # 无形资产原值
    accumulated_amortization: Decimal = Decimal('0')  # 累计摊销
    intangible_assets_net: Decimal = Decimal('0')  # 无形资产净值
    total_non_current_assets: Decimal = Decimal('0')  # 非流动资产合计
    total_assets: Decimal = Decimal('0')  # 资产总计
    # 负债和所有者权益
    accounts_payable: Decimal = Decimal('0')  # 应付账款
    tax_payable: Decimal = Decimal('0')  # 应交税费
    total_current_liabilities: Decimal = Decimal('0')  # 流动负债合计
    long_term_borrowings: Decimal = Decimal('0')  # 长期借款
    total_non_current_liabilities: Decimal = Decimal('0')  # 非流动负债合计
    total_liabilities: Decimal = Decimal('0')  # 负债合计
    paid_in_capital: Decimal = Decimal('0')  # 实收资本
    retained_earnings: Decimal = Decimal('0')  # 未分配利润
    total_equity: Decimal = Decimal('0')  # 所有者权益合计
    total_liabilities_and_equity: Decimal = Decimal('0')  # 负债和所有者权益总计


class IncomeStatement(BaseModel):
    """利润表 (会小企02表)"""
    period: str  # 期间
    # 一、营业收入
    revenue: Decimal = Decimal('0')
    # 二、营业成本
    cost_of_goods_sold: Decimal = Decimal('0')
    # 三、营业毛利
    gross_profit: Decimal = Decimal('0')
    # 四、营业费用
    selling_expenses: Decimal = Decimal('0')  # 销售费用
    administrative_expenses: Decimal = Decimal('0')  # 管理费用
    financial_expenses: Decimal = Decimal('0')  # 财务费用
    total_operating_expenses: Decimal = Decimal('0')  # 营业费用合计
    # 五、营业利润
    operating_profit: Decimal = Decimal('0')
    # 六、营业外收支
    non_operating_income: Decimal = Decimal('0')  # 营业外收入
    non_operating_expense: Decimal = Decimal('0')  # 营业外支出
    # 七、利润总额
    gross_profit_total: Decimal = Decimal('0')
    # 八、所得税费用
    income_tax_expense: Decimal = Decimal('0')
    # 九、净利润
    net_profit: Decimal = Decimal('0')


# ── Cash Flow (现金流) ──

class CashFlowTransactionCreate(BaseModel):
    type: str = Field(..., pattern="^(inflow|outflow)$")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    flow_category: str = Field("operating", pattern="^(operating|investing|financing)$")
    description: str = ""
    transaction_date: str
    counter_account_code: str = Field("2202", description="对方科目编码（按 flow_category 默认映射）")
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


class CashFlowTransactionUpdate(BaseModel):
    type: Optional[str] = Field(None, pattern="^(inflow|outflow)$")
    amount: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    flow_category: Optional[str] = Field(None, pattern="^(operating|investing|financing)$")
    description: Optional[str] = None
    transaction_date: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None


class CashFlowTransactionOut(BaseModel):
    id: int
    account_id: int
    type: str
    amount: Decimal = Field(validation_alias="amount_l2")
    flow_category: str = Field(validation_alias="flow_category_l2")
    description: str
    transaction_date: datetime = Field(validation_alias="transaction_date_l1")
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CashFlowStatement(BaseModel):
    period: str
    operating_activities: dict
    investing_activities: dict
    financing_activities: dict
    net_cash_flow: Decimal
    beginning_cash_balance: Decimal
    ending_cash_balance: Decimal