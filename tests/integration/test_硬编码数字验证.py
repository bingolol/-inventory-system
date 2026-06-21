"""硬编码数字验证测试 — 避免幻觉或异常

方法:
  1. 硬编码所有输入数据
  2. 硬编码计算公式
  3. 硬编码预期结果
  4. 验证系统计算结果是否等于预期值
"""

import os
import sys
import json
import time
import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import workspace
workspace.ensure_workspace()

from database import init_db, SessionLocal
init_db()

from main import app
from models import Account

_db = SessionLocal()
_account = _db.query(Account).first()
ACCOUNT_ID = _account.id if _account else 1
_db.close()

HEADERS = {"X-Account-ID": str(ACCOUNT_ID), "X-Operator": "verify_test"}


def get_entity_id(resp_json):
    if "id" in resp_json:
        return resp_json["id"]
    if "data" in resp_json and "id" in resp_json["data"]:
        return resp_json["data"]["id"]
    return None


def get_inventory_qty(client, product_id):
    resp = client.get("/api/inventory", params={"page": 1, "page_size": 500}, headers=HEADERS)
    assert resp.status_code == 200
    for item in resp.json().get("items", []):
        if item.get("product_id") == product_id:
            return item.get("quantity", 0)
    return 0


def round2(value):
    """四舍五入保留2位小数"""
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def data(client):
    """硬编码测试数据"""
    unique = str(int(time.time()))[-6:]
    d = {}
    
    # 供应商
    resp = client.post("/api/suppliers", json={
        "name": f"供应商A-{unique}", "contact": "张", "phone": "13800000001"
    }, headers=HEADERS)
    d["supplier_id"] = get_entity_id(resp.json())
    
    # 客户
    resp = client.post("/api/customers", json={
        "name": f"客户B-{unique}", "contact": "李", "phone": "13900000001"
    }, headers=HEADERS)
    d["customer_id"] = get_entity_id(resp.json())
    
    # 商品（有库存）
    resp = client.post("/api/products", json={
        "name": f"商品X-{unique}", "sku": f"X-{unique}", "unit": "个",
        "purchase_price": 100.00, "sale_price": 150.00,
        "track_inventory": True, "category": "测试"
    }, headers=HEADERS)
    d["product_id"] = get_entity_id(resp.json())
    
    return d


