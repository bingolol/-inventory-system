from pydantic import BaseModel
from decimal import Decimal


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