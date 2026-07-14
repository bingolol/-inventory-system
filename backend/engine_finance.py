"""财务引擎 — 会计凭证生成/冲红的唯一入口

所有业务操作（采购入库、销售出库）通过此引擎生成会计凭证，
业务代码不再手写 JournalEngine source dict。
"""
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session
import models
from finance_integration import post_journal, reverse_journal
from operation_result import EntityType
from utils import Q2
# BR-27: 税额是实体字段，引擎只读不推导
from errors import BusinessError, ErrorCode
from enums import OrderStatus
from lineage import reads, TIER_L3
from policy.vat_facts import VAT_GENERAL_DEFAULT_RATE, VAT_SMALL_SCALE_SYNDICATED_RATE


class FinanceEngine:
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id
        self._account = None

    @property
    def account(self):
        if self._account is None:
            self._account = self.db.get(models.Account, self.account_id)
        return self._account

    @staticmethod
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    def _vat_deduction(account) -> bool:
        if account is None:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": "账户信息缺失，无法判断进项税抵扣资格"})
        return account.taxpayer_type_l3 == "general"

    @staticmethod
    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    def _vat_rate(account) -> Decimal:
        """获取默认增值税税率

        注意：此方法仅提供默认税率，用于小规模纳税人销售价税分离的兜底场景。
        - 一般纳税人：默认 13%，但实际销售时以行项 item.tax_rate_l1 为准（支持 13%/9%/6% 多税率商品）
        - 小规模纳税人：法定征收率 3%（减按 1% 征收的优惠在 AccountingEngine.calculate_vat 中处理）
        """
        if account is None:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": "账户信息缺失，无法确定增值税税率"})
        return VAT_GENERAL_DEFAULT_RATE.value if account.taxpayer_type_l3 == "general" else VAT_SMALL_SCALE_SYNDICATED_RATE.value

    @reads("Account.taxpayer_type_l3", tier=TIER_L3, source="policy")
    def _account_config(self) -> dict:
        return {
            "enable_vat_deduction": self._vat_deduction(self.account),
            "taxpayer_type": self.account.taxpayer_type_l3,
            "vat_rate": self._vat_rate(self.account),
        }

    def record_purchase(self, order, *, force=False):
        if not order or not order.items:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                data={"details": "采购单无明细，无法生成凭证"}
            )

        config = self._account_config()

        # 进项税可抵扣 = 一般纳税人 + 专票（普票不可抵扣，即使一般纳税人）
        from enums import InvoiceDirection, InvoiceType
        purchase_invoice = None
        if order.auto_generated_from:
            purchase_invoice = self.db.query(models.Invoice).filter(
                models.Invoice.account_id == self.account_id,
                models.Invoice.invoice_no == order.auto_generated_from,
                models.Invoice.is_reversed == False,
            ).first()
        if not purchase_invoice:
            purchase_invoice = self.db.query(models.Invoice).filter(
                models.Invoice.account_id == self.account_id,
                models.Invoice.related_order_type == "purchase_order",
                models.Invoice.related_order_id == order.id,
                models.Invoice.direction == InvoiceDirection.IN,
                models.Invoice.is_reversed == False,
            ).first()
        if purchase_invoice and purchase_invoice.invoice_type == InvoiceType.ORDINARY:
            config["enable_vat_deduction"] = False

        enable_vat = config["enable_vat_deduction"]

        if order.total_price_l1 is None:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": "采购单总价不可为空"})
        if order.tax_amount_l1 is None:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": "采购单税额不可为空"})
        total_with_tax = Decimal(str(order.total_price_l1))
        tax_amount = Decimal(str(order.tax_amount_l1))
        total_without_tax = (total_with_tax - tax_amount).quantize(Q2)

        items = []
        for item in order.items:
            product = self.db.query(models.Product).filter(
                models.Product.id == item.product_id,
                models.Product.account_id == self.account_id,
            ).first()
            if not product:
                raise BusinessError(
                    code=ErrorCode.ORDER_NOT_FOUND,
                    data={"order_type": "商品", "order_id": item.product_id},
                )
            track_inv = product.track_inventory_l3
            total_with_tax_per_item = (item.total_price_l1 / total_without_tax * total_with_tax).quantize(Q2) if total_without_tax and total_without_tax != 0 else Decimal("0")
            items.append({
                "product_id": item.product_id,
                "total_price": item.total_price_l1,
                "total_with_tax": total_with_tax_per_item,
                "track_inventory": track_inv,
            })

        source = {
            "partner_id": order.supplier_id or 0,
            "total_with_tax": total_with_tax,
            "total_without_tax": total_without_tax,
            "tax_amount": tax_amount,
            "items": items,
            "source_model": EntityType.PURCHASE_ORDER,
            "source_id": order.id,
            "date": order.purchase_date_l1,
            "account_config": config,
            "payment_method": getattr(order, "payment_method", "company"),
        }
        return post_journal(self.db, self.account_id, EntityType.PURCHASE_ORDER, source, force=force)

    def record_sale(self, order, *, force=False):
        if not order or not order.items:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                data={"details": "销售单无明细，无法生成凭证"}
            )

        if order.total_price_l1 is None:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": "销售单总价不可为空"})
        if order.tax_amount_l1 is None:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                data={"details": "销售单税额不可为空"})
        total_with_tax = Decimal(str(order.total_price_l1))
        tax_amount = Decimal(str(order.tax_amount_l1))
        total_without_tax = (total_with_tax - tax_amount).quantize(Q2)
        source = {
            "partner_id": order.customer_id or 0,
            "total_with_tax": total_with_tax,
            "total_without_tax": total_without_tax,
            "tax_amount": tax_amount,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity_l1,
                    "unit_price": str(item.unit_price_l1),
                    "unit_cost": str(item.unit_cost_l2) if item.unit_cost_l2 else "0",
                }
                for item in order.items
            ],
            "source_model": EntityType.SALE_ORDER,
            "source_id": order.id,
            "date": order.sale_date_l1,
            "account_config": self._account_config(),
        }
        return post_journal(self.db, self.account_id, EntityType.SALE_ORDER, source, force=force)

    def _resolve_order(self, order_id: int, model):
        order = self.db.query(model).filter(
            model.id == order_id,
            model.account_id == self.account_id,
        ).first()
        if not order:
            order_type = "销售单" if model.__name__ == "SaleOrder" else "采购单"
            raise BusinessError(
                code=ErrorCode.ORDER_NOT_FOUND,
                data={"order_type": order_type, "order_id": order_id},
            )
        return order

    def reverse_purchase(self, order_id: int, *, force=False):
        self._resolve_order(order_id, models.PurchaseOrder)
        return reverse_journal(self.db, self.account_id, EntityType.PURCHASE_ORDER, order_id, force=force)

    def reverse_sale(self, order_id: int, *, force=False):
        self._resolve_order(order_id, models.SaleOrder)
        return reverse_journal(self.db, self.account_id, EntityType.SALE_ORDER, order_id, force=force)