# ═══════════════════════════════════════════════════════════════
# 硬编码验证: 采购
# ═══════════════════════════════════════════════════════════════
class TestPurchaseVerification:
    """采购硬编码验证"""
    
    def test_purchase_quantity_and_amount(self, client, data):
        """验证采购数量和金额"""
        # ── 硬编码输入 ──
        INPUT_QUANTITY = 50
        INPUT_UNIT_PRICE = 100.00
        INPUT_TAX_RATE = 0.13
        
        # ── 硬编码计算公式 ──
        # 采购金额 = 数量 × 单价
        EXPECTED_AMOUNT = Decimal(str(INPUT_QUANTITY)) * Decimal(str(INPUT_UNIT_PRICE))
        # 采购税额 = 金额 × 税率
        EXPECTED_TAX = EXPECTED_AMOUNT * Decimal(str(INPUT_TAX_RATE))
        # 采购价税合计 = 金额 + 税额
        EXPECTED_TOTAL = EXPECTED_AMOUNT + EXPECTED_TAX
        
        # ── 执行采购 ──
        resp = client.post("/api/purchases", json={
            "supplier_id": data["supplier_id"],
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-01-05T10:00:00",
            "items": [{
                "product_id": data["product_id"],
                "quantity": INPUT_QUANTITY,
                "unit_price": INPUT_UNIT_PRICE,
                "tax_rate": INPUT_TAX_RATE
            }]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        
        # ── 获取系统计算结果 ──
        resp_data = resp.json().get("data", resp.json())
        ACTUAL_AMOUNT = Decimal(str(resp_data.get("items", [{}])[0].get("total_price", 0)))
        ACTUAL_TOTAL = Decimal(str(resp_data.get("total_price", 0)))
        
        # ── 验证库存 ──
        ACTUAL_STOCK = get_inventory_qty(client, data["product_id"])
        EXPECTED_STOCK = INPUT_QUANTITY
        
        # ── 硬编码验证 ──
        print(f"\n=== 采购验证 ===")
        print(f"输入: 数量={INPUT_QUANTITY}, 单价={INPUT_UNIT_PRICE}, 税率={INPUT_TAX_RATE}")
        print(f"预期金额: {EXPECTED_AMOUNT}")
        print(f"实际金额: {ACTUAL_AMOUNT}")
        print(f"差异: {abs(EXPECTED_AMOUNT - ACTUAL_AMOUNT)}")
        print(f"预期库存: {EXPECTED_STOCK}")
        print(f"实际库存: {ACTUAL_STOCK}")
        print(f"差异: {abs(EXPECTED_STOCK - ACTUAL_STOCK)}")
        
        # 验证
        assert ACTUAL_AMOUNT == EXPECTED_AMOUNT, \
            f"采购金额错误: 预期{EXPECTED_AMOUNT}, 实际{ACTUAL_AMOUNT}"
        assert ACTUAL_STOCK == EXPECTED_STOCK, \
            f"库存错误: 预期{EXPECTED_STOCK}, 实际{ACTUAL_STOCK}"


# ═══════════════════════════════════════════════════════════════
# 硬编码验证: 销售
# ═══════════════════════════════════════════════════════════════
class TestSaleVerification:
    """销售硬编码验证"""
    
    def test_sale_quantity_and_amount(self, client, data):
        """验证销售数量和金额"""
        # ── 硬编码输入 ──
        INPUT_QUANTITY = 20
        INPUT_UNIT_PRICE = 150.00
        INPUT_TAX_RATE = 0.01
        
        # ── 硬编码计算公式 ──
        # 销售金额 = 数量 × 单价
        EXPECTED_AMOUNT = Decimal(str(INPUT_QUANTITY)) * Decimal(str(INPUT_UNIT_PRICE))
        # 销售税额 = 金额 × 税率
        EXPECTED_TAX = EXPECTED_AMOUNT * Decimal(str(INPUT_TAX_RATE))
        # 销售价税合计 = 金额 + 税额
        EXPECTED_TOTAL = EXPECTED_AMOUNT + EXPECTED_TAX
        
        # ── 获取销售前库存 ──
        STOCK_BEFORE = get_inventory_qty(client, data["product_id"])
        
        # ── 执行销售 ──
        resp = client.post("/api/sales", json={
            "customer_id": data["customer_id"],
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-01-15T10:00:00",
            "items": [{
                "product_id": data["product_id"],
                "quantity": INPUT_QUANTITY,
                "unit_price": INPUT_UNIT_PRICE,
                "tax_rate": INPUT_TAX_RATE
            }]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        
        # ── 获取系统计算结果 ──
        resp_data = resp.json().get("data", resp.json())
        ACTUAL_AMOUNT = Decimal(str(resp_data.get("items", [{}])[0].get("total_price", 0)))
        ACTUAL_TOTAL = Decimal(str(resp_data.get("total_price", 0)))
        
        # ── 获取销售后库存 ──
        STOCK_AFTER = get_inventory_qty(client, data["product_id"])
        
        # ── 硬编码计算预期库存 ──
        EXPECTED_STOCK_AFTER = STOCK_BEFORE - INPUT_QUANTITY
        
        # ── 硬编码验证 ──
        print(f"\n=== 销售验证 ===")
        print(f"输入: 数量={INPUT_QUANTITY}, 单价={INPUT_UNIT_PRICE}, 税率={INPUT_TAX_RATE}")
        print(f"预期金额: {EXPECTED_AMOUNT}")
        print(f"实际金额: {ACTUAL_AMOUNT}")
        print(f"差异: {abs(EXPECTED_AMOUNT - ACTUAL_AMOUNT)}")
        print(f"销售前库存: {STOCK_BEFORE}")
        print(f"预期库存: {EXPECTED_STOCK_AFTER}")
        print(f"实际库存: {STOCK_AFTER}")
        print(f"差异: {abs(EXPECTED_STOCK_AFTER - STOCK_AFTER)}")
        
        # 验证
        assert ACTUAL_AMOUNT == EXPECTED_AMOUNT, \
            f"销售金额错误: 预期{EXPECTED_AMOUNT}, 实际{ACTUAL_AMOUNT}"
        assert STOCK_AFTER == EXPECTED_STOCK_AFTER, \
            f"库存错误: 预期{EXPECTED_STOCK_AFTER}, 实际{STOCK_AFTER}"


# ═══════════════════════════════════════════════════════════════
# 硬编码验证: 退货
# ═══════════════════════════════════════════════════════════════
class TestReturnVerification:
    """退货硬编码验证"""
    
    def test_return_stock_restoration(self, client, data):
        """验证退货后库存回补"""
        # ── 硬编码输入 ──
        RETURN_QUANTITY = 5
        
        # ── 获取退货前库存 ──
        STOCK_BEFORE = get_inventory_qty(client, data["product_id"])
        
        # ── 创建销售单（待退货） ──
        resp = client.post("/api/sales", json={
            "customer_id": data["customer_id"],
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-02-01T10:00:00",
            "items": [{
                "product_id": data["product_id"],
                "quantity": RETURN_QUANTITY,
                "unit_price": 150.00,
                "tax_rate": 0.01
            }]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        sale_id = get_entity_id(resp.json())
        
        # ── 获取销售后库存 ──
        STOCK_AFTER_SALE = get_inventory_qty(client, data["product_id"])
        
        # ── 硬编码计算预期库存 ──
        EXPECTED_STOCK_AFTER_SALE = STOCK_BEFORE - RETURN_QUANTITY
        
        # ── 执行退货（取消销售单） ──
        resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp.status_code == 200
        
        # ── 获取退货后库存 ──
        STOCK_AFTER_RETURN = get_inventory_qty(client, data["product_id"])
        
        # ── 硬编码计算预期库存 ──
        EXPECTED_STOCK_AFTER_RETURN = STOCK_AFTER_SALE + RETURN_QUANTITY
        
        # ── 硬编码验证 ──
        print(f"\n=== 退货验证 ===")
        print(f"退货数量: {RETURN_QUANTITY}")
        print(f"销售前库存: {STOCK_BEFORE}")
        print(f"预期销售后库存: {EXPECTED_STOCK_AFTER_SALE}")
        print(f"实际销售后库存: {STOCK_AFTER_SALE}")
        print(f"预期退货后库存: {EXPECTED_STOCK_AFTER_RETURN}")
        print(f"实际退货后库存: {STOCK_AFTER_RETURN}")
        
        # 验证
        assert STOCK_AFTER_SALE == EXPECTED_STOCK_AFTER_SALE, \
            f"销售后库存错误: 预期{EXPECTED_STOCK_AFTER_SALE}, 实际{STOCK_AFTER_SALE}"
        assert STOCK_AFTER_RETURN == EXPECTED_STOCK_AFTER_RETURN, \
            f"退货后库存错误: 预期{EXPECTED_STOCK_AFTER_RETURN}, 实际{STOCK_AFTER_RETURN}"


# ═══════════════════════════════════════════════════════════════
# 硬编码验证: 发票
# ═══════════════════════════════════════════════════════════════
class TestInvoiceVerification:
    """发票硬编码验证"""
    
    def test_invoice_amount_calculation(self, client):
        """验证发票金额计算"""
        # ── 硬编码输入 ──
        INPUT_AMOUNT_WITH_TAX = 10100.00
        INPUT_TAX_RATE = 0.01
        
        # ── 硬编码计算公式 ──
        # 不含税金额 = 含税金额 / (1 + 税率)
        EXPECTED_AMOUNT_WITHOUT_TAX = round2(
            Decimal(str(INPUT_AMOUNT_WITH_TAX)) / (1 + Decimal(str(INPUT_TAX_RATE)))
        )
        # 税额 = 含税金额 - 不含税金额
        EXPECTED_TAX_AMOUNT = round2(
            Decimal(str(INPUT_AMOUNT_WITH_TAX)) - EXPECTED_AMOUNT_WITHOUT_TAX
        )
        
        # ── 执行发票创建 ──
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-VERIFY-{int(time.time())}",
            "direction": "out",
            "invoice_type": "ordinary",
            "amount_with_tax": str(INPUT_AMOUNT_WITH_TAX),
            "tax_rate": str(INPUT_TAX_RATE),
            "counterparty_name": "测试客户",
            "issue_date": "2026-03-15",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        
        # ── 获取系统计算结果 ──
        resp_data = resp.json().get("data", resp.json())
        ACTUAL_AMOUNT_WITHOUT_TAX = round2(Decimal(str(resp_data.get("amount_without_tax", 0))))
        ACTUAL_TAX_AMOUNT = round2(Decimal(str(resp_data.get("tax_amount", 0))))
        
        # ── 硬编码验证 ──
        print(f"\n=== 发票验证 ===")
        print(f"输入: 含税金额={INPUT_AMOUNT_WITH_TAX}, 税率={INPUT_TAX_RATE}")
        print(f"预期不含税金额: {EXPECTED_AMOUNT_WITHOUT_TAX}")
        print(f"实际不含税金额: {ACTUAL_AMOUNT_WITHOUT_TAX}")
        print(f"差异: {abs(EXPECTED_AMOUNT_WITHOUT_TAX - ACTUAL_AMOUNT_WITHOUT_TAX)}")
        print(f"预期税额: {EXPECTED_TAX_AMOUNT}")
        print(f"实际税额: {ACTUAL_TAX_AMOUNT}")
        print(f"差异: {abs(EXPECTED_TAX_AMOUNT - ACTUAL_TAX_AMOUNT)}")
        
        # 验证
        assert ACTUAL_AMOUNT_WITHOUT_TAX == EXPECTED_AMOUNT_WITHOUT_TAX, \
            f"不含税金额错误: 预期{EXPECTED_AMOUNT_WITHOUT_TAX}, 实际{ACTUAL_AMOUNT_WITHOUT_TAX}"
        assert ACTUAL_TAX_AMOUNT == EXPECTED_TAX_AMOUNT, \
            f"税额错误: 预期{EXPECTED_TAX_AMOUNT}, 实际{ACTUAL_TAX_AMOUNT}"
        
        # ── 验证金额平衡 ──
        EXPECTED_BALANCE = EXPECTED_AMOUNT_WITHOUT_TAX + EXPECTED_TAX_AMOUNT
        ACTUAL_BALANCE = ACTUAL_AMOUNT_WITHOUT_TAX + ACTUAL_TAX_AMOUNT
        print(f"预期平衡: {EXPECTED_AMOUNT_WITHOUT_TAX} + {EXPECTED_TAX_AMOUNT} = {EXPECTED_BALANCE}")
        print(f"实际平衡: {ACTUAL_AMOUNT_WITHOUT_TAX} + {ACTUAL_TAX_AMOUNT} = {ACTUAL_BALANCE}")
        
        assert ACTUAL_BALANCE == round2(Decimal(str(INPUT_AMOUNT_WITH_TAX))), \
            f"金额不平衡: {ACTUAL_BALANCE} != {INPUT_AMOUNT_WITH_TAX}"


# ═══════════════════════════════════════════════════════════════
# 硬编码验证: 增值税
# ═══════════════════════════════════════════════════════════════
class TestVATVerification:
    """增值税硬编码验证"""
    
    def test_vat_calculation(self, client):
        """验证增值税计算"""
        # ── 查询增值税报表 ──
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        
        # ── 获取系统计算结果 ──
        ACTUAL_OUTPUT_TAX = round2(Decimal(str(data.get("output_tax", 0))))
        ACTUAL_INPUT_TAX = round2(Decimal(str(data.get("input_tax", 0))))
        ACTUAL_TAX_PAYABLE = round2(Decimal(str(data.get("tax_payable", 0))))
        
        # ── 硬编码计算公式 ──
        # 应纳税额 = 销项税额 - 进项税额
        EXPECTED_TAX_PAYABLE = ACTUAL_OUTPUT_TAX - ACTUAL_INPUT_TAX
        
        # ── 硬编码验证 ──
        print(f"\n=== 增值税验证 ===")
        print(f"销项税额: {ACTUAL_OUTPUT_TAX}")
        print(f"进项税额: {ACTUAL_INPUT_TAX}")
        print(f"预期应纳税额: {EXPECTED_TAX_PAYABLE}")
        print(f"实际应纳税额: {ACTUAL_TAX_PAYABLE}")
        print(f"差异: {abs(EXPECTED_TAX_PAYABLE - ACTUAL_TAX_PAYABLE)}")
        
        # 验证（允许 ±0.01 舍入差异）
        diff = abs(ACTUAL_TAX_PAYABLE - EXPECTED_TAX_PAYABLE)
        assert diff <= Decimal('0.01'), \
            f"增值税计算错误: 预期{EXPECTED_TAX_PAYABLE}, 实际{ACTUAL_TAX_PAYABLE}, 差异{diff}"


# ═══════════════════════════════════════════════════════════════
# 硬编码验证: 所得税
# ═══════════════════════════════════════════════════════════════
class TestIncomeTaxVerification:
    """所得税硬编码验证"""
    
    def test_income_tax_calculation(self, client):
        """验证所得税计算"""
        # ── 查询所得税报表 ──
        resp = client.get("/api/income-tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        
        # ── 获取系统计算结果 ──
        ACTUAL_REVENUE = round2(Decimal(str(data.get("total_revenue", 0))))
        ACTUAL_COST = round2(Decimal(str(data.get("total_cost", 0))))
        ACTUAL_PROFIT = round2(Decimal(str(data.get("taxable_income", 0))))
        ACTUAL_TAX_RATE = Decimal(str(data.get("tax_rate", 0)))
        ACTUAL_TAX_AMOUNT = round2(Decimal(str(data.get("tax_amount", 0))))
        
        # ── 硬编码计算公式 ──
        # 利润 = 收入 - 成本
        EXPECTED_PROFIT = ACTUAL_REVENUE - ACTUAL_COST
        # 应纳税额 = 利润 × 税率
        EXPECTED_TAX_AMOUNT = round2(EXPECTED_PROFIT * ACTUAL_TAX_RATE)
        
        # ── 硬编码验证 ──
        print(f"\n=== 所得税验证 ===")
        print(f"收入: {ACTUAL_REVENUE}")
        print(f"成本: {ACTUAL_COST}")
        print(f"预期利润: {EXPECTED_PROFIT}")
        print(f"实际利润: {ACTUAL_PROFIT}")
        print(f"差异: {abs(EXPECTED_PROFIT - ACTUAL_PROFIT)}")
        print(f"税率: {ACTUAL_TAX_RATE}")
        print(f"预期应纳税额: {EXPECTED_TAX_AMOUNT}")
        print(f"实际应纳税额: {ACTUAL_TAX_AMOUNT}")
        print(f"差异: {abs(EXPECTED_TAX_AMOUNT - ACTUAL_TAX_AMOUNT)}")
        
        # 验证
        assert ACTUAL_PROFIT == EXPECTED_PROFIT, \
            f"利润计算错误: 预期{EXPECTED_PROFIT}, 实际{ACTUAL_PROFIT}"
        assert ACTUAL_TAX_AMOUNT == EXPECTED_TAX_AMOUNT, \
            f"所得税计算错误: 预期{EXPECTED_TAX_AMOUNT}, 实际{ACTUAL_TAX_AMOUNT}"


# ═══════════════════════════════════════════════════════════════
# 硬编码验证: 资产负债表
# ═══════════════════════════════════════════════════════════════
class TestBalanceSheetVerification:
    """资产负债表硬编码验证"""
    
    def test_balance_sheet_equation(self, client):
        """验证资产负债表恒等式"""
        # ── 查询资产负债表 ──
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 3},
                         headers=HEADERS)
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            data = resp.json()
            
            # ── 获取系统计算结果 ──
            ACTUAL_ASSETS = round2(Decimal(str(data.get("total_assets", 0))))
            ACTUAL_LIABILITIES = round2(Decimal(str(data.get("total_liabilities", 0))))
            ACTUAL_EQUITY = round2(Decimal(str(data.get("total_equity", 0))))
            
            # ── 硬编码计算公式 ──
            # 资产 = 负债 + 权益
            EXPECTED_ASSETS = ACTUAL_LIABILITIES + ACTUAL_EQUITY
            
            # ── 硬编码验证 ──
            print(f"\n=== 资产负债表验证 ===")
            print(f"资产总计: {ACTUAL_ASSETS}")
            print(f"负债合计: {ACTUAL_LIABILITIES}")
            print(f"权益合计: {ACTUAL_EQUITY}")
            print(f"预期资产: {EXPECTED_ASSETS}")
            print(f"差异: {abs(EXPECTED_ASSETS - ACTUAL_ASSETS)}")
            
            # 验证（允许±0.01容差）
            diff = abs(EXPECTED_ASSETS - ACTUAL_ASSETS)
            assert diff <= Decimal('0.01'), \
                f"资产负债表不平衡: 预期{EXPECTED_ASSETS}, 实际{ACTUAL_ASSETS}, 差异{diff}"


# ═══════════════════════════════════════════════════════════════
# 硬编码验证: 利润表
# ═══════════════════════════════════════════════════════════════
class TestIncomeStatementVerification:
    """利润表硬编码验证"""
    
    def test_income_statement_equation(self, client):
        """验证利润表恒等式"""
        # ── 查询利润表 ──
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 3},
                         headers=HEADERS)
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            data = resp.json()
            
            # ── 获取系统计算结果 ──
            ACTUAL_REVENUE = round2(Decimal(str(data.get("revenue", data.get("total_revenue", 0)))))
            ACTUAL_COST = round2(Decimal(str(data.get("cost", data.get("total_cost", 0)))))
            ACTUAL_PROFIT = round2(Decimal(str(data.get("gross_profit", 0))))
            
            # ── 硬编码计算公式 ──
            # 毛利润 = 收入 - 成本
            EXPECTED_PROFIT = ACTUAL_REVENUE - ACTUAL_COST
            
            # ── 硬编码验证 ──
            print(f"\n=== 利润表验证 ===")
            print(f"收入: {ACTUAL_REVENUE}")
            print(f"成本: {ACTUAL_COST}")
            print(f"预期毛利润: {EXPECTED_PROFIT}")
            print(f"实际毛利润: {ACTUAL_PROFIT}")
            print(f"差异: {abs(EXPECTED_PROFIT - ACTUAL_PROFIT)}")
            
            # 验证
            assert ACTUAL_PROFIT == EXPECTED_PROFIT, \
                f"毛利润计算错误: 预期{EXPECTED_PROFIT}, 实际{ACTUAL_PROFIT}"
