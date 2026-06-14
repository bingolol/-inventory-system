from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


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
    image_url: Optional[str] = None
    notes: str = ""


class InvoiceList(BaseModel):
    total: int
    items: List[InvoiceOut]