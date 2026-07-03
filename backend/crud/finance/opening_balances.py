"""期初余额查询"""

from datetime import datetime
from sqlalchemy.orm import Session
import models
def get_opening_balance(db: Session, account_id: int, opening_balance_id: int):
    return db.query(models.OpeningBalance).filter(
        models.OpeningBalance.account_id == account_id,
        models.OpeningBalance.id == opening_balance_id,
        models.OpeningBalance.is_reversed == False,
    ).first()


def get_opening_balance_by_date(db: Session, account_id: int, date: str):
    return db.query(models.OpeningBalance).filter(
        models.OpeningBalance.account_id == account_id,
        models.OpeningBalance.date_l1 == datetime.strptime(date, "%Y-%m-%d").date(),
        models.OpeningBalance.is_reversed == False,
    ).first()


def list_opening_balances(db: Session, account_id: int):
    return db.query(models.OpeningBalance).filter(
        models.OpeningBalance.account_id == account_id,
        models.OpeningBalance.is_reversed == False,
    ).order_by(models.OpeningBalance.date_l1.desc()).all()


def delete_opening_balance(db: Session, account_id: int, opening_balance_id: int, operator: str = "user"):
    """删除期初余额：通过 Command 走冲红凭证 + 标记作废，不再物理删除。"""
    from commands import dispatch
    from commands.finance_commands import DeleteOpeningBalance
    return dispatch(DeleteOpeningBalance(
        account_id=account_id,
        operator=operator,
        opening_balance_id=opening_balance_id,
    ), db)


def get_latest_opening_balance(db: Session, account_id: int, date: str = None):
    query = db.query(models.OpeningBalance).filter(
        models.OpeningBalance.account_id == account_id,
        models.OpeningBalance.is_reversed == False,
    )
    if date:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
        query = query.filter(models.OpeningBalance.date_l1 <= query_date)
    return query.order_by(models.OpeningBalance.date_l1.desc()).first()
