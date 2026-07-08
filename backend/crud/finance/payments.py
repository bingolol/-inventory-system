"""付款/收款查询"""

from sqlalchemy.orm import Session
import models
from utils import get_or_404

def list_payments(db: Session, account_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Payment).filter(
        models.Payment.account_id == account_id
    ).order_by(models.Payment.payment_date_l1.desc()).offset(skip).limit(limit).all()


def get_payment(db: Session, account_id: int, payment_id: int):
    return get_or_404(db, models.Payment, payment_id, account_id)


def list_receipts(db: Session, account_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Receipt).filter(
        models.Receipt.account_id == account_id
    ).order_by(models.Receipt.receipt_date_l1.desc()).offset(skip).limit(limit).all()


def get_receipt(db: Session, account_id: int, receipt_id: int):
    return get_or_404(db, models.Receipt, receipt_id, account_id)