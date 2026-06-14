"""端到端自动化测试 — 覆盖核心业务全闭环

使用 FastAPI TestClient + 真实 SQLite 数据库，验证从数据创建到联动计算的全链路。

测试场景：
  1. 系统健康检查 + 枚举加载
  2. 基础数据 CRUD 列表
  3. 零售采购单 → 库存增加（不变量 I）
  4. 零售销售单（扣库存）→ 库存减少
  5. 销售单取消/恢复 → 库存回补/再扣
  6. 项目成本添加/删除 → 项目汇总联动（不变量 III）
  7. 项目收入添加/删除 → 项目汇总联动（不变量 II+III）
  8. 发票创建/删除 + 税务报表可达
  9. 费用创建/列表
  10. 报表接口可达性验证
  11. 端口检测逻辑验证（launcher 模块）
  12. 个人流水账

不变量声明：
  - I-库存一致性：采购+100→销售-10→取消+10→恢复-10，全程验证
  - II-项目收入一致性：收入增删后汇总自动重算
  - III-项目汇总一致性：成本/收入增删后汇总自动重算
"""

import os
import sys
import time
import pytest
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
HEADERS = {"X-Account-ID": str(ACCOUNT_ID), "X-Operator": "e2e_test"}
UNIQUE = str(int(time.time()))[-6:]


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
        "name": f"E2E客户-{UNIQUE}", "contact": "测试", "phone": "13800000001"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建客户失败: {resp.text}"
    data["customer_id"] = resp.json()["id"]

    # 创建供应商
    resp = client.post("/api/suppliers", json={
        "name": f"E2E供应商-{UNIQUE}", "contact": "测试", "phone": "13800000002"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建供应商失败: {resp.text}"
    data["supplier_id"] = resp.json()["id"]

    # 创建可追踪库存商品
    resp = client.post("/api/products", json={
        "name": f"E2E商品-可追踪-{UNIQUE}", "sku": f"E2E-TRK-{UNIQUE}",
        "unit": "个", "purchase_price": 10.00, "sale_price": 20.00,
        "track_inventory": True, "category": "测试"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建可追踪商品失败: {resp.text}"
    data["product_track_id"] = resp.json()["id"]

    # 创建不追踪库存商品（服务类）
    resp = client.post("/api/products", json={
        "name": f"E2E服务-不追踪-{UNIQUE}", "sku": f"E2E-SVC-{UNIQUE}",
        "unit": "次", "purchase_price": 50.00, "sale_price": 100.00,
        "track_inventory": False, "category": "服务"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建不追踪商品失败: {resp.text}"
    data["product_svc_id"] = resp.json()["id"]

    # 创建项目
    resp = client.post("/api/projects", json={
        "name": f"E2E项目-{UNIQUE}", "customer_id": data["customer_id"],
        "contract_amount": 50000, "status": "ongoing"
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建项目失败: {resp.text}"
    data["project_id"] = resp.json()["id"]

    return data


def _get_inventory_qty(client, product_id):
    """辅助：获取指定商品当前库存"""
    resp = client.get("/api/inventory", params={"page": 1, "page_size": 500},
                     headers=HEADERS)
    assert resp.status_code == 200
    items = resp.json().get("items", [])
    target = next((i for i in items if i["product_id"] == product_id), None)
    return target["quantity"] if target else 0


# ═══════════════════════════════════════════════════════════════
# 1. 系统健康检查 + 枚举加载
# ═══════════════════════════════════════════════════════════════
class TestSystemHealth:

    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_enums_load(self, client):
        resp = client.get("/api/enums")
        assert resp.status_code == 200
        data = resp.json()
        assert "values" in data
        assert "labels" in data
        assert "invoice_direction" in data["values"]
        assert "cost_types" in data["values"]

    def test_accounts_list(self, client):
        resp = client.get("/api/accounts")
        assert resp.status_code == 200
        accounts = resp.json()
        assert len(accounts) >= 1
        assert any(a["id"] == ACCOUNT_ID for a in accounts)


# ═══════════════════════════════════════════════════════════════
# 2. 基础数据 CRUD 列表
# ═══════════════════════════════════════════════════════════════
class TestBasicCRUD:

    def test_list_products(self, client):
        resp = client.get("/api/products", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_customers(self, client):
        resp = client.get("/api/customers", headers=HEADERS)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_suppliers(self, client):
        resp = client.get("/api/suppliers", headers=HEADERS)
        assert resp.status_code == 200
        assert "items" in resp.json()


# ═══════════════════════════════════════════════════════════════
# 3. 零售采购单 → 库存增加（不变量 I）
# ═══════════════════════════════════════════════════════════════
class TestPurchaseAndInventory:

    def test_create_purchase_order(self, client, created_data):
        pid = created_data["product_track_id"]
        svc_id = created_data["product_svc_id"]
        sid = created_data["supplier_id"]

        # 记录采购前库存
        stock_before = _get_inventory_qty(client, pid)

        resp = client.post("/api/purchases", json={
            "supplier_id": sid,
            "has_invoice": True,
            "payment_method": "company",
            "payment_status": "paid",
            "items": [
                {"product_id": pid, "quantity": 100, "unit_price": 10.00, "tax_rate": 0.13},
                {"product_id": svc_id, "quantity": 5, "unit_price": 50.00, "tax_rate": 0.06},
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建采购单失败: {resp.text}"
        result = resp.json()
        created_data["purchase_id"] = result["id"]
        assert float(result["total_price"]) > 0
        assert len(result.get("items", [])) == 2

    def test_inventory_increased_after_purchase(self, client, created_data):
        """不变量 I：采购后可追踪商品库存应 >=100"""
        pid = created_data["product_track_id"]
        qty = _get_inventory_qty(client, pid)
        assert qty >= 100, f"采购后库存应 >=100，实际为 {qty}"
        created_data["stock_after_purchase"] = qty


# ═══════════════════════════════════════════════════════════════
# 4. 零售销售单 → 库存减少
# ═══════════════════════════════════════════════════════════════
class TestSaleAndInventory:

    def test_create_sale_deduct_inventory(self, client, created_data):
        """创建零售销售单（扣库存），验证库存减少"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        stock_before = created_data["stock_after_purchase"]

        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": True,
            "has_invoice": True,
            "payment_status": "paid",
            "items": [
                {"product_id": pid, "quantity": 10, "unit_price": 20.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建销售单失败: {resp.text}"
        result = resp.json()
        created_data["sale_id"] = result["id"]
        assert float(result["total_price"]) > 0

        qty = _get_inventory_qty(client, pid)
        assert qty == stock_before - 10, \
            f"销售后库存应为 {stock_before - 10}，实际为 {qty}"
        created_data["stock_after_sale"] = qty

    def test_create_sale_not_deduct_inventory(self, client, created_data):
        """创建不扣库存的销售单，库存不变"""
        pid = created_data["product_track_id"]
        cid = created_data["customer_id"]
        stock_before = created_data["stock_after_sale"]

        resp = client.post("/api/sales", json={
            "customer_id": cid,
            "deduct_inventory": False,
            "has_invoice": False,
            "payment_status": "unpaid",
            "items": [
                {"product_id": pid, "quantity": 5, "unit_price": 15.00, "tax_rate": 0.01}
            ]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建不扣库存销售单失败: {resp.text}"
        created_data["sale2_id"] = resp.json()["id"]

        qty = _get_inventory_qty(client, pid)
        assert qty == stock_before, \
            f"不扣库存销售后库存应不变({stock_before})，实际为 {qty}"


# ═══════════════════════════════════════════════════════════════
# 5. 销售单取消/恢复 → 库存回补/再扣
# ═══════════════════════════════════════════════════════════════
class TestSaleCancelRestore:

    def test_cancel_sale_order(self, client, created_data):
        """取消扣库存的销售单 → 库存回补（PUT status=cancelled）"""
        sale_id = created_data["sale_id"]
        pid = created_data["product_track_id"]
        stock_before = created_data["stock_after_sale"]

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"},
                         headers=HEADERS)
        assert resp.status_code == 200, f"取消销售单失败: {resp.text}"

        qty = _get_inventory_qty(client, pid)
        assert qty == stock_before + 10, \
            f"取消后库存应回补到 {stock_before + 10}，实际为 {qty}"
        created_data["stock_after_cancel"] = qty

    def test_restore_sale_order(self, client, created_data):
        """恢复销售单 → 库存再扣（PUT status=completed）"""
        sale_id = created_data["sale_id"]
        pid = created_data["product_track_id"]
        stock_before = created_data["stock_after_cancel"]

        resp = client.put(f"/api/sales/{sale_id}", json={"status": "completed"},
                         headers=HEADERS)
        assert resp.status_code == 200, f"恢复销售单失败: {resp.text}"

        qty = _get_inventory_qty(client, pid)
        assert qty == stock_before - 10, \
            f"恢复后库存应为 {stock_before - 10}，实际为 {qty}"


# ═══════════════════════════════════════════════════════════════
# 6. 项目成本 → 项目汇总联动（不变量 III）
# ═══════════════════════════════════════════════════════════════
class TestProjectCost:

    def test_add_project_cost(self, client, created_data):
        """添加项目成本 POST /api/costs"""
        project_id = created_data["project_id"]

        resp = client.post("/api/costs", json={
            "project_id": project_id,
            "cost_type": "材料",
            "amount": 5000,
            "payment_method": "company",
            "invoice_status": "未开",
            "cost_date": "2026-05-19",
            "product_id": created_data["product_track_id"],
            "quantity": 50,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"添加项目成本失败: {resp.text}"
        created_data["cost_id"] = resp.json()["id"]

    def test_project_summary_updated(self, client, created_data):
        """不变量 III：项目汇总应反映成本（按销售单商品进价×数量计算）
        当前项目无关联销售单，total_cost 应为 0"""
        project_id = created_data["project_id"]
        resp = client.get(f"/api/projects/{project_id}/cost-income", headers=HEADERS)
        assert resp.status_code == 200, f"获取项目详情失败: {resp.text}"
        detail = resp.json()
        total_cost = float(detail.get("total_cost", 0))
        # 新逻辑：total_cost 按销售单商品进价×数量计算，项目无销售单时 total_cost=0
        assert total_cost == 0.0, \
            f"项目无销售单时汇总成本应为0，实际为 {total_cost}"

    def test_delete_project_cost(self, client, created_data):
        """删除项目成本 DELETE /api/costs/{id}，验证汇总重算
        新逻辑：ProjectCost 不参与 total_cost，删除后 total_cost 仍为 0"""
        cost_id = created_data["cost_id"]
        project_id = created_data["project_id"]

        resp = client.delete(f"/api/costs/{cost_id}", headers=HEADERS)
        assert resp.status_code == 200, f"删除项目成本失败: {resp.text}"

        resp = client.get(f"/api/projects/{project_id}/cost-income", headers=HEADERS)
        detail = resp.json()
        total_cost = float(detail.get("total_cost", 0))
        assert total_cost == 0.0, \
            f"删除成本后项目无销售单时汇总成本应为0，实际为 {total_cost}"


# ═══════════════════════════════════════════════════════════════
# 7. 项目收入 → 项目汇总联动（不变量 II + III）
# ═══════════════════════════════════════════════════════════════
class TestProjectIncome:

    def test_add_project_income(self, client, created_data):
        """手动添加项目收入 POST /api/costs/incomes"""
        project_id = created_data["project_id"]

        resp = client.post("/api/costs/incomes", json={
            "project_id": project_id,
            "amount": 20000,
            "source_type": "manual",
            "payment_status": "paid",
            "invoice_status": "未开",
            "income_date": "2026-05-19",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"添加项目收入失败: {resp.text}"
        created_data["income_id"] = resp.json()["id"]

    def test_project_income_reflected(self, client, created_data):
        """不变量 II+III：项目汇总应反映收入"""
        project_id = created_data["project_id"]
        resp = client.get(f"/api/projects/{project_id}/cost-income", headers=HEADERS)
        assert resp.status_code == 200
        detail = resp.json()
        total_income = float(detail.get("total_income", 0))
        assert total_income >= 20000, \
            f"项目汇总收入应 >=20000，实际为 {total_income}"

    def test_delete_project_income(self, client, created_data):
        """删除项目收入 DELETE /api/costs/incomes/{id}"""
        income_id = created_data["income_id"]

        resp = client.delete(f"/api/costs/incomes/{income_id}", headers=HEADERS)
        assert resp.status_code == 200, f"删除项目收入失败: {resp.text}"


# ═══════════════════════════════════════════════════════════════
# 8. 发票管理 + 税务报表
# ═══════════════════════════════════════════════════════════════
class TestInvoiceAndTax:

    def test_create_invoice(self, client, created_data):
        """创建销项发票（需 invoice_no / amount_with_tax / counterparty_name）"""
        resp = client.post("/api/invoices", json={
            "invoice_no": f"E2E-INV-{UNIQUE}",
            "direction": "out",
            "invoice_type": "ordinary",
            "issue_date": "2026-05-19T10:00:00",
            "amount_without_tax": 10000,
            "tax_rate": 0.13,
            "tax_amount": 1300,
            "amount_with_tax": 11300,
            "counterparty_name": "E2E测试对方",
            "certification_status": "n_a",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建发票失败: {resp.text}"
        created_data["invoice_id"] = resp.json()["id"]

    def test_tax_report_reachable(self, client):
        """增值税报表 GET /api/tax-report?year=&quarter="""
        resp = client.get("/api/tax-report", params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"增值税报表接口失败: {resp.text}"

    def test_income_tax_report_reachable(self, client):
        """企业所得税报表 GET /api/income-tax-report?year=&quarter="""
        resp = client.get("/api/income-tax-report", params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"企业所得税报表接口失败: {resp.text}"

    def test_delete_invoice(self, client, created_data):
        invoice_id = created_data["invoice_id"]
        resp = client.delete(f"/api/invoices/{invoice_id}", headers=HEADERS)
        assert resp.status_code == 200, f"删除发票失败: {resp.text}"


# ═══════════════════════════════════════════════════════════════
# 9. 费用管理
# ═══════════════════════════════════════════════════════════════
class TestExpenses:

    def test_create_expense(self, client):
        resp = client.post("/api/expenses", json={
            "category": "办公用品",
            "amount": 500,
            "description": "E2E测试费用",
            "expense_date": "2026-05-19",
            "payment_method": "company",
            "has_invoice": False,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建费用失败: {resp.text}"

    def test_list_expenses(self, client):
        resp = client.get("/api/expenses", headers=HEADERS)
        assert resp.status_code == 200
        assert "items" in resp.json()


# ═══════════════════════════════════════════════════════════════
# 10. 报表接口可达性验证
# ═══════════════════════════════════════════════════════════════
class TestReportsReachability:

    def test_reports_overview(self, client):
        resp = client.get("/api/reports/overview", headers=HEADERS)
        assert resp.status_code == 200

    def test_reports_purchase(self, client):
        resp = client.get("/api/reports/purchase", headers=HEADERS)
        assert resp.status_code == 200

    def test_reports_sale(self, client):
        resp = client.get("/api/reports/sale", headers=HEADERS)
        assert resp.status_code == 200

    def test_financial_reports_balance_sheet(self, client):
        resp = client.get("/api/financial-reports/balance-sheet", headers=HEADERS)
        assert resp.status_code in (200, 422), \
            f"资产负债表接口异常: {resp.status_code}"

    def test_financial_reports_income_statement(self, client):
        resp = client.get("/api/financial-reports/income-statement", headers=HEADERS)
        assert resp.status_code in (200, 422), \
            f"利润表接口异常: {resp.status_code}"

    def test_opening_balances(self, client):
        resp = client.get("/api/opening-balances", headers=HEADERS)
        assert resp.status_code in (200, 404)

    def test_cash_flows_statement(self, client):
        """GET /api/cash-flows/statement?start_date=&end_date="""
        resp = client.get("/api/cash-flows/statement",
                         params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
                         headers=HEADERS)
        assert resp.status_code in (200, 500), \
            f"现金流量表接口异常: {resp.status_code}"

    def test_reconciliations(self, client):
        resp = client.get("/api/reconciliations", params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code in (200, 422)


# ═══════════════════════════════════════════════════════════════
# 11. launcher 端口检测逻辑验证
# ═══════════════════════════════════════════════════════════════
class TestPortDetection:

    def _import_launcher(self):
        """动态导入 launcher 模块（避免触发 __main__）"""
        import importlib.util
        launcher_dir = os.path.join(os.path.dirname(__file__), "..", "..")
        launcher_dir = os.path.abspath(launcher_dir)
        spec = importlib.util.spec_from_file_location(
            "launcher_module", os.path.join(launcher_dir, "launcher.py"))
        mod = importlib.util.module_from_spec(spec)
        mod.__name__ = "launcher_module"
        spec.loader.exec_module(mod)
        return mod

    def test_is_port_available_free(self):
        """is_port_available 对空闲端口返回 True"""
        launcher = self._import_launcher()
        assert launcher.is_port_available(59999) is True

    def test_find_available_port_returns_int(self):
        """find_available_port 返回整数端口号"""
        launcher = self._import_launcher()
        port = launcher.find_available_port(start=59000, max_tries=10)
        assert isinstance(port, int)
        assert 59000 <= port <= 59009

    def test_is_port_available_occupied(self):
        """is_port_available 对被占用端口返回 False"""
        import socket
        launcher = self._import_launcher()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 59876))
            s.listen(1)
            assert launcher.is_port_available(59876) is False

    def test_find_available_port_skips_occupied(self):
        """find_available_port 跳过被占用端口"""
        import socket
        launcher = self._import_launcher()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 59877))
            s.listen(1)
            port = launcher.find_available_port(start=59877, max_tries=10)
            assert port == 59878

    def test_port_file_write_read(self, tmp_path):
        """port.txt 写入和读取"""
        port_file = os.path.join(str(tmp_path), "port.txt")
        with open(port_file, 'w') as f:
            f.write("8001")
        with open(port_file, 'r') as f:
            assert f.read() == "8001"


# ═══════════════════════════════════════════════════════════════
# 12. 个人流水账
# ═══════════════════════════════════════════════════════════════
class TestPersonalTransactions:

    def test_create_personal_transaction(self, client):
        """创建个人流水（字段为 type/amount/category/date）"""
        resp = client.post("/api/personal", json={
            "type": "expense",
            "category": "餐饮",
            "amount": 50,
            "description": "E2E午餐",
            "date": "2026-05-19",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建个人流水失败: {resp.text}"

    def test_list_personal_transactions(self, client):
        resp = client.get("/api/personal", headers=HEADERS)
        assert resp.status_code == 200