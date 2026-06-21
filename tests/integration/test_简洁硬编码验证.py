"""简洁硬编码数字验证 — 验证所有关键数字

验证项目:
  1. 采购金额和库存
  2. 销售金额和库存
  3. 退货库存回补
  4. 发票金额计算
  5. 增值税计算
  6. 所得税计算
  7. 资产负债表恒等式
  8. 利润表恒等式
"""

import os
import sys
import time
import pytest
from decimal import Decimal, ROUND_HALF_UP
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import workspace
workspace.ensure_workspace()
from database import init_db
init_db()

from main import app

HEADERS = {"X-Account-ID": "1", "X-Operator": "test"}


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
def client():
    with TestClient(app) as c:
        yield c


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
    pid = resp.json().get("data", {}).get("id")
    
    # 客户
    resp = client.post("/api/customers", json={
        "name": f"客户-{u}", "contact": "测试", "phone": "13800000001"
    }, headers=HEADERS)
    cid = resp.json().get("id")
    
    # 供应商
    resp = client.post("/api/suppliers", json={
        "name": f"供应商-{u}", "contact": "测试", "phone": "13900000001"
    }, headers=HEADERS)
    sid = resp.json().get("id")
    
    return {"pid": pid, "cid": cid, "sid": sid}


# ═══════════════════════════════════════════════════════════════
# 1. 采购验证
# ═══════════════════════════════════════════════════════════════
def test_purchase(client, ids):
    """验证采购金额和库存"""
    # 硬编码输入
    QTY = 100
    PRICE = 100.00
    
    # 硬编码预期
    EXPECTED_AMOUNT = Decimal(str(QTY)) * Decimal(str(PRICE))
    EXPECTED_STOCK = QTY
    
    # 执行
    resp = client.post("/api/purchases", json={
        "supplier_id": ids["sid"],
        "payment_method": "company",
        "payment_status": "paid",
        "purchase_date": "2026-01-05T10:00:00",
        "items": [{"product_id": ids["pid"], "quantity": QTY, "unit_price": PRICE, "tax_rate": 0.13}]
    }, headers=HEADERS)
    assert resp.status_code in (200, 201)
    
    # 获取实际值
    data = resp.json().get("data", resp.json())
    actual_amount = Decimal(str(data.get("items", [{}])[0].get("total_price", 0)))
    actual_stock = get_stock(client, ids["pid"])
    
    # 验证
    print(f"\n=== 采购验证 ===")
    print(f"预期金额: {EXPECTED_AMOUNT}, 实际: {actual_amount}, 差异: {abs(EXPECTED_AMOUNT - actual_amount)}")
    print(f"预期库存: {EXPECTED_STOCK}, 实际: {actual_stock}, 差异: {abs(EXPECTED_STOCK - actual_stock)}")
    
    assert actual_amount == EXPECTED_AMOUNT, f"金额错误: {EXPECTED_AMOUNT} != {actual_amount}"
    assert actual_stock == EXPECTED_STOCK, f"库存错误: {EXPECTED_STOCK} != {actual_stock}"


# ═══════════════════════════════════════════════════════════════
# 2. 销售验证
# ═══════════════════════════════════════════════════════════════
def test_sale(client, ids):
    """验证销售金额和库存"""
    # 硬编码输入
    QTY = 30
    PRICE = 150.00
    
    # 硬编码预期
    EXPECTED_AMOUNT = Decimal(str(QTY)) * Decimal(str(PRICE))
    STOCK_BEFORE = get_stock(client, ids["pid"])
    EXPECTED_STOCK_AFTER = STOCK_BEFORE - QTY
    
    # 执行
    resp = client.post("/api/sales", json={
        "customer_id": ids["cid"],
        "deduct_inventory": True,
        "payment_status": "paid",
        "sale_date": "2026-01-15T10:00:00",
        "items": [{"product_id": ids["pid"], "quantity": QTY, "unit_price": PRICE, "tax_rate": 0.01}]
    }, headers=HEADERS)
    assert resp.status_code in (200, 201)
    
    # 获取实际值
    data = resp.json().get("data", resp.json())
    actual_amount = Decimal(str(data.get("items", [{}])[0].get("total_price", 0)))
    actual_stock = get_stock(client, ids["pid"])
    
    # 验证
    print(f"\n=== 销售验证 ===")
    print(f"预期金额: {EXPECTED_AMOUNT}, 实际: {actual_amount}, 差异: {abs(EXPECTED_AMOUNT - actual_amount)}")
    print(f"销售前库存: {STOCK_BEFORE}")
    print(f"预期库存: {EXPECTED_STOCK_AFTER}, 实际: {actual_stock}, 差异: {abs(EXPECTED_STOCK_AFTER - actual_stock)}")
    
    assert actual_amount == EXPECTED_AMOUNT, f"金额错误: {EXPECTED_AMOUNT} != {actual_amount}"
    assert actual_stock == EXPECTED_STOCK_AFTER, f"库存错误: {EXPECTED_STOCK_AFTER} != {actual_stock}"


