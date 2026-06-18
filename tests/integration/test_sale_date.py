"""集成测试：销售单 sale_date 自定义日期"""
import pytest
from datetime import datetime
from commands.base import dispatch
from commands.sale_commands import CreateSaleOrder
from models import SaleOrder


@pytest.mark.integration
class TestSaleDateCustom:
    """销售单创建时支持自定义 sale_date"""

    def _get_account_id(self, db):
        from models import Account
        acc = db.query(Account).first()
        return acc.id if acc else 1

    def test_create_sale_with_custom_date(self, db):
        """创建销售单时传入自定义日期 → sale_date 等于传入值"""
        account_id = self._get_account_id(db)
        custom_date = datetime(2025, 3, 15, 10, 30, 0)

        try:
            order = dispatch(CreateSaleOrder(
                account_id=account_id,
                has_invoice=False,
                payment_status="unpaid",
                notes="自定义日期测试",
                sale_date=custom_date,
                items=[{"product_id": 1, "quantity": 1, "unit_price": 100}],
            ), db)
            db.flush()

            assert order.sale_date is not None
            assert order.sale_date.year == 2025
            assert order.sale_date.month == 3
            assert order.sale_date.day == 15
        except Exception:
            db.rollback()
            raise

    def test_schema_accepts_sale_date(self):
        """SaleOrderCreate schema 接受 sale_date 字段"""
        from schemas.order import SaleOrderCreate
        from decimal import Decimal

        data = SaleOrderCreate(
            customer_id=None,
            has_invoice=False,
            payment_status="unpaid",
            notes="schema测试",
            sale_date=datetime(2025, 6, 1),
            items=[{"product_id": 1, "quantity": 1, "unit_price": 50, "tax_rate": Decimal("0.03")}],
        )
        assert data.sale_date is not None
        assert data.sale_date.year == 2025
        assert data.sale_date.month == 6
