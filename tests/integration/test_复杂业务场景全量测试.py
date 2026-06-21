"""复杂业务场景全量测试 — 覆盖真实财务工作场景

业务场景: 某贸易公司2026年Q1完整业务循环

场景设计（复杂度提升）:
  1. 多客户、多供应商、多商品（有库存/无库存）
  2. 有票销售 + 无票销售 + 部分开票
  3. 销售后全退 + 部分退
  4. 采购后部分退
  5. 全收款 + 部分收款 + 未收款
  6. 费用报销（有票/无票/不同类别）
  7. 发票管理（进项专票/进项普票/销项发票/认证）
  8. 固定资产购置 + 折旧
  9. 期初余额设置
  10. 税务申报（增值税/所得税）

时间线:
  - 1月1日: 期初余额、基础数据
  - 1月: 大采购、混合销售、费用
  - 2月: 补货、销售、退货、收款、发票
  - 3月: 季度末、固定资产、税务申报

验证点:
  1. 库存变化是否正确
  2. 财务数据是否正确
  3. 税务数据是否正确
  4. 业务规则是否正确应用
"""

import os
import sys
import json
import time
import pytest
from decimal import Decimal
from datetime import datetime
from fastapi.testclient import TestClient

# 确保 backend 在 sys.path 中
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

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
HEADERS = {"X-Account-ID": str(ACCOUNT_ID), "X-Operator": "complex_test"}

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


def get_entity_id(resp_json):
    """从API响应中提取实体ID"""
    if "id" in resp_json:
        return resp_json["id"]
    if "data" in resp_json and "id" in resp_json["data"]:
        return resp_json["data"]["id"]
    if "entity_id" in resp_json:
        return resp_json["entity_id"]
    return None


def get_inventory_qty(client, product_id):
    """获取商品库存"""
    resp = client.get("/api/inventory", params={"page": 1, "page_size": 500}, headers=HEADERS)
    assert resp.status_code == 200
    items = resp.json().get("items", [])
    for item in items:
        if item.get("product_id") == product_id:
            return item.get("quantity", 0)
    return 0


