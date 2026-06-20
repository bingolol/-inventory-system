"""银行账户/流水 Schema"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class BankAccountBase(BaseModel):
    bank_name: str = Field(..., max_length=100, description="银行名称")
    account_number: str = Field(..., max_length=50, description="银行账号")
    balance: Decimal = Field(default=Decimal('0'), ge=0, max_digits=12, decimal_places=2, description="当前余额")
    description: str = Field(default="", max_length=500, description="描述")


class BankAccountCreate(BankAccountBase):
    pass


class BankAccountUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    balance: Optional[Decimal] = None
    description: Optional[str] = None


class BankAccountOut(BankAccountBase):
    id: int
    account_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BankAccountList(BaseModel):
    total: int
    items: List[BankAccountOut]


# ── 银行流水 Schema ──

class BankTransactionBase(BaseModel):
    bank_account_id: int = Field(..., description="银行账户ID")
    transaction_type: str = Field(..., pattern="^(inflow|outflow)$", description="类型: inflow/outflow")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="金额")
    transaction_date: datetime = Field(..., description="交易日期")
    description: str = Field(default="", max_length=500, description="描述")
    reference_no: str = Field(..., min_length=1, max_length=100, description="银行流水号（必填，用于对账）")


class BankTransactionCreate(BankTransactionBase):
    pass


class BankTransactionOut(BankTransactionBase):
    id: int
    account_id: int
    balance_after: Decimal
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}
