"""库存领域模型 — 封装库存业务规则和不变量，与ORM模型解耦。

核心规则：
1. 库存数量不能为负（领域层强制非负，扣减前应先校验）
2. account_id 必须有值
3. product_id 必须有值且大于0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.base import DomainModel


@dataclass
class InventoryDomain(DomainModel["Inventory"]):
    """库存领域模型 — 封装业务规则

    与 ORM Inventory 的关键映射：
    - quantity: 当前库存数量，领域层强制非负
    - account_id: 所属账本ID
    - product_id: 商品ID

    注意：ORM 层注释"允许负数"，但领域层 enforce 非负。
    超卖场景应由业务逻辑在扣减前校验，而非在数据层允许负库存。
    """

    id: int = 0
    account_id: int = 0
    product_id: int = 0
    quantity: int = 0

    # ── 业务规则 ────────────────────────────────────────────

    def is_available(self, needed: int) -> bool:
        """库存是否满足需求量"""
        return self.quantity >= needed

    def can_deduct(self, amount: int) -> bool:
        """是否可以扣减指定数量（扣减后不为负）"""
        return self.quantity - amount >= 0

    # ── 不变量校验 ──────────────────────────────────────────

    def validate(self) -> list[str]:
        """不变量校验，返回违规列表（空列表=通过）"""
        violations: list[str] = []

        # 1. 库存不能为负
        if self.quantity < 0:
            violations.append(
                f"库存不能为负: quantity={self.quantity}"
            )

        # 2. account_id 必须有值
        if not self.account_id:
            violations.append("account_id不能为空")

        # 3. product_id 必须有值且大于0
        if not self.product_id:
            violations.append("product_id不能为空")

        return violations

    # ── ORM 转换 ────────────────────────────────────────────

    @classmethod
    def from_orm(cls, orm_obj) -> InventoryDomain:
        """从 Inventory ORM 对象构建领域对象。"""
        return cls(
            id=orm_obj.id,
            account_id=orm_obj.account_id,
            product_id=orm_obj.product_id,
            quantity=orm_obj.quantity if orm_obj.quantity is not None else 0,
        )