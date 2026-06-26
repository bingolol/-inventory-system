import pytest
from decimal import Decimal
from commands.base import dispatch
from commands.sale_commands import CreateSaleOrder, CancelSaleOrder, RestoreSaleOrder
from commands.product_commands import CreateProduct
from models import Inventory
from enums import OrderStatus, PaymentStatus


def _get_inventory_qty(db, account_id, product_id):
    inv = db.query(Inventory).filter(
        Inventory.account_id == account_id,
        Inventory.product_id == product_id,
    ).first()
    return inv.quantity if inv else None


@pytest.mark.integration
class TestInventoryRestoreIntegration:

    def test_cancel_restores_inventory(self, db):
        account_id = 1

        product1 = dispatch(CreateProduct(
            account_id=account_id,
            name="测试商品A_库存回补",
            purchase_price=10.0,
        ), db)
        db.commit()

        try:
            inv = Inventory(
                account_id=account_id,
                product_id=product1.id,
                quantity=100,
            )
            db.add(inv)
            db.commit()

            inv_before = _get_inventory_qty(db, account_id, product1.id)
            assert inv_before == 100

            order = dispatch(CreateSaleOrder(
                account_id=account_id,
                deduct_inventory=True,
                payment_status=PaymentStatus.PAID,
                items=[
                    {'product_id': product1.id, 'quantity': 5, 'unit_price': Decimal('20')},
                ],
            ), db)
            db.commit()
            assert order.status == OrderStatus.COMPLETED

            inv_after_sale = _get_inventory_qty(db, account_id, product1.id)
            assert inv_after_sale == 95

            result = dispatch(CancelSaleOrder(
                account_id=account_id,
                order_id=order.id,
            ), db)
            db.commit()
            assert result.status == OrderStatus.CANCELLED

            inv_after_cancel = _get_inventory_qty(db, account_id, product1.id)
            assert inv_after_cancel == 100

            dispatch(RestoreSaleOrder(
                account_id=account_id,
                order_id=order.id,
            ), db)
            db.commit()

            inv_after_restore = _get_inventory_qty(db, account_id, product1.id)
            assert inv_after_restore == 95

        except Exception:
            db.rollback()
            raise

        finally:
            try:
                dispatch(RestoreSaleOrder(
                    account_id=account_id,
                    order_id=order.id,
                ), db)
                db.commit()
            except Exception:
                db.rollback()
