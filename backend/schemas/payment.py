"""付款/收款 Schema"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


class PaymentBase(BaseModel):
    payment_type: str = Field(..., pattern="^(expense|purchase|salary|tax)$", description="付款类型: expense/purchase/salary/tax(缴税清负债)")
    related_entity_type: str = Field(..., description="关联实体类型: expense/purchase_order/tax_payable")
    related_entity_id: int = Field(..., description="关联实体ID")
    amount: Decimal = Field(..., max_digits=12, decimal_places=2, description="付款金额（冲红可为负）")
<<<<<<< Updated upstream
=======
    withholding_tax_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2,
        description="代扣个人所得税(仅 payment_type=salary 时使用,实发=amount,代扣=withholding_tax_amount,应发=amount+withholding_tax_amount)")
>>>>>>> Stashed changes
    payment_method: str = Field(default="company", description="付款方式: company/private_advance")
    payment_date: datetime = Field(..., description="付款日期")
    bank_account_id: Optional[int] = Field(None, description="银行账户ID")
    description: str = Field(default="", description="描述")


class PaymentCreate(PaymentBase):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="付款金额")


class PaymentOut(PaymentBase):
    id: int
    account_id: int
    amount: Decimal = Field(validation_alias="amount_l1")
    withholding_tax_amount: Decimal = Field(default=Decimal("0"), validation_alias="withholding_tax_amount_l1")
    payment_date: datetime = Field(validation_alias="payment_date_l1")
    bank_transaction_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
