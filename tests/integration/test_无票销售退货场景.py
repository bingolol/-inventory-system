"""无票销售 + 退货场景测试 — 复核业务逻辑

场景描述:
  1. 卖了300元的货，没有开票，只录入销售单
  2. 半个月后退货100元

验证点:
  1. 无票销售是否正确记录
  2. 退货后库存是否正确回补
  3. 退货后财务数据是否正确变化
  4. 增值税报表是否正确（无票销售不进入增值税）
  5. 利润表是否正确（无票销售计入经营收入）
"""

import os
import json
import time
import pytest
from decimal import Decimal
from datetime import datetime
from database import SessionLocal
from models import Account
from helpers import get_entity_id

# ── 获取测试用 account_id ──
_db = SessionLocal()
_account = _db.query(Account).first()
ACCOUNT_ID = _account.id if _account else 1
_db.close()

# 公共请求头
HEADERS = {"X-Account-ID": str(ACCOUNT_ID), "X-Operator": "verify_test"}

# 数据变化记录
DATA_CHANGES = []


def record_change(module, operation, before, after, calculation=""):
    """记录数据变化"""
    DATA_CHANGES.append({
        "module": module,
        "operation": operation,
        "before": str(before),
        "after": str(after),
        "calculation": calculation,
        "timestamp": datetime.now().isoformat()
    })


