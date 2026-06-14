"""商品 + 库存 Command + Handler — 4个命令覆盖商品/库存全部写操作

从 crud/products.py 提取，Command 模式封装。
每个 Handler 包含：数据校验 → ORM 操作 → 日志记录。
"""

from dataclasses import dataclass
from typing import Any, Optional

import models
from sqlalchemy import or_

from .base import Command, CommandHandler, register
from .crud_compat import _log, get_or_create_inventory


# ═══════════════════════════════════════════════════════════
# 1. CreateProduct — 创建商品（含初始库存）
# ═══════════════════════════════════════════════════════════

@dataclass
class CreateProduct(Command):
    name: str = ""
    sku: str = ""
    category: str = ""
    unit: str = ""
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None
    min_stock: int = 0
    description: str = ""
    initial_stock: float = 0.0


@register(CreateProduct)
class CreateProductHandler(CommandHandler):
    def handle(self, cmd: CreateProduct, db: Any) -> Any:
        # 1. 创建商品
        product = models.Product(
            account_id=cmd.account_id,
            name=cmd.name,
            sku=cmd.sku,
            category=cmd.category,
            unit=cmd.unit,
            purchase_price=cmd.purchase_price,
            sale_price=cmd.sale_price,
            min_stock=cmd.min_stock,
            description=cmd.description,
        )
        db.add(product)
        db.flush()

        # 2. 创建初始库存记录
        inv = models.Inventory(
            account_id=cmd.account_id,
            product_id=product.id,
            quantity=cmd.initial_stock,
        )
        db.add(inv)

        # 3. 日志
        _log(db, cmd.account_id, "create", "product", product.id,
             f"创建商品: {product.name} (SKU:{product.sku})", operator=cmd.operator)
        db.flush()
        return product


# ═══════════════════════════════════════════════════════════
# 2. UpdateProduct — 更新商品信息
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdateProduct(Command):
    product_id: int = 0
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None
    min_stock: Optional[int] = None
    description: Optional[str] = None


@register(UpdateProduct)
class UpdateProductHandler(CommandHandler):
    def handle(self, cmd: UpdateProduct, db: Any) -> Any:
        # 1. 查询商品
        product = db.query(models.Product).filter(
            models.Product.account_id == cmd.account_id,
            models.Product.id == cmd.product_id,
        ).first()
        if not product:
            return None

        # 2. 部分更新
        updates = {
            'name': cmd.name,
            'sku': cmd.sku,
            'category': cmd.category,
            'unit': cmd.unit,
            'purchase_price': cmd.purchase_price,
            'sale_price': cmd.sale_price,
            'min_stock': cmd.min_stock,
            'description': cmd.description,
        }
        for k, v in updates.items():
            if v is not None:
                setattr(product, k, v)

        # 3. 日志
        _log(db, cmd.account_id, "update", "product", product.id,
             f"更新商品: {product.name}", operator=cmd.operator)
        db.flush()
        return product


# ═══════════════════════════════════════════════════════════
# 3. DeleteProduct — 删除商品（含业务约束校验）
# ═══════════════════════════════════════════════════════════

@dataclass
class DeleteProduct(Command):
    product_id: int = 0


@register(DeleteProduct)
class DeleteProductHandler(CommandHandler):
    def handle(self, cmd: DeleteProduct, db: Any) -> bool:
        # 1. 查询商品
        product = db.query(models.Product).filter(
            models.Product.account_id == cmd.account_id,
            models.Product.id == cmd.product_id,
        ).first()
        if not product:
            return False

        # 2. 业务约束校验：存在采购或销售记录则拒绝删除
        purchase_count = db.query(models.PurchaseItem).join(models.PurchaseOrder).filter(
            models.PurchaseOrder.account_id == cmd.account_id,
            models.PurchaseItem.product_id == cmd.product_id,
        ).count()
        sale_count = db.query(models.SaleItem).join(models.SaleOrder).filter(
            models.SaleOrder.account_id == cmd.account_id,
            models.SaleItem.product_id == cmd.product_id,
        ).count()
        if purchase_count > 0 or sale_count > 0:
            raise ValueError(
                f"该商品存在 {purchase_count} 条采购记录和 {sale_count} 条销售记录，无法删除"
            )

        # 3. 删除关联库存
        db.query(models.Inventory).filter(
            models.Inventory.account_id == cmd.account_id,
            models.Inventory.product_id == cmd.product_id,
        ).delete()

        # 4. 删除商品
        _log(db, cmd.account_id, "delete", "product", product.id,
             f"删除商品: {product.name}", operator=cmd.operator)
        db.delete(product)
        db.flush()
        return True


# ═══════════════════════════════════════════════════════════
# 4. AdjustInventory — 库存盘点调整
# ═══════════════════════════════════════════════════════════

@dataclass
class AdjustInventory(Command):
    product_id: int = 0
    quantity: float = 0.0


@register(AdjustInventory)
class AdjustInventoryHandler(CommandHandler):
    def handle(self, cmd: AdjustInventory, db: Any) -> Any:
        # 1. 获取或创建库存记录
        inv = get_or_create_inventory(db, cmd.account_id, cmd.product_id)
        old_qty = inv.quantity

        # 2. 更新数量
        inv.quantity = cmd.quantity

        # 3. 日志（记录新旧数量对比）
        _log(db, cmd.account_id, "adjust", "inventory", cmd.product_id,
             f"库存盘点: {old_qty}->{cmd.quantity}", operator=cmd.operator)
        db.flush()
        return inv
