"""OrderIntake — 销售/采购订单共享的 intake seam

负责校验、单号、items 创建、总额计算等共性逻辑。
类型专有差异通过 OrderIntakeAdapter 注入，避免 create_sale_order /
create_purchase_order 之间大量代码重复。
"""

from abc import ABC, abstractmethod
from calendar import monthrange
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import models
from crud.base import gen_order_no
from crud.products import get_product
from domain.sale_order import SaleOrderDomain
from engine_finance import FinanceEngine
from enums import OrderStatus, OrderType, PaymentMethod, PaymentStatus
from errors import BusinessError, ErrorCode
from events import emit
from rules import enforce_rules
from utils import _d, Q2


# ═══════════════════════════════════════════════════════════
# Adapter 接口
# ═══════════════════════════════════════════════════════════

class OrderIntakeAdapter(ABC):
    """销售/采购 intake 适配器接口。"""

    @property
    @abstractmethod
    def order_type_label(self) -> str: ...

    @property
    @abstractmethod
    def order_prefix(self) -> str: ...

    @property
    @abstractmethod
    def order_model(self) -> type: ...

    @property
    @abstractmethod
    def item_model(self) -> type: ...

    @property
    @abstractmethod
    def date_field(self) -> str: ...

    @property
    @abstractmethod
    def initial_status(self) -> str: ...

    @abstractmethod
    def build_order_kwargs(self, *, partner_id: Optional[int], date_value: datetime,
                           notes: str, image_url: str, **kwargs) -> Dict[str, Any]: ...

    @abstractmethod
    def apply_status_transition(self, order: Any) -> None: ...

    @abstractmethod
    def emit_created_event(self, *, db: Any, account_id: int, order: Any,
                           operator: str, deduct_inventory: bool, log_action: str,
                           log_detail: str) -> None: ...

    @abstractmethod
    def post_create_checks(self, *, db: Any, account_id: int, order: Any,
                           date_value: datetime) -> None: ...


class SaleIntakeAdapter(OrderIntakeAdapter):
    """销售单 intake 适配器。"""

    order_type_label = "销售单"
    order_prefix = "SO"
    order_model = models.SaleOrder
    item_model = models.SaleItem
    date_field = "sale_date_l1"
    initial_status = OrderStatus.PENDING

    def build_order_kwargs(self, *, partner_id, date_value, notes, image_url, **kwargs):
        return {
            "customer_id": partner_id,
            "order_type": OrderType.RETAIL,
            "payment_status": kwargs.get("payment_status", PaymentStatus.UNPAID),
            "has_invoice_l1": kwargs.get("has_invoice", True),
            "status": self.initial_status,
            "notes": notes,
            "image_url": image_url,
            "total_price_l1": Decimal("0"),
            "tax_amount_l1": _d(kwargs.get("tax_amount")) if kwargs.get("tax_amount") is not None else Decimal("0"),
            self.date_field: date_value,
        }

    def apply_status_transition(self, order):
        domain = SaleOrderDomain.from_orm(order)
        violations = domain.validate()
        if violations:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": f"销售单校验失败: {'; '.join(violations)}"})
        domain.transition_to(OrderStatus.COMPLETED)
        order.status = domain.status

    def emit_created_event(self, *, db, account_id, order, operator, deduct_inventory,
                           log_action, log_detail):
        emit("sale_order.created", db=db, account_id=account_id, order=order,
             operator=operator, deduct_inventory=deduct_inventory,
             log_action=log_action, log_detail=log_detail)

    def post_create_checks(self, *, db, account_id, order, date_value):
        # AS-04 权责发生制校验：期间有销售订单时总账 6001 应有贷方发生额
        # 必须在财务 handler 生成凭证后执行，因此放在 emit 之后
        s_date = date_value.date() if isinstance(date_value, datetime) else date_value
        enforce_rules(db, ["AS-04"], {
            "account_id": account_id,
            "start_date": s_date.replace(day=1),
            "end_date": s_date.replace(day=monthrange(s_date.year, s_date.month)[1]),
        })


class PurchaseIntakeAdapter(OrderIntakeAdapter):
    """采购单 intake 适配器。"""

    order_type_label = "采购单"
    order_prefix = "PO"
    order_model = models.PurchaseOrder
    item_model = models.PurchaseItem
    date_field = "purchase_date_l1"
    initial_status = OrderStatus.COMPLETED

    def build_order_kwargs(self, *, partner_id, date_value, notes, image_url, **kwargs):
        return {
            "supplier_id": partner_id,
            "order_type": OrderType.RETAIL,
            "payment_method": kwargs.get("payment_method", PaymentMethod.COMPANY),
            "status": self.initial_status,
            "notes": notes,
            "image_url": image_url,
            "total_price_l1": Decimal("0"),
            "tax_amount_l1": _d(kwargs.get("tax_amount")) if kwargs.get("tax_amount") is not None else Decimal("0"),
            self.date_field: date_value,
        }

    def apply_status_transition(self, order):
        # 采购单创建即完成，无需状态机转换
        pass

    def emit_created_event(self, *, db, account_id, order, operator, deduct_inventory,
                           log_action, log_detail):
        emit("purchase_order.created", db=db, account_id=account_id, order=order,
             operator=operator, log_action=log_action, log_detail=log_detail)

    def post_create_checks(self, *, db, account_id, order, date_value):
        # 采购单暂无销售类权责发生制校验
        pass


# ═══════════════════════════════════════════════════════════
# 共享 intake 逻辑
# ═══════════════════════════════════════════════════════════

