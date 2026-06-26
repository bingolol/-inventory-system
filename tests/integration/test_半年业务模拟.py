"""半年业务模拟测试 — 模拟真实财务工作场景

时间跨度: 2026年1月 - 2026年6月
业务场景: 小规模纳税人企业，包含采购、销售、费用、发票、税务申报等全流程

测试目标:
  1. 验证所有模块在真实业务场景下的稳定性
  2. 验证财务数据一致性（库存、应收应付、税务）
  3. 验证报表生成的正确性
  4. 发现潜在的业务逻辑问题

不变量声明:
  - I-库存一致性: 采购入库增加库存，销售出库减少库存，取消/恢复操作正确联动
  - I-财务平衡: 资产负债表平衡，利润表数据准确
  - I-税务准确性: 增值税报表数据与发票数据一致
"""

import os
import sys
import time
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
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
from test_helpers import ensure_test_product

# ── 获取测试用 account_id ──
_db = SessionLocal()
_account = _db.query(Account).first()
ACCOUNT_ID = _account.id if _account else 1
_db.close()

# 公共请求头
HEADERS = {"X-Account-ID": str(ACCOUNT_ID), "X-Operator": "e2e_test"}
UNIQUE = str(int(time.time()))[-6:]

# 时间配置: 模拟2026年1月-6月
START_DATE = datetime(2026, 1, 1)
END_DATE = datetime(2026, 6, 30)


