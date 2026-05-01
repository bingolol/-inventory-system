"""测试重复商品校验"""
from crud.orders import create_sale_order, create_purchase_order
from database import SessionLocal, init_db
from schemas import SaleOrderCreate, SaleItemCreate, PurchaseOrderCreate, PurchaseItemCreate

init_db()
db = SessionLocal()

# 测试1: 销售单重复商品应报错
try:
    data = SaleOrderCreate(
        items=[
            SaleItemCreate(product_id=9, quantity=5, unit_price=100),
            SaleItemCreate(product_id=9, quantity=3, unit_price=200),
        ]
    )
    create_sale_order(db, 1, data)
    print("FAIL: 应该报错但没有")
except ValueError as e:
    print(f"PASS: 销售单重复商品校验 - {e}")

# 测试2: 采购单重复商品应报错
try:
    data = PurchaseOrderCreate(
        items=[
            PurchaseItemCreate(product_id=9, quantity=5, unit_price=100),
            PurchaseItemCreate(product_id=9, quantity=3, unit_price=200),
        ]
    )
    create_purchase_order(db, 1, data)
    print("FAIL: 应该报错但没有")
except ValueError as e:
    print(f"PASS: 采购单重复商品校验 - {e}")

# 测试3: 不重复商品应正常
try:
    data = SaleOrderCreate(
        customer_id=7,
        project_id=1,
        items=[
            SaleItemCreate(product_id=9, quantity=5, unit_price=100),
            SaleItemCreate(product_id=29, quantity=3, unit_price=200),
        ]
    )
    order = create_sale_order(db, 1, data)
    print(f"PASS: 不同商品正常创建，order_id={order.id}")
except Exception as e:
    print(f"FAIL: 不同商品创建失败 - {e}")

db.close()