"""库存引擎 — 库存流水的唯一入口

StockMove 是所有库存数据的单一真相源，Inventory 表仅为性能缓存。
一旦写入 StockMove，严禁修改或删除，错误修正必须通过冲红调整单。
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
import models
from errors import BusinessError, ErrorCode
from operation_result import EntityType
from utils import Q2
# price tools moved to command layer — engines read pre-computed amounts
from lineage import writes, derives, reads, TIER_L1, TIER_L2, TIER_L3, TIER_L4
from rules import enforce_rules
from cost_engine import weighted_average


class InventoryEngine:
    def __init__(self, db: Session):
        self.db = db

    def _get_move_date(self, source_type: str, source_id: int) -> datetime:
        """从源单据获取业务日期"""
        if source_type == EntityType.PURCHASE_ORDER:
            po = self.db.query(models.PurchaseOrder).filter(models.PurchaseOrder.id == source_id).first()
            return po.purchase_date_l1 if po and po.purchase_date_l1 else datetime.now()
        if source_type == EntityType.SALE_ORDER:
            so = self.db.query(models.SaleOrder).filter(models.SaleOrder.id == source_id).first()
            return so.sale_date_l1 if so and so.sale_date_l1 else datetime.now()
        if source_type.endswith("_reversal"):
            base_type = source_type.replace("_reversal", "")
            return self._get_move_date(base_type, source_id)
        if source_type == "inventory_adjustment":
            return datetime.now()
        return datetime.now()

    def _get_product(self, account_id: int, product_id: int):
        """查询并校验产品存在性"""
        product = self.db.query(models.Product).filter(
            models.Product.id == product_id,
            models.Product.account_id == account_id,
        ).first()
        if not product:
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
        return product

    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    @writes("StockMove.quantity_l1", tier=TIER_L1, source="external")
    @writes("StockMove.unit_cost_l2", tier=TIER_L2, source="engine")
    @writes("StockMove.total_cost_l2", tier=TIER_L2, source="engine")
    @writes("StockMove.move_date_l1", tier=TIER_L1, source="external")
    @derives("Inventory.quantity_l4", from_fields=["StockMove.quantity_l1"])
    @derives("Inventory.average_cost_l4", from_fields=["StockMove.unit_cost_l2"])
    @derives("Inventory.total_value_l4", from_fields=["StockMove.total_cost_l2"])
    def inbound(self, account_id: int, product_id: int, quantity: int,
                unit_price: Decimal, source_type: str, source_id: int,
                tax_rate: Decimal = None,
                operator: str = "user",
                move_date: datetime = None,
                force: bool = False) -> dict:
        """采购入库/调整入库

        unit_price 由调用方保证已做价税分离（命令层负责）。
        total_cost = qty * unit_price，直接写入 StockMove。

        返回: {"product_id", "quantity", "total_cost", "tax_amount", "total_amount"}
        """
        product = self._get_product(account_id, product_id)
        if not product.track_inventory_l3:
            return {"product_id": product_id, "quantity": quantity,
                    "total_cost": Decimal("0"), "tax_amount": Decimal("0"),
                    "total_amount": Decimal("0")}

        import models
        account = self.db.query(models.Account).filter(models.Account.id == account_id).first()
        if not account:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"账本不存在: account_id={account_id}"})

        new_qty = Decimal(str(quantity))
        total_cost = (new_qty * Decimal(str(unit_price))).quantize(Q2)
        total_amount = total_cost
        tax_amount = Decimal("0")

        existing = self.db.query(models.StockMove).filter(
            models.StockMove.source_type == source_type,
            models.StockMove.source_id == source_id,
            models.StockMove.product_id == product_id,
        ).first()
        if existing and not force:
            return {"product_id": product_id, "quantity": quantity,
                    "total_cost": total_cost, "tax_amount": tax_amount,
                    "total_amount": total_amount}

        inv = self.db.query(models.Inventory).filter(
            models.Inventory.account_id == account_id,
            models.Inventory.product_id == product_id,
        ).with_for_update().first()
        if not inv:
            inv = models.Inventory(account_id=account_id, product_id=product_id, quantity_l4=0)
            self.db.add(inv)
            self.db.flush()

        old_qty = Decimal(str(inv.quantity_l4))
        old_value = Decimal(str(inv.total_value_l4))

        avg_cost = weighted_average(old_qty + new_qty, old_value + total_cost)

        move = models.StockMove(
            product_id=product_id,
            account_id=account_id,
            quantity_l1=new_qty,
            unit_cost_l2=avg_cost,
            total_cost_l2=total_cost,
            source_type=source_type,
            source_id=source_id,
            move_date_l1=move_date or self._get_move_date(source_type, source_id),
        )
        self.db.add(move)

        inv.quantity_l4 += quantity
        inv.average_cost_l4 = avg_cost
        inv.total_value_l4 = (old_value + total_cost).quantize(Q2)
        self.db.flush()

        # AS-03 库存账面价值一致性校验(Inventory.total_value == Σ StockMove.total_cost)
        enforce_rules(self.db, ["AS-03"], {"product_id": product_id})

        return {"product_id": product_id, "quantity": quantity,
                "total_cost": total_cost, "tax_amount": tax_amount,
                "total_amount": total_amount}

    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    def outbound(self, account_id: int, product_id: int, quantity: int,
                 source_type: str, source_id: int,
                 operator: str = "user",
                 move_date: datetime = None) -> Decimal:
        """销售出库/调整出库

        1. 校验库存充足
        2. 写入 StockMove（真相源）
        3. 更新 Inventory 缓存
        4. 返回 unit_cost（用于 COGS 计算）
        """
        product = self._get_product(account_id, product_id)
        if not product.track_inventory_l3:
            return Decimal("0")

        existing = self.db.query(models.StockMove).filter(
            models.StockMove.source_type == source_type,
            models.StockMove.source_id == source_id,
            models.StockMove.product_id == product_id,
        ).first()
        if existing:
            return existing.unit_cost_l2

        return self._record_outbound(account_id, product_id, quantity,
                                      source_type, source_id, operator, move_date)

    @writes("StockMove.quantity_l1", tier=TIER_L1, source="external")
    @writes("StockMove.unit_cost_l2", tier=TIER_L2, source="engine")
    @writes("StockMove.total_cost_l2", tier=TIER_L2, source="engine")
    @writes("StockMove.move_date_l1", tier=TIER_L1, source="external")
    @derives("Inventory.quantity_l4", from_fields=["StockMove.quantity_l1"])
    @derives("Inventory.total_value_l4", from_fields=["StockMove.total_cost_l2"])
    def _record_outbound(self, account_id: int, product_id: int, quantity: int,
                         source_type: str, source_id: int,
                         operator: str = "user",
                         move_date: datetime = None) -> Decimal:
        """执行出库写操作（无幂等检查，被 outbound / force_outbound 共用）"""
        product = self._get_product(account_id, product_id)
        if not product.track_inventory_l3:
            return Decimal("0")

        inv = self.db.query(models.Inventory).filter(
            models.Inventory.account_id == account_id,
            models.Inventory.product_id == product_id,
        ).with_for_update().first()
        if not inv:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"商品 {product.name} 无库存记录"})
        if inv.quantity_l4 < quantity:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"库存不足: {product.name} 当前库存{inv.quantity_l4}, 需要出库{quantity}"})

        unit_cost = inv.average_cost_l4 or Decimal("0")
        out_qty = Decimal(str(quantity))
        out_cost = (out_qty * unit_cost).quantize(Q2)

        move = models.StockMove(
            product_id=product_id,
            account_id=account_id,
            quantity_l1=-out_qty,
            unit_cost_l2=unit_cost,
            total_cost_l2=out_cost,
            source_type=source_type,
            source_id=source_id,
            move_date_l1=move_date or self._get_move_date(source_type, source_id),
        )
        self.db.add(move)

        inv.quantity_l4 -= quantity
        inv.total_value_l4 = (Decimal(str(inv.total_value_l4)) - out_cost).quantize(Q2)
        if inv.quantity_l4 <= 0:
            inv.average_cost_l4 = Decimal("0")
        self.db.flush()

        # AS-03 库存账面价值一致性校验(Inventory.total_value == Σ StockMove.total_cost)
        enforce_rules(self.db, ["AS-03"], {"product_id": product_id})

        return unit_cost

    def force_outbound(self, account_id: int, product_id: int, quantity: int,
                       source_type: str, source_id: int,
                       operator: str = "user") -> Decimal:
        """强制出库（跳过幂等检查），用于 RestoreOrderHandler / 明细更新重建等场景。

        注意：此处的 "force" 仅指跳过 (source_type, source_id) 的幂等检查，
        **并非跳过非负校验**。底层 _record_outbound 仍会校验
        inv.quantity < quantity 并在库存不足时抛 BusinessError。
        因此本方法不会产生负库存——与 outbound 的非负约束一致。
        """
        return self._record_outbound(account_id, product_id, quantity,
                                     source_type, source_id, operator)

    def force_inbound(self, account_id: int, product_id: int, quantity: int,
                      unit_price: Decimal, source_type: str, source_id: int,
                      tax_rate: Decimal = None,
                      operator: str = "user",
                      move_date: datetime = None) -> dict:
        """强制入库（跳过幂等检查），用于订单恢复/明细全量替换后重建库存流水

        与 force_outbound 对称：当同一 source_id 已有入库流水（如订单被取消后恢复、
        明细全量替换后重建）时，普通 inbound 会因幂等直接返回而不写新流水，
        导致库存与实际业务脱节。此方法跳过幂等检查，始终写入新的 StockMove。
        """
        return self.inbound(account_id, product_id, quantity, unit_price,
                            source_type, source_id, tax_rate=tax_rate,
                            operator=operator, move_date=move_date, force=True)

    @reads("Product.track_inventory_l3", tier=TIER_L3, source="policy")
    @writes("StockMove.quantity_l1", tier=TIER_L1, source="external")
    @writes("StockMove.unit_cost_l2", tier=TIER_L2, source="engine")
    @writes("StockMove.total_cost_l2", tier=TIER_L2, source="engine")
    @writes("StockMove.move_date_l1", tier=TIER_L1, source="external")
    @derives("Inventory.quantity_l4", from_fields=["StockMove.quantity_l1"])
    @derives("Inventory.total_value_l4", from_fields=["StockMove.total_cost_l2"])
    @reads("StockMove.unit_cost_l2", tier=TIER_L2, source="engine")
    @reads("StockMove.total_cost_l2", tier=TIER_L2, source="engine")
    def reverse(self, account_id: int, product_id: int, quantity: int,
                unit_cost: Decimal, source_type: str, source_id: int,
                operator: str = "user",
                source_id_override: Optional[int] = None,
                force: bool = False) -> None:
        """红冲库存移动（用于取消订单 / 部分退货 / 明细更新冲红）

        写一条方向相反的 StockMove，更新缓存。

        - 整单取消：不传 source_id_override，使用 (source_type_reversal, source_id) 做幂等检查
        - 部分退货：传 source_id_override=return_id（纳秒时间戳），
          StockMove.source_id 字段使用 return_id 避免与整单冲销的幂等冲突；
          但 _get_move_date 仍用原 source_id 取业务日期，确保 StockMove.move_date 与原单日期一致。
        - 明细更新冲红：传 force=True 跳过幂等检查，并取最近一次正向流水作为冲红基准
          （同一 source_id 经过"冲红+重建"后会有多条正向流水，需冲红最近一条而非最早一条）。
        """
        product = self._get_product(account_id, product_id)
        if not product.track_inventory_l3:
            return

        rev_source_type = f"{source_type}_reversal"
        actual_sid = source_id_override if source_id_override is not None else source_id
        existing = self.db.query(models.StockMove).filter(
            models.StockMove.source_type == rev_source_type,
            models.StockMove.source_id == actual_sid,
            models.StockMove.product_id == product_id,
        ).first()
        if existing and not force:
            return

        # 自动从原始 StockMove 获取正确成本（处理价税分离后的差异）
        # 同时判断原始方向：正数=入库(采购)，负数=出库(销售)
        # force 模式下取最近一条正向流水（"冲红+重建"后有多条，需冲红最近一条）
        orig_query = self.db.query(models.StockMove).filter(
            models.StockMove.source_type == source_type,
            models.StockMove.source_id == source_id,
            models.StockMove.product_id == product_id,
        )
        if force:
            original = orig_query.order_by(models.StockMove.id.desc()).first()
        else:
            original = orig_query.first()
        # ⚠️ 反向冲销用原流水的实际单价（total_cost / quantity），
        # 不用派生的 unit_cost（移动加权平均）——避免采购退货借贷不同源。
        # 采购入库：total_cost/qty = 发票不含税单价（真相源）
        # 销售出库：total_cost/qty = avg_cost（与 unit_cost 等价，无副作用）
        if original:
            orig_qty = Decimal(str(original.quantity_l1))
            orig_total_cost = Decimal(str(original.total_cost_l2))
            if orig_qty != 0:
                effective_unit_cost = (orig_total_cost / orig_qty).quantize(Decimal("0.000001"))
            else:
                effective_unit_cost = Decimal(str(unit_cost))
        else:
            effective_unit_cost = Decimal(str(unit_cost))
        rev_qty = Decimal(str(quantity))
        rev_cost = (rev_qty * effective_unit_cost).quantize(Q2)

        # 反转方向：原始正→冲销负，原始负→冲销正
        # 修复 #6：original 为 None 时抛异常，而非默认按入库红冲
        # 原代码 is_inbound = original is None or original.quantity > 0
        # 在 original 缺失时默认按入库方向处理，可能导致方向反转错误。
        if original is None:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                data={"details": f"找不到原始库存流水: source_type={source_type}, source_id={source_id}, product_id={product_id}"},
            )
        is_inbound = original.quantity_l1 > 0
        sign = Decimal("-1") if is_inbound else Decimal("1")
        move = models.StockMove(
            product_id=product_id,
            account_id=account_id,
            quantity_l1=rev_qty * sign,
            unit_cost_l2=effective_unit_cost,
            total_cost_l2=rev_cost,
            source_type=rev_source_type,
            source_id=actual_sid,
            ref_source_id=source_id if source_id_override is not None else None,
            move_date_l1=self._get_move_date(source_type, source_id),
        )
        self.db.add(move)

        inv = self.db.query(models.Inventory).filter(
            models.Inventory.account_id == account_id,
            models.Inventory.product_id == product_id,
        ).with_for_update().first()
        if not inv:
            return

        old_qty = Decimal(str(inv.quantity_l4))
        old_value = Decimal(str(inv.total_value_l4))

        if is_inbound:
            # 采购入库反向 = 采购退货 → 库存减少
            # 库存不足时拒绝（避免库存负数，符合会计实务）
            if old_qty < rev_qty:
                raise BusinessError(
                    code=ErrorCode.INVENTORY_INSUFFICIENT,
                    message=f"库存不足，无法退货。商品: {product.name}，当前库存: {old_qty}，退货数量: {rev_qty}",
                    data={"required": float(rev_qty), "current": float(old_qty)},
                )
            inv.quantity_l4 -= quantity
            inv.total_value_l4 = (old_value - rev_cost).quantize(Q2)
        else:
            inv.quantity_l4 += quantity
            inv.total_value_l4 = (old_value - rev_cost).quantize(Q2)
        new_qty = Decimal(str(inv.quantity_l4))
        inv.average_cost_l4 = weighted_average(new_qty, Decimal(str(inv.total_value_l4)))
        self.db.flush()

        # AS-03 库存账面价值一致性校验(Inventory.total_value == Σ StockMove.total_cost)
        enforce_rules(self.db, ["AS-03"], {"product_id": product_id})
