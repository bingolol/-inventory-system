from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# ── Invoice ──

class InvoiceBase(BaseModel):
    invoice_no: str = Field(..., max_length=50)
    direction: str = Field(..., pattern="^(in|out)$")
    invoice_type: str = Field(..., pattern="^(ordinary|special)$")
    tax_rate: Decimal = Field(..., ge=0, le=1, max_digits=12, decimal_places=2)
    amount_without_tax: Decimal = Field(..., max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(..., max_digits=12, decimal_places=2)
    amount_with_tax: Decimal = Field(..., max_digits=12, decimal_places=2)
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
    # 创建发票时金额必须非负（红字发票由系统 reverse 流程生成，不走此 schema）
    amount_without_tax: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    amount_with_tax: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)


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


class InvoiceItemCreate(BaseModel):
    """发票商品明细行"""
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, max_digits=12, decimal_places=6)
    tax_rate: Decimal = Field(..., ge=0, le=1, max_digits=12, decimal_places=2,
        description="行项税率，必填。一般纳税人13%/9%/6%，小规模1%，出口0%")


class InvoiceQuickCreate(BaseModel):
    invoice_no: str = Field(..., max_length=50)
    direction: str = Field(..., pattern="^(in|out)$")
    invoice_type: str = Field(..., pattern="^(ordinary|special)$")
    amount_with_tax: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2,
        description="税额（外部输入，发票上的实际税额。必须手动填写，系统不推导。0税率发票可填0）")
    tax_rate: Decimal = Field(..., ge=0, le=1, max_digits=12, decimal_places=2)
    counterparty_name: str = Field(..., max_length=200)
    seller_name: str = Field(..., max_length=200, description="销方名称")
    buyer_name: str = Field(..., max_length=200, description="买方名称")
    issue_date: str  # YYYY-MM-DD
    items: List[InvoiceItemCreate] = Field(..., min_length=1, description="商品明细（至少1行）")
    sale_order_action: Optional[str] = Field(None, pattern="^(link_existing|auto_create)$",
        description="销项发票必填：link_existing=关联已有销售单, auto_create=自动生成销售单")
    purchase_order_action: Optional[str] = Field(None, pattern="^(link_existing|auto_create)$",
        description="进项发票必填：link_existing=关联已有采购单, auto_create=自动生成采购单")
    related_order_id: Optional[int] = Field(None, description="关联订单ID（link_existing时必填）")
    related_order_type: Optional[str] = Field(None, pattern="^(sale_order|purchase_order|expense|fixed_asset)$")
    image_url: Optional[str] = None
    notes: str = ""
    # 可选：发票同时入账固定资产（合并自原 POST /with-fixed-asset）
    fixed_asset: Optional[FixedAssetBlock] = None

    @model_validator(mode="after")
    def validate_order_action(self):
        """销项发票必填 sale_order_action；进项发票必填 purchase_order_action；link_existing 时必填 related_order_id

        例外：携带 fixed_asset 块的进项发票走固定资产过账分支（dr 1601/222102 / cr 2202），
        不再生成采购单，因此 purchase_order_action 可留空。
        """
        if self.direction == "out":
            if not self.sale_order_action:
                raise ValueError("销项发票必填 sale_order_action（link_existing 或 auto_create）")
            if self.sale_order_action == "link_existing" and not self.related_order_id:
                raise ValueError("sale_order_action=link_existing 时必填 related_order_id")
        elif self.direction == "in":
            # 固定资产场景：跳过 purchase_order_action 强制校验
            if self.fixed_asset is None:
                if not self.purchase_order_action:
                    raise ValueError("进项发票必填 purchase_order_action（link_existing 或 auto_create），"
                                     "或携带 fixed_asset 块走固定资产过账分支")
                if self.purchase_order_action == "link_existing" and not self.related_order_id:
                    raise ValueError("purchase_order_action=link_existing 时必填 related_order_id")
        return self

    @model_validator(mode="after")
    def validate_tax_amount(self):
        """BR-27: tax_amount 必须手动输入，系统不推导。tax_rate > 0 时 tax_amount 必须 > 0。"""
        if self.tax_rate > 0 and self.tax_amount == 0:
            raise ValueError("tax_rate > 0 时 tax_amount 必须手动填写，系统不再内部推导税额（BR-27）")
        computed = self.amount_with_tax - self.tax_amount
        if computed < 0:
            raise ValueError(f"amount_with_tax ({self.amount_with_tax}) 不能小于 tax_amount ({self.tax_amount})")
        return self


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