class OrderIntake:
    """订单创建 intake seam。

    通过 adapter 区分销售/采购，统一处理：
    - 商品明细校验（非空、无重复、必填字段）
    - 业务日期解析
    - 单号生成
    - 订单对象创建
    - 明细金额计算
    - 总额/税额回写
    - 状态转换
    - 领域事件触发
    - 后置准则校验
    """

    def __init__(self, adapter: OrderIntakeAdapter):
        self.adapter = adapter

    def create_order(
        self,
        db: Any,
        account_id: int,
        operator: str,
        items: List[dict],
        business_date: Any,
        partner_id: Optional[int] = None,
        total_price: Optional[Any] = None,
        tax_amount: Optional[Any] = None,
        notes: str = "",
        image_url: str = "",
        order_no: Optional[str] = None,
        auto_generated_from: Optional[str] = None,
        **type_kwargs,
    ) -> Any:
        self._validate_items(items)
        date_value = self._parse_date(business_date)
        if order_no is None:
            order_no = gen_order_no(db, self.adapter.order_prefix, date_value)

        order = self.adapter.order_model(
            account_id=account_id,
            order_no=order_no,
            **self.adapter.build_order_kwargs(
                partner_id=partner_id,
                date_value=date_value,
                notes=notes,
                image_url=image_url,
                tax_amount=tax_amount,
                **type_kwargs,
            ),
        )
        db.add(order)
        db.flush()

        account = db.get(models.Account, account_id)
        enable_vat = FinanceEngine._vat_deduction(account)
        items_data, total_tax = self._calculate_items(db, account_id, items, enable_vat)

        if total_price is not None:
            from crud.orders import _distribute_total_price
            _distribute_total_price(items_data, total_price)

        for it in items_data:
            item = self.adapter.item_model(
                order_id=order.id,
                product_id=it["product_id"],
                quantity_l1=it["quantity_l1"],
                unit_price_l1=it["unit_price_l1"],
                tax_rate_l1=it["tax_rate_l1"],
                total_price_l1=it["total_price_l1"],
            )
            db.add(item)

        final_total = sum(_d(it["total_price_l1"]) for it in items_data)
        order.total_price_l1 = (_d(total_price) if total_price is not None else (final_total + total_tax)).quantize(Q2)
        order.tax_amount_l1 = (_d(tax_amount) if tax_amount is not None else total_tax).quantize(Q2)
        db.flush()

        self.adapter.apply_status_transition(order)
        db.flush()

        log_detail = (
            f"创建{self.adapter.order_type_label} {order_no}: {len(items)}项商品, 总价={order.total_price_l1}"
            if not auto_generated_from
            else f"发票 {auto_generated_from} 自动生成{self.adapter.order_type_label} {order_no}: 价税合计={order.total_price_l1}, 税额={order.tax_amount_l1}"
        )

        # adapter 决定是否扣减库存（销售单专用）
        deduct_inventory = type_kwargs.get("deduct_inventory", True)
        self.adapter.emit_created_event(
            db=db, account_id=account_id, order=order, operator=operator,
            deduct_inventory=deduct_inventory,
            log_action="create", log_detail=log_detail,
        )

        self.adapter.post_create_checks(db=db, account_id=account_id, order=order, date_value=date_value)

        db.flush()
        return order

    # ── 私有工具方法 ──

    def _validate_items(self, items: List[dict]) -> None:
        if not items:
            raise BusinessError(code=ErrorCode.ORDER_EMPTY_ITEMS,
                                data={"order_type": self.adapter.order_type_label})

        product_ids = [it["product_id"] for it in items]
        dup_pids = [pid for pid, cnt in Counter(product_ids).items() if cnt > 1]
        if dup_pids:
            raise BusinessError(code=ErrorCode.ORDER_DUPLICATE_PRODUCT,
                                data={"product_ids": dup_pids})

        for it in items:
            for key in ("quantity_l1", "unit_price_l1", "tax_rate_l1"):
                if key not in it:
                    raise BusinessError(
                        code=ErrorCode.VALIDATION_ERROR,
                        data={"details": f"商品明细缺少字段 {key}，请通过 Schema.to_orm_kwargs() 生成"},
                    )

    def _parse_date(self, business_date: Any) -> datetime:
        if not business_date:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"{self.adapter.order_type_label}日期不能为空，请提供业务发生日期",
                ai_instruction=f"STOP_RETRYING. {self.adapter.date_field} 字段必填，请补充业务日期。",
            )

        if isinstance(business_date, str):
            return datetime.fromisoformat(business_date)
        elif isinstance(business_date, datetime):
            return business_date
        elif hasattr(business_date, "year"):
            return datetime(business_date.year, business_date.month, business_date.day)
        return business_date

    def _calculate_items(self, db: Any, account_id: int, items: List[dict],
                         enable_vat: bool) -> Tuple[List[dict], Decimal]:
        items_data = []
        total_tax = Decimal("0")
        for it in items:
            product = get_product(db, account_id, it["product_id"])
            if not product:
                raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND,
                                    data={"product_id": it["product_id"]})
            line_total = (_d(it["quantity_l1"]) * _d(it["unit_price_l1"])).quantize(Q2)
            tax_rate = it["tax_rate_l1"]
            item_tax = (line_total * _d(tax_rate)).quantize(Q2) if enable_vat else Decimal("0")
            items_data.append({
                "product_id": it["product_id"],
                "quantity_l1": it["quantity_l1"],
                "unit_price_l1": it["unit_price_l1"],
                "tax_rate_l1": tax_rate,
                "total_price_l1": line_total,
            })
            total_tax += item_tax
        return items_data, total_tax
