"""FinanceOrchestrator — commands 调用 engines 的统一入口

把"先库存、后财务"的订单入账顺序，以及折旧/摊销/月结等流程
集中到一处，避免 commands 里散落 InventoryEngine + FinanceEngine 的调用。
"""

from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

import models
from engine_inventory import InventoryEngine
from engine_finance import FinanceEngine
from engine_fixed_asset import FixedAssetEngine
from engine_intangible_asset import IntangibleAssetEngine
from engine_period_close import PeriodCloseEngine


class FinanceOrchestrator:
    def __init__(self, db: Session, account_id: int):
        self.db = db
        self.account_id = account_id
        self.inventory = InventoryEngine(db)
        self.finance = FinanceEngine(db, account_id)
        self.fixed_asset = FixedAssetEngine(db, account_id)
        self.intangible_asset = IntangibleAssetEngine(db, account_id)
        self.period_close = PeriodCloseEngine(db)

    def _product(self, product_id: int):
        return self.db.query(models.Product).filter(
            models.Product.id == product_id,
            models.Product.account_id == self.account_id,
        ).first()

    def record_sale_order_completed(self, order: models.SaleOrder, operator: str):
        """销售单完成入账：库存出库 + 销售凭证"""
        for item in order.items:
            product = self._product(item.product_id)
            if product and product.track_inventory_l3:
                unit_cost = self.inventory.force_outbound(
                    account_id=self.account_id,
                    product_id=item.product_id,
                    quantity=item.quantity_l1,
                    source_type="sale_order",
                    source_id=order.id,
                    operator=operator,
                    move_date=order.sale_date_l1,
                )
                item.set_calculated_cost(unit_cost)
            else:
                item.set_calculated_cost(Decimal("0"))
        return self.finance.record_sale(order)

    def reverse_sale_order(self, order: models.SaleOrder, operator: str, force: bool = False):
        """冲销销售单：库存回退 + 冲销凭证"""
        for item in order.items:
            product = self._product(item.product_id)
            if product and product.track_inventory_l3:
                self.inventory.reverse(
                    account_id=self.account_id,
                    product_id=item.product_id,
                    quantity=item.quantity_l1,
                    unit_cost=Decimal(str(item.unit_cost_l2 or 0)),
                    source_type="sale_order",
                    source_id=order.id,
                    operator=operator,
                    force=force,
                )
        return self.finance.reverse_sale(order.id, force=force)

    def record_purchase_order_completed(self, order: models.PurchaseOrder, operator: str):
        """采购单完成入账：库存入库 + 采购凭证"""
        for item in order.items:
            product = self._product(item.product_id)
            if product and product.track_inventory_l3:
                self.inventory.force_inbound(
                    account_id=self.account_id,
                    product_id=item.product_id,
                    quantity=item.quantity_l1,
                    unit_price=item.unit_price_l1,
                    source_type="purchase_order",
                    source_id=order.id,
                    tax_rate=item.tax_rate_l1,
                    operator=operator,
                    move_date=order.purchase_date_l1,
                )
        return self.finance.record_purchase(order)

    def reverse_purchase_order(self, order: models.PurchaseOrder, operator: str, force: bool = False):
        """冲销采购单：库存回退 + 冲销凭证"""
        for item in order.items:
            product = self._product(item.product_id)
            if product and product.track_inventory_l3:
                self.inventory.reverse(
                    account_id=self.account_id,
                    product_id=item.product_id,
                    quantity=item.quantity_l1,
                    unit_cost=Decimal("0"),
                    source_type="purchase_order",
                    source_id=order.id,
                    operator=operator,
                    force=force,
                )
        return self.finance.reverse_purchase(order.id, force=force)

    def batch_depreciate(self, period: str) -> List[models.FixedAssetDepreciation]:
        """批量计提固定资产折旧"""
        return self.fixed_asset.batch_depreciate(period)

    def batch_amortize(self, period: str) -> List[models.IntangibleAssetAmortization]:
        """批量计提无形资产摊销"""
        return self.intangible_asset.batch_amortize(period)

    def close_period(self, period: str, force: bool = False):
        """月结"""
        return self.period_close.execute(self.account_id, period, force=force)
