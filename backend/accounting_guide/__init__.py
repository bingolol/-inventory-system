# ⚠️ 注意：本路由仅包含只读操作（GET），不需要 uow 包裹。
# 如未来新增写操作（POST/PUT/DELETE），务必使用 `with unit_of_work(db):` 包裹。

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import timedelta

from database import get_db
from models import Account
from account_dep import get_account_id
from utils import _d
from errors import BusinessError, ErrorCode
from policy.entity_profile import build_profile

from .helper import get_quarter_dates
from .basics import build_module_basics, build_module_statements
from .tax_modules import build_module_vat, build_module_income_tax, build_module_surcharge
from .static_modules import (
    build_module_month_close, build_module_expenses,
    build_module_cogs, build_module_reversal,
)

router = APIRouter()


@router.get("/accounting-guide")
async def get_accounting_guide(
    year: int = Query(..., description="年份"),
    quarter: int = Query(..., ge=1, le=4, description="季度 1-4"),
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND,
                            data={"order_type": "账本", "order_id": account_id})

    start_date, end_date = get_quarter_dates(year, quarter)
    profile = build_profile(account, ref_date=start_date.date())

    m1 = build_module_basics(db, account_id, start_date, end_date)
    m2 = build_module_vat(db, account_id, start_date, end_date, account)
    m3 = build_module_income_tax(db, account_id, start_date, end_date, account)
    m4 = build_module_surcharge(m2["vat_payable"], profile.surcharge_halved)
    m5 = build_module_month_close()
    m6 = build_module_expenses()
    m7 = build_module_cogs()
    m8 = build_module_reversal()
    m9 = build_module_statements(db, account_id, start_date, end_date)

    return {
        "profile": {
            "type": account.type, "name": account.name,
            "taxpayer_type": account.taxpayer_type_l3,
            "taxpayer_label": "小规模纳税人" if account.taxpayer_type_l3 == "small_scale" else "一般纳税人",
            "income_type": profile.income_type,
            "income_label": {
                "personal": "个体工商户（不缴企业所得税）",
                "small_micro": "小型微利企业（5%）",
                "general": "一般企业（25%）",
            }.get(profile.income_type, "未知"),
            "surcharge_halved": profile.surcharge_halved,
        },
        "period": {
            "year": year, "quarter": quarter, "label": f"{year}年第{quarter}季度",
            "start": start_date.strftime("%Y-%m-%d"),
            "end": (end_date - timedelta(days=1)).strftime("%Y-%m-%d"),
        },
        "module_1_basics": m1, "module_2_vat": m2, "module_3_income_tax": m3,
        "module_4_surcharge": m4, "module_5_month_close": m5, "module_6_expenses": m6,
        "module_7_cogs": m7, "module_8_reversal": m8, "module_9_statements": m9,
    }
