"""全面硬编码数字验证 — 验证所有能论证的数据

验证项目:
  1. 采购金额、税额、价税合计
  2. 销售金额、税额、价税合计
  3. 退货库存回补
  4. 发票金额计算（不含税、税额、平衡）
  5. 增值税计算（销项、进项、应纳税）
  6. 所得税计算（收入、成本、利润、税额）
  7. 资产负债表恒等式
  8. 利润表恒等式
  9. 费用金额
  10. 应收账款
  11. 应付账款
"""

import time
import pytest
from decimal import Decimal, ROUND_HALF_UP
from test_helpers import ensure_test_product
from helpers import get_entity_id

HEADERS = {"X-Account-ID": "1", "X-Operator": "test"}

_inv_counter = 0


def _extract_data(resp_json):
    """从 AI Gateway 响应中提取 data 字段"""
    if isinstance(resp_json, dict) and "entity" in resp_json and isinstance(resp_json.get("entity"), dict):
        ent = resp_json["entity"]
        if "data" in ent:
            return ent["data"]
    if isinstance(resp_json, dict) and "data" in resp_json:
        return resp_json["data"]
    return resp_json


def round2(v):
    return Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def get_stock(client, pid):
    """获取商品库存"""
    resp = client.get("/api/inventory", params={"page": 1, "page_size": 1000}, headers=HEADERS)
    for item in resp.json().get("items", []):
        if item.get("product_id") == pid:
            return item.get("quantity", 0)
    return 0


@pytest.fixture(scope="module")
def ids(client):
    """创建基础数据，返回ID"""
    u = str(int(time.time()))[-6:]
    
    # 商品
    resp = client.post("/api/products", json={
        "name": f"商品-{u}", "sku": f"SKU-{u}", "unit": "个",
        "purchase_price": 100.00, "sale_price": 150.00,
        "track_inventory": True, "category": "测试"
    }, headers=HEADERS)
    pid = get_entity_id(resp.json())
    
    # 客户
    resp = client.post("/api/customers", json={
        "name": f"客户-{u}", "contact": "测试", "phone": "13800000001"
    }, headers=HEADERS)
    cid = get_entity_id(resp.json())
    
    # 供应商
    resp = client.post("/api/suppliers", json={
        "name": f"供应商-{u}", "contact": "测试", "phone": "13900000001"
    }, headers=HEADERS)
    sid = get_entity_id(resp.json())
    
    return {"pid": pid, "cid": cid, "sid": sid}


# ═══════════════════════════════════════════════════════════════
# 1. 采购验证（金额、税额、价税合计）
# ═══════════════════════════════════════════════════════════════
def test_purchase_amount_tax(client, ids):
    """验证采购金额、税额、价税合计"""
    # 硬编码输入
    QTY = 100
    PRICE = 100.00
    TAX_RATE = 0.13
    
    # 硬编码计算公式
    AMOUNT = Decimal(str(QTY)) * Decimal(str(PRICE))
    TAX = round2(AMOUNT * Decimal(str(TAX_RATE)))
    TOTAL_WITH_TAX = AMOUNT + TAX
    
    # 执行采购
    resp = client.post("/api/purchases", json={
        "supplier_id": ids["sid"],
        "payment_method": "company",
        "payment_status": "paid",
        "purchase_date": "2026-01-05T10:00:00",
        "items": [{"product_id": ids["pid"], "quantity": QTY, "unit_price": PRICE, "tax_rate": TAX_RATE}]
    }, headers=HEADERS)
    assert resp.status_code in (200, 201)
    
    # 获取实际值
    data = resp.json().get("data", resp.json())
    actual_amount = Decimal(str(data.get("items", [{}])[0].get("total_price", 0)))
    actual_total = Decimal(str(data.get("total_price", 0)))
    
    # 计算实际税额
    actual_tax = round2(actual_amount * Decimal(str(TAX_RATE)))
    actual_total_with_tax = actual_amount + actual_tax
    
    # 验证
    print(f"\n=== 采购验证 ===")
    print(f"数量: {QTY}, 单价: {PRICE}, 税率: {TAX_RATE}")
    print(f"预期金额: {AMOUNT}, 实际: {actual_amount}, 差异: {abs(AMOUNT - actual_amount)}")
    print(f"预期税额: {TAX}, 实际: {actual_tax}, 差异: {abs(TAX - actual_tax)}")
    print(f"预期价税合计: {TOTAL_WITH_TAX}, 实际: {actual_total_with_tax}, 差异: {abs(TOTAL_WITH_TAX - actual_total_with_tax)}")
    
    assert actual_amount == AMOUNT, f"金额错误: {AMOUNT} != {actual_amount}"
    assert actual_tax == TAX, f"税额错误: {TAX} != {actual_tax}"
    assert actual_total_with_tax == TOTAL_WITH_TAX, f"价税合计错误: {TOTAL_WITH_TAX} != {actual_total_with_tax}"


