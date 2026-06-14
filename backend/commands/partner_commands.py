"""供应商 + 客户 Command + Handler — 6个命令覆盖伙伴管理全部写操作

从 crud/partners.py 提取，Command 模式封装。
每个 Handler 包含：数据校验 → ORM 操作 → 日志记录。
"""

from dataclasses import dataclass
from typing import Any, Optional

import models

from .base import Command, CommandHandler, register
from .crud_compat import _log


# ═══════════════════════════════════════════════════════════
# 1. CreateSupplier — 创建供应商
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateSupplier(Command):
    name: str = ""
    contact: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""


@register(CreateSupplier)
class CreateSupplierHandler(CommandHandler):
    def handle(self, cmd: CreateSupplier, db: Any) -> Any:
        supplier = models.Supplier(
            account_id=cmd.account_id,
            name=cmd.name,
            contact=cmd.contact,
            phone=cmd.phone,
            address=cmd.address,
            notes=cmd.notes,
        )
        db.add(supplier)
        db.flush()

        _log(db, cmd.account_id, "create", "supplier", supplier.id,
             f"创建供应商: {supplier.name}", operator=cmd.operator)
        return supplier


# ═══════════════════════════════════════════════════════════
# 2. UpdateSupplier — 更新供应商
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateSupplier(Command):
    supplier_id: int = 0
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


@register(UpdateSupplier)
class UpdateSupplierHandler(CommandHandler):
    def handle(self, cmd: UpdateSupplier, db: Any) -> Any:
        supplier = db.query(models.Supplier).filter(
            models.Supplier.account_id == cmd.account_id,
            models.Supplier.id == cmd.supplier_id,
        ).first()
        if not supplier:
            return None

        updates = {
            'name': cmd.name,
            'contact': cmd.contact,
            'phone': cmd.phone,
            'address': cmd.address,
            'notes': cmd.notes,
        }
        for k, v in updates.items():
            if v is not None:
                setattr(supplier, k, v)

        _log(db, cmd.account_id, "update", "supplier", supplier.id,
             f"更新供应商: {supplier.name}", operator=cmd.operator)
        db.flush()
        return supplier


# ═══════════════════════════════════════════════════════════
# 3. DeleteSupplier — 删除供应商（含业务约束校验）
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteSupplier(Command):
    supplier_id: int = 0


@register(DeleteSupplier)
class DeleteSupplierHandler(CommandHandler):
    def handle(self, cmd: DeleteSupplier, db: Any) -> bool:
        # 1. 查询供应商
        supplier = db.query(models.Supplier).filter(
            models.Supplier.account_id == cmd.account_id,
            models.Supplier.id == cmd.supplier_id,
        ).first()
        if not supplier:
            return False

        # 2. 业务约束校验：存在采购记录则拒绝删除
        po_count = db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.supplier_id == cmd.supplier_id,
            models.PurchaseOrder.account_id == cmd.account_id,
        ).count()
        if po_count > 0:
            raise ValueError(f"该供应商存在 {po_count} 条采购记录，无法删除")

        # 3. 删除
        _log(db, cmd.account_id, "delete", "supplier", supplier.id,
             f"删除供应商: {supplier.name}", operator=cmd.operator)
        db.delete(supplier)
        db.flush()
        return True


# ═══════════════════════════════════════════════════════════
# 4. CreateCustomer — 创建客户
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateCustomer(Command):
    name: str = ""
    contact: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""


@register(CreateCustomer)
class CreateCustomerHandler(CommandHandler):
    def handle(self, cmd: CreateCustomer, db: Any) -> Any:
        customer = models.Customer(
            account_id=cmd.account_id,
            name=cmd.name,
            contact=cmd.contact,
            phone=cmd.phone,
            address=cmd.address,
            notes=cmd.notes,
        )
        db.add(customer)
        db.flush()

        _log(db, cmd.account_id, "create", "customer", customer.id,
             f"创建客户: {customer.name}", operator=cmd.operator)
        return customer


# ═══════════════════════════════════════════════════════════
# 5. UpdateCustomer — 更新客户
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateCustomer(Command):
    customer_id: int = 0
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


@register(UpdateCustomer)
class UpdateCustomerHandler(CommandHandler):
    def handle(self, cmd: UpdateCustomer, db: Any) -> Any:
        customer = db.query(models.Customer).filter(
            models.Customer.account_id == cmd.account_id,
            models.Customer.id == cmd.customer_id,
        ).first()
        if not customer:
            return None

        updates = {
            'name': cmd.name,
            'contact': cmd.contact,
            'phone': cmd.phone,
            'address': cmd.address,
            'notes': cmd.notes,
        }
        for k, v in updates.items():
            if v is not None:
                setattr(customer, k, v)

        _log(db, cmd.account_id, "update", "customer", customer.id,
             f"更新客户: {customer.name}", operator=cmd.operator)
        db.flush()
        return customer


# ═══════════════════════════════════════════════════════════
# 6. DeleteCustomer — 删除客户（含业务约束校验）
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteCustomer(Command):
    customer_id: int = 0


@register(DeleteCustomer)
class DeleteCustomerHandler(CommandHandler):
    def handle(self, cmd: DeleteCustomer, db: Any) -> bool:
        # 1. 查询客户
        customer = db.query(models.Customer).filter(
            models.Customer.account_id == cmd.account_id,
            models.Customer.id == cmd.customer_id,
        ).first()
        if not customer:
            return False

        # 2. 业务约束校验：存在销售记录则拒绝
        so_count = db.query(models.SaleOrder).filter(
            models.SaleOrder.customer_id == cmd.customer_id,
            models.SaleOrder.account_id == cmd.account_id,
        ).count()
        if so_count > 0:
            raise ValueError(
                f"该客户存在 {so_count} 条销售记录，无法删除"
            )

        # 3. 删除
        _log(db, cmd.account_id, "delete", "customer", customer.id,
             f"删除客户: {customer.name}", operator=cmd.operator)
        db.delete(customer)
        db.flush()
        return True
