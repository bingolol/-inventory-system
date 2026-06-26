"""P0 合规性测试：商品命令 — 禁止 initial_stock、库存非负约束"""

import pytest
from decimal import Decimal

from database import SessionLocal, init_db
from commands.base import dispatch
from commands.product_commands import CreateProduct, AdjustInventory
from errors import BusinessError


@pytest.fixture(autouse=True)
def _init():
    init_db()

@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


# 使用已存在的默认账号（account_id=1）
ACCOUNT_ID = 1
OPERATOR = "test"


class TestProductCommands:
    """商品命令合规测试"""

    def test_create_product_no_inventory(self, db):
        """创建商品不产生库存记录"""
        product = dispatch(CreateProduct(
            account_id=ACCOUNT_ID,
            operator=OPERATOR,
            name="合规测试商品",
            sku="COMPLIANCE-001",
            unit="个",
            purchase_price=Decimal("100"),
            sale_price=Decimal("150"),
        ), db)
        db.commit()

        from models import Inventory
        inv = db.query(Inventory).filter(
            Inventory.product_id == product.id
        ).first()
        assert inv is None, "商品创建不应产生库存记录"

    def test_inventory_non_negative(self, db):
        """库存调整不能导致负数"""
        from models import Product
        product = dispatch(CreateProduct(
            account_id=ACCOUNT_ID, operator=OPERATOR,
            name="负库存测试", sku="NEG-001",
            purchase_price=10, sale_price=20,
        ), db)
        db.commit()

        with pytest.raises(BusinessError) as exc:
            dispatch(AdjustInventory(
                account_id=ACCOUNT_ID, operator=OPERATOR,
                product_id=product.id, quantity=-5,
                reason="测试负库存",
            ), db)
        assert "库存" in str(exc.value)

    def test_adjustment_positive_ok(self, db):
        """正向库存调整正常执行"""
        product = dispatch(CreateProduct(
            account_id=ACCOUNT_ID, operator=OPERATOR,
            name="调整测试", sku="ADJ-001",
            purchase_price=10, sale_price=20,
        ), db)
        db.commit()

        result = dispatch(AdjustInventory(
            account_id=ACCOUNT_ID, operator=OPERATOR,
            product_id=product.id, quantity=100,
            reason="初始化",
        ), db)
        db.commit()
        assert result is not None
