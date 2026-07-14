"""收款 Schema"""

from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ReceiptBase(BaseModel):
    receipt_type: Optional[str] = Field(None, description="收款类型: sale")
    related_entity_type: Optional[str] = Field(None, description="关联实体类型: sale_order")
    related_entity_id: Optional[int] = Field(None, description="关联实体ID")
    sale_order_id: Optional[int] = Field(None, description="销售单ID捷径字段，自动填充以上三字段")
    amount: Decimal = Field(..., max_digits=12, decimal_places=2, description="收款金额（冲红可为负）")
    receipt_method: str = Field(default="company", description="收款方式: company/private_advance")
    receipt_date: datetime = Field(..., description="收款日期")
    bank_account_id: Optional[int] = Field(None, description="银行账户ID")
    description: str = Field(default="", description="描述")

    @model_validator(mode="after")
    def _apply_sale_order_shortcut(self):
        if self.sale_order_id is not None:
            self.receipt_type = "sale"
            self.related_entity_type = "sale_order"
            self.related_entity_id = self.sale_order_id
        else:
            if not self.receipt_type or not self.related_entity_type or self.related_entity_id is None:
                raise ValueError("provide sale_order_id OR (receipt_type + related_entity_type + related_entity_id)")
        return self


class ReceiptCreate(ReceiptBase):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="收款金额")


class ReceiptOut(ReceiptBase):
    id: int
    account_id: int
    amount: Decimal = Field(validation_alias="amount_l1")
    receipt_date: datetime = Field(validation_alias="receipt_date_l1")
    bank_transaction_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
