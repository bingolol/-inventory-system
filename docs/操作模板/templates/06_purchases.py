"""模板 06：采购与进项发票

业务流程：进项发票（自动算税额）→ 自动生成/关联采购单 → 认证（一般纳税人专票）
所有发票录入走 POST /api/invoices/quick。
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import post, get, extract_id


# === 进项发票（快捷录入，自动算税额） ===

def create_input_invoice_quick(invoice_no, invoice_type, tax_rate,
                                amount_with_tax, counterparty_name,
                                seller_name, buyer_name, issue_date,
                                items, purchase_order_action,
                                related_order_id=None, notes=None):
    """创建进项发票（走 /api/invoices/quick）。

    系统自动：
    - 按 amount_with_tax / (1+tax_rate) 算不含税金额 + 税额
    - 根据 purchase_order_action 处理采购单：
        * "auto_create"：用 items 自动建采购单 + 入库
        * "link_existing"：关联 related_order_id 指定的采购单（必填 related_order_id）

    参数：
        invoice_no: 发票号
        invoice_type: "special"（专票）或 "ordinary"（普票）
        tax_rate: 税率（如 0.13）
        amount_with_tax: 价税合计（不含税/税额系统自动算）
        counterparty_name: 交易对方名称（如供应商名）
        seller_name: 销方名称（一般填供应商名）
        buyer_name: 购方名称（一般填本公司名）
        issue_date: 开票日期 "YYYY-MM-DD"
        items: 商品明细 [{"product_id": 1, "quantity": 10, "unit_price": 1000.00, "tax_rate": 0.13}, ...]
               注意：unit_price 是不含税单价，行 tax_rate 必填
        purchase_order_action: "auto_create" 或 "link_existing"
        related_order_id: 关联采购单 ID（link_existing 时必填）
        notes: 备注
    """
    body = {
        "invoice_no": invoice_no,
        "direction": "in",
        "invoice_type": invoice_type,
        "tax_rate": tax_rate,
        "amount_with_tax": amount_with_tax,
        "counterparty_name": counterparty_name,
        "seller_name": seller_name,
        "buyer_name": buyer_name,
        "issue_date": issue_date,
        "items": items,
        "purchase_order_action": purchase_order_action,
    }
    if related_order_id: body["related_order_id"] = related_order_id
    if notes: body["notes"] = notes
    return post("/api/invoices/quick", body)


# === 采购单（独立创建，用于 link_existing 模式） ===

def create_purchase_order(supplier_id, items, purchase_date, notes=None):
    """单独创建采购单（不绑定发票，后续发票用 link_existing 关联）。

    参数：
        supplier_id: 供应商 ID
        items: [{"product_id": 1, "quantity": 10, "unit_price": 1000.00}, ...]
        purchase_date: "YYYY-MM-DD"
        notes: 备注
    """
    body = {
        "supplier_id": supplier_id,
        "items": items,
        "purchase_date": purchase_date,
    }
    if notes: body["notes"] = notes
    return post("/api/purchases", body)


def get_purchase_order(po_id):
    """查询采购单详情。"""
    return get(f"/api/purchases/{po_id}")


def list_purchase_orders(start_date=None, end_date=None):
    """查询采购单列表。"""
    q = []
    if start_date: q.append(f"start_date={start_date}")
    if end_date: q.append(f"end_date={end_date}")
    qs = ("?" + "&".join(q)) if q else ""
    return get(f"/api/purchases{qs}")


# === 发票查询与认证 ===

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


def certify_invoice(invoice_id):
    """认证进项专票（一般纳税人专用，普票无需认证）。

    返回成功后该进项税额可抵扣。
    """
    return post(f"/api/invoices/{invoice_id}/certify", {})


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    SUP_ID = 1
    PROD_ID = 2

    print("=== 方式 A：发票 + auto_create 自动建采购单（推荐） ===")
    inv = create_input_invoice_quick(
        invoice_no="IN20260615001",
        invoice_type="special",
        tax_rate=0.13,
        amount_with_tax=11300.00,
        counterparty_name="供应商甲",
        seller_name="供应商甲",
        buyer_name="本公司",
        issue_date="2026-06-15",
        items=[
            {"product_id": PROD_ID, "quantity": 10, "unit_price": 1000.00, "tax_rate": 0.13},
        ],
        purchase_order_action="auto_create",
        notes="采购商品A 10个",
    )
    print(f"   {inv}")
    inv_id = extract_id(inv)

    print("\n=== 方式 B：先建采购单，发票 link_existing 关联 ===")
    po = create_purchase_order(
        supplier_id=SUP_ID,
        items=[{"product_id": PROD_ID, "quantity": 5, "unit_price": 1000.00}],
        purchase_date="2026-06-16",
    )
    po_id = extract_id(po)
    inv2 = create_input_invoice_quick(
        invoice_no="IN20260616002",
        invoice_type="ordinary",
        tax_rate=0.13,
        amount_with_tax=5650.00,
        counterparty_name="供应商甲",
        seller_name="供应商甲",
        buyer_name="本公司",
        issue_date="2026-06-16",
        items=[
            {"product_id": PROD_ID, "quantity": 5, "unit_price": 1000.00, "tax_rate": 0.13},
        ],
        purchase_order_action="link_existing",
        related_order_id=po_id,
    )
    print(f"   {inv2}")

    print("\n3. 认证专票（方式 A 的专票）")
    cer = certify_invoice(inv_id)
    print(f"   {cer}")
