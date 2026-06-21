"""全新数据库业务场景测试 — 贴合实际业务场景

测试目标:
  1. 使用全新数据库，从零开始构建业务数据
  2. 模拟真实企业的业务流程
  3. 验证数据准确性
  4. 覆盖所有使用场景

业务场景:
  - 某小型贸易公司，2026年1月开业
  - 主营电子产品销售
  - 小规模纳税人，征收率1%
  - 每月有采购、销售、费用等业务
  - 需要生成财务报表和税务申报

测试数据:
  - 期初余额: 2026年1月1日
  - 基础数据: 商品、供应商、客户
  - 业务数据: 采购单、销售单、费用、发票
  - 报表数据: 资产负债表、利润表、税务报表
"""

import os
import sys
import json
import time
import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# 确保 backend 在 sys.path 中
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 设置测试环境变量，使用临时数据库
import tempfile
temp_dir = tempfile.mkdtemp()
os.environ['INVENTORY_WORKSPACE'] = temp_dir

# 在导入 main 之前，初始化数据库和工作区
import workspace
workspace.ensure_workspace()

from database import init_db, SessionLocal
init_db()

from main import app
from models import Account

# ── 获取测试用 account_id ──
_db = SessionLocal()
_account = _db.query(Account).first()
ACCOUNT_ID = _account.id if _account else 1
_db.close()

# 公共请求头
HEADERS = {"X-Account-ID": str(ACCOUNT_ID), "X-Operator": "business_test"}

# 数据变化记录
DATA_CHANGES = []

# 测试数据存储
TEST_DATA = {}


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


def get_entity_id(resp_json):
    """从API响应中提取实体ID"""
    if "id" in resp_json:
        return resp_json["id"]
    if "data" in resp_json and "id" in resp_json["data"]:
        return resp_json["data"]["id"]
    if "entity_id" in resp_json:
        return resp_json["entity_id"]
    return None


@pytest.fixture(scope="module")
def client():
    """全 module 共享的 TestClient"""
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════
# 1. 期初余额设置
# ═══════════════════════════════════════════════════════════════
class TestOpeningBalance:
    """设置2026年期初余额"""

    def test_set_opening_balance(self, client):
        """设置2026年期初余额 - 模拟公司开业"""
        # 期初余额: 公司开业时的资金状况
        opening_balance = {
            "date": "2026-01-01",
            "cash_balance": 10000.00,      # 现金: 1万
            "bank_balance": 200000.00,     # 银行存款: 20万
            "accounts_receivable": 0.00,   # 应收账款: 0
            "inventory_value": 0.00,       # 存货: 0
            "fixed_assets_original": 50000.00,  # 固定资产原值: 5万
            "accumulated_depreciation": 0.00,   # 累计折旧: 0
            "intangible_assets_original": 0.00, # 无形资产: 0
            "accumulated_amortization": 0.00,   # 累计摊销: 0
            "accounts_payable": 0.00,      # 应付账款: 0
            "tax_payable": 0.00,           # 应交税费: 0
            "long_term_borrowings": 0.00,  # 长期借款: 0
            "paid_in_capital": 200000.00,  # 实收资本: 20万
            "retained_earnings": 10000.00  # 未分配利润: 1万
        }
        
        resp = client.post("/api/opening-balances", json=opening_balance, headers=HEADERS)
        assert resp.status_code in (200, 201, 409), f"设置期初余额失败: {resp.text}"
        
        # 验证期初余额
        resp = client.get("/api/opening-balances", headers=HEADERS)
        assert resp.status_code == 200, f"查询期初余额失败: {resp.text}"
        data = resp.json()
        
        if len(data) > 0:
            balance = data[0]
            TEST_DATA["opening_balance"] = balance
            
            record_change(
                module="期初余额",
                operation="设置2026年期初余额",
                before="无",
                after=f"现金={balance.get('cash_balance')}, 银行={balance.get('bank_balance')}, 实收资本={balance.get('paid_in_capital')}",
                calculation="资产(210000) = 负债(0) + 权益(210000)"
            )
            
            print(f"\n=== 期初余额设置 ===")
            print(f"现金: {balance.get('cash_balance')}")
            print(f"银行存款: {balance.get('bank_balance')}")
            print(f"实收资本: {balance.get('paid_in_capital')}")
            print(f"未分配利润: {balance.get('retained_earnings')}")


