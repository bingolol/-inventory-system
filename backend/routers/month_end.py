"""月结 API — POST /api/finance/month-close"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from database import get_db
from account_dep import get_account_id, get_operator
from uow import unit_of_work
from commands.base import dispatch
from commands.month_end import MonthEndClose

router = APIRouter()


class MonthEndCloseRequest(BaseModel):
    period: str  # YYYY-MM
    force: bool = False  # 强制重跑:冲红旧 period_close/year_close 凭证后重做

    @field_validator("period")
    @classmethod
    def validate_period(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", v):
            raise ValueError("period 格式必须为 YYYY-MM")
        return v


@router.post("/month-close")
def month_end_close(
    body: MonthEndCloseRequest,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    with unit_of_work(db):
        result = dispatch(MonthEndClose(
            account_id=account_id,
            operator=operator,
            period=body.period,
            force=body.force,
        ), db)
    return result
