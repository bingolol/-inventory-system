from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from schemas.invoice import InvoiceOut


# ── Opening Balance (期初余额) ──

class OpeningBalanceBase(BaseModel):
    date: str  # YYYY-MM-DD格式
    cash_balance: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    bank_balance: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    accounts_receivable: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    inventory_value: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    accounts_payable: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    tax_payable: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2)
    retained_earnings: Decimal = Field(default=Decimal('0'), max_digits=12, decimal_places=2)


class OpeningBalanceCreate(OpeningBalanceBase):
    pass


class OpeningBalanceUpdate(BaseModel):
    date: Optional[str] = None
    cash_balance: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    bank_balance: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    accounts_receivable: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    inventory_value: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    accounts_payable: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    tax_payable: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    retained_earnings: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)


class OpeningBalanceOut(OpeningBalanceBase):
    id: int
    account_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
    
    @classmethod
    def model_validate(cls, obj):
        # 将date字段转换为字符串格式
        if hasattr(obj, 'date') and obj.date:
            obj.date = obj.date.isoformat()
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


# ── IncomeTaxReport (企业所得税年度报表) ──

class IncomeTaxReport(BaseModel):
    year: int
    quarter: Optional[int] = None
    account_id: int
    # ── 税务口径核心字段（发票说话）──
    # 收入
    total_revenue: Decimal  # 销项发票不含税金额合计
    # 成本
    total_cost: Decimal     # 进项发票不含税金额合计
    # 费用
    operating_expenses: Decimal  # 有票费用合计（仅可税前扣除部分）
    # 利润
    gross_profit: Decimal   # total_revenue - total_cost
    taxable_income: Decimal # gross_profit - operating_expenses（简化，不考虑纳税调整）
    # 税率
    tax_rate: Decimal       # 小微企业实际税率（如5%或更低）
    tax_amount: Decimal     # 应纳企业所得税 = taxable_income * tax_rate
    # ── 税务口径明细（前端对比展示用）──
    invoice_revenue: Decimal = Decimal('0')      # 销项发票不含税金额
    invoice_cost: Decimal = Decimal('0')         # 进项发票不含税金额
    invoiced_expenses: Decimal = Decimal('0')    # 有票费用
    non_invoice_expenses: Decimal = Decimal('0') # 无票费用（仅供参考，不可税前扣除）


# ── Financial Reports (三大报表) ──

class BalanceSheet(BaseModel):
    date: str
    assets: dict
    liabilities: dict
    equity: dict


class IncomeStatement(BaseModel):
    period: str
    revenue: Decimal
    cost_of_goods_sold: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    operating_profit: Decimal
    net_profit: Decimal


# ── Cash Flow (现金流) ──

class CashFlowTransactionCreate(BaseModel):
    type: str = Field(..., pattern="^(inflow|outflow)$")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    flow_category: str = Field("operating", pattern="^(operating|investing|financing)$")
    description: str = ""
    transaction_date: str
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
    amount: Decimal
    flow_category: str
    description: str
    transaction_date: datetime
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CashFlowStatement(BaseModel):
    period: str
    operating_activities: dict
    investing_activities: dict
    financing_activities: dict
    net_cash_flow: Decimal
    beginning_cash_balance: Decimal
    ending_cash_balance: Decimal