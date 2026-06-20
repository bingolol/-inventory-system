"""付款/收款 Schema"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class PaymentBase(BaseModel):
    payment_type: str = Field(..., pattern="^(expense|purchase|salary|tax)$", description="付款类型: expense/purchase/salary/tax(缴税清负债)")
    related_entity_type: str = Field(..., description="关联实体类型: expense/purchase_order/tax_payable")
    related_entity_id: int = Field(..., description="关联实体ID")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="付款金额")
    payment_method: str = Field(default="company", description="付款方式: company/private_advance")
    payment_date: datetime = Field(..., description="付款日期")
    bank_account_id: Optional[int] = Field(None, description="银行账户ID")
    description: str = Field(default="", max_length=500, description="描述")


class PaymentCreate(PaymentBase):
    pass


class PaymentOut(PaymentBase):
    id: int
    account_id: int
    bank_transaction_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
