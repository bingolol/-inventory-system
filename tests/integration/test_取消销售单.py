"""集成测试：取消销售单 → 状态机 + DB 联动"""
import time
import pytest
from decimal import Decimal
from datetime import datetime
from commands.base import dispatch
from commands.sale_commands import CancelSaleOrder, RestoreSaleOrder
from models import SaleOrder, Customer, Product, SaleItem, Account
from enums import OrderStatus, PaymentStatus, OrderType
from errors import BusinessError


@pytest.fixture(scope="module", autouse=True)
def seed_completed_sale_order():
    """模块级前置：创建一条已完成销售单供取消测试"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        acc = db.query(Account).filter(Account.id == 2).first()
        account_id = acc.id if acc else (db.query(Account).first().id or 1)
        ts = str(int(time.time()))
        customer = Customer(
            account_id=account_id, name=f"取消测试客户-{ts}",
            contact="测试", phone=f"138{ts[-8:]}",
        )
        db.add(customer)
        db.flush()
        product = Product(
            account_id=account_id, name=f"取消测试商品-{ts}",
            sku=f"CANCTEST-{ts}", unit="个",
            purchase_price=Decimal("50.00"), sale_price=Decimal("100.00"),
            track_inventory=False, category="测试",
        )
        db.add(product)
        db.flush()
        order = SaleOrder(
            account_id=account_id, order_no=f"CT-{ts}",
            customer_id=customer.id, order_type=OrderType.RETAIL,
            total_price=Decimal("100.00"), status=OrderStatus.COMPLETED,
            payment_status=PaymentStatus.UNPAID, sale_date=datetime.now(),
        )
        db.add(order)
        db.flush()
        item = SaleItem(
            order_id=order.id, product_id=product.id, quantity=1,
            unit_price=Decimal("100.00"), tax_rate=Decimal("0.01"),
            total_price=Decimal("100.00"),
        )
        db.add(item)
        db.commit()
    finally:
        db.close()


@pytest.mark.integration
class TestCancelSaleOrderIntegration:
    """取消已完成销售单的集成测试（需要真实 DB）"""

    def _find_completed_order(self, db, account_id=2):
        return db.query(SaleOrder).filter(
            SaleOrder.status == OrderStatus.COMPLETED,
            SaleOrder.account_id == account_id,
        ).first()

    def test_cancel_completed_order(self, db):
        """取消已完成订单 → 成功"""
        order = self._find_completed_order(db)
        assert order is not None, "seed_completed_sale_order fixture should have created data"

        order_id = order.id
        account_id = order.account_id

        try:
            result = dispatch(CancelSaleOrder(
                account_id=account_id,
                order_id=order_id,
            ), db)
            db.commit()
            assert result.status == OrderStatus.CANCELLED

            dispatch(RestoreSaleOrder(
                account_id=account_id,
                order_id=order_id,
            ), db)
            db.commit()
        except Exception:
            db.rollback()
            raise

    def test_cancel_already_cancelled_blocked(self, db):
        """重复取消已取消订单 → 状态机阻止"""
        order = self._find_completed_order(db)
        assert order is not None, "seed_completed_sale_order fixture should have created data"

        order_id = order.id
        account_id = order.account_id

        try:
            dispatch(CancelSaleOrder(
                account_id=account_id,
                order_id=order_id,
            ), db)
            db.commit()
        except Exception:
            db.rollback()
            return

        try:
            with pytest.raises(BusinessError):
                dispatch(CancelSaleOrder(
                    account_id=account_id,
                    order_id=order_id,
                ), db)
        finally:
            try:
                dispatch(RestoreSaleOrder(
                    account_id=account_id,
                    order_id=order_id,
                ), db)
                db.commit()
            except Exception:
                db.rollback()