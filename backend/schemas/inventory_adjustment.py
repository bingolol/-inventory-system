from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InventoryAdjustmentCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., description="调整数量（正=入库，负=出库）")
    reason: str = Field(default="other", pattern=r"^(inventory_count|spoilage|exchange|other)$")
    notes: str = ""


class InventoryAdjustmentOut(BaseModel):
    id: int
    account_id: int
    product_id: int
    quantity: int
    reason: str
    notes: str
    operator: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
