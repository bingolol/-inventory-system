"""集成测试：销售单自定义金额 + 差额自动分配 + 单价精度

⚠️ 迁移说明：原测试直接调用 crud.orders 写函数，已改为 Command dispatch 调用，
确保与生产代码路径一致（状态机校验 + EventBus 集成）。
v7 改造：移除 Project 模块相关引用。
精度增强：验证 unit_price 列支持6位小数，分摊后 quantity×unit_price 与 total_price 一致。
"""
import pytest
from decimal import Decimal
from commands.base import dispatch
from commands.sale_commands import CreateSaleOrder, DeleteSaleOrder
from models import Product, Customer, SaleOrder


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


@pytest.mark.integration
class TestCustomPriceIntegration:
    """自定义金额的集成测试（需要真实 DB）"""

    def test_auto_calculate_without_total_price(self, db):
        """不传 total_price → 自动计算"""
        account_id = 1
        products = _get_test_products(db, account_id, 2)
        customer_id = _get_test_customer(db, account_id)

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

    def test_unit_price_precision_6_digits(self, db):
        """分摊后 unit_price 应保留6位小数精度，quantity×unit_price 与 total_price 一致"""
        account_id = 1
        products = _get_test_products(db, account_id, 1)
        customer_id = _get_test_customer(db, account_id)

        order = dispatch(CreateSaleOrder(
            account_id=account_id,
            customer_id=customer_id,
            total_price=Decimal('10.00'),
            items=[
                {'product_id': products[0][0], 'quantity': 3, 'unit_price': Decimal('0')},
            ],
        ), db)
        try:
            db.flush()
            # 从数据库重新查询，验证存储后的精度（非内存态）
            db.expire_all()
            stored_order = db.query(SaleOrder).filter(SaleOrder.id == order.id).first()
            item = stored_order.items[0]
            # unit_price 应为 3.333333（6位），不是 3.33（2位）
            assert item.unit_price == Decimal('3.333333'), f"Expected 3.333333, got {item.unit_price}"
            # quantity × unit_price 应等于 total_price（在量化精度内）
            reconstructed = Decimal(str(item.quantity)) * item.unit_price
            assert abs(reconstructed - item.total_price) < Decimal('0.01'), \
                f"quantity×unit_price={reconstructed} != total_price={item.total_price}"
        finally:
            dispatch(DeleteSaleOrder(account_id=account_id, order_id=order.id), db)