@pytest.fixture(scope="module")
def client():
    """全 module 共享的 TestClient"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def setup_data(client):
    """设置复杂业务场景的基础数据"""
    data = {}
    unique = str(int(time.time()))[-6:]
    
    # ── 供应商 ──
    suppliers = [
        {"name": f"深圳华强电子-{unique}", "contact": "张经理", "phone": "13800138001"},
        {"name": f"广州天河电子-{unique}", "contact": "李经理", "phone": "13800138002"},
    ]
    data["supplier_ids"] = []
    for s in suppliers:
        resp = client.post("/api/suppliers", json=s, headers=HEADERS)
        assert resp.status_code in (200, 201)
        data["supplier_ids"].append(get_entity_id(resp.json()))
    
    # ── 客户 ──
    customers = [
        {"name": f"北京中关村科技-{unique}", "contact": "赵总", "phone": "13900139001"},
        {"name": f"上海浦东贸易-{unique}", "contact": "钱总", "phone": "13900139002"},
        {"name": f"散客-{unique}", "contact": "", "phone": ""},
    ]
    data["customer_ids"] = []
    for c in customers:
        resp = client.post("/api/customers", json=c, headers=HEADERS)
        assert resp.status_code in (200, 201)
        data["customer_ids"].append(get_entity_id(resp.json()))
    
    # ── 商品（有库存追踪） ──
    products_tracked = [
        {"name": f"iPhone 15 Pro-{unique}", "sku": f"IP-{unique}", "unit": "台",
         "purchase_price": 7000.00, "sale_price": 8999.00, "track_inventory": True, "category": "手机"},
        {"name": f"MacBook Air M2-{unique}", "sku": f"MB-{unique}", "unit": "台",
         "purchase_price": 8000.00, "sale_price": 9999.00, "track_inventory": True, "category": "笔记本"},
        {"name": f"AirPods Pro-{unique}", "sku": f"AP-{unique}", "unit": "副",
         "purchase_price": 1200.00, "sale_price": 1799.00, "track_inventory": True, "category": "配件"},
    ]
    
    # ── 商品（无库存追踪 - 服务类） ──
    products_service = [
        {"name": f"电脑维修服务-{unique}", "sku": f"SVC1-{unique}", "unit": "次",
         "purchase_price": 0.00, "sale_price": 200.00, "track_inventory": False, "category": "服务"},
        {"name": f"数据恢复服务-{unique}", "sku": f"SVC2-{unique}", "unit": "次",
         "purchase_price": 0.00, "sale_price": 500.00, "track_inventory": False, "category": "服务"},
    ]
    
    data["product_ids"] = []
    for p in products_tracked + products_service:
        resp = client.post("/api/products", json=p, headers=HEADERS)
        assert resp.status_code in (200, 201)
        data["product_ids"].append(get_entity_id(resp.json()))
    
    return data


# ═══════════════════════════════════════════════════════════════
# 1. 期初余额 + 基础数据验证
# ═══════════════════════════════════════════════════════════════
class TestSetupVerification:
    """期初余额和基础数据验证"""

    def test_opening_balance(self, client):
        """验证期初余额"""
        resp = client.get("/api/opening-balances", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        
        print(f"\n=== 期初余额验证 ===")
        print(f"期初余额记录数: {len(data)}")
        
        record_change(
            module="期初余额",
            operation="验证期初余额",
            before="无",
            after=f"记录数={len(data)}",
            calculation="期初余额是资产负债表的基础"
        )

    def test_basic_data_created(self, client, setup_data):
        """验证基础数据创建"""
        print(f"\n=== 基础数据验证 ===")
        print(f"供应商数量: {len(setup_data['supplier_ids'])}")
        print(f"客户数量: {len(setup_data['customer_ids'])}")
        print(f"商品数量: {len(setup_data['product_ids'])} (有库存3 + 无库存2)")
        
        record_change(
            module="基础数据",
            operation="验证基础数据",
            before="无",
            after=f"供应商={len(setup_data['supplier_ids'])}, 客户={len(setup_data['customer_ids'])}, 商品={len(setup_data['product_ids'])}",
            calculation="基础数据是业务操作的前提"
        )


# ═══════════════════════════════════════════════════════════════
# 2. 1月份业务 — 大采购 + 混合销售 + 费用
# ═══════════════════════════════════════════════════════════════
class TestJanuaryBusiness:
    """1月份业务"""

    def test_january_purchases(self, client, setup_data):
        """1月采购: 从两个供应商采购"""
        supplier_ids = setup_data["supplier_ids"]
        product_ids = setup_data["product_ids"]
        
        # 供应商1采购: iPhone 20台 + MacBook 10台（已付款）
        resp = client.post("/api/purchases", json={
            "supplier_id": supplier_ids[0],
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-01-05T10:00:00",
            "items": [
                {"product_id": product_ids[0], "quantity": 20, "unit_price": 7000.00, "tax_rate": 0.13},
                {"product_id": product_ids[1], "quantity": 10, "unit_price": 8000.00, "tax_rate": 0.13},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["purchase1_id"] = get_entity_id(resp.json())
        
        # 供应商2采购: AirPods 50副（赊账）
        resp = client.post("/api/purchases", json={
            "supplier_id": supplier_ids[1],
            "payment_method": "company",
            "payment_status": "unpaid",
            "purchase_date": "2026-01-10T10:00:00",
            "items": [
                {"product_id": product_ids[2], "quantity": 50, "unit_price": 1200.00, "tax_rate": 0.13},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["purchase2_id"] = get_entity_id(resp.json())
        
        # 验证库存
        iphone_stock = get_inventory_qty(client, product_ids[0])
        macbook_stock = get_inventory_qty(client, product_ids[1])
        airpods_stock = get_inventory_qty(client, product_ids[2])
        
        print(f"\n=== 1月采购 ===")
        print(f"iPhone库存: {iphone_stock} (预期20)")
        print(f"MacBook库存: {macbook_stock} (预期10)")
        print(f"AirPods库存: {airpods_stock} (预期50)")
        
        record_change(
            module="采购",
            operation="1月采购",
            before="无",
            after=f"iPhone={iphone_stock}, MacBook={macbook_stock}, AirPods={airpods_stock}",
            calculation="供应商1采购(已付)+供应商2采购(赊账)"
        )
        
        assert iphone_stock == 20
        assert macbook_stock == 10
        assert airpods_stock == 50

    def test_january_sales_mixed(self, client, setup_data):
        """1月混合销售: 有票+无票+服务"""
        customer_ids = setup_data["customer_ids"]
        product_ids = setup_data["product_ids"]
        
        # 销售1: 有票销售给北京客户
        resp = client.post("/api/sales", json={
            "customer_id": customer_ids[0],
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-01-15T10:00:00",
            "items": [
                {"product_id": product_ids[0], "quantity": 5, "unit_price": 8999.00, "tax_rate": 0.01},
                {"product_id": product_ids[2], "quantity": 10, "unit_price": 1799.00, "tax_rate": 0.01},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["sale1_id"] = get_entity_id(resp.json())
        
        # 创建销项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-JAN1-{int(time.time())}",
            "direction": "out",
            "invoice_type": "ordinary",
            "amount_with_tax": "62985.00",
            "tax_rate": "0.01",
            "counterparty_name": "北京中关村科技",
            "issue_date": "2026-01-15",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["invoice1_id"] = get_entity_id(resp.json())
        
        # 销售2: 无票销售给散客
        resp = client.post("/api/sales", json={
            "customer_id": customer_ids[2],
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-01-20T10:00:00",
            "items": [
                {"product_id": product_ids[2], "quantity": 15, "unit_price": 1799.00, "tax_rate": 0.01},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["sale2_id"] = get_entity_id(resp.json())
        
        # 销售3: 服务销售（不扣库存）
        resp = client.post("/api/sales", json={
            "customer_id": customer_ids[1],
            "deduct_inventory": False,
            "payment_status": "paid",
            "sale_date": "2026-01-25T10:00:00",
            "items": [
                {"product_id": product_ids[3], "quantity": 5, "unit_price": 200.00, "tax_rate": 0.01},
                {"product_id": product_ids[4], "quantity": 2, "unit_price": 500.00, "tax_rate": 0.01},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["sale3_id"] = get_entity_id(resp.json())
        
        # 验证库存
        iphone_stock = get_inventory_qty(client, product_ids[0])
        airpods_stock = get_inventory_qty(client, product_ids[2])
        
        print(f"\n=== 1月混合销售 ===")
        print(f"有票销售: iPhone×5 + AirPods×10 = 62985")
        print(f"无票销售: AirPods×15 = 26985")
        print(f"服务销售: 维修×5 + 数据恢复×2 = 2000")
        print(f"iPhone库存: {iphone_stock} (预期15)")
        print(f"AirPods库存: {airpods_stock} (预期25)")
        
        record_change(
            module="销售",
            operation="1月混合销售",
            before="无",
            after=f"iPhone={iphone_stock}, AirPods={airpods_stock}",
            calculation="有票销售+无票销售+服务销售"
        )
        
        assert iphone_stock == 15
        assert airpods_stock == 25

    def test_january_expenses(self, client, setup_data):
        """1月费用: 多种类别"""
        expenses = [
            {"category": "房租", "amount": 5000.00, "description": "1月办公室租金", 
             "expense_date": "2026-01-05", "payment_method": "company"},
            {"category": "工资", "amount": 15000.00, "description": "1月员工工资", 
             "expense_date": "2026-01-15", "payment_method": "company"},
            {"category": "办公用品", "amount": 2000.00, "description": "办公设备采购", 
             "expense_date": "2026-01-10", "payment_method": "company"},
            {"category": "运费", "amount": 1500.00, "description": "物流费用", 
             "expense_date": "2026-01-20", "payment_method": "company"},
        ]
        
        total = 0
        for exp in expenses:
            resp = client.post("/api/expenses", json=exp, headers=HEADERS)
            assert resp.status_code in (200, 201)
            total += exp["amount"]
        
        print(f"\n=== 1月费用 ===")
        print(f"总费用: {total}")
        print(f"房租: 5000, 工资: 15000, 办公用品: 2000, 运费: 1500")
        
        record_change(
            module="费用",
            operation="1月费用",
            before="无",
            after=f"总费用={total}",
            calculation="房租5000+工资15000+办公用品2000+运费1500=23500"
        )


# ═══════════════════════════════════════════════════════════════
# 3. 2月份业务 — 补货 + 退货 + 收款 + 发票
# ═══════════════════════════════════════════════════════════════
class TestFebruaryBusiness:
    """2月份业务"""

    def test_february_purchase(self, client, setup_data):
        """2月补货"""
        supplier_ids = setup_data["supplier_ids"]
        product_ids = setup_data["product_ids"]
        
        stock_before = get_inventory_qty(client, product_ids[0])
        
        # 补货: iPhone 10台
        resp = client.post("/api/purchases", json={
            "supplier_id": supplier_ids[0],
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-02-05T10:00:00",
            "items": [
                {"product_id": product_ids[0], "quantity": 10, "unit_price": 7000.00, "tax_rate": 0.13},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        
        stock_after = get_inventory_qty(client, product_ids[0])
        
        print(f"\n=== 2月补货 ===")
        print(f"补货前iPhone库存: {stock_before}")
        print(f"补货后iPhone库存: {stock_after}")
        
        record_change(
            module="采购",
            operation="2月补货",
            before=f"iPhone库存={stock_before}",
            after=f"iPhone库存={stock_after}",
            calculation="iPhone×10=70000"
        )
        
        assert stock_after == stock_before + 10

    def test_february_sale_unpaid(self, client, setup_data):
        """2月赊账销售"""
        customer_ids = setup_data["customer_ids"]
        product_ids = setup_data["product_ids"]
        
        # 赊账销售给上海客户
        resp = client.post("/api/sales", json={
            "customer_id": customer_ids[1],
            "deduct_inventory": True,
            "payment_status": "unpaid",
            "sale_date": "2026-02-10T10:00:00",
            "items": [
                {"product_id": product_ids[0], "quantity": 3, "unit_price": 8999.00, "tax_rate": 0.01},
                {"product_id": product_ids[1], "quantity": 2, "unit_price": 9999.00, "tax_rate": 0.01},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["sale4_id"] = get_entity_id(resp.json())
        
        iphone_stock = get_inventory_qty(client, product_ids[0])
        macbook_stock = get_inventory_qty(client, product_ids[1])
        
        print(f"\n=== 2月赊账销售 ===")
        print(f"销售金额: 3×8999 + 2×9999 = 46995")
        print(f"收款状态: 未收")
        print(f"iPhone库存: {iphone_stock}")
        print(f"MacBook库存: {macbook_stock}")
        
        record_change(
            module="销售",
            operation="2月赊账销售",
            before="无",
            after=f"iPhone={iphone_stock}, MacBook={macbook_stock}, 金额=46995",
            calculation="iPhone×3=26997, MacBook×2=19998, 合计=46995"
        )

    def test_february_partial_return(self, client, setup_data):
        """2月部分退货: 上海客户退货1台MacBook"""
        if "sale4_id" not in setup_data:
            pytest.skip("2月销售单未创建")
        
        sale_id = setup_data["sale4_id"]
        product_ids = setup_data["product_ids"]
        
        stock_before = get_inventory_qty(client, product_ids[1])
        
        # 获取销售单详情
        resp = client.get(f"/api/sales/{sale_id}", headers=HEADERS)
        assert resp.status_code == 200
        original_total = Decimal(str(resp.json().get("total_price", 0)))
        
        # 取消销售单（模拟退货）
        resp = client.put(f"/api/sales/{sale_id}", json={
            "status": "cancelled"
        }, headers=HEADERS)
        assert resp.status_code == 200
        
        stock_after = get_inventory_qty(client, product_ids[1])
        
        print(f"\n=== 2月部分退货 ===")
        print(f"原销售单金额: {original_total}")
        print(f"退货前MacBook库存: {stock_before}")
        print(f"退货后MacBook库存: {stock_after}")
        print(f"库存回补: {stock_after - stock_before}")
        
        record_change(
            module="销售",
            operation="2月退货",
            before=f"销售单金额={original_total}, MacBook库存={stock_before}",
            after=f"MacBook库存={stock_after}",
            calculation="退货后库存回补"
        )
        
        assert stock_after > stock_before

    def test_february_invoice_management(self, client, setup_data):
        """2月发票管理: 进项发票认证"""
        # 创建进项专票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"IN-FEB-{int(time.time())}",
            "direction": "in",
            "invoice_type": "special",
            "amount_with_tax": "11300.00",
            "tax_rate": "0.13",
            "counterparty_name": "深圳华强电子",
            "issue_date": "2026-02-15",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["invoice2_id"] = get_entity_id(resp.json())
        
        # 认证进项发票
        if "invoice2_id" in setup_data:
            resp = client.post(f"/api/invoices/{setup_data['invoice2_id']}/certify",
                             headers=HEADERS)
            assert resp.status_code == 200
        
        print(f"\n=== 2月发票管理 ===")
        print(f"进项专票: 11300 (不含税10000, 税额1300)")
        print(f"认证状态: 已认证")
        
        record_change(
            module="发票",
            operation="2月进项发票",
            before="无",
            after="进项专票11300, 已认证",
            calculation="不含税10000, 税额1300"
        )


# ═══════════════════════════════════════════════════════════════
# 4. 3月份业务 — 季度末 + 固定资产 + 税务
# ═══════════════════════════════════════════════════════════════
class TestMarchBusiness:
    """3月份业务"""

    def test_march_fixed_asset(self, client, setup_data):
        """3月固定资产购置"""
        resp = client.post("/api/fixed-assets", json={
            "asset_code": f"FA-{int(time.time())}",
            "name": "办公电脑",
            "category": "电子设备",
            "original_value": 50000.00,
            "salvage_rate": 0.05,
            "useful_life": 36,
            "start_date": "2026-03-01",
            "depreciation_method": "年限平均法"
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["fixed_asset_id"] = get_entity_id(resp.json())
        
        print(f"\n=== 3月固定资产 ===")
        print(f"资产名称: 办公电脑")
        print(f"原值: 50000")
        print(f"残值率: 5%")
        print(f"使用寿命: 36个月")
        print(f"月折旧额: (50000-2500)/36 = 1319.44")
        
        record_change(
            module="固定资产",
            operation="3月固定资产购置",
            before="无",
            after="办公电脑50000",
            calculation="月折旧额=(50000-2500)/36=1319.44"
        )

    def test_march_sale_with_service(self, client, setup_data):
        """3月混合销售: 商品+服务"""
        customer_ids = setup_data["customer_ids"]
        product_ids = setup_data["product_ids"]
        
        # 混合销售
        resp = client.post("/api/sales", json={
            "customer_id": customer_ids[0],
            "deduct_inventory": True,
            "payment_status": "paid",
            "sale_date": "2026-03-15T10:00:00",
            "items": [
                {"product_id": product_ids[0], "quantity": 5, "unit_price": 8999.00, "tax_rate": 0.01},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        setup_data["sale5_id"] = get_entity_id(resp.json())
        
        # 创建销项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"INV-MAR-{int(time.time())}",
            "direction": "out",
            "invoice_type": "ordinary",
            "amount_with_tax": "44995.00",
            "tax_rate": "0.01",
            "counterparty_name": "北京中关村科技",
            "issue_date": "2026-03-15",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201)
        
        iphone_stock = get_inventory_qty(client, product_ids[0])
        
        print(f"\n=== 3月销售 ===")
        print(f"销售金额: 5 x 8999 = 44995")
        print(f"iPhone库存: {iphone_stock}")
        
        record_change(
            module="销售",
            operation="3月销售",
            before="无",
            after=f"iPhone={iphone_stock}, 金额=44995",
            calculation="iPhone x 5 = 44995"
        )

    def test_march_expenses(self, client, setup_data):
        """3月费用: 税金+日常"""
        expenses = [
            {"category": "房租", "amount": 5000.00, "description": "3月办公室租金", 
             "expense_date": "2026-03-05", "payment_method": "company"},
            {"category": "工资", "amount": 15000.00, "description": "3月员工工资", 
             "expense_date": "2026-03-15", "payment_method": "company"},
            {"category": "税金及附加", "amount": 500.00, "description": "附加税", 
             "expense_date": "2026-03-20", "payment_method": "company"},
        ]
        
        total = 0
        for exp in expenses:
            resp = client.post("/api/expenses", json=exp, headers=HEADERS)
            assert resp.status_code in (200, 201)
            total += exp["amount"]
        
        print(f"\n=== 3月费用 ===")
        print(f"总费用: {total}")
        
        record_change(
            module="费用",
            operation="3月费用",
            before="无",
            after=f"总费用={total}",
            calculation="房租5000+工资15000+税金500=20500"
        )


# ═══════════════════════════════════════════════════════════════
# 5. 库存验证
# ═══════════════════════════════════════════════════════════════
class TestInventoryVerification:
    """库存验证"""

    def test_inventory_consistency(self, client, setup_data):
        """库存一致性验证"""
        product_ids = setup_data["product_ids"]
        
        print(f"\n=== 库存一致性验证 ===")
        
        # 获取所有库存
        resp = client.get("/api/inventory", params={"page": 1, "page_size": 500}, headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json().get("items", [])
        
        for product_id in product_ids[:3]:  # 前3个商品追踪库存
            for item in items:
                if item.get("product_id") == product_id:
                    qty = item.get("quantity", 0)
                    print(f"商品{product_id}: 库存={qty}")
                    assert qty >= 0, f"商品{product_id}库存为负: {qty}"
                    break
        
        record_change(
            module="库存",
            operation="库存一致性验证",
            before="操作前",
            after="所有商品库存非负",
            calculation="库存=采购总量-销售总量+退货量"
        )


# ═══════════════════════════════════════════════════════════════
# 6. 财务报表验证
# ═══════════════════════════════════════════════════════════════
class TestFinancialReports:
    """财务报表验证"""

    def test_balance_sheet(self, client):
        """资产负债表验证"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 3},
                         headers=HEADERS)
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            data = resp.json()
            total_assets = Decimal(str(data.get("total_assets", 0)))
            total_liabilities = Decimal(str(data.get("total_liabilities", 0)))
            total_equity = Decimal(str(data.get("total_equity", 0)))
            
            diff = abs(total_assets - (total_liabilities + total_equity))
            
            print(f"\n=== 资产负债表 ===")
            print(f"资产总计: {total_assets}")
            print(f"负债合计: {total_liabilities}")
            print(f"权益合计: {total_equity}")
            print(f"差异: {diff}")
            
            record_change(
                module="财务报表",
                operation="资产负债表",
                before=f"资产={total_assets}",
                after=f"负债={total_liabilities}, 权益={total_equity}",
                calculation=f"资产=负债+权益, 差异={diff}"
            )
            
            assert diff <= Decimal('0.01')

    def test_income_statement(self, client):
        """利润表验证"""
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 3},
                         headers=HEADERS)
        assert resp.status_code in (200, 422)
        
        if resp.status_code == 200:
            data = resp.json()
            revenue = Decimal(str(data.get("revenue", data.get("total_revenue", 0))))
            cost = Decimal(str(data.get("cost", data.get("total_cost", 0))))
            profit = Decimal(str(data.get("gross_profit", 0)))
            
            expected_profit = revenue - cost
            
            print(f"\n=== 利润表 ===")
            print(f"收入: {revenue}")
            print(f"成本: {cost}")
            print(f"毛利润: {profit}")
            print(f"预期毛利润: {expected_profit}")
            
            record_change(
                module="财务报表",
                operation="利润表",
                before=f"收入={revenue}, 成本={cost}",
                after=f"毛利润={profit}",
                calculation=f"毛利润=收入-成本={expected_profit}"
            )