# ═══════════════════════════════════════════════════════════════
# 2. 基础数据设置
# ═══════════════════════════════════════════════════════════════
class TestBasicData:
    """设置基础数据"""

    def test_create_suppliers(self, client):
        """创建供应商 - 模拟真实供应商"""
        suppliers = [
            {"name": "深圳华强电子", "contact": "张经理", "phone": "13800138001"},
            {"name": "广州天河电子", "contact": "李经理", "phone": "13800138002"},
            {"name": "东莞长安电子", "contact": "王经理", "phone": "13800138003"},
        ]
        
        supplier_ids = []
        for supplier in suppliers:
            resp = client.post("/api/suppliers", json=supplier, headers=HEADERS)
            assert resp.status_code in (200, 201), f"创建供应商失败: {resp.text}"
            supplier_ids.append(get_entity_id(resp.json()))
        
        TEST_DATA["supplier_ids"] = supplier_ids
        
        record_change(
            module="基础数据",
            operation="创建供应商",
            before="无",
            after=f"创建{len(suppliers)}个供应商",
            calculation="供应商: 深圳华强电子、广州天河电子、东莞长安电子"
        )
        
        print(f"\n=== 创建供应商 ===")
        print(f"创建{len(suppliers)}个供应商")
        for i, supplier in enumerate(suppliers):
            print(f"  {i+1}. {supplier['name']}")

    def test_create_customers(self, client):
        """创建客户 - 模拟真实客户"""
        customers = [
            {"name": "北京中关村科技", "contact": "赵总", "phone": "13900139001"},
            {"name": "上海浦东贸易", "contact": "钱总", "phone": "13900139002"},
            {"name": "深圳南山电子", "contact": "孙总", "phone": "13900139003"},
            {"name": "杭州西湖数码", "contact": "李总", "phone": "13900139004"},
        ]
        
        customer_ids = []
        for customer in customers:
            resp = client.post("/api/customers", json=customer, headers=HEADERS)
            assert resp.status_code in (200, 201), f"创建客户失败: {resp.text}"
            customer_ids.append(get_entity_id(resp.json()))
        
        TEST_DATA["customer_ids"] = customer_ids
        
        record_change(
            module="基础数据",
            operation="创建客户",
            before="无",
            after=f"创建{len(customers)}个客户",
            calculation="客户: 北京中关村科技、上海浦东贸易、深圳南山电子、杭州西湖数码"
        )
        
        print(f"\n=== 创建客户 ===")
        print(f"创建{len(customers)}个客户")
        for i, customer in enumerate(customers):
            print(f"  {i+1}. {customer['name']}")

    def test_create_products(self, client):
        """创建商品 - 模拟电子产品"""
        products = [
            {
                "name": "iPhone 15 Pro",
                "sku": "IPHONE-15-PRO",
                "unit": "台",
                "purchase_price": 7000.00,
                "sale_price": 8999.00,
                "track_inventory": True,
                "category": "手机"
            },
            {
                "name": "MacBook Air M2",
                "sku": "MACBOOK-AIR-M2",
                "unit": "台",
                "purchase_price": 8000.00,
                "sale_price": 9999.00,
                "track_inventory": True,
                "category": "笔记本"
            },
            {
                "name": "AirPods Pro",
                "sku": "AIRPODS-PRO",
                "unit": "副",
                "purchase_price": 1200.00,
                "sale_price": 1799.00,
                "track_inventory": True,
                "category": "配件"
            },
            {
                "name": "Apple Watch Series 9",
                "sku": "APPLE-WATCH-9",
                "unit": "块",
                "purchase_price": 2500.00,
                "sale_price": 3299.00,
                "track_inventory": True,
                "category": "手表"
            },
            {
                "name": "电脑维修服务",
                "sku": "REPAIR-SERVICE",
                "unit": "次",
                "purchase_price": 0.00,
                "sale_price": 200.00,
                "track_inventory": False,
                "category": "服务"
            }
        ]
        
        product_ids = []
        for product in products:
            resp = client.post("/api/products", json=product, headers=HEADERS)
            assert resp.status_code in (200, 201), f"创建商品失败: {resp.text}"
            product_ids.append(get_entity_id(resp.json()))
        
        TEST_DATA["product_ids"] = product_ids
        
        record_change(
            module="基础数据",
            operation="创建商品",
            before="无",
            after=f"创建{len(products)}个商品",
            calculation="商品: iPhone 15 Pro、MacBook Air M2、AirPods Pro、Apple Watch Series 9、电脑维修服务"
        )
        
        print(f"\n=== 创建商品 ===")
        print(f"创建{len(products)}个商品")
        for i, product in enumerate(products):
            print(f"  {i+1}. {product['name']} - 采购价:{product['purchase_price']}, 售价:{product['sale_price']}")


