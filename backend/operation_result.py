"""OperationResult - 统一操作结果格式

所有写操作（创建/更新/删除）都返回此格式，让端侧Agent能够：
1. 知道操作是否成功
2. 知道具体发生了什么变化
3. 知道下一步该做什么
4. 自检是否出现幻觉
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional


class OperationType(str, Enum):
    """操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class EntityType(str, Enum):
    """业务实体类型 — 全仓 source_model / related_entity_type / source_type 唯一真相源"""
    PURCHASE_ORDER = "purchase_order"
    SALE_ORDER = "sale_order"
    EXPENSE = "expense"
    PAYMENT = "payment"
    RECEIPT = "receipt"
    PRODUCT = "product"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    INVOICE = "invoice"
    OPENING_BALANCE = "opening_balance"
    FIXED_ASSET = "fixed_asset"
    BANK_ENTRY = "bank_entry"
    PERSONAL_ADVANCE = "personal_advance"
    PERSONAL_ADVANCE_REPAYMENT = "personal_advance_repayment"
    DEPRECIATION = "depreciation"
    ASSET_DISPOSAL = "asset_disposal"
    FIXED_ASSET_PURCHASE = "fixed_asset_purchase"
    INTANGIBLE_ASSET_PURCHASE = "intangible_asset_purchase"
    CASH_FLOW = "cash_flow"
    SALE_RETURN = "sale_return"
    PURCHASE_RETURN = "purchase_return"
    TAX_SURCHARGE = "tax_surcharge"
    TAX_INCOME = "tax_income"
    TAX_INCOME_REVERSAL = "tax_income_reversal"
    VAT_TRANSFER_OUT = "vat_transfer_out"
    VAT_EXEMPTION = "vat_exemption"
    BANK_FEE_ENTRY = "bank_fee_entry"
    REVERSE_ENTRY = "reverse_entry"
    PERIOD_CLOSE = "period_close"
    YEAR_CLOSE = "year_close"
    REVERSAL = "reversal"
    INVENTORY_ADJUSTMENT = "inventory_adjustment"


@dataclass
class OperationResult:
    """统一操作结果格式"""
    operation: OperationType
    entity_type: EntityType
    entity_id: int
    summary: str
    ai_hint: str
    data: Dict[str, Any] = field(default_factory=dict)
    changes: Dict[str, Any] = field(default_factory=dict)
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """序列化为 JSON 响应体，处理 Decimal 类型"""
        def convert_decimals(obj: Any) -> Any:
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(v) for v in obj]
            return obj

        return {
            "success": self.success,
            "operation": self.operation.value,
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "summary": self.summary,
            "changes": convert_decimals(self.changes),
            "ai_hint": self.ai_hint,
            "data": convert_decimals(self.data),
        }
