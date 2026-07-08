"""供应商 + 客户 读取 CRUD

写操作已迁移至 commands 层（CreatePartner/UpdatePartner/DeletePartner）。
本模块仅保留 list/get 查询函数，供 routers 直接调用。
"""

from sqlalchemy.orm import Session
import models
from utils import get_or_404


# ── 供应商 ──

def list_suppliers(db: Session, account_id: int, skip: int = 0, limit: int = 100, search: str = None):
    q = db.query(models.Supplier).filter(models.Supplier.account_id == account_id)
    if search:
        q = q.filter(models.Supplier.name.contains(search))
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return total, items


def get_supplier(db: Session, account_id: int, supplier_id: int):
    return get_or_404(db, models.Supplier, supplier_id, account_id)


# ── 客户 ──

def list_customers(db: Session, account_id: int, skip: int = 0, limit: int = 100, search: str = None):
    q = db.query(models.Customer).filter(models.Customer.account_id == account_id)
    if search:
        q = q.filter(models.Customer.name.contains(search))
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return total, items


def get_customer(db: Session, account_id: int, customer_id: int):
    return get_or_404(db, models.Customer, customer_id, account_id)