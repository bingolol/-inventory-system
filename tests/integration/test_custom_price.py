"""集成测试：销售单自定义金额 + 差额自动分配

⚠️ 迁移说明：原测试直接调用 crud.orders 写函数，已改为 Command dispatch 调用，
确保与生产代码路径一致（状态机校验 + EventBus 集成）。
"""
import pytest
from decimal import Decimal
from commands.base import dispatch
from commands.sale_commands import CreateSaleOrder, DeleteSaleOrder
from models import Product, Customer, Project


def _get_test_products(db, account_id, count=3):
    """获取测试用商品，返回 list[(id, price)]"""
    prods = db.query(Product).filter(
        Product.account_id == account_id,
    ).limit(count).all()
    if len(prods) < count:
        pytest.skip(f"Need at least {count} products for account {account_id}")
    return [(p.id, float(p.purchase_price or 100)) for p in prods]


def _get_test_customer(db, account_id):
    cust = db.query(Customer).filter(Customer.account_id == account_id).first()
    if not cust:
        pytest.skip(f"No customer found for account {account_id}")
    return cust.id


def _get_test_project(db, account_id):
    proj = db.query(Project).filter(Project.account_id == account_id).first()
    if not proj:
        pytest.skip(f"No project found for account {account_id}")
    return proj.id


@pytest.mark.integration
class TestCustomPriceIntegration:
    """自定义金额的集成测试（需要真实 DB）"""

    def test_auto_calculate_without_total_price(self, db):
        """不传 total_price → 自动计算"""
        account_id = 1
        products = _get_test_products(db, account_id, 2)
        customer_id = _get_test_customer(db, account_id)
        project_id = _get_test_project(db, account_id)

        order = dispatch(CreateSaleOrder(
            account_id=account_id,
            customer_id=customer_id,
            items=[
                {'product_id': products[0][0], 'quantity': 2, 'unit_price': Decimal('100')},
                {'product_id': products[1][0], 'quantity': 1, 'unit_price': Decimal('200')},
            ],
        ), db)
        try:
            assert float(order.total_price) == 400.0
        finally:
            dispatch(DeleteSaleOrder(account_id=account_id, order_id=order.id), db)

    def test_distribute_to_zero_price_items(self, db):
        """传 total_price，单价为0 → 差额分配到单价为0的行"""
        account_id = 1
        products = _get_test_products(db, account_id, 3)
        customer_id = _get_test_customer(db, account_id)
        project_id = _get_test_project(db, account_id)

        order = dispatch(CreateSaleOrder(
            account_id=account_id,
            customer_id=customer_id,
            total_price=Decimal('5000'),
            items=[
                {'product_id': products[0][0], 'quantity': 12, 'unit_price': Decimal('0')},
                {'product_id': products[1][0], 'quantity': 1, 'unit_price': Decimal('0')},
                {'product_id': products[2][0], 'quantity': 1, 'unit_price': Decimal('0')},
            ],
        ), db)
        try:
            assert float(order.total_price) == 5000.0
            item_sum = sum(item.total_price for item in order.items)
            assert abs(float(item_sum) - 5000.0) < 0.02
        finally:
            dispatch(DeleteSaleOrder(account_id=account_id, order_id=order.id), db)

    def test_distribute_to_partial_zero_price_items(self, db):
        """传 total_price，部分行有单价 → 差额分配到单价为0的行"""
        account_id = 1
        products = _get_test_products(db, account_id, 3)
        customer_id = _get_test_customer(db, account_id)
        project_id = _get_test_project(db, account_id)

        order = dispatch(CreateSaleOrder(
            account_id=account_id,
            customer_id=customer_id,
            total_price=Decimal('5000'),
            items=[
                {'product_id': products[0][0], 'quantity': 12, 'unit_price': Decimal('200')},
                {'product_id': products[1][0], 'quantity': 1, 'unit_price': Decimal('0')},
                {'product_id': products[2][0], 'quantity': 1, 'unit_price': Decimal('0')},
            ],
        ), db)
        try:
            assert float(order.total_price) == 5000.0
            item_sum = sum(item.total_price for item in order.items)
            assert abs(float(item_sum) - 5000.0) < 0.02
        finally:
            dispatch(DeleteSaleOrder(account_id=account_id, order_id=order.id), db)

    def test_proportional_discount_when_all_have_price(self, db):
        """传 total_price，所有行都有单价 → 按比例打折"""
        account_id = 1
        products = _get_test_products(db, account_id, 2)
        customer_id = _get_test_customer(db, account_id)
        project_id = _get_test_project(db, account_id)

        order = dispatch(CreateSaleOrder(
            account_id=account_id,
            customer_id=customer_id,
            total_price=Decimal('360'),
            items=[
                {'product_id': products[0][0], 'quantity': 2, 'unit_price': Decimal('100')},
                {'product_id': products[1][0], 'quantity': 1, 'unit_price': Decimal('200')},
            ],
        ), db)
        try:
            assert float(order.total_price) == 360.0
            item_sum = sum(item.total_price for item in order.items)
            assert abs(float(item_sum) - 360.0) < 0.02
        finally:
            dispatch(DeleteSaleOrder(account_id=account_id, order_id=order.id), db)