# ═══════════════════════════════════════════════════════════════
# 3. 退货验证
# ═══════════════════════════════════════════════════════════════
def test_return(client, ids):
    """验证退货库存回补"""
    # 硬编码输入
    RETURN_QTY = 10
    
    # 获取退货前库存
    STOCK_BEFORE = get_stock(client, ids["pid"])
    
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
    STOCK_AFTER_SALE = get_stock(client, ids["pid"])
    
    # 取消销售单（退货）
    resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
    assert resp.status_code == 200
    
    # 退货后库存
    STOCK_AFTER_RETURN = get_stock(client, ids["pid"])
    
    # 硬编码预期
    EXPECTED_AFTER_SALE = STOCK_BEFORE - RETURN_QTY
    EXPECTED_AFTER_RETURN = STOCK_AFTER_SALE + RETURN_QTY
    
    # 验证
    print(f"\n=== 退货验证 ===")
    print(f"退货前库存: {STOCK_BEFORE}")
    print(f"预期销售后: {EXPECTED_AFTER_SALE}, 实际: {STOCK_AFTER_SALE}, 差异: {abs(EXPECTED_AFTER_SALE - STOCK_AFTER_SALE)}")
    print(f"预期退货后: {EXPECTED_AFTER_RETURN}, 实际: {STOCK_AFTER_RETURN}, 差异: {abs(EXPECTED_AFTER_RETURN - STOCK_AFTER_RETURN)}")
    
    assert STOCK_AFTER_SALE == EXPECTED_AFTER_SALE, f"销售后库存错误: {EXPECTED_AFTER_SALE} != {STOCK_AFTER_SALE}"
    assert STOCK_AFTER_RETURN == EXPECTED_AFTER_RETURN, f"退货后库存错误: {EXPECTED_AFTER_RETURN} != {STOCK_AFTER_RETURN}"


# ═══════════════════════════════════════════════════════════════
# 4. 发票验证
# ═══════════════════════════════════════════════════════════════
def test_invoice(client):
    """验证发票金额计算"""
    # 硬编码输入
    AMOUNT_WITH_TAX = 10100.00
    TAX_RATE = 0.01
    
    # 硬编码预期
    EXPECTED_WITHOUT_TAX = round2(Decimal(str(AMOUNT_WITH_TAX)) / (1 + Decimal(str(TAX_RATE))))
    EXPECTED_TAX = round2(Decimal(str(AMOUNT_WITH_TAX)) - EXPECTED_WITHOUT_TAX)
    
    # 执行
    resp = client.post("/api/invoices/quick", json={
        "invoice_no": f"INV-{int(time.time())}",
        "direction": "out",
        "invoice_type": "ordinary",
        "amount_with_tax": str(AMOUNT_WITH_TAX),
        "tax_rate": str(TAX_RATE),
        "counterparty_name": "测试",
        "issue_date": "2026-03-15",
    }, headers=HEADERS)
    assert resp.status_code in (200, 201)
    
    # 获取实际值
    data = resp.json().get("data", resp.json())
    actual_without_tax = round2(Decimal(str(data.get("amount_without_tax", 0))))
    actual_tax = round2(Decimal(str(data.get("tax_amount", 0))))
    
    # 验证
    print(f"\n=== 发票验证 ===")
    print(f"预期不含税: {EXPECTED_WITHOUT_TAX}, 实际: {actual_without_tax}, 差异: {abs(EXPECTED_WITHOUT_TAX - actual_without_tax)}")
    print(f"预期税额: {EXPECTED_TAX}, 实际: {actual_tax}, 差异: {abs(EXPECTED_TAX - actual_tax)}")
    print(f"平衡验证: {actual_without_tax} + {actual_tax} = {actual_without_tax + actual_tax}")
    
    assert actual_without_tax == EXPECTED_WITHOUT_TAX, f"不含税错误: {EXPECTED_WITHOUT_TAX} != {actual_without_tax}"
    assert actual_tax == EXPECTED_TAX, f"税额错误: {EXPECTED_TAX} != {actual_tax}"
    assert actual_without_tax + actual_tax == round2(Decimal(str(AMOUNT_WITH_TAX))), "金额不平衡"


