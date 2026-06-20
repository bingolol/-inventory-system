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
    related_order_type: Optional[str] = Field(None, pattern="^(sale_order|purchase_order|expense|fixed_asset)$")
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


class FixedAssetBlock(BaseModel):
    """发票关联固定资产的嵌套对象（用于 /quick 合并原 /with-fixed-asset 能力）

    当发票同时入账一项固定资产（如购入设备）时，携带本对象，
    系统会在同一事务内原子创建发票 + 固定资产并自动关联。
    """
    asset_code: str = Field(..., max_length=50)
    asset_name: str = Field(..., max_length=100)
    category: Optional[str] = None
    salvage_rate: Decimal = Field(default=Decimal('0.05'), ge=0, le=1)
    useful_life: int = Field(..., gt=0)
    depreciation_method: str = Field(default="年限平均法")
    start_date: str  # YYYY-MM-DD
    accumulated_depreciation: Decimal = Field(default=Decimal('0'), ge=0)
    asset_status: str = Field(default="在用")


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
    # 可选：发票同时入账固定资产（合并自原 POST /with-fixed-asset）
    fixed_asset: Optional[FixedAssetBlock] = None


class InvoiceList(BaseModel):
    total: int
    items: List[InvoiceOut]


class InvoiceWithFixedAssetCreate(BaseModel):
    """发票 + 固定资产联合创建"""
    # 发票字段
    invoice_no: str = Field(..., max_length=50)
    direction: str = Field(default="in", pattern="^(in|out)$")
    invoice_type: str = Field(default="ordinary", pattern="^(ordinary|special)$")
    tax_rate: Decimal = Field(..., ge=0, le=1, max_digits=12, decimal_places=2)
    amount_with_tax: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    counterparty_name: str = Field(..., max_length=200)
    issue_date: str  # YYYY-MM-DD
    notes: str = ""

    # 固定资产字段
    asset_code: str = Field(..., max_length=50)
    asset_name: str = Field(..., max_length=100)
    category: Optional[str] = None
    salvage_rate: Decimal = Field(default=Decimal('0.05'), ge=0, le=1)
    useful_life: int = Field(..., gt=0)
    depreciation_method: str = Field(default="年限平均法")
    start_date: str  # YYYY-MM-DD
    accumulated_depreciation: Decimal = Field(default=Decimal('0'), ge=0)
    asset_status: str = Field(default="在用")


class InvoiceWithFixedAssetUpdate(BaseModel):
    """发票 + 固定资产联合更新（联动）"""
    # 发票可更新字段
    amount_with_tax: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2)
    tax_rate: Optional[Decimal] = Field(None, ge=0, le=1, max_digits=12, decimal_places=2)
    counterparty_name: Optional[str] = None
    issue_date: Optional[str] = None
    notes: Optional[str] = None

    # 资产可更新字段
    asset_name: Optional[str] = None
    category: Optional[str] = None
    salvage_rate: Optional[Decimal] = None
    useful_life: Optional[int] = None
    depreciation_method: Optional[str] = None
    start_date: Optional[str] = None
    asset_status: Optional[str] = None