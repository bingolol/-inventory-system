"""集成测试辅助函数 — 补充 test helpers 层"""
import uuid
from decimal import Decimal
from database import SessionLocal, set_maintenance_mode
from models import Product, Inventory
from commands.base import dispatch
from commands.product_commands import AdjustInventory


def ensure_test_product(account_id=None, min_stock=1000):
    """确保至少存在一个测试商品，返回 product_id

    如果指定 account_id 下已有商品则直接返回其 ID；否则创建一个新商品。
    同时保证该商品库存不低于 min_stock，避免下游销售出库因库存不足失败。
    """
    aid = account_id if account_id is not None else 1

    db = SessionLocal()
    try:
        # 只查询实物商品（track_inventory_l3=True）。
        # 服务类商品无库存概念，AdjustInventory 对其返回 None inv 会报错。
        product = db.query(Product).filter(
            Product.account_id == aid,
            Product.track_inventory_l3 == True,
        ).first()
        if not product:
            tag = uuid.uuid4().hex[:8]
            product = Product(
                account_id=aid,
                name=f"测试商品-{tag}",
                sku=f"SKU-TEST-{tag}",
                unit="个",
                purchase_price_l3=10,
                sale_price_l3=20,
                track_inventory_l3=True,
                category="测试",
            )
            db.add(product)
            db.flush()
            db.refresh(product)

        inv = db.query(Inventory).filter(
            Inventory.account_id == aid,
            Inventory.product_id == product.id,
        ).first()
        current_stock = int(inv.quantity_l4) if inv else 0
        if current_stock < min_stock:
            set_maintenance_mode(True)
            try:
                dispatch(
                    AdjustInventory(
                        account_id=aid,
                        product_id=product.id,
                        quantity=float(min_stock),
                        adjust_date="2026-01-01",
                        reason="测试初始化库存",
                        unit_cost=float(product.purchase_price_l3 or 10),
                    ),
                    db,
                )
                db.commit()
            finally:
                set_maintenance_mode(False)

        return product.id
    finally:
        db.close()
