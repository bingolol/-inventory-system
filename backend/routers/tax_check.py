"""税务核对 API — GET /api/tax/check?period=YYYY-MM&declared_xxx=..."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from account_dep import get_account_id
from engine_tax_check import TaxCheckEngine

router = APIRouter()


class TaxCheckResponse(BaseModel):
    period: str
    period_start: str
    period_end: str
    checks: list
    all_passed: bool
    warnings: list[str]


@router.get("/check", response_model=TaxCheckResponse)
def tax_check(
    period: str = Query(..., description="YYYY-MM"),
    declared_sales: Optional[float] = Query(None, alias="sales"),
    declared_output_vat: Optional[float] = Query(None, alias="output_vat"),
    declared_input_vat: Optional[float] = Query(None, alias="input_vat"),
    declared_unpaid_vat: Optional[float] = Query(None, alias="unpaid_vat"),
    declared_income_tax: Optional[float] = Query(None, alias="income_tax"),
    declared_surcharge: Optional[float] = Query(None, alias="surcharge"),
    declared_vat_payable: Optional[float] = Query(None, alias="vat_payable"),
    declared_gross_profit: Optional[float] = Query(None, alias="gross_profit"),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    declared = {}
    for key, val in [
        ("sales", declared_sales), ("output_vat", declared_output_vat),
        ("input_vat", declared_input_vat), ("unpaid_vat", declared_unpaid_vat),
        ("income_tax", declared_income_tax), ("surcharge", declared_surcharge),
        ("vat_payable", declared_vat_payable), ("gross_profit", declared_gross_profit),
    ]:
        if val is not None:
            declared[key] = val

    engine = TaxCheckEngine(db, account_id)
    return engine.execute(period, declared)