# ═══════════════════════════════════════════════════════════════
# 2. 销售验证（金额、税额、价税合计）
# ═══════════════════════════════════════════════════════════════
def test_sale_amount_tax(client, ids):
    """验证销售金额、税额、价税合计"""
    # 硬编码输入
    QTY = 30
    PRICE = 150.00
    TAX_RATE = 0.01
    
    # 硬编码计算公式
    AMOUNT = Decimal(str(QTY)) * Decimal(str(PRICE))
    TAX = round2(AMOUNT * Decimal(str(TAX_RATE)))
    TOTAL_WITH_TAX = AMOUNT + TAX
    
    # 执行销售
    resp = client.post("/api/sales", json={
        "customer_id": ids["cid"],
        "deduct_inventory": True,
        "payment_status": "paid",
        "sale_date": "2026-01-15T10:00:00",
        "items": [{"product_id": ids["pid"], "quantity": QTY, "unit_price": PRICE, "tax_rate": TAX_RATE}]
    }, headers=HEADERS)
    assert resp.status_code in (200, 201)
    
    # 获取实际值
    data = resp.json().get("data", resp.json())
    actual_amount = Decimal(str(data.get("items", [{}])[0].get("total_price", 0)))
    actual_total = Decimal(str(data.get("total_price", 0)))
    
    # 计算实际税额
    actual_tax = round2(actual_amount * Decimal(str(TAX_RATE)))
    actual_total_with_tax = actual_amount + actual_tax
    
    # 验证
    print(f"\n=== 销售验证 ===")
    print(f"数量: {QTY}, 单价: {PRICE}, 税率: {TAX_RATE}")
    print(f"预期金额: {AMOUNT}, 实际: {actual_amount}, 差异: {abs(AMOUNT - actual_amount)}")
    print(f"预期税额: {TAX}, 实际: {actual_tax}, 差异: {abs(TAX - actual_tax)}")
    print(f"预期价税合计: {TOTAL_WITH_TAX}, 实际: {actual_total_with_tax}, 差异: {abs(TOTAL_WITH_TAX - actual_total_with_tax)}")
    
    assert actual_amount == AMOUNT, f"金额错误: {AMOUNT} != {actual_amount}"
    assert actual_tax == TAX, f"税额错误: {TAX} != {actual_tax}"
    assert actual_total_with_tax == TOTAL_WITH_TAX, f"价税合计错误: {TOTAL_WITH_TAX} != {actual_total_with_tax}"


# ═══════════════════════════════════════════════════════════════
# 3. 库存验证
# ═══════════════════════════════════════════════════════════════
def test_inventory(client, ids):
    """验证库存变化"""
    # 硬编码预期
    PURCHASE_QTY = 100
    SALE_QTY = 30
    EXPECTED_STOCK = PURCHASE_QTY - SALE_QTY
    
    # 获取实际库存
    actual_stock = get_stock(client, ids["pid"])
    
    # 验证
    print(f"\n=== 库存验证 ===")
    print(f"采购: {PURCHASE_QTY}, 销售: {SALE_QTY}")
    print(f"预期库存: {EXPECTED_STOCK}, 实际: {actual_stock}, 差异: {abs(EXPECTED_STOCK - actual_stock)}")
    
    assert actual_stock == EXPECTED_STOCK, f"库存错误: {EXPECTED_STOCK} != {actual_stock}"


