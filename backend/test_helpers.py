"""集成测试公共辅助函数（放在 backend/ 下，确保 sys.path 已含 backend）"""
from decimal import Decimal
from datetime import datetime
from database import SessionLocal
from models import Account, Product, Inventory


def ensure_test_product(account_id: int = None) -> int:
    """获取或创建测试商品，确保库存≥100，返回 product_id。

    供所有集成测试共用，避免新数据库无商品导致测试失败。
    """
    db = SessionLocal()
    try:
        if account_id is None:
            acc = db.query(Account).first()
            account_id = acc.id if acc else 1
        product = db.query(Product).filter(Product.account_id == account_id).first()
        if not product:
            product = Product(
                account_id=account_id,
                name=f"测试商品-{datetime.now().strftime('%H%M%S%f')}",
                sku=f"TEST-{datetime.now().strftime('%H%M%S%f')}",
                unit="个",
                purchase_price=Decimal("50.00"),
                sale_price=Decimal("100.00"),
                track_inventory=True,
                category="测试",
            )
            db.add(product)
            db.flush()
        inv = db.query(Inventory).filter(
            Inventory.account_id == account_id,
            Inventory.product_id == product.id
        ).first()
        if inv is None:
            inv = Inventory(account_id=account_id, product_id=product.id, quantity=100)
            db.add(inv)
        elif inv.quantity < 100:
            inv.quantity = 100
        db.commit()
        return product.id
    finally:
        db.close()
