"""商品 + 库存 Command + Handler — 4个命令覆盖商品/库存全部写操作

从 crud/products.py 提取，Command 模式封装。
每个 Handler 包含：数据校验 → ORM 操作 → 日志记录。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import time
from typing import Any, Optional

import models
from sqlalchemy import or_

from .base import Command, CommandHandler, register
from crud.base import _log, get_or_create_inventory
from errors import BusinessError, ErrorCode
from utils import Q2
from engine_inventory import InventoryEngine


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
            raise BusinessError(code=ErrorCode.PRODUCT_HAS_TRANSACTIONS, data={"purchase_count": purchase_count, "sale_count": sale_count})

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
    adjust_date: Optional[str] = None
    reason: Optional[str] = None  # 报损原因（减少库存时必填）
    # 盘盈入库时若商品无 average_cost 且无 purchase_price，必须显式提供 unit_cost
    # 否则零成本入库会污染 StockMove.total_cost 和后续 COGS
    unit_cost: Optional[float] = None


@register(AdjustInventory)
class AdjustInventoryHandler(CommandHandler):
    def handle(self, cmd: AdjustInventory, db: Any) -> Any:
        # 1. 校验：库存数量不能为负
        if cmd.quantity < 0:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"库存数量不能为负: {cmd.quantity}",
                ai_instruction="STOP_RETRYING. 库存数量不能为负，请检查输入。"
            )

        # 2. 获取或创建库存记录
        inv = get_or_create_inventory(db, cmd.account_id, cmd.product_id)
        product = db.query(models.Product).filter(
            models.Product.id == cmd.product_id,
            models.Product.account_id == cmd.account_id,
        ).first()
        old_qty = inv.quantity
        new_qty = Decimal(str(cmd.quantity))
        delta = new_qty - old_qty

        # 2a. 库存调整（无论增加或减少）必须填写原因
        if delta != 0 and not cmd.reason:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="库存调整必须填写原因，例如：盘盈、盘亏、损坏、过期、丢失、纠错等",
                ai_instruction="STOP_RETRYING. 库存调整时 reason 字段必填，请补充调整原因。"
            )

        # 3. 通过 InventoryEngine 创建 StockMove（BR-7 合规）
        if delta != 0 and product and product.track_inventory:
            adj_id = int(time.time() * 1000)
            engine = InventoryEngine(db)
            # 优先级：显式 unit_cost（盘盈估值）> average_cost（已有库存）> purchase_price（兜底）
            # 修复：原代码兜底到 purchase_price=0 时会零成本入库，污染 StockMove.total_cost
            # 和后续 COGS。现拦截实物商品盘盈入库零成本场景。
            if cmd.unit_cost is not None and cmd.unit_cost > 0:
                unit_cost = Decimal(str(cmd.unit_cost))
            elif inv.average_cost and inv.average_cost > 0:
                unit_cost = inv.average_cost
            else:
                unit_cost = Decimal(str(product.purchase_price or 0))

            # 实物商品盘盈入库（delta>0）零成本拦截
            # 服务类商品（track_inventory=False）不走此分支，不受影响
            if delta > 0 and unit_cost <= Decimal("0"):
                raise BusinessError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=(
                        f"实物商品盘盈入库需要指定成本：商品 {product.name} 的 average_cost 和 purchase_price 均为 0。"
                        f"请先通过采购单建立商品成本，或在 adjust-inventory 接口提供 unit_cost 参数。"
                    ),
                    ai_instruction=(
                        "STOP_RETRYING. 实物商品盘盈入库需要非零成本。"
                        "（1）先创建采购单建立商品成本；或"
                        "（2）在 adjust-inventory 接口显式提供 unit_cost 参数。"
                        "服务类商品请将 track_inventory 设为 False 后再调整。"
                    ),
                    data={"product_id": cmd.product_id, "product_name": product.name, "delta": float(delta)}
                )
            move_date = None
            if cmd.adjust_date:
                move_date = datetime.strptime(cmd.adjust_date, "%Y-%m-%d")
            if delta > 0:
                engine.inbound(
                    account_id=cmd.account_id, product_id=cmd.product_id,
                    quantity=int(delta), unit_price=unit_cost,
                    source_type="inventory_adjustment", source_id=adj_id,
                    tax_rate=Decimal("0"), operator=cmd.operator,
                    move_date=move_date,
                )
            else:
                engine.outbound(
                    account_id=cmd.account_id, product_id=cmd.product_id,
                    quantity=int(-delta), source_type="inventory_adjustment",
                    source_id=adj_id, operator=cmd.operator,
                    move_date=move_date,
                )

            # 3a. 过账
            value = (abs(delta) * unit_cost).quantize(Q2)
            if value > 0:
                from finance_integration import post_journal
                from datetime import date
                journal_date = cmd.adjust_date if cmd.adjust_date else date.today().isoformat()
                if delta < 0:
                    # 修复 #8：盘亏先挂 1901 待处理财产损溢，查明原因后再转入费用
                    lines = [
                        {"account_code": "1901", "debit": value, "credit": Decimal("0")},
                        {"account_code": "1405", "debit": Decimal("0"), "credit": value},
                    ]
                else:
                    # 修复 #8：盘盈先挂 1901 待处理财产损溢，查明原因后再转入收入
                    lines = [
                        {"account_code": "1405", "debit": value, "credit": Decimal("0")},
                        {"account_code": "1901", "debit": Decimal("0"), "credit": value},
                    ]
                post_journal(db, cmd.account_id, "opening_balance", {
                    "date": journal_date,
                    "lines": lines,
                })
        else:
            inv.quantity = new_qty

        # 4. 日志（记录调整原因）
        log_detail = f"库存盘点: {old_qty}->{cmd.quantity}（原因: {cmd.reason}）"
        _log(db, cmd.account_id, "adjust", "inventory", cmd.product_id,
             log_detail, operator=cmd.operator)
        db.flush()
        return inv
