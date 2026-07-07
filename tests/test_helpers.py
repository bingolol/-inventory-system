"""集成测试辅助函数 — 补充 test helpers 层"""
import uuid
from database import SessionLocal
from models import Product


def ensure_test_product(account_id=None):
    """确保至少存在一个测试商品，返回 product_id

    如果指定 account_id 下已有商品则直接返回其 ID，否则创建一个新商品。
    """
    aid = account_id if account_id is not None else 1

    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.account_id == aid).first()
        if product:
            return product.id

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
        db.commit()
        db.refresh(product)
        return product.id
    finally:
        db.close()