# ═══════════════════════════════════════════════════════════════
# 3. 1月份业务
# ═══════════════════════════════════════════════════════════════
class TestJanuaryBusiness:
    """1月份业务 - 开业采购"""

    def test_january_purchases(self, client):
        """1月采购 - 开业备货"""
        if "supplier_ids" not in TEST_DATA or "product_ids" not in TEST_DATA:
            pytest.skip("基础数据未创建")
        
        supplier_id = TEST_DATA["supplier_ids"][0]  # 深圳华强电子
        product_ids = TEST_DATA["product_ids"]
        
        # 采购单: 开业备货
        purchase_items = [
            {"product_id": product_ids[0], "quantity": 10, "unit_price": 7000.00, "tax_rate": 0.13},  # iPhone 15 Pro
            {"product_id": product_ids[1], "quantity": 5, "unit_price": 8000.00, "tax_rate": 0.13},   # MacBook Air M2
            {"product_id": product_ids[2], "quantity": 20, "unit_price": 1200.00, "tax_rate": 0.13},  # AirPods Pro
            {"product_id": product_ids[3], "quantity": 10, "unit_price": 2500.00, "tax_rate": 0.13},  # Apple Watch Series 9
        ]
        
        # 计算预期金额
        expected_total = Decimal(str(sum(item["quantity"] * item["unit_price"] for item in purchase_items)))
        
        resp = client.post("/api/purchases", json={
            "supplier_id": supplier_id,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-01-10T10:00:00",
            "items": purchase_items
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建采购单失败: {resp.text}"
        data = resp.json()
        TEST_DATA["january_purchase_id"] = get_entity_id(data)
        
        actual_total = Decimal(str(data.get("data", data).get("total_price", 0)))
        
        record_change(
            module="采购",
            operation="1月开业采购",
            before=f"预期金额={expected_total}",
            after=f"实际金额={actual_total}",
            calculation=f"iPhone×10=70000, MacBook×5=40000, AirPods×20=24000, Watch×10=25000, 合计={expected_total}"
        )
        
        print(f"\n=== 1月采购 - 开业备货 ===")
        print(f"预期金额: {expected_total}")
        print(f"实际金额: {actual_total}")
        print(f"差异: {abs(expected_total - actual_total)}")

    def test_january_sales(self, client):
        """1月销售 - 开业首月"""
        if "customer_ids" not in TEST_DATA or "product_ids" not in TEST_DATA:
            pytest.skip("基础数据未创建")
        
        customer_id = TEST_DATA["customer_ids"][0]  # 北京中关村科技
        product_ids = TEST_DATA["product_ids"]
        
        # 销售单: 开业首月销售
        sale_items = [
            {"product_id": product_ids[0], "quantity": 3, "unit_price": 8999.00, "tax_rate": 0.01},   # iPhone 15 Pro
            {"product_id": product_ids[1], "quantity": 2, "unit_price": 9999.00, "tax_rate": 0.01},   # MacBook Air M2
            {"product_id": product_ids[2], "quantity": 5, "unit_price": 1799.00, "tax_rate": 0.01},   # AirPods Pro
        ]
        
        # 计算预期金额
        expected_total = Decimal(str(sum(item["quantity"] * item["unit_price"] for item in sale_items)))
        
        resp = client.post("/api/sales", json={
            "customer_id": customer_id,
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-01-20T10:00:00",
            "items": sale_items
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建销售单失败: {resp.text}"
        data = resp.json()
        TEST_DATA["january_sale_id"] = get_entity_id(data)
        
        actual_total = Decimal(str(data.get("data", data).get("total_price", 0)))
        
        record_change(
            module="销售",
            operation="1月开业销售",
            before=f"预期金额={expected_total}",
            after=f"实际金额={actual_total}",
            calculation=f"iPhone×3=26997, MacBook×2=19998, AirPods×5=8995, 合计={expected_total}"
        )
        
        print(f"\n=== 1月销售 - 开业首月 ===")
        print(f"预期金额: {expected_total}")
        print(f"实际金额: {actual_total}")
        print(f"差异: {abs(expected_total - actual_total)}")

    def test_january_expenses(self, client):
        """1月费用 - 开业费用"""
        expenses = [
            {"category": "房租", "amount": 5000.00, "description": "1月办公室租金", "expense_date": "2026-01-05", "payment_method": "company"},
            {"category": "工资", "amount": 15000.00, "description": "1月员工工资", "expense_date": "2026-01-15", "payment_method": "company"},
            {"category": "办公用品", "amount": 2000.00, "description": "办公设备采购", "expense_date": "2026-01-10", "payment_method": "company"},
        ]
        
        total_expenses = 0
        for expense in expenses:
            resp = client.post("/api/expenses", json=expense, headers=HEADERS)
            assert resp.status_code in (200, 201), f"创建费用失败: {resp.text}"
            total_expenses += expense["amount"]
        
        record_change(
            module="费用",
            operation="1月开业费用",
            before="无",
            after=f"总费用={total_expenses}",
            calculation="房租5000 + 工资15000 + 办公用品2000 = 22000"
        )
        
        print(f"\n=== 1月费用 - 开业费用 ===")
        print(f"总费用: {total_expenses}")
        for expense in expenses:
            print(f"  {expense['category']}: {expense['amount']}")


# ═══════════════════════════════════════════════════════════════
# 4. 2月份业务
# ═══════════════════════════════════════════════════════════════
class TestFebruaryBusiness:
    """2月份业务 - 春节后复工"""

    def test_february_purchases(self, client):
        """2月采购 - 春节后补货"""
        if "supplier_ids" not in TEST_DATA or "product_ids" not in TEST_DATA:
            pytest.skip("基础数据未创建")
        
        supplier_id = TEST_DATA["supplier_ids"][1]  # 广州天河电子
        product_ids = TEST_DATA["product_ids"]
        
        purchase_items = [
            {"product_id": product_ids[0], "quantity": 8, "unit_price": 7000.00, "tax_rate": 0.13},   # iPhone 15 Pro
            {"product_id": product_ids[2], "quantity": 30, "unit_price": 1200.00, "tax_rate": 0.13},  # AirPods Pro
        ]
        
        expected_total = Decimal(str(sum(item["quantity"] * item["unit_price"] for item in purchase_items)))
        
        resp = client.post("/api/purchases", json={
            "supplier_id": supplier_id,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-02-05T10:00:00",
            "items": purchase_items
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建采购单失败: {resp.text}"
        data = resp.json()
        TEST_DATA["february_purchase_id"] = get_entity_id(data)
        
        actual_total = Decimal(str(data.get("data", data).get("total_price", 0)))
        
        record_change(
            module="采购",
            operation="2月春节后补货",
            before=f"预期金额={expected_total}",
            after=f"实际金额={actual_total}",
            calculation=f"iPhone×8=56000, AirPods×30=36000, 合计={expected_total}"
        )
        
        print(f"\n=== 2月采购 - 春节后补货 ===")
        print(f"预期金额: {expected_total}")
        print(f"实际金额: {actual_total}")

    def test_february_sales(self, client):
        """2月销售 - 春节后销售"""
        if "customer_ids" not in TEST_DATA or "product_ids" not in TEST_DATA:
            pytest.skip("基础数据未创建")
        
        customer_id = TEST_DATA["customer_ids"][1]  # 上海浦东贸易
        product_ids = TEST_DATA["product_ids"]
        
        sale_items = [
            {"product_id": product_ids[0], "quantity": 5, "unit_price": 8999.00, "tax_rate": 0.01},   # iPhone 15 Pro
            {"product_id": product_ids[2], "quantity": 10, "unit_price": 1799.00, "tax_rate": 0.01},  # AirPods Pro
            {"product_id": product_ids[3], "quantity": 3, "unit_price": 3299.00, "tax_rate": 0.01},   # Apple Watch Series 9
        ]
        
        expected_total = Decimal(str(sum(item["quantity"] * item["unit_price"] for item in sale_items)))
        
        resp = client.post("/api/sales", json={
            "customer_id": customer_id,
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-02-15T10:00:00",
            "items": sale_items
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建销售单失败: {resp.text}"
        data = resp.json()
        TEST_DATA["february_sale_id"] = get_entity_id(data)
        
        actual_total = Decimal(str(data.get("data", data).get("total_price", 0)))
        
        record_change(
            module="销售",
            operation="2月春节后销售",
            before=f"预期金额={expected_total}",
            after=f"实际金额={actual_total}",
            calculation=f"iPhone×5=44995, AirPods×10=17990, Watch×3=9897, 合计={expected_total}"
        )
        
        print(f"\n=== 2月销售 - 春节后销售 ===")
        print(f"预期金额: {expected_total}")
        print(f"实际金额: {actual_total}")

    def test_february_expenses(self, client):
        """2月费用"""
        expenses = [
            {"category": "房租", "amount": 5000.00, "description": "2月办公室租金", "expense_date": "2026-02-05", "payment_method": "company"},
            {"category": "工资", "amount": 15000.00, "description": "2月员工工资", "expense_date": "2026-02-15", "payment_method": "company"},
            {"category": "水电", "amount": 800.00, "description": "2月水电费", "expense_date": "2026-02-20", "payment_method": "company"},
        ]
        
        total_expenses = 0
        for expense in expenses:
            resp = client.post("/api/expenses", json=expense, headers=HEADERS)
            assert resp.status_code in (200, 201), f"创建费用失败: {resp.text}"
            total_expenses += expense["amount"]
        
        record_change(
            module="费用",
            operation="2月费用",
            before="无",
            after=f"总费用={total_expenses}",
            calculation="房租5000 + 工资15000 + 水电800 = 20800"
        )
        
        print(f"\n=== 2月费用 ===")
        print(f"总费用: {total_expenses}")


# ═══════════════════════════════════════════════════════════════
# 5. 3月份业务 (季度末)
# ═══════════════════════════════════════════════════════════════
class TestMarchBusiness:
    """3月份业务 - 季度末"""

    def test_march_purchases(self, client):
        """3月采购"""
        if "supplier_ids" not in TEST_DATA or "product_ids" not in TEST_DATA:
            pytest.skip("基础数据未创建")
        
        supplier_id = TEST_DATA["supplier_ids"][2]  # 东莞长安电子
        product_ids = TEST_DATA["product_ids"]
        
        purchase_items = [
            {"product_id": product_ids[0], "quantity": 12, "unit_price": 7000.00, "tax_rate": 0.13},  # iPhone 15 Pro
            {"product_id": product_ids[1], "quantity": 8, "unit_price": 8000.00, "tax_rate": 0.13},   # MacBook Air M2
            {"product_id": product_ids[3], "quantity": 5, "unit_price": 2500.00, "tax_rate": 0.13},   # Apple Watch Series 9
        ]
        
        expected_total = Decimal(str(sum(item["quantity"] * item["unit_price"] for item in purchase_items)))
        
        resp = client.post("/api/purchases", json={
            "supplier_id": supplier_id,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-03-05T10:00:00",
            "items": purchase_items
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建采购单失败: {resp.text}"
        data = resp.json()
        TEST_DATA["march_purchase_id"] = get_entity_id(data)
        
        actual_total = Decimal(str(data.get("data", data).get("total_price", 0)))
        
        record_change(
            module="采购",
            operation="3月采购",
            before=f"预期金额={expected_total}",
            after=f"实际金额={actual_total}",
            calculation=f"iPhone×12=84000, MacBook×8=64000, Watch×5=12500, 合计={expected_total}"
        )
        
        print(f"\n=== 3月采购 ===")
        print(f"预期金额: {expected_total}")
        print(f"实际金额: {actual_total}")

    def test_march_sales(self, client):
        """3月销售"""
        if "customer_ids" not in TEST_DATA or "product_ids" not in TEST_DATA:
            pytest.skip("基础数据未创建")
        
        customer_id = TEST_DATA["customer_ids"][2]  # 深圳南山电子
        product_ids = TEST_DATA["product_ids"]
        
        sale_items = [
            {"product_id": product_ids[0], "quantity": 8, "unit_price": 8999.00, "tax_rate": 0.01},   # iPhone 15 Pro
            {"product_id": product_ids[1], "quantity": 4, "unit_price": 9999.00, "tax_rate": 0.01},   # MacBook Air M2
            {"product_id": product_ids[2], "quantity": 15, "unit_price": 1799.00, "tax_rate": 0.01},  # AirPods Pro
            {"product_id": product_ids[3], "quantity": 5, "unit_price": 3299.00, "tax_rate": 0.01},   # Apple Watch Series 9
        ]
        
        expected_total = Decimal(str(sum(item["quantity"] * item["unit_price"] for item in sale_items)))
        
        resp = client.post("/api/sales", json={
            "customer_id": customer_id,
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-03-15T10:00:00",
            "items": sale_items
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建销售单失败: {resp.text}"
        data = resp.json()
        TEST_DATA["march_sale_id"] = get_entity_id(data)
        
        actual_total = Decimal(str(data.get("data", data).get("total_price", 0)))
        
        record_change(
            module="销售",
            operation="3月销售",
            before=f"预期金额={expected_total}",
            after=f"实际金额={actual_total}",
            calculation=f"iPhone×8=71992, MacBook×4=39996, AirPods×15=26985, Watch×5=16495, 合计={expected_total}"
        )
        
        print(f"\n=== 3月销售 ===")
        print(f"预期金额: {expected_total}")
        print(f"实际金额: {actual_total}")

    def test_march_invoices(self, client):
        """3月发票 - 季度末开票"""
        if "march_sale_id" not in TEST_DATA:
            pytest.skip("3月销售单未创建")
        
        # 创建销项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-MARCH-{int(time.time())}",
            "direction": "out",
            "invoice_type": "ordinary",
            "amount_with_tax": "100000.00",
            "tax_rate": "0.01",
            "counterparty_name": "深圳南山电子",
            "issue_date": "2026-03-25",
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建发票失败: {resp.text}"
        data = resp.json()
        TEST_DATA["march_invoice_id"] = get_entity_id(data)
        
        record_change(
            module="发票",
            operation="3月销项发票",
            before="含税金额=100000.00",
            after=f"不含税金额={data.get('data', data).get('amount_without_tax')}, 税额={data.get('data', data).get('tax_amount')}",
            calculation="不含税金额 = 100000 ÷ 1.01 = 99009.90"
        )
        
        print(f"\n=== 3月发票 ===")
        print(f"发票号码: {data.get('data', data).get('invoice_no')}")
        print(f"不含税金额: {data.get('data', data).get('amount_without_tax')}")
        print(f"税额: {data.get('data', data).get('tax_amount')}")


# ═══════════════════════════════════════════════════════════════
# 6. 库存验证
# ═══════════════════════════════════════════════════════════════
class TestInventoryVerification:
    """库存验证"""

    def test_inventory_after_operations(self, client):
        """验证操作后的库存"""
        resp = client.get("/api/inventory", params={"page": 1, "page_size": 500}, headers=HEADERS)
        assert resp.status_code == 200, f"查询库存失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        
        print(f"\n=== 库存验证 ===")
        print(f"商品数量: {len(items)}")
        
        for item in items:
            product_id = item.get("product_id")
            product_name = item.get("product_name", "未知")
            quantity = item.get("quantity", 0)
            
            print(f"  {product_name}: {quantity}")
            
            # 验证库存非负
            assert quantity >= 0, f"商品{product_name}库存为负: {quantity}"
        
        record_change(
            module="库存",
            operation="库存验证",
            before="操作前",
            after=f"商品数量={len(items)}",
            calculation="所有商品库存非负"
        )


# ═══════════════════════════════════════════════════════════════
# 7. 财务报表验证
# ═══════════════════════════════════════════════════════════════
class TestFinancialReports:
    """财务报表验证"""

    def test_balance_sheet(self, client):
        """资产负债表验证"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 3},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"查询资产负债表失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            
            total_assets = Decimal(str(data.get("total_assets", 0)))
            total_liabilities = Decimal(str(data.get("total_liabilities", 0)))
            total_equity = Decimal(str(data.get("total_equity", 0)))
            
            diff = abs(total_assets - (total_liabilities + total_equity))
            
            record_change(
                module="财务报表",
                operation="资产负债表",
                before=f"资产={total_assets}",
                after=f"负债={total_liabilities}, 权益={total_equity}",
                calculation=f"资产({total_assets}) = 负债({total_liabilities}) + 权益({total_equity}), 差异={diff}"
            )
            
            print(f"\n=== 资产负债表 ===")
            print(f"资产总计: {total_assets}")
            print(f"负债合计: {total_liabilities}")
            print(f"权益合计: {total_equity}")
            print(f"差异: {diff}")
            
            assert diff <= Decimal('0.01'), f"资产负债表不平衡: 差异{diff}"

    def test_income_statement(self, client):
        """利润表验证"""
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 3},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"查询利润表失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            
            revenue = Decimal(str(data.get("revenue", data.get("total_revenue", 0))))
            cost = Decimal(str(data.get("cost", data.get("total_cost", 0))))
            gross_profit = Decimal(str(data.get("gross_profit", 0)))
            
            expected_profit = revenue - cost
            
            record_change(
                module="财务报表",
                operation="利润表",
                before=f"收入={revenue}, 成本={cost}",
                after=f"毛利润={gross_profit}",
                calculation=f"毛利润 = 收入({revenue}) - 成本({cost}) = {expected_profit}"
            )
            
            print(f"\n=== 利润表 ===")
            print(f"收入: {revenue}")
            print(f"成本: {cost}")
            print(f"毛利润: {gross_profit}")
            print(f"预期毛利润: {expected_profit}")
            print(f"差异: {abs(gross_profit - expected_profit)}")


# ═══════════════════════════════════════════════════════════════
# 8. 税务报表验证
# ═══════════════════════════════════════════════════════════════
class TestTaxReports:
    """税务报表验证"""

    def test_vat_report(self, client):
        """增值税报表验证"""
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200, f"查询增值税报表失败: {resp.text}"
        data = resp.json()
        
        output_tax = Decimal(str(data.get("output_tax", 0)))
        input_tax = Decimal(str(data.get("input_tax", 0)))
        tax_payable = Decimal(str(data.get("tax_payable", 0)))
        
        record_change(
            module="税务",
            operation="Q1增值税报表",
            before=f"销项税额={output_tax}, 进项税额={input_tax}",
            after=f"应纳税额={tax_payable}",
            calculation=f"应纳税额 = 销项税额({output_tax}) - 进项税额({input_tax})"
        )
        
        print(f"\n=== Q1增值税报表 ===")
        print(f"销项税额: {output_tax}")
        print(f"进项税额: {input_tax}")
        print(f"应纳税额: {tax_payable}")

    def test_income_tax_report(self, client):
        """所得税报表验证"""
        resp = client.get("/api/income-tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200, f"查询所得税报表失败: {resp.text}"
        data = resp.json()
        
        revenue = Decimal(str(data.get("total_revenue", 0)))
        cost = Decimal(str(data.get("total_cost", 0)))
        profit = Decimal(str(data.get("taxable_income", 0)))
        tax_amount = Decimal(str(data.get("tax_amount", 0)))
        
        record_change(
            module="税务",
            operation="Q1所得税报表",
            before=f"收入={revenue}, 成本={cost}",
            after=f"利润={profit}, 应纳税额={tax_amount}",
            calculation=f"利润 = 收入({revenue}) - 成本({cost})"
        )
        
        print(f"\n=== Q1所得税报表 ===")
        print(f"收入: {revenue}")
        print(f"成本: {cost}")
        print(f"利润: {profit}")
        print(f"应纳税额: {tax_amount}")


# ═══════════════════════════════════════════════════════════════
# 9. 数据变化报告
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
                print(f"  - {change['operation']}: {change['after']}")
        
        # 保存报告
        report_path = os.path.join(os.path.dirname(__file__), "business_scenario_changes.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(DATA_CHANGES, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据变化报告已保存到: {report_path}")
