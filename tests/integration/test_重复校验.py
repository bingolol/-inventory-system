"""集成测试：重复商品校验

⚠️ 迁移说明：原测试直接调用 crud.orders 写函数，已改为 Command dispatch 调用，
确保与生产代码路径一致（状态机校验 + EventBus 集成）。
"""
import pytest
from decimal import Decimal
from commands.base import dispatch
from commands.sale_commands import CreateSaleOrder, DeleteSaleOrder
from commands.purchase_commands import CreatePurchaseOrder, DeletePurchaseOrder
from models import Product, Customer
from errors import BusinessError


def _get_test_products(db, account_id, count=2):
    prods = db.query(Product).filter(
        Product.account_id == account_id,
    ).limit(count).all()
    if len(prods) < count:
        pytest.skip(f"Need at least {count} products for account {account_id}")
    return prods


def _get_test_customer(db, account_id):
    cust = db.query(Customer).filter(Customer.account_id == account_id).first()
    if not cust:
        pytest.skip(f"No customer found for account {account_id}")
    return cust.id


@pytest.mark.integration
class TestDupCheckIntegration:
    """重复商品校验的集成测试（需要真实 DB）"""

    def test_sale_order_duplicate_product_blocked(self, db):
        """销售单重复商品 → 报错"""
        prods = _get_test_products(db, 1, 1)
        with pytest.raises(BusinessError):
            dispatch(CreateSaleOrder(
                account_id=1,
                deduct_inventory=False,
                items=[
                    {'product_id': prods[0].id, 'quantity': 5, 'unit_price': Decimal('100')},
                    {'product_id': prods[0].id, 'quantity': 3, 'unit_price': Decimal('200')},
                ],
            ), db)

    def test_purchase_order_duplicate_product_blocked(self, db):
        """采购单重复商品 → 报错"""
        prods = _get_test_products(db, 1, 1)
        with pytest.raises(BusinessError):
            dispatch(CreatePurchaseOrder(
                account_id=1,
                items=[
                    {'product_id': prods[0].id, 'quantity': 5, 'unit_price': Decimal('100')},
                    {'product_id': prods[0].id, 'quantity': 3, 'unit_price': Decimal('200')},
                ],
            ), db)

    def test_different_products_ok(self, db):
        """不同商品 → 正常创建"""
        prods = _get_test_products(db, 1, 2)
        customer_id = _get_test_customer(db, 1)

        order = dispatch(CreateSaleOrder(
            account_id=1,
            customer_id=customer_id,
            deduct_inventory=False,
            items=[
                {'product_id': prods[0].id, 'quantity': 5, 'unit_price': Decimal('100')},
                {'product_id': prods[1].id, 'quantity': 3, 'unit_price': Decimal('200')},
            ],
        ), db)
        try:
            assert order.id is not None
        finally:
            dispatch(DeleteSaleOrder(account_id=1, order_id=order.id), db)