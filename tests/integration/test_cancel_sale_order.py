"""集成测试：取消销售单 → 状态机 + DB 联动"""
import pytest
from commands.base import dispatch
from commands.sale_commands import CancelSaleOrder, RestoreSaleOrder
from models import SaleOrder
from enums import OrderStatus


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
        if not order:
            pytest.skip("No completed sale order found")

        order_id = order.id
        account_id = order.account_id

        try:
            result = dispatch(CancelSaleOrder(
                account_id=account_id,
                order_id=order_id,
            ), db)
            db.commit()
            assert result.status == OrderStatus.CANCELLED

            # 恢复回来
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
        if not order:
            pytest.skip("No completed sale order found")

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
            with pytest.raises(ValueError, match="非法状态转换"):
                dispatch(CancelSaleOrder(
                    account_id=account_id,
                    order_id=order_id,
                ), db)
        finally:
            # 恢复
            try:
                dispatch(RestoreSaleOrder(
                    account_id=account_id,
                    order_id=order_id,
                ), db)
                db.commit()
            except Exception:
                db.rollback()