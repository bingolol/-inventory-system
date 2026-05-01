from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class AccountOut(BaseModel):
    id: int
    name: str
    type: str
    code: str
    taxpayer_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


# 期初余额相关Schema
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


class ProductBase(BaseModel):
    name: str = Field(..., max_length=100)
    sku: Optional[str] = Field(default=None, max_length=50)
    category: str = ""
    unit: str = "个"
    purchase_price: Decimal = Field(default=Decimal('0'), max_digits=12, decimal_places=2)
    sale_price: Decimal = Field(default=Decimal('0'), max_digits=12, decimal_places=2)
    min_stock: int = 0
    description: str = ""


class ProductCreate(ProductBase):
    initial_stock: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    purchase_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    min_stock: Optional[int] = None
    description: Optional[str] = None


class ProductOut(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    current_stock: Optional[int] = None

    model_config = {"from_attributes": True}


class SupplierBase(BaseModel):
    name: str = Field(..., max_length=100)
    contact: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class SupplierOut(SupplierBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerBase(BaseModel):
    name: str = Field(..., max_length=100)
    contact: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CustomerOut(CustomerBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Purchase Order + Items ──

class PurchaseItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal('0.13'), ge=0, le=1, max_digits=12, decimal_places=2)


class PurchaseItemOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    total_price: Decimal

    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    supplier_id: Optional[int] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None
    has_invoice: bool = False
    payment_method: str = "company"
    image_url: Optional[str] = ""
    notes: str = ""
    items: List[PurchaseItemCreate]


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[int] = None
    project_id: Optional[int] = None
    has_invoice: Optional[bool] = None
    payment_method: Optional[str] = None
    payment_status: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    items: Optional[List[PurchaseItemCreate]] = None


class PurchaseOrderOut(BaseModel):
    id: int
    order_no: Optional[str] = None
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None
    total_price: Decimal
    has_invoice: bool
    payment_method: str
    payment_status: str
    status: str
    notes: str
    image_url: Optional[str] = ""
    purchase_date: datetime
    created_at: datetime
    items: List[PurchaseItemOut]

    model_config = {"from_attributes": True}


# ── Sale Order + Items ──

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal('0.01'), ge=0, le=1, max_digits=12, decimal_places=2)


class SaleItemOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    total_price: Decimal

    model_config = {"from_attributes": True}


class SaleOrderCreate(BaseModel):
    customer_id: Optional[int] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None
    deduct_inventory: Optional[bool] = False
    has_invoice: bool = False
    payment_status: str = "unpaid"
    image_url: Optional[str] = ""
    notes: str = ""
    total_price: Optional[Decimal] = None
    items: List[SaleItemCreate]


class SaleOrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    project_id: Optional[int] = None
    has_invoice: Optional[bool] = None
    payment_status: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    deduct_inventory: Optional[bool] = None
    total_price: Optional[Decimal] = None
    items: Optional[List[SaleItemCreate]] = None


class SaleOrderOut(BaseModel):
    id: int
    order_no: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    project_name: Optional[str] = None
    project_id: Optional[int] = None
    deduct_inventory: bool = False
    total_price: Decimal
    has_invoice: bool
    payment_status: str
    status: str
    notes: str
    image_url: Optional[str] = ""
    sale_date: datetime
    created_at: datetime
    items: List[SaleItemOut]

    model_config = {"from_attributes": True}


# ── Inventory ──

class InventoryOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_category: Optional[str] = None
    product_unit: Optional[str] = None
    min_stock: Optional[int] = None
    purchase_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    last_updated: Optional[datetime] = None
    is_alert: bool = False

    model_config = {"from_attributes": True}


class InventoryAdjust(BaseModel):
    quantity: int


# ── Operation Log ──

class OperationLogOut(BaseModel):
    id: int
    operation: str
    entity_type: str
    entity_id: int
    detail: str
    operator: str = "user"
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Personal Transaction (个人流水账) ──

class PersonalTransactionCreate(BaseModel):
    type: str = Field(..., pattern="^(income|expense)$")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    category: str = ""
    description: str = ""
    image_url: str = ""
    date: Optional[str] = None


class PersonalTransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[Decimal] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    date: Optional[str] = None


class PersonalTransactionOut(BaseModel):
    id: int
    type: str
    amount: Decimal
    category: str
    description: str
    image_url: str = ""
    date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ──

class ReportOverview(BaseModel):
    total_products: int
    total_stock_value: Decimal
    total_inventory_quantity: int
    positive_stock_count: int = 0
    negative_stock_count: int = 0
    today_purchase_count: int
    today_purchase_amount: Decimal
    today_sale_count: int
    today_sale_amount: Decimal
    low_stock_count: int


class PaginatedResponse(BaseModel):
    total: int
    items: list


class PersonalSummary(BaseModel):
    month_income: Decimal
    month_expense: Decimal
    month_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    total_balance: Decimal


# ── Invoice ──

class InvoiceBase(BaseModel):
    invoice_no: str = Field(..., max_length=50)
    direction: str = Field(..., pattern="^(in|out)$")
    invoice_type: str = Field(..., pattern="^(ordinary|special)$")
    tax_rate: Decimal = Field(..., ge=0, le=1, max_digits=12, decimal_places=2)
    amount_without_tax: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    amount_with_tax: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    counterparty_name: str = Field(..., max_length=200)
    issue_date: datetime
    pdf_path: Optional[str] = None
    image_url: Optional[str] = ""
    certification_status: str = "n_a"
    certification_date: Optional[datetime] = None
    project_name: Optional[str] = None
    related_order_id: Optional[int] = None
    related_order_type: Optional[str] = None
    notes: str = ""


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    invoice_no: Optional[str] = None
    direction: Optional[str] = None
    invoice_type: Optional[str] = None
    tax_rate: Optional[Decimal] = None
    amount_without_tax: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    amount_with_tax: Optional[Decimal] = None
    counterparty_name: Optional[str] = None
    issue_date: Optional[datetime] = None
    pdf_path: Optional[str] = None
    related_order_id: Optional[int] = None
    project_name: Optional[str] = None
    image_url: Optional[str] = None
    notes: Optional[str] = None


class InvoiceOut(InvoiceBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceQuickCreate(BaseModel):
    invoice_no: str = Field(..., max_length=50)
    direction: str = Field(..., pattern="^(in|out)$")
    invoice_type: str = Field(..., pattern="^(ordinary|special)$")
    amount_with_tax: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    tax_rate: Decimal = Field(..., ge=0, le=1, max_digits=12, decimal_places=2)
    counterparty_name: str = Field(..., max_length=200)
    issue_date: str  # YYYY-MM-DD
    project_name: Optional[str] = None
    image_url: Optional[str] = None
    notes: str = ""


class InvoiceList(BaseModel):
    total: int
    items: List[InvoiceOut]


# ── Expense ──

class ExpenseBase(BaseModel):
    project_name: Optional[str] = None
    category: str
    amount: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    expense_date: datetime
    has_invoice: bool = False
    payment_method: str = "company"
    description: str = ""
    image_url: str = ""


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    project_name: Optional[str] = None
    category: Optional[str] = None
    amount: Optional[Decimal] = None
    expense_date: Optional[str] = None
    has_invoice: Optional[bool] = None
    payment_method: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class ExpenseOut(ExpenseBase):
    id: int
    account_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


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
    account_id: int
    # 收入
    total_revenue: Decimal  # 全年收入合计（有票收入 + 无票收入，从sale_orders统计）
    # 成本
    total_cost: Decimal     # 全年成本合计（purchase_orders + expenses）
    # 费用
    operating_expenses: Decimal  # 经营费用（rent + salary + other expenses）
    # 利润
    gross_profit: Decimal   # total_revenue - total_cost
    taxable_income: Decimal # gross_profit - operating_expenses（简化，不考虑纳税调整）
    # 税率
    tax_rate: Decimal       # 小微企业实际税率（如5%或更低）
    tax_amount: Decimal     # 应纳企业所得税 = taxable_income * tax_rate


# ── ProjectSummary ──

class ProjectSummary(BaseModel):
    project_name: str
    income: Decimal
    cost: Decimal
    profit: Decimal
    sale_count: int
    purchase_count: int


# ── Financial Reports ──

class BalanceSheet(BaseModel):
    date: str
    assets: dict
    liabilities: dict
    equity: dict


# ── ProjectCost / ProjectIncome (从routers/projects移过来，消除循环依赖) ──

class ProjectCostCreate(BaseModel):
    project_id: int
    cost_type: str
    amount: Decimal = Field(..., max_digits=12, decimal_places=2)
    payment_method: str
    image_url: Optional[str] = ""
    invoice_status: str
    supplier_name: Optional[str] = None
    notes: Optional[str] = None
    cost_date: Optional[str] = None  # YYYY-MM-DD，在项目路由中转为datetime
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None  # 单价（仅前端辅助计算用，后端不存储）


class ProjectCostUpdate(BaseModel):
    cost_type: Optional[str] = None
    amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    invoice_status: Optional[str] = None
    image_url: Optional[str] = None
    supplier_name: Optional[str] = None
    notes: Optional[str] = None
    cost_date: Optional[str] = None  # YYYY-MM-DD
    product_id: Optional[int] = None
    quantity: Optional[int] = None


class ProjectCostOut(BaseModel):
    id: int
    project_id: int
    cost_type: str
    amount: Decimal
    payment_method: str
    image_url: Optional[str] = ""
    invoice_status: str
    supplier_name: Optional[str] = None
    notes: Optional[str] = None
    cost_date: Optional[str] = None
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    product_name: Optional[str] = None  # 展示用
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectIncomeCreate(BaseModel):
    project_id: int
    amount: Decimal = Field(..., max_digits=12, decimal_places=2)
    payment_status: str
    received_amount: Optional[Decimal] = None
    invoice_status: str
    notes: Optional[str] = None
    income_date: Optional[str] = None  # YYYY-MM-DD
    received_date: Optional[str] = None  # YYYY-MM-DD
    source_type: Optional[str] = None
    source_id: Optional[int] = None


class ProjectIncomeOut(BaseModel):
    id: int
    project_id: int
    amount: Decimal
    payment_status: str
    received_amount: Optional[Decimal] = None
    invoice_status: str
    notes: Optional[str] = None
    income_date: Optional[str] = None
    received_date: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncomeStatement(BaseModel):
    period: str
    revenue: Decimal
    cost_of_goods_sold: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    operating_profit: Decimal
    net_profit: Decimal


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