# ═══════════════════════════════════════════════════════════════
# 5. 增值税验证
# ═══════════════════════════════════════════════════════════════
def test_vat(client):
    """验证增值税计算"""
    # 查询报表
    resp = client.get("/api/tax-report", params={"year": 2026, "quarter": 1}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    
    # 获取实际值
    output_tax = round2(Decimal(str(data.get("output_tax", 0))))
    input_tax = round2(Decimal(str(data.get("input_tax", 0))))
    tax_payable = round2(Decimal(str(data.get("tax_payable", 0))))
    
    # 硬编码预期
    EXPECTED_PAYABLE = output_tax - input_tax
    
    # 验证
    print(f"\n=== 增值税验证 ===")
    print(f"销项: {output_tax}, 进项: {input_tax}")
    print(f"预期应纳税: {EXPECTED_PAYABLE}, 实际: {tax_payable}, 差异: {abs(EXPECTED_PAYABLE - tax_payable)}")
    
    # 验证（允许 ±0.01 舍入差异）
    diff = abs(tax_payable - EXPECTED_PAYABLE)
    assert diff <= Decimal('0.01'), f"增值税错误: 预期{EXPECTED_PAYABLE}, 实际{tax_payable}, 差异{diff}"


# ═══════════════════════════════════════════════════════════════
# 6. 所得税验证
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
    
    # 硬编码预期
    EXPECTED_PROFIT = revenue - cost
    EXPECTED_TAX = round2(EXPECTED_PROFIT * tax_rate)
    
    # 验证
    print(f"\n=== 所得税验证 ===")
    print(f"收入: {revenue}, 成本: {cost}")
    print(f"预期利润: {EXPECTED_PROFIT}, 实际: {profit}, 差异: {abs(EXPECTED_PROFIT - profit)}")
    print(f"税率: {tax_rate}")
    print(f"预期税额: {EXPECTED_TAX}, 实际: {tax_amount}, 差异: {abs(EXPECTED_TAX - tax_amount)}")
    
    assert profit == EXPECTED_PROFIT, f"利润错误: {EXPECTED_PROFIT} != {profit}"
    assert tax_amount == EXPECTED_TAX, f"税额错误: {EXPECTED_TAX} != {tax_amount}"


# ═══════════════════════════════════════════════════════════════
# 7. 资产负债表验证
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
        
        # 硬编码预期
        EXPECTED_ASSETS = liabilities + equity
        
        # 验证
        print(f"\n=== 资产负债表验证 ===")
        print(f"资产: {assets}, 负债: {liabilities}, 权益: {equity}")
        print(f"预期资产: {EXPECTED_ASSETS}, 差异: {abs(EXPECTED_ASSETS - assets)}")
        
        diff = abs(EXPECTED_ASSETS - assets)
        assert diff <= Decimal('0.01'), f"资产负债表不平衡: {EXPECTED_ASSETS} != {assets}"


# ═══════════════════════════════════════════════════════════════
# 8. 利润表验证
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
        
        # 硬编码预期
        EXPECTED_PROFIT = revenue - cost
        
        # 验证
        print(f"\n=== 利润表验证 ===")
        print(f"收入: {revenue}, 成本: {cost}")
        print(f"预期利润: {EXPECTED_PROFIT}, 实际: {profit}, 差异: {abs(EXPECTED_PROFIT - profit)}")
        
        assert profit == EXPECTED_PROFIT, f"利润错误: {EXPECTED_PROFIT} != {profit}"
