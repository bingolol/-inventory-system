"""个人流水账 CRUD（含事务包裹和金额精度）"""

import logging
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
import models, schemas

logger = logging.getLogger("inventory")

Q2 = Decimal('0.01')

def _d(val):
    """安全转换为 Decimal"""
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def list_personal_transactions(db: Session, account_id: int, skip: int = 0, limit: int = 100, type: str = None, category: str = None, start_date: str = None, end_date: str = None):
    q = db.query(models.PersonalTransaction).filter(models.PersonalTransaction.account_id == account_id)
    if type:
        q = q.filter(models.PersonalTransaction.type == type)
    if category:
        q = q.filter(models.PersonalTransaction.category == category)
    if start_date:
        q = q.filter(models.PersonalTransaction.date >= start_date)
    if end_date:
        q = q.filter(models.PersonalTransaction.date <= end_date + " 23:59:59")
    total = q.count()
    sum_income = q.filter(models.PersonalTransaction.type == "income").with_entities(sqlfunc.sum(models.PersonalTransaction.amount)).scalar() or 0
    sum_expense = q.filter(models.PersonalTransaction.type == "expense").with_entities(sqlfunc.sum(models.PersonalTransaction.amount)).scalar() or 0
    items = q.order_by(models.PersonalTransaction.date.desc()).offset(skip).limit(limit).all()
    return total, items, _d(sum_income).quantize(Q2), _d(sum_expense).quantize(Q2)


def create_personal_transaction(db: Session, account_id: int, data: schemas.PersonalTransactionCreate):
    tx = models.PersonalTransaction(
        account_id=account_id,
        type=data.type,
        amount=data.amount,
        category=data.category,
        description=data.description,
        image_url=data.image_url or "",
        date=datetime.strptime(data.date, "%Y-%m-%d") if data.date else datetime.now()
    )
    db.add(tx)
    db.flush()
    return tx


def update_personal_transaction(db: Session, account_id: int, tx_id: int, data: schemas.PersonalTransactionUpdate):
    tx = db.query(models.PersonalTransaction).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.id == tx_id
    ).first()
    if not tx:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "date" and v:
            v = datetime.strptime(v, "%Y-%m-%d")
        setattr(tx, k, v)
    db.flush()
    return tx


def delete_personal_transaction(db: Session, account_id: int, tx_id: int):
    tx = db.query(models.PersonalTransaction).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.id == tx_id
    ).first()
    if not tx:
        return False
    db.delete(tx)
    db.flush()
    return True


def get_personal_category_summary(db: Session, account_id: int, type: str = None, start_date: str = None, end_date: str = None):
    q = db.query(
        models.PersonalTransaction.category,
        sqlfunc.sum(models.PersonalTransaction.amount).label("total")
    ).filter(models.PersonalTransaction.account_id == account_id)
    if type:
        q = q.filter(models.PersonalTransaction.type == type)
    if start_date:
        q = q.filter(models.PersonalTransaction.date >= start_date)
    if end_date:
        q = q.filter(models.PersonalTransaction.date <= end_date + " 23:59:59")
    results = q.group_by(models.PersonalTransaction.category).order_by(sqlfunc.sum(models.PersonalTransaction.amount).desc()).all()
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
        q = db.query(sqlfunc.sum(models.PersonalTransaction.amount)).filter(
            models.PersonalTransaction.account_id == account_id,
            models.PersonalTransaction.date >= month_start,
            models.PersonalTransaction.date <= month_end
        )
        if type:
            q = q.filter(models.PersonalTransaction.type == type)
        total = q.scalar() or 0
        data.append({
            "month": month_key,
            "label": f"{y}年{m:02d}月",
            "total": _d(total).quantize(Q2)
        })
    return data


def get_personal_summary(db: Session, account_id: int):
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    month_income = db.query(sqlfunc.sum(models.PersonalTransaction.amount)).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.type == "income",
        models.PersonalTransaction.date >= month_start
    ).scalar() or 0

    month_expense = db.query(sqlfunc.sum(models.PersonalTransaction.amount)).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.type == "expense",
        models.PersonalTransaction.date >= month_start
    ).scalar() or 0

    total_income = db.query(sqlfunc.sum(models.PersonalTransaction.amount)).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.type == "income"
    ).scalar() or 0

    total_expense = db.query(sqlfunc.sum(models.PersonalTransaction.amount)).filter(
        models.PersonalTransaction.account_id == account_id,
        models.PersonalTransaction.type == "expense"
    ).scalar() or 0

    return schemas.PersonalSummary(
        month_income=_d(month_income).quantize(Q2),
        month_expense=_d(month_expense).quantize(Q2),
        month_balance=(_d(month_income) - _d(month_expense)).quantize(Q2),
        total_income=_d(total_income).quantize(Q2),
        total_expense=_d(total_expense).quantize(Q2),
        total_balance=(_d(total_income) - _d(total_expense)).quantize(Q2)
    )