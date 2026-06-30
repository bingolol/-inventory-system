"""模板 07：销售与销项发票

业务流程：销项发票（自动算税额）→ 自动生成/关联销售单 → 确认收入 + 结转成本
所有发票录入走 POST /api/invoices/quick。

⚠️ 销项发票 sale_order_action 必填：
  - "auto_create"：用 items 自动建销售单 + 出库 + 结转成本
  - "link_existing"：关联已有销售单（必填 related_order_id）

⚠️ 维修服务/咨询费等"无商品"场景：
  系统要求 items 至少 1 行（product_id 必填）。
  处理方法：在 02_products.py 中先建一个通用"服务类商品"（如"维修服务"、"咨询服务"），
  拿到 product_id 后，在销项发票的 items 中使用它。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


# === 销项发票（快捷录入，自动算税额） ===

def create_output_invoice_quick(invoice_no, invoice_type, tax_rate,
                                amount_with_tax, counterparty_name,
                                seller_name, buyer_name, issue_date,
                                items, sale_order_action,
                                related_order_id=None, notes=None):
    """创建销项发票（走 /api/invoices/quick）。

    系统自动：
    - 按 amount_with_tax / (1+tax_rate) 算不含税金额 + 税额
    - 根据 sale_order_action 处理销售单：
        * "auto_create"：用 items 自动建销售单 + 出库 + 结转成本
        * "link_existing"：关联 related_order_id 指定的销售单（必填 related_order_id）

    参数：
        invoice_no: 发票号
        invoice_type: "special"（专票）或 "ordinary"（普票）
        tax_rate: 税率（如 0.13）
        amount_with_tax: 价税合计（不含税/税额系统自动算）
        counterparty_name: 交易对方名称（如客户名）
        seller_name: 销方名称（一般填本公司名）
        buyer_name: 购方名称（一般填客户名）
        issue_date: 开票日期 "YYYY-MM-DD"
        items: 商品明细 [{"product_id": 1, "quantity": 1, "unit_price": 5000.00, "tax_rate": 0.13}, ...]
               注意：unit_price 是不含税单价，行 tax_rate 必填
        sale_order_action: "auto_create" 或 "link_existing"
        related_order_id: 关联销售单 ID（link_existing 时必填）
        notes: 备注
    """
    body = {
        "invoice_no": invoice_no,
        "direction": "out",
        "invoice_type": invoice_type,
        "tax_rate": tax_rate,
        "amount_with_tax": amount_with_tax,
        "counterparty_name": counterparty_name,
        "seller_name": seller_name,
        "buyer_name": buyer_name,
        "issue_date": issue_date,
        "items": items,
        "sale_order_action": sale_order_action,
    }
    if related_order_id: body["related_order_id"] = related_order_id
    if notes: body["notes"] = notes
    return post("/api/invoices/quick", body)


# === 销售单（独立创建，用于 link_existing 模式） ===

def create_sale_order(customer_id, items, sale_date, notes=None):
    """单独创建销售单（不绑定发票，后续发票用 link_existing 关联）。

    参数：
        customer_id: 客户 ID
        items: [{"product_id": 1, "quantity": 5, "unit_price": 1500.00}, ...]
        sale_date: "YYYY-MM-DD"
        notes: 备注
    """
    body = {
        "customer_id": customer_id,
        "items": items,
        "sale_date": sale_date,
    }
    if notes: body["notes"] = notes
    return post("/api/sales", body)


def get_sale_order(so_id):
    """查询销售单详情（含出库状态、关联发票）。"""
    return get(f"/api/sales/{so_id}")


def list_sale_orders(start_date=None, end_date=None):
    """查询销售单列表。"""
    q = []
    if start_date: q.append(f"start_date={start_date}")
    if end_date: q.append(f"end_date={end_date}")
    qs = ("?" + "&".join(q)) if q else ""
    return get(f"/api/sales{qs}")


# === 发票查询 ===

def list_invoices(direction=None, year=None, quarter=None,
                   invoice_type=None, certification_status=None):
    """查询发票列表。

    参数：
        direction: "in"（进项）/ "out"（销项），None 则全部
        year: 年份（如 2026）
        quarter: 季度（1-4，需配合 year）
        invoice_type: "special"（专票）/ "ordinary"（普票）
        certification_status: "n_a"（未认证/普票）/ "pending"（待认证）/ "certified"（已认证）
    """
    q = []
    if direction: q.append(f"direction={direction}")
    if year: q.append(f"year={year}")
    if quarter: q.append(f"quarter={quarter}")
    if invoice_type: q.append(f"invoice_type={invoice_type}")
    if certification_status: q.append(f"certification_status={certification_status}")
    qs = ("?" + "&".join(q)) if q else ""
    return get(f"/api/invoices{qs}")


def get_invoice(invoice_id):
    """查询单张发票。"""
    return get(f"/api/invoices/{invoice_id}")


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    CUS_ID = 2
    PROD_ID = 2

    print("=== 方式 A：发票 + auto_create 自动建销售单（推荐） ===")
    inv = create_output_invoice_quick(
        invoice_no="OUT20260620001",
        invoice_type="ordinary",
        tax_rate=0.13,
        amount_with_tax=7345.00,
        counterparty_name="客户乙",
        seller_name="本公司",
        buyer_name="客户乙",
        issue_date="2026-06-20",
        items=[
            {"product_id": PROD_ID, "quantity": 5, "unit_price": 1300.00, "tax_rate": 0.13},
        ],
        sale_order_action="auto_create",
        notes="向客户乙销售商品A 5个",
    )
    print(f"   {inv}")
    inv_id = extract_id(inv)

    print("\n=== 方式 B：先建销售单，发票 link_existing 关联 ===")
    so = create_sale_order(
        customer_id=CUS_ID,
        items=[{"product_id": PROD_ID, "quantity": 2, "unit_price": 1300.00}],
        sale_date="2026-06-21",
    )
    so_id = extract_id(so)
    inv2 = create_output_invoice_quick(
        invoice_no="OUT20260621002",
        invoice_type="special",
        tax_rate=0.13,
        amount_with_tax=2938.00,
        counterparty_name="客户乙",
        seller_name="本公司",
        buyer_name="客户乙",
        issue_date="2026-06-21",
        items=[
            {"product_id": PROD_ID, "quantity": 2, "unit_price": 1300.00, "tax_rate": 0.13},
        ],
        sale_order_action="link_existing",
        related_order_id=so_id,
    )
    print(f"   {inv2}")

    print("\n=== 维修服务场景（无商品，用通用服务商品） ===")
    print("   第 1 步：先在 02_products 中创建商品 '维修服务'（如 sku=SVC001, unit=次）")
    print("   第 2 步：拿到 product_id 后用本函数走销项发票，sale_order_action=auto_create")