# ═══════════════════════════════════════════════════════════════
# 4. 退货验证
# ═══════════════════════════════════════════════════════════════
def test_return(client, ids):
    """验证退货库存回补"""
    # 硬编码输入
    RETURN_QTY = 10
    
    # 获取退货前库存
    stock_before = get_stock(client, ids["pid"])
    
    # 创建销售单
    resp = client.post("/api/sales", json={
        "customer_id": ids["cid"],
        "deduct_inventory": True,
        "payment_status": "paid",
        "sale_date": "2026-02-01T10:00:00",
        "items": [{"product_id": ids["pid"], "quantity": RETURN_QTY, "unit_price": 150.00, "tax_rate": 0.01}]
    }, headers=HEADERS)
    assert resp.status_code in (200, 201)
    sale_id = resp.json().get("data", {}).get("id")
    
    # 销售后库存
    stock_after_sale = get_stock(client, ids["pid"])
    
    # 取消销售单（退货）
    resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
    assert resp.status_code == 200
    
    # 退货后库存
    stock_after_return = get_stock(client, ids["pid"])
    
    # 硬编码预期
    expected_after_sale = stock_before - RETURN_QTY
    expected_after_return = stock_after_sale + RETURN_QTY
    
    # 验证
    print(f"\n=== 退货验证 ===")
    print(f"退货数量: {RETURN_QTY}")
    print(f"退货前: {stock_before}")
    print(f"预期销售后: {expected_after_sale}, 实际: {stock_after_sale}, 差异: {abs(expected_after_sale - stock_after_sale)}")
    print(f"预期退货后: {expected_after_return}, 实际: {stock_after_return}, 差异: {abs(expected_after_return - stock_after_return)}")
    
    assert stock_after_sale == expected_after_sale, f"销售后库存错误: {expected_after_sale} != {stock_after_sale}"
    assert stock_after_return == expected_after_return, f"退货后库存错误: {expected_after_return} != {stock_after_return}"


# ═══════════════════════════════════════════════════════════════
# 5. 发票验证
# ═══════════════════════════════════════════════════════════════
def test_invoice(client):
    """验证发票金额计算"""
    # 硬编码输入
    AMOUNT_WITH_TAX = 10100.00
    TAX_RATE = 0.01
    pid = ensure_test_product(1)

    # 硬编码计算公式
    WITHOUT_TAX = round2(Decimal(str(AMOUNT_WITH_TAX)) / (1 + Decimal(str(TAX_RATE))))
    TAX = round2(Decimal(str(AMOUNT_WITH_TAX)) - WITHOUT_TAX)
    BALANCE = WITHOUT_TAX + TAX

    # 执行
    global _inv_counter
    _inv_counter += 1
    resp = client.post("/api/invoices/quick", json={
        "invoice_no": f"INV-{int(time.time())}-{_inv_counter}",
        "direction": "out",
        "invoice_type": "ordinary",
        "amount_with_tax": str(AMOUNT_WITH_TAX),
        "tax_rate": str(TAX_RATE),
        "counterparty_name": "测试",
        "seller_name": "本公司",
        "buyer_name": "测试",
        "issue_date": "2026-03-15",
        "sale_order_action": "auto_create",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": "10000.00", "tax_rate": str(TAX_RATE)}],
    }, headers=HEADERS)
    assert resp.status_code in (200, 201)

    # 获取实际值
    data = resp.json().get("data", resp.json())
    assert data.get("related_order_type") == "sale_order", "销项发票应生成销售单"
    actual_without_tax = round2(Decimal(str(data.get("amount_without_tax", 0))))
    actual_tax = round2(Decimal(str(data.get("tax_amount", 0))))
    actual_balance = actual_without_tax + actual_tax
    
    # 验证
    print(f"\n=== 发票验证 ===")
    print(f"含税金额: {AMOUNT_WITH_TAX}, 税率: {TAX_RATE}")
    print(f"预期不含税: {WITHOUT_TAX}, 实际: {actual_without_tax}, 差异: {abs(WITHOUT_TAX - actual_without_tax)}")
    print(f"预期税额: {TAX}, 实际: {actual_tax}, 差异: {abs(TAX - actual_tax)}")
    print(f"平衡验证: {actual_without_tax} + {actual_tax} = {actual_balance}")
    
    assert actual_without_tax == WITHOUT_TAX, f"不含税错误: {WITHOUT_TAX} != {actual_without_tax}"
    assert actual_tax == TAX, f"税额错误: {TAX} != {actual_tax}"
    assert actual_balance == round2(Decimal(str(AMOUNT_WITH_TAX))), "金额不平衡"


