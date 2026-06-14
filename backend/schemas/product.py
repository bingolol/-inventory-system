from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


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