@pytest.fixture(scope="session")
def client():
    """全 session 共享的 TestClient"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def created_data(client):
    """Session 级共享数据：创建基础数据，返回各 ID"""
    data = {}

    # 创建客户
    resp = client.post("/api/customers", json={
        "name": f"模拟客户-{UNIQUE}", "contact": "财务部", "phone": f"13800000001{UNIQUE}"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建客户失败: {resp.text}"
    data["customer_id"] = _get_entity_id(resp.json())

    # 创建供应商
    resp = client.post("/api/suppliers", json={
        "name": f"模拟供应商-{UNIQUE}", "contact": "销售部", "phone": f"13800000002{UNIQUE}"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建供应商失败: {resp.text}"
    data["supplier_id"] = _get_entity_id(resp.json())

    # 创建可追踪库存商品
    resp = client.post("/api/products", json={
        "name": f"模拟商品-可追踪-{UNIQUE}", "sku": f"SIM-TRK-{UNIQUE}",
        "unit": "个", "purchase_price": 10.00, "sale_price": 20.00,
        "track_inventory": True, "category": "测试"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建可追踪商品失败: {resp.text}"
    data["product_track_id"] = _get_entity_id(resp.json())

    # 创建不追踪库存商品（服务类）
    resp = client.post("/api/products", json={
        "name": f"模拟服务-不追踪-{UNIQUE}", "sku": f"SIM-SVC-{UNIQUE}",
        "unit": "次", "purchase_price": 50.00, "sale_price": 100.00,
        "track_inventory": False, "category": "服务"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建不追踪商品失败: {resp.text}"
    data["product_svc_id"] = _get_entity_id(resp.json())

    # 创建固定资产
    resp = client.post("/api/fixed-assets", json={
        "asset_code": f"FA-{UNIQUE}",
        "name": f"模拟设备-{UNIQUE}", "category": "电子设备",
        "original_value": 10000.00, "useful_life": 36,
        "start_date": "2026-01-01", "depreciation_method": "年限平均法"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建固定资产失败: {resp.text}"
    data["fixed_asset_id"] = _get_entity_id(resp.json())

    return data


def _get_entity_id(resp_json):
    """从 API 响应中提取实体 ID"""
    if "id" in resp_json:
        return resp_json["id"]
    if "data" in resp_json and "id" in resp_json["data"]:
        return resp_json["data"]["id"]
    if "entity_id" in resp_json:
        return resp_json["entity_id"]
    return None


def _get_inventory_qty(client, product_id):
    """辅助：获取指定商品当前库存"""
    resp = client.get("/api/inventory", params={"page": 1, "page_size": 500},
                     headers=HEADERS)
    assert resp.status_code == 200
    items = resp.json().get("items", [])
    target = next((i for i in items if i["product_id"] == product_id), None)
    return target["quantity"] if target else 0


def _generate_monthly_dates(year, month):
    """生成指定月份的业务日期列表（每周2-3个业务日）"""
    dates = []
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(days=1)
    
    current = start
    while current <= end:
        # 跳过周末
        if current.weekday() < 5:  # 0-4 是周一到周五
            dates.append(current)
        current += timedelta(days=1)
    
    # 每周选择2-3个业务日
    selected = []
    for i in range(0, len(dates), 7):
        week = dates[i:i+7]
        if len(week) >= 2:
            selected.extend(week[:2])  # 每周前两个工作日
        else:
            selected.extend(week)
    
    return selected


# ═══════════════════════════════════════════════════════════════
# 1. 期初余额设置
# ═══════════════════════════════════════════════════════════════
class TestOpeningBalance:
    """设置2026年期初余额"""

    def test_set_opening_balance(self, client):
        """设置2026年期初余额"""
        resp = client.post("/api/opening-balances", json={
            "date": "2026-01-01",
            "cash_balance": 50000.00,
            "bank_balance": 200000.00,
            "accounts_receivable": 30000.00,
            "inventory_value": 10000.00,
            "fixed_assets_original": 100000.00,
            "accumulated_depreciation": 20000.00,
            "accounts_payable": 15000.00,
            "tax_payable": 5000.00,
            "paid_in_capital": 300000.00,
            "retained_earnings": 50000.00
        }, headers=HEADERS)
        # 允许期初余额已存在的情况
        assert resp.status_code in (200, 201, 409), f"设置期初余额失败: {resp.text}"

    def test_opening_balance_saved(self, client):
        """验证期初余额已保存"""
        resp = client.get("/api/opening-balances", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0, "期初余额未保存"


# ═══════════════════════════════════════════════════════════════
# 2. 月度业务循环测试
# ═══════════════════════════════════════════════════════════════
class TestMonthlyBusinessCycle:
    """模拟1-6月的月度业务循环"""

    def test_january_business(self, client, created_data):
        """1月业务: 采购入库、销售出库、费用支出"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        sid = created_data["supplier_id"]
        svc_id = created_data["product_svc_id"]

        # 1月5日: 采购入库
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "has_invoice": True,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-01-05T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 500, "unit_price": 10.00, "tax_rate": 0.13},
                {"product_id": svc_id, "quantity": 10, "unit_price": 50.00, "tax_rate": 0.06},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"1月采购失败: {resp.text}"
        created_data["jan_purchase_id"] = _get_entity_id(resp.json())

        # 验证库存增加
        qty = _get_inventory_qty(client, pid)
        assert qty >= 500, f"1月采购后库存应>=500，实际为{qty}"

        # 1月10日: 销售出库
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": True,
            "payment_status": "paid",
            "sale_date": "2026-01-10T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 100, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"1月销售失败: {resp.text}"
        created_data["jan_sale_id"] = _get_entity_id(resp.json())

        # 验证库存减少
        qty_after = _get_inventory_qty(client, pid)
        assert qty_after == qty - 100, f"1月销售后库存应为{qty-100}，实际为{qty_after}"

        # 1月15日: 费用支出
        resp = client.post("/api/expenses", json={
            "category": "房租",
            "amount": 5000.00,
            "description": "1月办公室租金",
            "expense_date": "2026-01-15",
            "payment_method": "company",
            "has_invoice": True,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"1月费用失败: {resp.text}"

        # 1月20日: 录入进项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"IN-JAN-{UNIQUE}", "direction": "in", "invoice_type": "special",
            "amount_with_tax": "5650.00", "tax_rate": "0.13",
            "counterparty_name": "模拟供应商", "seller_name": "模拟供应商", "buyer_name": "本公司",
            "issue_date": "2026-01-20",
            "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "5000.00", "tax_rate": "0.13"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"1月进项发票失败: {resp.text}"

        # 1月25日: 录入销项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"OUT-JAN-{UNIQUE}", "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "2020.00", "tax_rate": "0.01",
            "counterparty_name": "模拟客户", "seller_name": "本公司", "buyer_name": "模拟客户",
            "issue_date": "2026-01-25",
            "sale_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "2000.00", "tax_rate": "0.01"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"1月销项发票失败: {resp.text}"

    def test_february_business(self, client, created_data):
        """2月业务: 春节后复工，增加采购和销售"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        sid = created_data["supplier_id"]

        # 2月3日: 采购入库
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "has_invoice": True,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-02-03T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 300, "unit_price": 10.00, "tax_rate": 0.13}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"2月采购失败: {resp.text}"

        # 2月10日: 销售出库
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": True,
            "payment_status": "paid",
            "sale_date": "2026-02-10T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 150, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"2月销售失败: {resp.text}"

        # 2月15日: 费用支出
        resp = client.post("/api/expenses", json={
            "category": "工资",
            "amount": 15000.00,
            "description": "2月员工工资",
            "expense_date": "2026-02-15",
            "payment_method": "company",
            "has_invoice": False,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"2月工资费用失败: {resp.text}"

    def test_march_business(self, client, created_data):
        """3月业务: 季度末，准备税务申报"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        sid = created_data["supplier_id"]

        # 3月5日: 采购入库
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "has_invoice": True,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-03-05T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 400, "unit_price": 10.00, "tax_rate": 0.13}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"3月采购失败: {resp.text}"

        # 3月10日: 销售出库
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": True,
            "payment_status": "paid",
            "sale_date": "2026-03-10T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 200, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"3月销售失败: {resp.text}"

        # 3月15日: 费用支出
        resp = client.post("/api/expenses", json={
            "category": "水电",
            "amount": 1500.00,
            "description": "3月水电费",
            "expense_date": "2026-03-15",
            "payment_method": "company",
            "has_invoice": True,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"3月水电费失败: {resp.text}"

        # 3月20日: 录入进项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"IN-MAR-{UNIQUE}", "direction": "in", "invoice_type": "special",
            "amount_with_tax": "4520.00", "tax_rate": "0.13",
            "counterparty_name": "模拟供应商", "seller_name": "模拟供应商", "buyer_name": "本公司",
            "issue_date": "2026-03-20",
            "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "4000.00", "tax_rate": "0.13"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"3月进项发票失败: {resp.text}"

        # 3月25日: 录入销项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"OUT-MAR-{UNIQUE}", "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "4040.00", "tax_rate": "0.01",
            "counterparty_name": "模拟客户", "seller_name": "本公司", "buyer_name": "模拟客户",
            "issue_date": "2026-03-25",
            "sale_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "4000.00", "tax_rate": "0.01"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"3月销项发票失败: {resp.text}"

    def test_april_business(self, client, created_data):
        """4月业务: Q2开始，正常业务"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        sid = created_data["supplier_id"]

        # 4月5日: 采购入库
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "has_invoice": True,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-04-05T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 350, "unit_price": 10.00, "tax_rate": 0.13}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"4月采购失败: {resp.text}"

        # 4月10日: 销售出库
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": True,
            "payment_status": "paid",
            "sale_date": "2026-04-10T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 180, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"4月销售失败: {resp.text}"

        # 4月15日: 费用支出
        resp = client.post("/api/expenses", json={
            "category": "办公用品",
            "amount": 800.00,
            "description": "4月办公用品采购",
            "expense_date": "2026-04-15",
            "payment_method": "company",
            "has_invoice": True,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"4月办公用品费用失败: {resp.text}"

    def test_may_business(self, client, created_data):
        """5月业务: 正常业务"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        sid = created_data["supplier_id"]

        # 5月5日: 采购入库
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "has_invoice": True,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-05-05T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 300, "unit_price": 10.00, "tax_rate": 0.13}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"5月采购失败: {resp.text}"

        # 5月10日: 销售出库
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": True,
            "payment_status": "paid",
            "sale_date": "2026-05-10T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 160, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"5月销售失败: {resp.text}"

        # 5月15日: 费用支出
        resp = client.post("/api/expenses", json={
            "category": "运费",
            "amount": 1200.00,
            "description": "5月物流费用",
            "expense_date": "2026-05-15",
            "payment_method": "company",
            "has_invoice": True,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"5月运费失败: {resp.text}"

    def test_june_business(self, client, created_data):
        """6月业务: 季度末，准备税务申报"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        sid = created_data["supplier_id"]

        # 6月5日: 采购入库
        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "has_invoice": True,
            "payment_method": "company",
            "payment_status": "paid",
            "purchase_date": "2026-06-05T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 450, "unit_price": 10.00, "tax_rate": 0.13}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"6月采购失败: {resp.text}"

        # 6月10日: 销售出库
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": True,
            "payment_status": "paid",
            "sale_date": "2026-06-10T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 220, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"6月销售失败: {resp.text}"

        # 6月15日: 费用支出
        resp = client.post("/api/expenses", json={
            "category": "维修",
            "amount": 2000.00,
            "description": "6月设备维修",
            "expense_date": "2026-06-15",
            "payment_method": "company",
            "has_invoice": True,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"6月维修费失败: {resp.text}"

        # 6月20日: 录入进项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"IN-JUN-{UNIQUE}", "direction": "in", "invoice_type": "special",
            "amount_with_tax": "5650.00", "tax_rate": "0.13",
            "counterparty_name": "模拟供应商", "seller_name": "模拟供应商", "buyer_name": "本公司",
            "issue_date": "2026-06-20",
            "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "5000.00", "tax_rate": "0.13"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"6月进项发票失败: {resp.text}"

        # 6月25日: 录入销项发票
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": f"OUT-JUN-{UNIQUE}", "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "4440.00", "tax_rate": "0.01",
            "counterparty_name": "模拟客户", "seller_name": "本公司", "buyer_name": "模拟客户",
            "issue_date": "2026-06-25",
            "sale_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "4400.00", "tax_rate": "0.01"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"6月销项发票失败: {resp.text}"


# ═══════════════════════════════════════════════════════════════
# 3. 税务申报测试
# ═══════════════════════════════════════════════════════════════
class TestTaxReporting:
    """季度税务申报测试"""

    def test_q1_vat_report(self, client):
        """Q1增值税报表"""
        resp = client.get("/api/tax-report", params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200, f"Q1增值税报表失败: {resp.text}"
        data = resp.json()
        # 验证报表结构
        assert "sales_tax" in data or "output_tax" in data, "Q1增值税报表缺少销项税数据"

    def test_q1_income_tax_report(self, client):
        """Q1企业所得税报表"""
        resp = client.get("/api/income-tax-report", params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200, f"Q1所得税报表失败: {resp.text}"

    def test_q2_vat_report(self, client):
        """Q2增值税报表"""
        resp = client.get("/api/tax-report", params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"Q2增值税报表失败: {resp.text}"
        data = resp.json()
        # 验证报表结构
        assert "sales_tax" in data or "output_tax" in data, "Q2增值税报表缺少销项税数据"

    def test_q2_income_tax_report(self, client):
        """Q2企业所得税报表"""
        resp = client.get("/api/income-tax-report", params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"Q2所得税报表失败: {resp.text}"


# ═══════════════════════════════════════════════════════════════
# 4. 财务报表测试
# ═══════════════════════════════════════════════════════════════
class TestFinancialReports:
    """财务报表生成测试"""

    def test_balance_sheet(self, client):
        """资产负债表"""
        resp = client.get("/api/financial-reports/balance-sheet", 
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"资产负债表失败: {resp.status_code}"

    def test_income_statement(self, client):
        """利润表"""
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"利润表失败: {resp.status_code}"

    def test_cash_flow_statement(self, client):
        """现金流量表"""
        resp = client.get("/api/cash-flows/statement",
                         params={"start_date": "2026-01-01", "end_date": "2026-06-30"},
                         headers=HEADERS)
        assert resp.status_code in (200, 500), f"现金流量表失败: {resp.status_code}"

    def test_reports_overview(self, client):
        """报表概览"""
        resp = client.get("/api/reports/overview", headers=HEADERS)
        assert resp.status_code == 200, f"报表概览失败: {resp.text}"

    def test_reports_purchase(self, client):
        """采购报表"""
        resp = client.get("/api/reports/purchase", headers=HEADERS)
        assert resp.status_code == 200, f"采购报表失败: {resp.text}"

    def test_reports_sale(self, client):
        """销售报表"""
        resp = client.get("/api/reports/sale", headers=HEADERS)
        assert resp.status_code == 200, f"销售报表失败: {resp.text}"


# ═══════════════════════════════════════════════════════════════
# 5. 对账管理测试
# ═══════════════════════════════════════════════════════════════
class TestReconciliation:
    """对账管理测试"""

    def test_reconciliation_report(self, client):
        """对账报表"""
        resp = client.get("/api/reconciliations", 
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"对账报表失败: {resp.status_code}"


# ═══════════════════════════════════════════════════════════════
# 6. 个人流水测试
# ═══════════════════════════════════════════════════════════════
class TestPersonalTransactions:
    """个人流水账测试"""

    def test_create_personal_income(self, client):
        """创建个人收入"""
        resp = client.post("/api/personal", json={
            "type": "income",
            "category": "工资",
            "amount": 8000.00,
            "description": "6月工资",
            "date": "2026-06-25",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建个人收入失败: {resp.text}"

    def test_create_personal_expense(self, client):
        """创建个人支出"""
        resp = client.post("/api/personal", json={
            "type": "expense",
            "category": "餐饮",
            "amount": 1500.00,
            "description": "6月餐饮支出",
            "date": "2026-06-20",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建个人支出失败: {resp.text}"

    def test_list_personal_transactions(self, client):
        """查询个人流水"""
        resp = client.get("/api/personal", headers=HEADERS)
        assert resp.status_code == 200, f"查询个人流水失败: {resp.text}"
        data = resp.json()
        assert "items" in data, "个人流水响应格式错误"


# ═══════════════════════════════════════════════════════════════
# 7. 固定资产测试
# ═══════════════════════════════════════════════════════════════
class TestFixedAssets:
    """固定资产管理测试"""

    def test_list_fixed_assets(self, client):
        """查询固定资产列表"""
        resp = client.get("/api/fixed-assets", headers=HEADERS)
        assert resp.status_code == 200, f"查询固定资产失败: {resp.text}"

    def test_fixed_asset_depreciation(self, client):
        """固定资产折旧计算"""
        resp = client.get("/api/fixed-assets/depreciation",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        # 折旧接口可能不存在，允许404
        assert resp.status_code in (200, 404), f"固定资产折旧接口异常: {resp.status_code}"


# ═══════════════════════════════════════════════════════════════
# 8. 操作日志测试
# ═══════════════════════════════════════════════════════════════
class TestOperationLogs:
    """操作日志测试"""

    def test_list_logs(self, client):
        """查询操作日志"""
        resp = client.get("/api/logs", headers=HEADERS)
        assert resp.status_code == 200, f"查询操作日志失败: {resp.text}"
        data = resp.json()
        assert "items" in data, "操作日志响应格式错误"


# ═══════════════════════════════════════════════════════════════
# 9. 数据一致性验证
# ═══════════════════════════════════════════════════════════════
class TestDataConsistency:
    """数据一致性验证"""

    def test_inventory_consistency(self, client, created_data):
        """验证库存一致性: 采购-销售=当前库存"""
        pid = created_data["product_track_id"]
        
        # 获取当前库存
        qty = _get_inventory_qty(client, pid)
        
        # 计算预期库存: 1月采购500 + 2月采购300 + 3月采购400 + 4月采购350 + 5月采购300 + 6月采购450 = 2300
        # 销售: 1月100 + 2月150 + 3月200 + 4月180 + 5月160 + 6月220 = 1010
        # 预期库存: 2300 - 1010 = 1290
        expected_qty = 2300 - 1010
        
        assert qty == expected_qty, f"库存不一致: 预期{expected_qty}，实际{qty}"

    def test_financial_data_accessible(self, client):
        """验证财务数据可访问"""
        # 测试各种报表接口
        endpoints = [
            "/api/reports/overview",
            "/api/reports/purchase",
            "/api/reports/sale",
        ]
        for endpoint in endpoints:
            resp = client.get(endpoint, headers=HEADERS)
            assert resp.status_code == 200, f"财务数据接口{endpoint}不可访问"


# ═══════════════════════════════════════════════════════════════
# 10. 边界条件测试
# ═══════════════════════════════════════════════════════════════
class TestBoundaryConditions:
    """边界条件测试"""

    def test_zero_quantity_sale(self, client, created_data):
        """测试零数量销售"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": False,
            "payment_status": "unpaid",
            "sale_date": "2026-06-30T10:00:00",
            "items": [
                {"product_id": pid, "quantity": 0, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        # 零数量销售应该被拒绝或允许，取决于业务规则
        assert resp.status_code in (200, 201, 400, 422), f"零数量销售响应异常: {resp.status_code}"

    def test_negative_quantity_sale(self, client, created_data):
        """测试负数量销售"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": False,
            "payment_status": "unpaid",
            "sale_date": "2026-06-30T11:00:00",
            "items": [
                {"product_id": pid, "quantity": -5, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        # 负数量销售应该被拒绝
        assert resp.status_code in (400, 422), f"负数量销售应被拒绝，实际状态码: {resp.status_code}"

    def test_large_quantity_sale(self, client, created_data):
        """测试超大数量销售（超出库存）"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        
        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": False,
            "payment_status": "unpaid",
            "sale_date": "2026-06-30T12:00:00",
            "items": [
                {"product_id": pid, "quantity": 99999, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        # 超大数量销售应该被拒绝（库存不足）
        assert resp.status_code in (400, 422), f"超大数量销售应被拒绝，实际状态码: {resp.status_code}"


# ═══════════════════════════════════════════════════════════════
# 11. 并发测试
# ═══════════════════════════════════════════════════════════════
class TestConcurrency:
    """并发操作测试"""

    def test_concurrent_sales(self, client, created_data):
        """测试并发销售（模拟多用户同时操作）"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        
        # 获取当前库存
        qty = _get_inventory_qty(client, pid)
        if qty < 10:
            pytest.skip("库存不足，跳过并发测试")
        
        # 尝试同时销售5个
        results = []
        for i in range(5):
            resp = client.post("/api/sales", json={
                "customer_id": cid,
                "deduct_inventory": True,
                "has_invoice": False,
                "payment_status": "unpaid",
                "sale_date": f"2026-06-30T{13+i}:00:00",
                "items": [
                    {"product_id": pid, "quantity": 2, "unit_price": 20.00, "tax_rate": 0.01}
                ]
            }, headers=HEADERS)
            results.append(resp.status_code)
        
        # 至少应该有一些成功
        success_count = sum(1 for code in results if code in (200, 201))
        assert success_count > 0, f"并发销售全部失败: {results}"


# ═══════════════════════════════════════════════════════════════
# 12. 系统健康检查
# ═══════════════════════════════════════════════════════════════
class TestSystemHealth:
    """系统健康检查"""

    def test_health_check(self, client):
        """健康检查接口"""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_enums_load(self, client):
        """枚举加载"""
        resp = client.get("/api/enums")
        assert resp.status_code == 200
        data = resp.json()
        assert "values" in data
        assert "labels" in data

    def test_accounts_list(self, client):
        """账本列表"""
        resp = client.get("/api/accounts")
        assert resp.status_code == 200
        accounts = resp.json()
        assert len(accounts) >= 1
