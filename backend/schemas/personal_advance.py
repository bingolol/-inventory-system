"""其他应付款/个人垫付 — Pydantic 模式"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

from enums import PERSONAL_ADVANCE_DEBIT_ACCOUNTS


class PersonalAdvanceBase(BaseModel):
    advancer_name: str = Field(..., min_length=1, max_length=100, description="垫付人姓名")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="垫付金额")
    advance_date: date = Field(..., description="垫付日期 YYYY-MM-DD")
    debit_account_code: str = Field(default="6601", description="借方科目编码")
    description: str = Field(default="", max_length=500)
    image_url: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _validate_debit_account(self):
        if self.debit_account_code not in PERSONAL_ADVANCE_DEBIT_ACCOUNTS:
            raise ValueError(
                f"debit_account_code '{self.debit_account_code}' 不合法，"
                f"合法值: {PERSONAL_ADVANCE_DEBIT_ACCOUNTS}"
            )
        return self


class PersonalAdvanceCreate(PersonalAdvanceBase):
    pass


class PersonalAdvanceOut(BaseModel):
    id: int
    account_id: int
    advance_no: str
    advancer_name: str
    amount: Decimal
    advance_date: datetime
    debit_account_code: str
    description: str
    image_url: str = ""
    repayment_status: str
    paid_amount: Decimal
    remaining_amount: Decimal = Field(default=Decimal("0"), description="未偿还余额 = amount - paid_amount")
    is_reversed: bool = False
    reversed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonalAdvanceRepaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="偿还金额")
    repayment_date: date = Field(..., description="偿还日期 YYYY-MM-DD")
    bank_account_id: Optional[int] = Field(default=None, description="银行账户ID，不传则走库存现金1001")
    description: str = Field(default="", max_length=500)


class PersonalAdvanceRepaymentOut(BaseModel):
    id: int
    account_id: int
    advance_id: int
    amount: Decimal
    repayment_date: datetime
    bank_account_id: Optional[int] = None
    bank_transaction_id: Optional[int] = None
    description: str
    is_reversed: bool = False
    reversed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PersonalAdvanceSummary(BaseModel):
    """按垫付人聚合的汇总"""
    advancer_name: str
    advance_count: int
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
