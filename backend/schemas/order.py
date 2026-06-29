from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ── Purchase Order + Items ──

class PurchaseItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=6)
    tax_rate: Decimal = Field(default=Decimal('0.13'), ge=0, le=1, max_digits=12, decimal_places=2)


class PurchaseItemOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    total_price: Decimal
    notes: Optional[str] = ""

    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    supplier_id: Optional[int] = None
    purchase_date: Optional[datetime] = None
    payment_method: str = "company"
    image_url: Optional[str] = ""
    notes: str = ""
    items: List[PurchaseItemCreate]


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[int] = None
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
    order_type: str = "retail"
    total_price: Decimal
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
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=6)
    tax_rate: Decimal = Field(default=Decimal('0.01'), ge=0, le=1, max_digits=12, decimal_places=2)


class SaleItemOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    total_price: Decimal
    notes: Optional[str] = ""

    model_config = {"from_attributes": True}


class SaleOrderCreate(BaseModel):
    customer_id: Optional[int] = None
    deduct_inventory: bool = True
    payment_status: str = "unpaid"
    image_url: Optional[str] = ""
    notes: str = ""
    total_price: Optional[Decimal] = None
    sale_date: datetime
    items: List[SaleItemCreate]


class SaleOrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    payment_status: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    total_price: Optional[Decimal] = None
    items: Optional[List[SaleItemCreate]] = None


class SaleOrderOut(BaseModel):
    id: int
    order_no: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    order_type: str = "retail"
    total_price: Decimal
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
    adjust_date: Optional[str] = None
    reason: Optional[str] = None  # 报损原因（减少库存时必填）