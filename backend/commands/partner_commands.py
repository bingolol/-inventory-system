"""供应商 + 客户 Command + Handler — 3个通用命令覆盖伙伴管理全部写操作

Supplier 和 Customer 共享相同的 CRUD 模式，通过 partner_type 参数化区分。
"""

from dataclasses import dataclass
from typing import Any, Optional

import models

from .base import Command, CommandHandler, register
from crud.base import _log
from errors import BusinessError, ErrorCode


# ═══════════════════════════════════════════════════════════
# 伙伴类型配置
# ═══════════════════════════════════════════════════════════

PARTNER_CONFIG = {
    "supplier": {
        "model": models.Supplier,
        "id_field": "supplier_id",
        "constraint_model": models.PurchaseOrder,
        "constraint_fk": "supplier_id",
        "error_code": ErrorCode.SUPPLIER_HAS_ORDERS,
        "label": "供应商",
    },
    "customer": {
        "model": models.Customer,
        "id_field": "customer_id",
        "constraint_model": models.SaleOrder,
        "constraint_fk": "customer_id",
        "error_code": ErrorCode.CUSTOMER_HAS_ORDERS,
        "label": "客户",
    },
}


# ═══════════════════════════════════════════════════════════
# 1. CreatePartner — 创建伙伴
# ═══════════════════════════════════════════════════════════

@dataclass
class CreatePartner(Command):
    partner_type: str = ""
    name: str = ""
    contact: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""


@register(CreatePartner)
class CreatePartnerHandler(CommandHandler):
    def handle(self, cmd: CreatePartner, db: Any) -> Any:
        cfg = PARTNER_CONFIG[cmd.partner_type]
        entity = cfg["model"](
            account_id=cmd.account_id,
            name=cmd.name,
            contact=cmd.contact,
            phone=cmd.phone,
            address=cmd.address,
            notes=cmd.notes,
        )
        db.add(entity)
        db.flush()
        _log(db, cmd.account_id, "create", cmd.partner_type, entity.id,
             f"创建{cfg['label']}: {entity.name}", operator=cmd.operator)
        return entity


# ═══════════════════════════════════════════════════════════
# 2. UpdatePartner — 更新伙伴
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdatePartner(Command):
    partner_type: str = ""
    partner_id: int = 0
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


@register(UpdatePartner)
class UpdatePartnerHandler(CommandHandler):
    def handle(self, cmd: UpdatePartner, db: Any) -> Any:
        cfg = PARTNER_CONFIG[cmd.partner_type]
        entity = db.query(cfg["model"]).filter(
            cfg["model"].account_id == cmd.account_id,
            cfg["model"].id == cmd.partner_id,
        ).first()
        if not entity:
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
                setattr(entity, k, v)

        _log(db, cmd.account_id, "update", cmd.partner_type, entity.id,
             f"更新{cfg['label']}: {entity.name}", operator=cmd.operator)
        db.flush()
        return entity


# ═══════════════════════════════════════════════════════════
# 3. DeletePartner — 删除伙伴（含业务约束校验）
# ═══════════════════════════════════════════════════════════

@dataclass
class DeletePartner(Command):
    partner_type: str = ""
    partner_id: int = 0


@register(DeletePartner)
class DeletePartnerHandler(CommandHandler):
    def handle(self, cmd: DeletePartner, db: Any) -> bool:
        cfg = PARTNER_CONFIG[cmd.partner_type]
        entity = db.query(cfg["model"]).filter(
            cfg["model"].account_id == cmd.account_id,
            cfg["model"].id == cmd.partner_id,
        ).first()
        if not entity:
            return False

        fk_col = getattr(cfg["constraint_model"], cfg["constraint_fk"])
        count = db.query(cfg["constraint_model"]).filter(
            fk_col == cmd.partner_id,
            cfg["constraint_model"].account_id == cmd.account_id,
        ).count()
        if count > 0:
            raise BusinessError(code=cfg["error_code"], data={"order_count": count})

        _log(db, cmd.account_id, "delete", cmd.partner_type, entity.id,
             f"删除{cfg['label']}: {entity.name}", operator=cmd.operator)
        db.delete(entity)
        db.flush()
        return True
