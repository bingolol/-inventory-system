# ⚠️ 注意：本路由当前仅包含只读操作（GET），不需要 uow 包裹。
# 如未来新增写操作（POST/PUT/DELETE），务必使用 `with unit_of_work(db):` 包裹。
#
# 企业所得税报表 — 会计准则口径（总账说话）
# 收入/成本/费用/利润全部取自《小企业会计准则》利润表，确保与财务报表一致。

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from database import get_db
from models import Account
from schemas import IncomeTaxReport
from account_dep import get_account_id
from utils import _d, Q2
from errors import BusinessError, ErrorCode
from accounting_engine import AccountingEngine
from crud.finance.income_statement import generate_income_statement

router = APIRouter()
_engine = AccountingEngine()


def _get_date_range(year: int, quarter: Optional[int]):
    """计算起止日期"""
    if quarter and 1 <= quarter <= 4:
        quarter_start_month = (quarter - 1) * 3 + 1
        start_date = datetime(year, quarter_start_month, 1)
        if quarter == 4:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, quarter_start_month + 3, 1)
    else:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year + 1, 1, 1)
    return start_date, end_date


def _calc_accounting_caliber(db: Session, account_id: int, start_date: datetime, end_date: datetime):
    """会计准则口径：直接复用利润表，避免税务/财务双轨。"""
    is_data = generate_income_statement(
        db, account_id,
        start_date.strftime("%Y-%m-%d"),
        (end_date - timedelta(days=1)).strftime("%Y-%m-%d")
    )

    revenue = _d(is_data.get("revenue", 0))
    cost = _d(is_data.get("cost_of_goods_sold", 0))
    tax_surcharge = _d(is_data.get("tax_surcharges", 0))
    operating_expenses = _d(is_data.get("total_operating_expenses", 0)) - tax_surcharge
    gross_profit = _d(is_data.get("gross_profit", 0))
    non_operating_income = _d(is_data.get("non_operating_income", 0))
    non_operating_expense = _d(is_data.get("non_operating_expense", 0))
    gross_profit_total = _d(is_data.get("gross_profit_total", 0))

    return {
        "revenue": revenue,
        "cost": cost,
        "tax_surcharge": tax_surcharge,
        "operating_expenses": operating_expenses,
        "gross_profit": gross_profit,
        "non_operating_income": non_operating_income,
        "non_operating_expense": non_operating_expense,
        "taxable_income": gross_profit_total,
    }


@router.get("", response_model=IncomeTaxReport)
async def get_income_tax_report(
    year: int,
    quarter: Optional[int] = None,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id)
):
    """获取企业所得税报表（会计准则口径：利润表说话）"""
    # 获取账本信息
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "账本", "order_id": account_id})

    start_date, end_date = _get_date_range(year, quarter)

    # 会计准则口径：直接复用利润表（总账 6001/6401/6403/6601-6603/6301/6701 等）
    data = _calc_accounting_caliber(db, account_id, start_date, end_date)

    revenue = data["revenue"]
    cost = data["cost"]
    expenses = data["operating_expenses"]
    taxable_income = data["taxable_income"]
    if taxable_income < 0:
        taxable_income = Decimal('0')

    # 使用 AccountingEngine 计算所得税
    raw_type = account.taxpayer_type_l3 if account.taxpayer_type_l3 else "small_scale"
    taxpayer_type = "small_micro" if raw_type in ("small_scale", "small_micro") else "general"
    entity_type = account.type if account.type else "company"
    tax_result = _engine.calculate_income_tax(
        profit=taxable_income,
        taxpayer_type=taxpayer_type,
        entity_type=entity_type,
    )

    # 构建报表
    report = IncomeTaxReport(
        year=year,
        quarter=quarter,
        account_id=account_id,
        total_revenue=revenue.quantize(Q2),
        total_cost=cost.quantize(Q2),
        operating_expenses=expenses.quantize(Q2),
        gross_profit=data["gross_profit"].quantize(Q2),
        taxable_income=taxable_income.quantize(Q2),
        tax_rate=tax_result.tax_rate,
        tax_amount=tax_result.tax_payable,
    )

    return report