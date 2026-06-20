"""采购单领域模型 — 封装采购单业务规则和不变量，与ORM模型解耦。

核心规则：
1. 状态机：只允许合法的状态转换
2. 金额一致：total_price = sum(items.total_price)
3. 已完成单据必须有商品明细
4. 数量校验：每行数量 > 0
5. payment_method 必须是合法值
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from domain.base import DomainModel
from domain.money import Money
from enums import OrderStatus, OrderType, PaymentStatus, PaymentMethod
from errors import BusinessError, ErrorCode


# ── 状态机：合法转换表 ──────────────────────────────────
VALID_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.PENDING: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: {OrderStatus.CANCELLED},
    OrderStatus.CANCELLED: {OrderStatus.COMPLETED},  # 恢复
}


@dataclass
class PurchaseOrderLine:
    """采购单明细行值对象"""

    product_id: int
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    total_price: Money


@dataclass
class PurchaseOrderDomain(DomainModel):
    """采购单领域模型 — 封装业务规则

    与销售单的关键差异：
    - 关联供应商（supplier_id）而非客户
    - 有 payment_method 字段（company / private_advance）
    - 没有 deduct_inventory（采购入库固定加库存，无扣库存选项）
    - 库存影响：completed 入库，cancelled 回补
    """

    id: int = 0
    account_id: int = 0
    order_no: str = ""
    supplier_id: Optional[int] = None
    status: str = OrderStatus.PENDING
    payment_status: str = PaymentStatus.UNPAID
    payment_method: str = PaymentMethod.COMPANY
    has_invoice: bool = False
    purchase_date: str = ""
    notes: str = ""
    order_type: str = OrderType.RETAIL
    total_price: Money = field(default_factory=Money.zero)
    items: list[PurchaseOrderLine] = field(default_factory=list)

    # ── 状态机 ──────────────────────────────────────────────

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in VALID_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: str) -> None:
        if not self.can_transition_to(new_status):
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": self.status, "action": new_status})
        self.status = new_status

    # ── 业务规则 ────────────────────────────────────────────

    def is_completed(self) -> bool:
        return self.status == OrderStatus.COMPLETED

    def is_cancelled(self) -> bool:
        return self.status == OrderStatus.CANCELLED

    def affects_inventory(self) -> bool:
        """当前状态是否影响库存（completed=入库）"""
        return self.is_completed()

    # ── 不变量校验 ──────────────────────────────────────────

    def validate(self) -> list[str]:
        violations: list[str] = []

        # 1. 已完成单据必须有商品明细
        if self.is_completed() and not self.items:
            violations.append("已完成采购单必须有商品明细")

        # 2. 金额一致：total_price == sum(items.total_price)
        if self.items:
            calc_total = Money.sum(item.total_price for item in self.items)
            if calc_total != self.total_price:
                violations.append(
                    f"金额不一致: total={self.total_price}, 明细合计={calc_total}"
                )

        # 3. 数量校验：每行数量 > 0
        for i, item in enumerate(self.items):
            if item.quantity <= 0:
                violations.append(f"第{i + 1}行数量必须大于0: quantity={item.quantity}")

        # 4. payment_method 合法性
        valid_methods = {PaymentMethod.COMPANY, PaymentMethod.PRIVATE_ADVANCE}
        if self.payment_method not in valid_methods:
            violations.append(
                f"非法支付方式: {self.payment_method}，合法值: {valid_methods}"
            )

        # 5. payment_status 合法性
        valid_payment_statuses = {
            PaymentStatus.PAID, PaymentStatus.UNPAID,
            PaymentStatus.PENDING, PaymentStatus.PARTIAL,
        }
        if self.payment_status not in valid_payment_statuses:
            violations.append(
                f"非法付款状态: {self.payment_status}，合法值: {valid_payment_statuses}"
            )

        return violations

    # ── ORM 转换 ────────────────────────────────────────────

    @classmethod
    def from_orm(cls, orm_obj) -> PurchaseOrderDomain:
        items = [
            PurchaseOrderLine(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=Decimal(str(item.unit_price)) if item.unit_price else Decimal("0"),
                tax_rate=Decimal(str(item.tax_rate)) if item.tax_rate else Decimal("0"),
                total_price=Money(item.total_price),
            )
            for item in (orm_obj.items or [])
        ]
        return cls(
            id=orm_obj.id,
            account_id=orm_obj.account_id,
            order_no=orm_obj.order_no or "",
            supplier_id=orm_obj.supplier_id,
            status=orm_obj.status or OrderStatus.PENDING,
            payment_status=orm_obj.payment_status or PaymentStatus.UNPAID,
            payment_method=orm_obj.payment_method or PaymentMethod.COMPANY,
            has_invoice=bool(orm_obj.has_invoice),
            purchase_date=str(orm_obj.purchase_date) if orm_obj.purchase_date else "",
            notes=orm_obj.notes or "",
            order_type=getattr(orm_obj, 'order_type', None) or OrderType.RETAIL,
            total_price=Money(orm_obj.total_price),
            items=items,
        )