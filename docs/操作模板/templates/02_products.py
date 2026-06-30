"""模板 02：商品管理

商品分两类：
- 实物商品（track_inventory=True，默认）：采购入库/销售出库，受库存约束
- 服务类商品（track_inventory=False）：维修服务/咨询费/技术服务/租赁费/运费等
  无实物商品，销售/采购不触发库存出/入库

⚠️ 维修服务/咨询服务/技术服务/租赁费/运费等"无实物商品"必须设 track_inventory=False。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, put, extract_id


def create_product(name, sku, unit, purchase_price=None, sale_price=None,
                   category=None, track_inventory=True, initial_stock=0):
    """创建商品。

    参数：
        name: 商品名称
        sku: SKU 唯一编码
        unit: 单位（个/台/件/次/小时）
        purchase_price: 参考采购价（可选，不影响实际成本）
        sale_price: 参考销售价（可选，不影响实际开票）
        category: 分类（可选）
        track_inventory: 是否追踪库存（默认 True）。
            ⚠️ 维修服务/咨询服务/技术服务/租赁费/运费等"无实物商品"必须设 False。
            False 时销售/采购不会触发库存出/入库，也不会因"库存不足"报错。
        initial_stock: 初始库存（实物商品可设，服务类商品忽略）
    """
    body = {
        "name": name, "sku": sku, "unit": unit,
        "track_inventory": track_inventory, "initial_stock": initial_stock,
    }
    if purchase_price is not None: body["purchase_price"] = purchase_price
    if sale_price is not None: body["sale_price"] = sale_price
    if category: body["category"] = category
    return post("/api/products", body)


def create_service_product(name, sku, unit="次", sale_price=None, category="服务"):
    """创建服务类商品（封装 create_product + track_inventory=False）。

    适用：维修服务、咨询服务、技术服务、设计费、租赁费等无实物商品。
    """
    return create_product(
        name=name, sku=sku, unit=unit,
        sale_price=sale_price, category=category,
        track_inventory=False,
    )


def list_products(search=None, sku=None, category=None):
    """查询商品列表。

    参数：
        search: 按名称模糊搜索
        sku: 按 SKU 精确查询
        category: 按分类精确筛选
    """
    q = []
    if search: q.append(f"search={search}")
    if sku: q.append(f"sku={sku}")
    if category: q.append(f"category={category}")
    qs = ("?" + "&".join(q)) if q else ""
    return get(f"/api/products{qs}")


def get_product(product_id):
    """查询单个商品。"""
    return get(f"/api/products/{product_id}")


def update_product(product_id, **fields):
    """修改商品。fields 支持同 create_product 的参数。"""
    return put(f"/api/products/{product_id}", fields)


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("1. 创建实物商品")
    p = create_product(name="商品A", sku="SPA001", unit="个",
                        purchase_price=1000, sale_price=1500)
    print(f"   {p}")
    pid = extract_id(p)

    print("\n2. 创建服务类商品（track_inventory=False）")
    svc = create_service_product(name="维修服务", sku="SVC001", sale_price=500)
    print(f"   {svc}")

    print("\n3. 按 category 查询")
    r = list_products(category="服务")
    print(f"   {r}")
