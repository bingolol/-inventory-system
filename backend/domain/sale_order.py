"""销售单领域模型 — 状态机 + 不变量，与 ORM 解耦。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from domain.base import DomainModel
from domain.money import Money
from enums import OrderStatus, OrderType
from errors import BusinessError, ErrorCode

# ── 状态转换表 ──────────────────────────────────────────────

VALID_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.PENDING:   {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: {OrderStatus.CANCELLED},
    OrderStatus.CANCELLED: {OrderStatus.COMPLETED},  # 恢复操作：cancelled → completed
}

# ── 行项值对象 ──────────────────────────────────────────────

@dataclass(frozen=True)
class SaleOrderLine:
    """销售单行项（值对象），对应 ORM SaleItem。"""
    product_id: int
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    total_price: Money

# ── 领域模型 ────────────────────────────────────────────────

class SaleOrderDomain(DomainModel["SaleOrder"]):
    """销售单领域模型 — 封装状态机与业务不变量。"""

    def __init__(
        self,
        id: Optional[int] = None,
        order_no: str = "",
        customer_id: Optional[int] = None,
        total_price: Optional[Money] = None,
        has_invoice: bool = False,
        payment_status: str = "unpaid",
        status: str = OrderStatus.PENDING,
        notes: str = "",
        order_type: str = OrderType.RETAIL,
        items: Optional[list[SaleOrderLine]] = None,
    ) -> None:
        self.id = id
        self.order_no = order_no
        self.customer_id = customer_id
        self.total_price = total_price or Money.zero()
        self.has_invoice = has_invoice
        self.payment_status = payment_status
        self.status = status
        self.notes = notes
        self.order_type = order_type
        self.items: list[SaleOrderLine] = items or []

    # ── 状态机 ─────────────────────────────────────────────

    def can_transition_to(self, target: str) -> bool:
        """判断当前状态是否可转换到目标状态。"""
        allowed = VALID_TRANSITIONS.get(self.status, set())
        return target in allowed

    def transition_to(self, target: str) -> None:
        """执行状态转换，非法转换抛 ValueError。"""
        if not self.can_transition_to(target):
            raise BusinessError(code=ErrorCode.ORDER_INVALID_STATE, data={"status": self.status, "action": target})
        self.status = target

    # ── 业务规则 ───────────────────────────────────────────

    def can_delete(self) -> bool:
        """判断当前状态是否可删除。已完成或已取消状态均可删除。"""
        return self.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED)

    # ── 不变量校验 ─────────────────────────────────────────

    def validate(self) -> list[str]:
        """不变量校验，返回违规列表（空=通过）。"""
        violations: list[str] = []

        # 行项校验
        for item in self.items:
            if item.quantity <= 0:
                violations.append(
                    f"商品ID={item.product_id} 数量必须>0，当前={item.quantity}"
                )
            if item.unit_price < 0:
                violations.append(
                    f"商品ID={item.product_id} 单价不能为负"
                )
            if item.total_price.amount < 0:
                violations.append(
                    f"商品ID={item.product_id} 小计不能为负"
                )

        return violations

    @classmethod
    def from_orm(cls, orm_obj) -> SaleOrderDomain:
        items = [
            SaleOrderLine(
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
            order_no=orm_obj.order_no or "",
            customer_id=orm_obj.customer_id,
            total_price=Money(orm_obj.total_price),
            has_invoice=bool(orm_obj.has_invoice),
            payment_status=orm_obj.payment_status or "unpaid",
            status=orm_obj.status or OrderStatus.PENDING,
            notes=orm_obj.notes or "",
            order_type=getattr(orm_obj, 'order_type', None) or OrderType.RETAIL,
            items=items,
        )