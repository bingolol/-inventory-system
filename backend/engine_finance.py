"""财务引擎 — 会计凭证生成/冲红的唯一入口

所有业务操作（采购入库、销售出库）通过此引擎生成会计凭证，
业务代码不再手写 JournalEngine source dict。
"""
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session
import models
from finance_integration import post_journal, reverse_journal
from utils import Q2


class FinanceEngine:
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id
        self._account = None

    @property
    def account(self):
        if self._account is None:
            self._account = self.db.query(models.Account).get(self.account_id)
        return self._account

    @staticmethod
    def _vat_deduction(account) -> bool:
        if account is None:
            return False
        return account.taxpayer_type == "general"

    @staticmethod
    def _vat_rate(account) -> Decimal:
        """获取默认增值税税率

        注意：此方法仅提供默认税率，用于小规模纳税人销售价税分离的兜底场景。
        - 一般纳税人：默认 13%，但实际销售时以行项 item.tax_rate 为准（支持 13%/9%/6% 多税率商品）
        - 小规模纳税人：法定征收率 3%（减按 1% 征收的优惠在 AccountingEngine.calculate_vat 中处理）
        """
        if account is None:
            return Decimal("0.03")
        return Decimal("0.13") if account.taxpayer_type == "general" else Decimal("0.03")

    def _account_config(self) -> dict:
        return {
            "enable_vat_deduction": self._vat_deduction(self.account),
            "taxpayer_type": self.account.taxpayer_type if self.account else "small_scale",
            "vat_rate": self._vat_rate(self.account),
        }

    def record_purchase(self, order, calculated_data: List[dict] = None) -> None:
        if calculated_data is not None:
            total_with_tax = Decimal(sum(Decimal(str(i["total_amount"])) for i in calculated_data)).quantize(Q2)
            total_without_tax = Decimal(sum(Decimal(str(i["total_cost"])) for i in calculated_data)).quantize(Q2)
            tax_amount = Decimal(sum(Decimal(str(i["tax_amount"])) for i in calculated_data)).quantize(Q2)
        else:
            from finance_integration import _calc_tax_from_items
            items_for_tax = [
                {"total_price": str(item.total_price), "tax_rate": str(item.tax_rate)}
                for item in order.items
            ]
            tax_info = _calc_tax_from_items(order.total_price, items_for_tax)
            total_with_tax = order.total_price
            total_without_tax = tax_info["total_without_tax"]
            tax_amount = tax_info["tax_amount"]

        source = {
            "partner_id": order.supplier_id or 0,
            "total_with_tax": total_with_tax,
            "total_without_tax": total_without_tax,
            "tax_amount": tax_amount,
            "source_model": "purchase_order",
            "source_id": order.id,
            "date": order.purchase_date,
            "account_config": self._account_config(),
        }
        post_journal(self.db, self.account_id, "purchase_order", source)

    def record_sale(self, order) -> None:
        is_small_scale = self.account and self.account.taxpayer_type == "small_scale"
        total_without_tax = Decimal('0')
        tax_amount = Decimal('0')
        for item in order.items:
            line_total = Decimal(str(item.total_price))
            total_without_tax += line_total
            rate = item.tax_rate
            if is_small_scale and rate and rate > 0:
                rate = self._vat_rate(self.account)
            if rate:
                tax_amount += (line_total * Decimal(str(rate))).quantize(Q2)
        tax_amount = tax_amount.quantize(Q2)
        total_with_tax = (total_without_tax + tax_amount).quantize(Q2)
        source = {
            "partner_id": order.customer_id or 0,
            "total_with_tax": total_with_tax,
            "total_without_tax": total_without_tax,
            "tax_amount": tax_amount,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                    "unit_cost": str(item.unit_cost) if item.unit_cost else "0",
                }
                for item in order.items
            ],
            "source_model": "sale_order",
            "source_id": order.id,
            "date": order.sale_date,
            "account_config": self._account_config(),
        }
        post_journal(self.db, self.account_id, "sale_order", source)

    def reverse_purchase(self, order_id: int) -> None:
        """冲红采购凭证"""
        reverse_journal(self.db, self.account_id, "purchase_order", order_id)

    def reverse_sale(self, order_id: int) -> None:
        """冲红销售凭证"""
        reverse_journal(self.db, self.account_id, "sale_order", order_id)
