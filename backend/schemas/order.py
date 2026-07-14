from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from .mappers import FieldMap, SchemaMapper


# ── 共享映射器 ──

_item_to_orm_mapper = SchemaMapper([
    FieldMap("product_id"),
    FieldMap("quantity", "quantity_l1"),
    FieldMap("unit_price", "unit_price_l1"),
    FieldMap("tax_rate", "tax_rate_l1"),
])


# ── Purchase Order + Items ──

class PurchaseItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=6,
        description="不含税单价。行金额 = quantity × unit_price，税额另计。")
    tax_rate: Decimal = Field(..., ge=0, le=1, max_digits=12, decimal_places=2)

    def to_orm_kwargs(self) -> dict:
        return _item_to_orm_mapper.map(self.model_dump())


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


_purchase_order_lifecycle_mapper = SchemaMapper([
    FieldMap("supplier_id"),
    FieldMap("business_date", "purchase_date"),
    FieldMap("payment_method"),
    FieldMap("image_url"),
    FieldMap("notes"),
    FieldMap("items", transform=lambda items: [it.to_orm_kwargs() for it in items]),
])


class PurchaseOrderCreate(BaseModel):
    supplier_id: Optional[int] = None
    business_date: datetime
    payment_method: str = "company"
    image_url: Optional[str] = ""
    notes: str = ""
    items: List[PurchaseItemCreate]

    def to_lifecycle_kwargs(self) -> dict:
        return _purchase_order_lifecycle_mapper.map(self.model_dump())


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
    business_date: datetime
    created_at: datetime
    items: List[PurchaseItemOut]

    model_config = {"from_attributes": True}


# ── Sale Order + Items ──

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=6,
        description="不含税单价。行金额 = quantity × unit_price，税额另计。")
    tax_rate: Decimal = Field(..., ge=0, le=1, max_digits=12, decimal_places=2)

    def to_orm_kwargs(self) -> dict:
        return _item_to_orm_mapper.map(self.model_dump())


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


_sale_order_lifecycle_mapper = SchemaMapper([
    FieldMap("customer_id"),
    FieldMap("deduct_inventory"),
    FieldMap("payment_status"),
    FieldMap("has_invoice"),
    FieldMap("image_url"),
    FieldMap("notes"),
    FieldMap("total_price"),
    FieldMap("business_date", "sale_date"),
    FieldMap("items", transform=lambda items: [it.to_orm_kwargs() for it in items]),
])


class SaleOrderCreate(BaseModel):
    customer_id: Optional[int] = None
    deduct_inventory: bool = True
    payment_status: str = "unpaid"
    has_invoice: bool  # 散客现金销售不开发票时传 False
    image_url: Optional[str] = ""
    notes: str = ""
    total_price: Optional[Decimal] = None
    business_date: datetime
    items: List[SaleItemCreate]

    def to_lifecycle_kwargs(self) -> dict:
        return _sale_order_lifecycle_mapper.map(self.model_dump())


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
    has_invoice: bool
    notes: str
    image_url: Optional[str] = ""
    business_date: datetime
    created_at: datetime
    items: List[SaleItemOut]

    model_config = {"from_attributes": True}


# ── Inventory ──

class InventoryOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    average_cost: Optional[Decimal] = None
    total_value: Optional[Decimal] = None
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
    # 盘盈入库时若商品无 average_cost 且无 purchase_price，必须显式提供 unit_cost
    # 否则零成本入库会污染 StockMove.total_cost_l2 和后续 COGS
    unit_cost: Optional[float] = Field(default=None, ge=0, description="盘盈估值单价（实物商品无成本时必填）")


# ── 退货（部分冲红）──

class ReturnItemCreate(BaseModel):
    """退货明细"""
    product_id: int
    quantity: int = Field(..., gt=0, description="退货数量（必须>0）")


class SaleReturnCreate(BaseModel):
    """销售退货请求"""
    return_date: str = Field(..., description="退货业务日期 YYYY-MM-DD")
    reason: str = Field(default="", max_length=500, description="退货原因")
    items: List[ReturnItemCreate] = Field(..., min_length=1)


class PurchaseReturnCreate(BaseModel):
    """采购退货请求"""
    return_date: str = Field(..., description="退货业务日期 YYYY-MM-DD")
    reason: str = Field(default="", max_length=500, description="退货原因")
    items: List[ReturnItemCreate] = Field(..., min_length=1)
