from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ── Operation Log ──

class OperationLogOut(BaseModel):
    id: int
    operation: str
    entity_type: str
    entity_id: int
    detail: str
    operator: str = "user"
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Personal Transaction (个人流水账) ──

class PersonalTransactionCreate(BaseModel):
    type: str = Field(..., pattern="^(income|expense)$")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    category: str = ""
    description: str = ""
    image_url: str = ""
    date: Optional[str] = None


class PersonalTransactionUpdate(BaseModel):
    type: Optional[str] = None
    amount: Optional[Decimal] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    date: Optional[str] = None


class PersonalTransactionOut(BaseModel):
    id: int
    type: str
    amount: Decimal
    category: str
    description: str
    image_url: str = ""
    date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}