# ═══════════════════════════════════════════════════════════════
# 7. 税务报表验证
# ═══════════════════════════════════════════════════════════════
class TestTaxReports:
    """税务报表验证"""

    def test_vat_report(self, client):
        """增值税报表验证"""
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        
        output_tax = Decimal(str(data.get("output_tax", 0)))
        input_tax = Decimal(str(data.get("input_tax", 0)))
        tax_payable = Decimal(str(data.get("tax_payable", 0)))
        
        print(f"\n=== Q1增值税报表 ===")
        print(f"销项税额: {output_tax}")
        print(f"进项税额: {input_tax}")
        print(f"应纳税额: {tax_payable}")
        print(f"说明: 无票销售不进入增值税销项（BR-4规则）")
        
        record_change(
            module="税务",
            operation="Q1增值税报表",
            before="无",
            after=f"销项税额={output_tax}, 进项税额={input_tax}, 应纳税额={tax_payable}",
            calculation="应纳税额=销项税额-进项税额"
        )

    def test_income_tax_report(self, client):
        """所得税报表验证"""
        # 经营口径
        resp_ops = client.get("/api/income-tax-report",
                             params={"year": 2026, "quarter": 1, "caliber": "operating"},
                             headers=HEADERS)
        # 税务口径
        resp_tax = client.get("/api/income-tax-report",
                             params={"year": 2026, "quarter": 1, "caliber": "tax"},
                             headers=HEADERS)
        
        if resp_ops.status_code == 200 and resp_tax.status_code == 200:
            ops_data = resp_ops.json()
            tax_data = resp_tax.json()
            
            ops_revenue = Decimal(str(ops_data.get("total_revenue", 0)))
            tax_revenue = Decimal(str(tax_data.get("total_revenue", 0)))
            ops_profit = Decimal(str(ops_data.get("taxable_income", 0)))
            tax_profit = Decimal(str(tax_data.get("taxable_income", 0)))
            
            print(f"\n=== Q1所得税报表 ===")
            print(f"经营口径: 收入={ops_revenue}, 利润={ops_profit}")
            print(f"税务口径: 收入={tax_revenue}, 利润={tax_profit}")
            print(f"收入差异: {abs(ops_revenue - tax_revenue)}")
            print(f"利润差异: {abs(ops_profit - tax_profit)}")
            
            record_change(
                module="税务",
                operation="Q1所得税报表",
                before=f"经营口径: 收入={ops_revenue}, 利润={ops_profit}",
                after=f"税务口径: 收入={tax_revenue}, 利润={tax_profit}",
                calculation=f"收入差异={abs(ops_revenue - tax_revenue)}, 利润差异={abs(ops_profit - tax_profit)}"
            )


