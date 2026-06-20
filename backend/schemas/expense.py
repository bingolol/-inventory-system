from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ── Expense ──

class ExpenseBase(BaseModel):
    category: str
    functional_category: str = "管理费用"
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    expense_date: datetime
    has_invoice: bool = False
    payment_method: str = "company"
    payment_status: str = "unpaid"
    description: str = ""
    image_url: str = ""


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
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