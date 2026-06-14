from pydantic import BaseModel
from datetime import datetime


class AccountOut(BaseModel):
    id: int
    name: str
    type: str
    code: str
    taxpayer_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountUpdate(BaseModel):
    name: str


class AccountCreate(BaseModel):
    name: str
    type: str = "company"
    code: str = ""
    taxpayer_type: str = "small_scale"