"""测试销售单自定义金额 + 差额自动分配"""
from crud.orders import create_sale_order, update_sale_order, delete_sale_order
from database import SessionLocal, init_db
from schemas import SaleOrderCreate, SaleItemCreate, SaleOrderUpdate

init_db()
db = SessionLocal()

# 测试1: 不传 total_price → 自动计算
try:
    data = SaleOrderCreate(
        customer_id=7, project_id=1,
        items=[
            SaleItemCreate(product_id=9, quantity=2, unit_price=100),
            SaleItemCreate(product_id=29, quantity=1, unit_price=200),
        ]
    )
    order = create_sale_order(db, 1, data)
    assert order.total_price == 400.0, f"FAIL: {order.total_price}"
    print(f"PASS: 不传total_price自动计算 = {order.total_price}")
    delete_sale_order(db, 1, order.id)
except Exception as e:
    print(f"FAIL: {e}")

# 测试2: 传 total_price，单价为0 → 差额分配到单价为0的行
try:
    data = SaleOrderCreate(
        customer_id=7, project_id=1,
        total_price=5000,
        items=[
            SaleItemCreate(product_id=9, quantity=12, unit_price=0),
            SaleItemCreate(product_id=29, quantity=1, unit_price=0),
            SaleItemCreate(product_id=30, quantity=1, unit_price=0),
        ]
    )
    order = create_sale_order(db, 1, data)
    assert order.total_price == 5000.0, f"FAIL total_price: {order.total_price}"
    item_sum = sum(item.total_price for item in order.items)
    assert abs(item_sum - 5000.0) < 0.02, f"FAIL item_sum: {item_sum}"
    print(f"PASS: total_price=5000, 单价0→自动分配, 各行合计={item_sum}")
    for item in order.items:
        print(f"  product_id={item.product_id}, qty={item.quantity}, unit_price={item.unit_price:.4f}, total={item.total_price:.2f}")
    delete_sale_order(db, 1, order.id)
except Exception as e:
    print(f"FAIL: {e}")

# 测试3: 传 total_price，部分行有单价 → 差额分配到单价为0的行
try:
    data = SaleOrderCreate(
        customer_id=7, project_id=1,
        total_price=5000,
        items=[
            SaleItemCreate(product_id=9, quantity=12, unit_price=200),
            SaleItemCreate(product_id=29, quantity=1, unit_price=0),
            SaleItemCreate(product_id=30, quantity=1, unit_price=0),
        ]
    )
    order = create_sale_order(db, 1, data)
    assert order.total_price == 5000.0, f"FAIL total_price: {order.total_price}"
    item_sum = sum(item.total_price for item in order.items)
    assert abs(item_sum - 5000.0) < 0.02, f"FAIL item_sum: {item_sum}"
    print(f"PASS: total_price=5000, 部分有单价→差额分配, 各行合计={item_sum}")
    for item in order.items:
        print(f"  product_id={item.product_id}, qty={item.quantity}, unit_price={item.unit_price:.4f}, total={item.total_price:.2f}")
    delete_sale_order(db, 1, order.id)
except Exception as e:
    print(f"FAIL: {e}")

# 测试4: 传 total_price，所有行都有单价 → 按比例打折
try:
    data = SaleOrderCreate(
        customer_id=7, project_id=1,
        total_price=360,  # 400 * 0.9 = 打9折
        items=[
            SaleItemCreate(product_id=9, quantity=2, unit_price=100),
            SaleItemCreate(product_id=29, quantity=1, unit_price=200),
        ]
    )
    order = create_sale_order(db, 1, data)
    assert order.total_price == 360.0, f"FAIL total_price: {order.total_price}"
    item_sum = sum(item.total_price for item in order.items)
    assert abs(item_sum - 360.0) < 0.02, f"FAIL item_sum: {item_sum}"
    print(f"PASS: total_price=360, 全有单价→按比例打折, 各行合计={item_sum}")
    for item in order.items:
        print(f"  product_id={item.product_id}, qty={item.quantity}, unit_price={item.unit_price:.4f}, total={item.total_price:.2f}")
    delete_sale_order(db, 1, order.id)
except Exception as e:
    print(f"FAIL: {e}")

db.close()
print("Done")