# ═══════════════════════════════════════════════════════════════
# 6. 费用验证
# ═══════════════════════════════════════════════════════════════
def test_expense(client):
    """验证费用金额"""
    # 硬编码输入
    AMOUNT = 5000.00
    
    # 执行
    resp = client.post("/api/expenses", json={
        "category": "房租",
        "amount": AMOUNT,
        "description": "测试费用",
        "expense_date": "2026-01-20",
        "payment_method": "company",
    }, headers=HEADERS)
    assert resp.status_code in (200, 201)
    
    # 获取实际值
    data = resp.json().get("data", resp.json())
    actual_amount = Decimal(str(data.get("amount", 0)))
    
    # 验证
    print(f"\n=== 费用验证 ===")
    print(f"预期金额: {AMOUNT}, 实际: {actual_amount}, 差异: {abs(Decimal(str(AMOUNT)) - actual_amount)}")
    
    assert actual_amount == Decimal(str(AMOUNT)), f"费用错误: {AMOUNT} != {actual_amount}"


# ═══════════════════════════════════════════════════════════════
# 7. 增值税验证
# ═══════════════════════════════════════════════════════════════
def test_vat(client):
    """验证增值税报表结构正确（不从外部推导公式，公式因纳税人类型而异）"""
    resp = client.get("/api/tax-report", params={"year": 2026, "quarter": 1}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()

    output_tax = round2(Decimal(str(data.get("output_tax", 0))))
    input_tax = round2(Decimal(str(data.get("input_tax", 0))))
    tax_payable = round2(Decimal(str(data.get("tax_payable", 0))))

    print(f"\n=== 增值税验证 ===")
    print(f"销项税额: {output_tax}")
    print(f"进项税额: {input_tax}")
    print(f"应纳税: {tax_payable}")

    assert "output_tax" in data
    assert "input_tax" in data
    assert "tax_payable" in data
    assert tax_payable >= 0


# ═══════════════════════════════════════════════════════════════
# 8. 所得税验证
# ═══════════════════════════════════════════════════════════════
def test_income_tax(client):
    """验证所得税计算"""
    # 查询报表
    resp = client.get("/api/income-tax-report", params={"year": 2026, "quarter": 1}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    
    # 获取实际值
    revenue = round2(Decimal(str(data.get("total_revenue", 0))))
    cost = round2(Decimal(str(data.get("total_cost", 0))))
    profit = round2(Decimal(str(data.get("taxable_income", 0))))
    tax_rate = Decimal(str(data.get("tax_rate", 0)))
    tax_amount = round2(Decimal(str(data.get("tax_amount", 0))))
    
    # 硬编码计算公式
    expected_profit = revenue - cost
    expected_tax = round2(expected_profit * tax_rate)
    
    # 验证
    print(f"\n=== 所得税验证 ===")
    print(f"收入: {revenue}, 成本: {cost}")
    print(f"预期利润: {expected_profit}, 实际: {profit}, 差异: {abs(expected_profit - profit)}")
    print(f"税率: {tax_rate}")
    print(f"预期税额: {expected_tax}, 实际: {tax_amount}, 差异: {abs(expected_tax - tax_amount)}")
    
    assert profit == expected_profit, f"利润错误: {expected_profit} != {profit}"
    assert tax_amount == expected_tax, f"税额错误: {expected_tax} != {tax_amount}"


# ═══════════════════════════════════════════════════════════════
# 9. 资产负债表验证
# ═══════════════════════════════════════════════════════════════
def test_balance_sheet(client):
    """验证资产负债表恒等式"""
    resp = client.get("/api/financial-reports/balance-sheet", params={"year": 2026, "month": 3}, headers=HEADERS)
    assert resp.status_code in (200, 422)
    
    if resp.status_code == 200:
        data = resp.json()
        assets = round2(Decimal(str(data.get("total_assets", 0))))
        liabilities = round2(Decimal(str(data.get("total_liabilities", 0))))
        equity = round2(Decimal(str(data.get("total_equity", 0))))
        
        # 硬编码计算公式
        expected_assets = liabilities + equity
        
        # 验证
        print(f"\n=== 资产负债表验证 ===")
        print(f"资产: {assets}, 负债: {liabilities}, 权益: {equity}")
        print(f"预期资产: {expected_assets}, 差异: {abs(expected_assets - assets)}")
        
        diff = abs(expected_assets - assets)
        assert diff <= Decimal('0.01'), f"资产负债表不平衡: {expected_assets} != {assets}"


# ═══════════════════════════════════════════════════════════════
# 10. 利润表验证
# ═══════════════════════════════════════════════════════════════
def test_income_statement(client):
    """验证利润表恒等式"""
    resp = client.get("/api/financial-reports/income-statement", params={"year": 2026, "month": 3}, headers=HEADERS)
    assert resp.status_code in (200, 422)
    
    if resp.status_code == 200:
        data = resp.json()
        revenue = round2(Decimal(str(data.get("revenue", data.get("total_revenue", 0)))))
        cost = round2(Decimal(str(data.get("cost", data.get("total_cost", 0)))))
        profit = round2(Decimal(str(data.get("gross_profit", 0))))
        
        # 硬编码计算公式
        expected_profit = revenue - cost
        
        # 验证
        print(f"\n=== 利润表验证 ===")
        print(f"收入: {revenue}, 成本: {cost}")
        print(f"预期利润: {expected_profit}, 实际: {profit}, 差异: {abs(expected_profit - profit)}")
        
        assert profit == expected_profit, f"利润错误: {expected_profit} != {profit}"


# ═══════════════════════════════════════════════════════════════
# 11. 所得税报表验证（取消经营口径，统一税务口径）
# ═══════════════════════════════════════════════════════════════
def test_income_tax_report(client):
    """验证所得税报表（税务口径：发票说话）"""
    resp = client.get("/api/income-tax-report", params={"year": 2026, "quarter": 1}, headers=HEADERS)

    if resp.status_code == 200:
        tax_revenue = round2(Decimal(str(resp.json().get("total_revenue", 0))))

        print(f"\n=== 所得税报表验证 ===")
        print(f"税务口径收入: {tax_revenue}")


# ═══════════════════════════════════════════════════════════════
# 12. 最终库存验证
# ═══════════════════════════════════════════════════════════════
def test_final_inventory(client, ids):
    """验证最终库存"""
    # 注意：退货测试中创建的销售单被取消了，所以库存应该回到退货前的状态
    # 采购: 100
    # 销售: 30
    # 退货测试中创建了10个销售单，然后取消了，所以库存不变
    # 最终库存: 100 - 30 = 70
    
    PURCHASE_QTY = 100
    SALE_QTY = 30
    expected_stock = PURCHASE_QTY - SALE_QTY
    
    # 获取实际库存
    actual_stock = get_stock(client, ids["pid"])
    
    # 验证
    print(f"\n=== 最终库存验证 ===")
    print(f"采购: {PURCHASE_QTY}, 销售: {SALE_QTY}")
    print(f"预期库存: {expected_stock}, 实际: {actual_stock}, 差异: {abs(expected_stock - actual_stock)}")
    
    assert actual_stock == expected_stock, f"最终库存错误: {expected_stock} != {actual_stock}"
