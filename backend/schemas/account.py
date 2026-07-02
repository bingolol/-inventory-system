from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class AccountOut(BaseModel):
    id: int
    name: str
    type: str
    code: str
    taxpayer_type: str = Field(validation_alias="taxpayer_type_l3")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AccountUpdate(BaseModel):
    name: str


class AccountCreate(BaseModel):
    name: str
    type: str = "company"
    code: str = ""
    taxpayer_type: str = "small_scale"