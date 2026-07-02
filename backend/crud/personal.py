"""个人流水账 查询 + 统计 CRUD

写操作已迁移至 commands 层（CreatePersonalTransaction/UpdatePersonalTransaction/DeletePersonalTransaction）。
本模块保留 list 查询和统计报表函数，供 routers 直接调用。
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
import models, schemas

from utils import _d, Q2


def list_personal_transactions(db: Session, account_id: int, skip: int = 0, limit: int = 100, type: str = None, category: str = None, start_date: str = None, end_date: str = None):
    q = db.query(models.PersonalTransaction).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.is_reversed == False,
    )
    if type:
        q = q.filter(models.PersonalTransaction.type == type)
    if category:
        q = q.filter(models.PersonalTransaction.category == category)
    if start_date:
        q = q.filter(models.PersonalTransaction.date_l1 >= start_date)
    if end_date:
        q = q.filter(models.PersonalTransaction.date_l1 <= end_date + " 23:59:59")
    total = q.count()
    sum_income = q.filter(models.PersonalTransaction.type == "income").with_entities(sqlfunc.sum(models.PersonalTransaction.amount_l1)).scalar()
    sum_income = sum_income if sum_income is not None else 0
    sum_expense = q.filter(models.PersonalTransaction.type == "expense").with_entities(sqlfunc.sum(models.PersonalTransaction.amount_l1)).scalar()
    sum_expense = sum_expense if sum_expense is not None else 0
    items = q.order_by(models.PersonalTransaction.date_l1.desc()).offset(skip).limit(limit).all()
    return total, items, _d(sum_income).quantize(Q2), _d(sum_expense).quantize(Q2)


def get_personal_category_summary(db: Session, account_id: int, type: str = None, start_date: str = None, end_date: str = None):
    q = db.query(
        models.PersonalTransaction.category,
        sqlfunc.sum(models.PersonalTransaction.amount_l1).label("total")
    ).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.is_reversed == False,
    )
    if type:
        q = q.filter(models.PersonalTransaction.type == type)
    if start_date:
        q = q.filter(models.PersonalTransaction.date_l1 >= start_date)
    if end_date:
        q = q.filter(models.PersonalTransaction.date_l1 <= end_date + " 23:59:59")
    results = q.group_by(models.PersonalTransaction.category).order_by(sqlfunc.sum(models.PersonalTransaction.amount_l1).desc()).all()
    return [{"category": r[0] or "未分类", "total": _d(r[1]).quantize(Q2)} for r in results]


def get_personal_monthly_summary(db: Session, account_id: int, type: str = None, months: int = 12):
    now = datetime.now()
    data = []
    seen_months = []
    for i in range(months - 1, -1, -1):
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        month_key = f"{y}-{m:02d}"
        if month_key in seen_months:
            continue
        seen_months.append(month_key)
        month_start = datetime(y, m, 1)
        import calendar
        last_day = calendar.monthrange(y, m)[1]
        month_end = datetime(y, m, last_day, 23, 59, 59)
        q = db.query(sqlfunc.sum(models.PersonalTransaction.amount_l1)).filter(
            models.PersonalTransaction.account_id == account_id,
            models.PersonalTransaction.date_l1 >= month_start,
            models.PersonalTransaction.date_l1 <= month_end,
            models.PersonalTransaction.is_reversed == False,
        )
        if type:
            q = q.filter(models.PersonalTransaction.type == type)
        total = q.scalar()
        total = total if total is not None else 0
        data.append({
            "month": month_key,
            "label": f"{y}年{m:02d}月",
            "total": _d(total).quantize(Q2)
        })
    return data


def get_personal_summary(db: Session, account_id: int):
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    month_income = db.query(sqlfunc.sum(models.PersonalTransaction.amount_l1)).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.type == "income",
        models.PersonalTransaction.date_l1 >= month_start,
        models.PersonalTransaction.is_reversed == False,
    ).scalar()
    month_income = month_income if month_income is not None else 0

    month_expense = db.query(sqlfunc.sum(models.PersonalTransaction.amount_l1)).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.type == "expense",
        models.PersonalTransaction.date_l1 >= month_start,
        models.PersonalTransaction.is_reversed == False,
    ).scalar()
    month_expense = month_expense if month_expense is not None else 0

    total_income = db.query(sqlfunc.sum(models.PersonalTransaction.amount_l1)).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.type == "income",
        models.PersonalTransaction.is_reversed == False,
    ).scalar()
    total_income = total_income if total_income is not None else 0

    total_expense = db.query(sqlfunc.sum(models.PersonalTransaction.amount_l1)).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.type == "expense",
        models.PersonalTransaction.is_reversed == False,
    ).scalar()
    total_expense = total_expense if total_expense is not None else 0

    return schemas.PersonalSummary(
        month_income=_d(month_income).quantize(Q2),
        month_expense=_d(month_expense).quantize(Q2),
        month_balance=(_d(month_income) - _d(month_expense)).quantize(Q2),
        total_income=_d(total_income).quantize(Q2),
        total_expense=_d(total_expense).quantize(Q2),
        total_balance=(_d(total_income) - _d(total_expense)).quantize(Q2)
    )