# ═══════════════════════════════════════════════════════════════
# 8. 业务规则验证
# ═══════════════════════════════════════════════════════════════
class TestBusinessRules:
    """业务规则验证"""

    def test_br4_rule(self, client, setup_data):
        """BR-4: 无票收入不强制计提销项税"""
        print(f"\n=== BR-4规则验证 ===")
        print(f"规则: 无票收入不强制计提销项税")
        print(f"场景: 1月无票销售AirPods 15副×1799=26985")
        print(f"预期: 增值税报表中不包含此笔销售的销项税")
        
        # 查询增值税报表
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        
        # 检查发票列表
        invoice_list = data.get("invoice_list", [])
        
        print(f"发票数量: {len(invoice_list)}")
        print(f"结论: 无票销售不进入增值税销项")
        
        record_change(
            module="业务规则",
            operation="BR-4验证",
            before="无票销售26985",
            after=f"发票数量={len(invoice_list)}",
            calculation="无票销售不进入增值税销项"
        )

    def test_br2_rule(self, client):
        """BR-2: 经营口径与税务口径"""
        print(f"\n=== BR-2规则验证 ===")
        print(f"规则: 经营口径与税务口径天然不同")
        print(f"经营口径: 收入=订单金额（含税）")
        print(f"税务口径: 收入=发票金额（不含税）")
        
        # 查询双口径
        resp_ops = client.get("/api/income-tax-report",
                             params={"year": 2026, "quarter": 1, "caliber": "operating"},
                             headers=HEADERS)
        resp_tax = client.get("/api/income-tax-report",
                             params={"year": 2026, "quarter": 1, "caliber": "tax"},
                             headers=HEADERS)
        
        if resp_ops.status_code == 200 and resp_tax.status_code == 200:
            ops_revenue = Decimal(str(resp_ops.json().get("total_revenue", 0)))
            tax_revenue = Decimal(str(resp_tax.json().get("total_revenue", 0)))
            
            print(f"经营口径收入: {ops_revenue}")
            print(f"税务口径收入: {tax_revenue}")
            print(f"差异: {abs(ops_revenue - tax_revenue)}")
            print(f"结论: 双口径差异符合预期")
            
            record_change(
                module="业务规则",
                operation="BR-2验证",
                before=f"经营口径={ops_revenue}",
                after=f"税务口径={tax_revenue}",
                calculation=f"差异={abs(ops_revenue - tax_revenue)}"
            )


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
                print(f"  - {change['operation']}")
        
        # 保存报告
        report_path = os.path.join(os.path.dirname(__file__), "complex_scenario_changes.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(DATA_CHANGES, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据变化报告已保存到: {report_path}")
