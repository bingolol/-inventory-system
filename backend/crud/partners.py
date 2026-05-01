"""供应商 + 客户 CRUD（含事务包裹 + 关联检查）"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import models, schemas

from .base import _log

logger = logging.getLogger("inventory")


# ── 供应商 ──

def list_suppliers(db: Session, account_id: int, skip: int = 0, limit: int = 100, search: str = None):
    q = db.query(models.Supplier).filter(models.Supplier.account_id == account_id)
    if search:
        q = q.filter(models.Supplier.name.contains(search))
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return total, items


def get_supplier(db: Session, account_id: int, supplier_id: int):
    return db.query(models.Supplier).filter(
        models.Supplier.account_id == account_id,
        models.Supplier.id == supplier_id
    ).first()


def create_supplier(db: Session, account_id: int, data: schemas.SupplierCreate):
    supplier = models.Supplier(account_id=account_id, **data.model_dump())
    db.add(supplier)
    db.flush()
    _log(db, account_id, "create", "supplier", supplier.id, f"创建供应商: {supplier.name}")
    return supplier


def update_supplier(db: Session, account_id: int, supplier_id: int, data: schemas.SupplierUpdate):
    supplier = get_supplier(db, account_id, supplier_id)
    if not supplier:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(supplier, k, v)
    _log(db, account_id, "update", "supplier", supplier_id, f"更新供应商: {supplier.name}")
    db.flush()
    return supplier


def delete_supplier(db: Session, account_id: int, supplier_id: int):
    supplier = get_supplier(db, account_id, supplier_id)
    if not supplier:
        return False
    # 关联检查：存在采购记录则拒绝删除
    po_count = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.supplier_id == supplier_id,
        models.PurchaseOrder.account_id == account_id
    ).count()
    if po_count > 0:
        raise ValueError(f"该供应商存在 {po_count} 条采购记录，无法删除")
    _log(db, account_id, "delete", "supplier", supplier_id, f"删除供应商: {supplier.name}")
    db.delete(supplier)
    db.flush()
    return True


# ── 客户 ──

def list_customers(db: Session, account_id: int, skip: int = 0, limit: int = 100, search: str = None):
    q = db.query(models.Customer).filter(models.Customer.account_id == account_id)
    if search:
        q = q.filter(models.Customer.name.contains(search))
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return total, items


def get_customer(db: Session, account_id: int, customer_id: int):
    return db.query(models.Customer).filter(
        models.Customer.account_id == account_id,
        models.Customer.id == customer_id
    ).first()


def create_customer(db: Session, account_id: int, data: schemas.CustomerCreate):
    customer = models.Customer(account_id=account_id, **data.model_dump())
    db.add(customer)
    db.flush()
    _log(db, account_id, "create", "customer", customer.id, f"创建客户: {customer.name}")
    return customer


def update_customer(db: Session, account_id: int, customer_id: int, data: schemas.CustomerUpdate):
    customer = get_customer(db, account_id, customer_id)
    if not customer:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(customer, k, v)
    _log(db, account_id, "update", "customer", customer_id, f"更新客户: {customer.name}")
    db.flush()
    return customer


def delete_customer(db: Session, account_id: int, customer_id: int):
    customer = get_customer(db, account_id, customer_id)
    if not customer:
        return False
    # 关联检查1：存在销售记录则拒绝
    so_count = db.query(models.SaleOrder).filter(
        models.SaleOrder.customer_id == customer_id,
        models.SaleOrder.account_id == account_id
    ).count()
    # 关联检查2：存在项目关联则拒绝
    proj_count = db.query(models.Project).filter(
        models.Project.customer_id == customer_id,
        models.Project.account_id == account_id
    ).count()
    if so_count > 0 or proj_count > 0:
        raise ValueError(f"该客户存在 {so_count} 条销售记录和 {proj_count} 个项目关联，无法删除")
    _log(db, account_id, "delete", "customer", customer_id, f"删除客户: {customer.name}")
    db.delete(customer)
    db.flush()
    return True