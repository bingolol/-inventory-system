"""其他应付款/个人垫付 — Pydantic 模式"""

<<<<<<< Updated upstream
from pydantic import BaseModel, Field, model_validator
=======
from pydantic import BaseModel, Field, ConfigDict, model_validator
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
    amount: Decimal
    advance_date: datetime
=======
    amount: Decimal = Field(validation_alias="amount_l1")
    advance_date: datetime = Field(validation_alias="advance_date_l1")
>>>>>>> Stashed changes
    debit_account_code: str
    description: str
    image_url: str = ""
    repayment_status: str
<<<<<<< Updated upstream
    paid_amount: Decimal
=======
    paid_amount: Decimal = Field(validation_alias="paid_amount_l4")
>>>>>>> Stashed changes
    remaining_amount: Decimal = Field(default=Decimal("0"), description="未偿还余额 = amount - paid_amount")
    is_reversed: bool = False
    reversed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

<<<<<<< Updated upstream
    model_config = {"from_attributes": True}
=======
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
>>>>>>> Stashed changes


class PersonalAdvanceRepaymentCreate(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="偿还金额")
    repayment_date: date = Field(..., description="偿还日期 YYYY-MM-DD")
    bank_account_id: Optional[int] = Field(default=None, description="银行账户ID，不传则走库存现金1001")
    description: str = Field(default="", max_length=500)


class PersonalAdvanceRepaymentOut(BaseModel):
    id: int
    account_id: int
    advance_id: int
<<<<<<< Updated upstream
    amount: Decimal
    repayment_date: datetime
=======
    amount: Decimal = Field(validation_alias="amount_l1")
    repayment_date: datetime = Field(validation_alias="repayment_date_l1")
>>>>>>> Stashed changes
    bank_account_id: Optional[int] = None
    bank_transaction_id: Optional[int] = None
    description: str
    is_reversed: bool = False
    reversed_at: Optional[datetime] = None
    created_at: datetime

<<<<<<< Updated upstream
    model_config = {"from_attributes": True}
=======
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
>>>>>>> Stashed changes


class PersonalAdvanceSummary(BaseModel):
    """按垫付人聚合的汇总"""
    advancer_name: str
    advance_count: int
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
