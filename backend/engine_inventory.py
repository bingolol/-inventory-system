"""库存引擎 — 库存流水的唯一入口

StockMove 是所有库存数据的单一真相源，Inventory 表仅为性能缓存。
一旦写入 StockMove，严禁修改或删除，错误修正必须通过冲红调整单。
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
import models
from errors import BusinessError, ErrorCode
from utils import Q2


class InventoryEngine:
    def __init__(self, db: Session):
        self.db = db

    def _get_product(self, account_id: int, product_id: int):
        """查询并校验产品存在性"""
        product = self.db.query(models.Product).filter(
            models.Product.id == product_id,
            models.Product.account_id == account_id,
        ).first()
        if not product:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
        return product

    def inbound(self, account_id: int, product_id: int, quantity: int,
                unit_price: Decimal, source_type: str, source_id: int,
                tax_rate: Decimal = None,
                operator: str = "user") -> dict:
        """采购入库/调整入库

        unit_price 是不含税单价（API 约定）。
        按纳税人类型做价税分离：
        - 一般纳税人(enable_vat_deduction=True)：
          total_cost = qty * unit_price (不含税), total_amount = total_cost * (1+rate) (含税)
        - 小规模(enable_vat_deduction=False)：
          unit_price 视为含税单价，全额进成本

        返回: {"product_id", "quantity", "total_cost", "tax_amount", "total_amount"}
        """
        product = self._get_product(account_id, product_id)
        if not product.track_inventory:
            return {"product_id": product_id, "quantity": quantity,
                    "total_cost": Decimal("0"), "tax_amount": Decimal("0"),
                    "total_amount": Decimal("0")}

        from crud.base import get_account
        account = get_account(self.db, account_id)
        if not account:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"账本不存在: account_id={account_id}"})

        new_qty = Decimal(str(quantity))
        is_general = account.taxpayer_type == "general"
        if is_general and tax_rate is not None:
            rate = Decimal(str(tax_rate))
            total_cost = (new_qty * Decimal(str(unit_price))).quantize(Q2)  # 不含税
            total_amount = (total_cost * (Decimal("1") + rate)).quantize(Q2)  # 含税
            tax_amount = (total_amount - total_cost).quantize(Q2)
        else:
            # 小规模：unit_price 含税，全额进成本
            total_amount = (new_qty * Decimal(str(unit_price))).quantize(Q2)
            total_cost = total_amount
            tax_amount = Decimal("0")

        existing = self.db.query(models.StockMove).filter(
            models.StockMove.source_type == source_type,
            models.StockMove.source_id == source_id,
            models.StockMove.product_id == product_id,
        ).first()
        if existing:
            return {"product_id": product_id, "quantity": quantity,
                    "total_cost": total_cost, "tax_amount": tax_amount,
                    "total_amount": total_amount}

        inv = self.db.query(models.Inventory).filter(
            models.Inventory.account_id == account_id,
            models.Inventory.product_id == product_id,
        ).with_for_update().first()
        if not inv:
            inv = models.Inventory(account_id=account_id, product_id=product_id, quantity=0)
            self.db.add(inv)
            self.db.flush()

        old_qty = Decimal(str(inv.quantity))
        old_value = Decimal(str(inv.total_value))

        avg_cost = unit_price
        if old_qty + new_qty > 0:
            avg_cost = ((old_value + total_cost) / (old_qty + new_qty)).quantize(Decimal("0.000001"))

        move = models.StockMove(
            product_id=product_id,
            account_id=account_id,
            quantity=new_qty,
            unit_cost=avg_cost,
            total_cost=total_cost,
            source_type=source_type,
            source_id=source_id,
        )
        self.db.add(move)

        inv.quantity += quantity
        inv.average_cost = avg_cost
        inv.total_value = (old_value + total_cost).quantize(Q2)
        self.db.flush()

        return {"product_id": product_id, "quantity": quantity,
                "total_cost": total_cost, "tax_amount": tax_amount,
                "total_amount": total_amount}

    def outbound(self, account_id: int, product_id: int, quantity: int,
                 source_type: str, source_id: int,
                 operator: str = "user") -> Decimal:
        """销售出库/调整出库

        1. 校验库存充足
        2. 写入 StockMove（真相源）
        3. 更新 Inventory 缓存
        4. 返回 unit_cost（用于 COGS 计算）
        """
        product = self._get_product(account_id, product_id)
        if not product.track_inventory:
            return Decimal("0")

        existing = self.db.query(models.StockMove).filter(
            models.StockMove.source_type == source_type,
            models.StockMove.source_id == source_id,
            models.StockMove.product_id == product_id,
        ).first()
        if existing:
            return existing.unit_cost

        return self._record_outbound(account_id, product_id, quantity,
                                     source_type, source_id, operator)

    def _record_outbound(self, account_id: int, product_id: int, quantity: int,
                         source_type: str, source_id: int,
                         operator: str = "user") -> Decimal:
        """执行出库写操作（无幂等检查，被 outbound / force_outbound 共用）"""
        product = self._get_product(account_id, product_id)
        if not product.track_inventory:
            return Decimal("0")

        inv = self.db.query(models.Inventory).filter(
            models.Inventory.account_id == account_id,
            models.Inventory.product_id == product_id,
        ).with_for_update().first()
        if not inv:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"商品 {product.name} 无库存记录"})
        if inv.quantity < quantity:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"库存不足: {product.name} 当前库存{inv.quantity}, 需要出库{quantity}"})

        unit_cost = inv.average_cost or Decimal("0")
        out_qty = Decimal(str(quantity))
        out_cost = (out_qty * unit_cost).quantize(Q2)

        move = models.StockMove(
            product_id=product_id,
            account_id=account_id,
            quantity=-out_qty,
            unit_cost=unit_cost,
            total_cost=out_cost,
            source_type=source_type,
            source_id=source_id,
        )
        self.db.add(move)

        inv.quantity -= quantity
        inv.total_value = (Decimal(str(inv.total_value)) - out_cost).quantize(Q2)
        if inv.quantity <= 0:
            inv.average_cost = Decimal("0")
        self.db.flush()

        return unit_cost

    def force_outbound(self, account_id: int, product_id: int, quantity: int,
                       source_type: str, source_id: int,
                       operator: str = "user") -> Decimal:
        """强制出库（跳过幂等检查），用于 RestoreOrderHandler 等场景"""
        return self._record_outbound(account_id, product_id, quantity,
                                     source_type, source_id, operator)

    def reverse(self, account_id: int, product_id: int, quantity: int,
                unit_cost: Decimal, source_type: str, source_id: int,
                operator: str = "user") -> None:
        """红冲库存移动（用于取消订单）

        写一条方向相反的 StockMove，更新缓存。
        """
        product = self._get_product(account_id, product_id)
        if not product.track_inventory:
            return

        rev_source_type = f"{source_type}_reversal"
        existing = self.db.query(models.StockMove).filter(
            models.StockMove.source_type == rev_source_type,
            models.StockMove.source_id == source_id,
            models.StockMove.product_id == product_id,
        ).first()
        if existing:
            return

        # 自动从原始 StockMove 获取正确成本（处理价税分离后的差异）
        # 同时判断原始方向：正数=入库(采购)，负数=出库(销售)
        original = self.db.query(models.StockMove).filter(
            models.StockMove.source_type == source_type,
            models.StockMove.source_id == source_id,
            models.StockMove.product_id == product_id,
        ).first()
        effective_unit_cost = original.unit_cost if original else Decimal(str(unit_cost))
        rev_qty = Decimal(str(quantity))
        rev_cost = (rev_qty * effective_unit_cost).quantize(Q2)

        # 反转方向：原始正→冲销负，原始负→冲销正
        is_inbound = original is None or original.quantity > 0
        sign = Decimal("-1") if is_inbound else Decimal("1")
        move = models.StockMove(
            product_id=product_id,
            account_id=account_id,
            quantity=rev_qty * sign,
            unit_cost=effective_unit_cost,
            total_cost=rev_cost,
            source_type=rev_source_type,
            source_id=source_id,
        )
        self.db.add(move)

        inv = self.db.query(models.Inventory).filter(
            models.Inventory.account_id == account_id,
            models.Inventory.product_id == product_id,
        ).with_for_update().first()
        if not inv:
            return

        old_qty = Decimal(str(inv.quantity))
        old_value = Decimal(str(inv.total_value))

        if is_inbound:
            inv.quantity -= quantity
            inv.total_value = (old_value - rev_cost).quantize(Q2)
        else:
            inv.quantity += quantity
            inv.total_value = (old_value + rev_cost).quantize(Q2)
        new_qty = Decimal(str(inv.quantity))
        if new_qty > 0:
            inv.average_cost = (Decimal(str(inv.total_value)) / new_qty).quantize(Decimal("0.000001"))
        else:
            inv.average_cost = Decimal("0")
        self.db.flush()
