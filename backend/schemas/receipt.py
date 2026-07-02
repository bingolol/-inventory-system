"""收款 Schema"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


class ReceiptBase(BaseModel):
    receipt_type: str = Field(..., description="收款类型: sale")
    related_entity_type: str = Field(..., description="关联实体类型: sale_order")
    related_entity_id: int = Field(..., description="关联实体ID")
    amount: Decimal = Field(..., max_digits=12, decimal_places=2, description="收款金额（冲红可为负）")
    receipt_method: str = Field(default="company", description="收款方式: company/private_advance")
    receipt_date: datetime = Field(..., description="收款日期")
    bank_account_id: Optional[int] = Field(None, description="银行账户ID")
    description: str = Field(default="", description="描述")


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