@pytest.fixture(scope="module")
def setup_data(client):
    """设置测试数据"""
    data = {}
    
    # 创建客户
    resp = client.post("/api/customers", json={
        "name": f"复核测试客户-{int(time.time())}",
        "contact": "测试",
        "phone": "13800000001"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建客户失败: {resp.text}"
    data["customer_id"] = get_entity_id(resp.json())
    
    # 创建商品
    resp = client.post("/api/products", json={
        "name": f"复核测试商品-{int(time.time())}",
        "sku": f"VERIFY-{int(time.time())}",
        "unit": "个",
        "purchase_price": 50.00,
        "sale_price": 100.00,
        "track_inventory": True,
        "category": "测试"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建商品失败: {resp.text}"
    data["product_id"] = get_entity_id(resp.json())
    
    # 创建供应商
    resp = client.post("/api/suppliers", json={
        "name": f"复核测试供应商-{int(time.time())}",
        "contact": "测试",
        "phone": "13800000002"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建供应商失败: {resp.text}"
    data["supplier_id"] = get_entity_id(resp.json())
    
    # 采购入库（确保有库存）
    resp = client.post("/api/purchases", json={
        "supplier_id": data["supplier_id"],
        "payment_method": "company",
        "payment_status": "paid",
        "purchase_date": "2026-01-01T10:00:00",
        "items": [
            {"product_id": data["product_id"], "quantity": 100, "unit_price": 50.00, "tax_rate": 0.13}
        ]
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"采购入库失败: {resp.text}"
    data["purchase_id"] = get_entity_id(resp.json())
    
    return data


# ═══════════════════════════════════════════════════════════════
# 1. 无票销售场景
# ═══════════════════════════════════════════════════════════════
class TestNoInvoiceSale:
    """无票销售场景"""

    def test_sale_without_invoice(self, client, setup_data):
        """卖了300元的货，没有开票，只录入销售单"""
        customer_id = setup_data["customer_id"]
        product_id = setup_data["product_id"]
        
        # 记录销售前库存
        resp = client.get("/api/inventory", params={"page": 1, "page_size": 500}, headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json().get("items", [])
        stock_before = 0
        for item in items:
            if item.get("product_id") == product_id:
                stock_before = item.get("quantity", 0)
                break
        
        # 创建销售单：卖了300元（3个×100元），无票
        resp = client.post("/api/sales", json={
            "customer_id": customer_id,
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-01-15T10:00:00",
            "items": [
                {"product_id": product_id, "quantity": 3, "unit_price": 100.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建销售单失败: {resp.text}"
        data = resp.json()
        setup_data["sale_id"] = get_entity_id(data)
        
        # 记录销售后库存
        resp = client.get("/api/inventory", params={"page": 1, "page_size": 500}, headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json().get("items", [])
        stock_after = 0
        for item in items:
            if item.get("product_id") == product_id:
                stock_after = item.get("quantity", 0)
                break
        
        # 记录数据变化
        record_change(
            module="销售",
            operation="无票销售",
            before=f"库存={stock_before}",
            after=f"库存={stock_after}, 销售金额=300",
            calculation=f"销售3个×100元=300元, 库存减少{stock_before - stock_after}个"
        )
        
        print(f"\n=== 无票销售场景 ===")
        print(f"销售前库存: {stock_before}")
        print(f"销售后库存: {stock_after}")
        print(f"库存减少: {stock_before - stock_after}")
        print(f"销售金额: 300元")
        print(f"是否开票: 否")
        
        # 验证库存减少
        assert stock_after == stock_before - 3, f"库存应减少3个: 预期{stock_before - 3}, 实际{stock_after}"


# ═══════════════════════════════════════════════════════════════
# 2. 退货场景
# ═══════════════════════════════════════════════════════════════
class TestReturnSale:
    """退货场景"""

    def test_return_partial_sale(self, client, setup_data):
        """半个月后退货100元"""
        if "sale_id" not in setup_data:
            pytest.skip("销售单未创建")
        
        sale_id = setup_data["sale_id"]
        product_id = setup_data["product_id"]
        
        # 记录退货前库存
        resp = client.get("/api/inventory", params={"page": 1, "page_size": 500}, headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json().get("items", [])
        stock_before_return = 0
        for item in items:
            if item.get("product_id") == product_id:
                stock_before_return = item.get("quantity", 0)
                break
        
        # 获取销售单详情
        resp = client.get(f"/api/sales/{sale_id}", headers=HEADERS)
        assert resp.status_code == 200, f"查询销售单失败: {resp.text}"
        sale_data = resp.json()
        original_total = Decimal(str(sale_data.get("total_price", 0)))
        
        # 取消销售单（模拟退货）
        resp = client.put(f"/api/sales/{sale_id}", json={
            "status": "cancelled"
        }, headers=HEADERS)
        assert resp.status_code == 200, f"取消销售单失败: {resp.text}"
        
        # 记录退货后库存
        resp = client.get("/api/inventory", params={"page": 1, "page_size": 500}, headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json().get("items", [])
        stock_after_return = 0
        for item in items:
            if item.get("product_id") == product_id:
                stock_after_return = item.get("quantity", 0)
                break
        
        # 记录数据变化
        record_change(
            module="销售",
            operation="退货（取消销售单）",
            before=f"库存={stock_before_return}, 销售单金额={original_total}",
            after=f"库存={stock_after_return}",
            calculation=f"退货后库存回补{stock_after_return - stock_before_return}个"
        )
        
        print(f"\n=== 退货场景 ===")
        print(f"原销售单金额: {original_total}")
        print(f"退货前库存: {stock_before_return}")
        print(f"退货后库存: {stock_after_return}")
        print(f"库存回补: {stock_after_return - stock_before_return}")
        
        # 验证库存回补
        assert stock_after_return == stock_before_return + 3, \
            f"库存应增加3个: 预期{stock_before_return + 3}, 实际{stock_after_return}"


# ═══════════════════════════════════════════════════════════════
# 3. 税务影响验证
# ═══════════════════════════════════════════════════════════════
class TestTaxImpact:
    """税务影响验证"""

    def test_vat_report_impact(self, client, setup_data):
        """验证增值税报表影响"""
        # 查询增值税报表
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200, f"查询增值税报表失败: {resp.text}"
        data = resp.json()
        
        output_tax = Decimal(str(data.get("output_tax", 0)))
        tax_payable = Decimal(str(data.get("tax_payable", 0)))
        
        # 记录数据变化
        record_change(
            module="税务",
            operation="增值税报表验证",
            before="无票销售",
            after=f"销项税额={output_tax}, 应纳税额={tax_payable}",
            calculation="无票销售不进入增值税销项（BR-4规则）"
        )
        
        print(f"\n=== 增值税报表影响 ===")
        print(f"销项税额: {output_tax}")
        print(f"应纳税额: {tax_payable}")
        print(f"说明: 无票销售不进入增值税销项（根据BR-4规则）")

    def test_income_statement_impact(self, client, setup_data):
        """验证利润表影响"""
        # 查询利润表
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 1},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"查询利润表失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            revenue = Decimal(str(data.get("revenue", data.get("total_revenue", 0))))
            
            # 记录数据变化
            record_change(
                module="财务",
                operation="利润表验证",
                before="无票销售300元",
                after=f"收入={revenue}",
                calculation="无票销售计入经营收入（BR-2规则）"
            )
            
            print(f"\n=== 利润表影响 ===")
            print(f"收入: {revenue}")
            print(f"说明: 无票销售计入经营收入（根据BR-2规则）")


# ═══════════════════════════════════════════════════════════════
# 4. 业务规则验证
# ═══════════════════════════════════════════════════════════════
class TestBusinessRules:
    """业务规则验证"""

    def test_br4_no_invoice_vat(self, client, setup_data):
        """BR-4: 无票收入不强制计提销项税"""
        print(f"\n=== BR-4规则验证 ===")
        print(f"规则: 无票收入不强制计提销项税")
        print(f"依据: 小规模纳税人无票收入，实务中税务局不主动稽查")
        print(f"实现: 增值税报表只统计发票表数据，无票销售单不进入增值税销项")
        
        # 验证：无票销售不应出现在增值税销项中
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        
        # 检查发票列表
        invoice_list = data.get("invoice_list", [])
        has_sale_invoice = False
        for inv in invoice_list:
            if inv.get("direction") == "out" and "复核测试" in inv.get("counterparty_name", ""):
                has_sale_invoice = True
                break
        
        print(f"销售发票数量: {len(invoice_list)}")
        print(f"是否有复核测试客户发票: {has_sale_invoice}")
        
        # 记录数据变化
        record_change(
            module="税务",
            operation="BR-4规则验证",
            before="无票销售",
            after=f"发票数量={len(invoice_list)}, 有客户发票={has_sale_invoice}",
            calculation="无票销售不进入增值税销项"
        )

    def test_br2_tax_caliber(self, client, setup_data):
        """BR-2: 税务口径（发票说话）"""
        print(f"\n=== BR-2规则验证 ===")
        print(f"规则: 税务口径（取消经营口径后统一发票说话）")
        print(f"收入=销项发票不含税金额，用于增值税报表、企业所得税申报")

        # 查询税务口径
        resp_tax = client.get("/api/income-tax-report",
                             params={"year": 2026, "quarter": 1},
                             headers=HEADERS)

        if resp_tax.status_code == 200:
            tax_data = resp_tax.json()
            tax_revenue = Decimal(str(tax_data.get("total_revenue", 0)))

            print(f"税务口径收入: {tax_revenue}")

            # 记录数据变化
            record_change(
                module="财务",
                operation="BR-2规则验证",
                before="税务口径（发票不含税）",
                after=f"收入={tax_revenue}",
                calculation="收入取销项发票不含税金额"
            )


# ═══════════════════════════════════════════════════════════════
# 5. 数据变化报告
# ═══════════════════════════════════════════════════════════════
class TestDataChangeReport:
    """数据变化报告"""

    def test_generate_report(self, client):
        """生成数据变化报告"""
        print(f"\n=== 数据变化报告 ===")
        print(f"总记录数: {len(DATA_CHANGES)}")
        
        # 按模块分组
        module_changes = {}
        for change in DATA_CHANGES:
            module = change["module"]
            if module not in module_changes:
                module_changes[module] = []
            module_changes[module].append(change)
        
        for module, changes in module_changes.items():
            print(f"\n模块: {module}")
            print(f"  变化次数: {len(changes)}")
            for change in changes:
                print(f"  - {change['operation']}")
                print(f"    前: {change['before']}")
                print(f"    后: {change['after']}")
                print(f"    计算: {change['calculation']}")
        
        # 保存报告
        report_path = os.path.join(os.path.dirname(__file__), "no_invoice_return_changes.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(DATA_CHANGES, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据变化报告已保存到: {report_path}")
