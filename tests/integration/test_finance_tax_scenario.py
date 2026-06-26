"""财务税务实际场景测试 — 模拟一个完整季度的记账与申报链路

场景:小规模纳税人 2026 Q2
  1. 采购带进项专票 → 认证 → 进项税额
  2. 销售开销项发票 → 销项税额
  3. 季度增值税申报 → 销项-进项抵扣,应纳税额正确
  4. 所得税预缴计算 → 小微优惠(利润≤300万,实际税负5%)
  5. 会计预检查 → 发票金额/增值税/所得税 校验闭环
  6. 资产负债表平衡校验
"""
import pytest
from datetime import datetime
from decimal import Decimal
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, init_db
from models import Account, Invoice
from test_helpers import ensure_test_product


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _uniq(prefix):
    return f"{prefix}-{datetime.now().strftime('%H%M%S%f')}"


def _account_id():
    db = SessionLocal()
    try:
        acc = db.query(Account).first()
        return acc.id if acc else 1
    finally:
        db.close()


def _account_taxpayer_type(aid):
    db = SessionLocal()
    try:
        acc = db.query(Account).filter(Account.id == aid).first()
        return acc.taxpayer_type if acc else "small_scale"
    finally:
        db.close()


@pytest.mark.integration
class TestFullTaxScenario:
    """完整季度记账+申报场景"""

    def test_01_create_input_special_invoice(self, client):
        """采购环节:录入进项专票(13%)→ 待认证"""
        aid = _account_id()
        pid = ensure_test_product(aid)
        r = client.post("/api/invoices/quick", json={
            "invoice_no": _uniq("IN-SPEC"), "direction": "in", "invoice_type": "special",
            "amount_with_tax": "11300.00", "tax_rate": "0.13",
            "counterparty_name": "供应商甲", "seller_name": "供应商甲", "buyer_name": "本公司",
            "issue_date": "2026-04-15",
            "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "10000.00", "tax_rate": "0.13"}],
        }, headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert float(data["amount_without_tax"]) == 10000.00
        assert float(data["tax_amount"]) == 1300.00
        assert data["certification_status"] == "n_a"

    def test_02_certify_input_invoice(self, client):
        """认证进项专票 → 可抵扣"""
        aid = _account_id()
        db = SessionLocal()
        try:
            inv = db.query(Invoice).filter(
                Invoice.account_id == aid,
                Invoice.direction == "in",
                Invoice.invoice_type == "special",
            ).order_by(Invoice.id.desc()).first()
            inv_id = inv.id
        finally:
            db.close()
        r = client.post(f"/api/invoices/{inv_id}/certify",
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text

    def test_03_create_output_invoice(self, client):
        """销售环节:开销项发票(1%征收率)→ 销项税额"""
        aid = _account_id()
        pid = ensure_test_product(aid)
        r = client.post("/api/invoices/quick", json={
            "invoice_no": _uniq("OUT-ORD"), "direction": "out", "invoice_type": "ordinary",
            "amount_with_tax": "10100.00", "tax_rate": "0.01",
            "counterparty_name": "客户乙", "seller_name": "本公司", "buyer_name": "客户乙",
            "issue_date": "2026-05-20",
            "sale_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "10000.00", "tax_rate": "0.01"}],
        }, headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert float(data["amount_without_tax"]) == 10000.00
        assert float(data["tax_amount"]) == 100.00

    def test_04_quarterly_vat_report(self, client):
        """季度增值税申报 → 销项税额正确汇总"""
        aid = _account_id()
        r = client.get("/api/tax-report?year=2026&quarter=2",
                       headers={"X-Account-ID": str(aid)})
        assert r.status_code == 200, r.text
        report = r.json()
        assert report["year"] == 2026
        assert report["quarter"] == 2
        # 销项税额至少含本场景的 100.00
        assert float(report["output_tax"]) >= 100.00
        # 销项不含税收入至少 10000
        assert float(report["output_total"]) >= 10000.00

    def test_05_vat_check_endpoint_consistent(self, client):
        """会计预检查:增值税计算与引擎一致"""
        r = client.get("/api/accounting/vat?total_revenue=10000&taxpayer_type=small_scale",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        # 小规模减按1%:10000 * 1% = 100
        assert float(data["result"]["tax_payable"]) == 100.00

    def test_06_income_tax_small_micro(self, client):
        """所得税:小微优惠(利润≤300万,实际税负5%)"""
        r = client.get("/api/accounting/income-tax?profit=100000&taxpayer_type=small_micro",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        # 100000 * 25% * 20% = 5000
        assert float(data["result"]["tax_payable"]) == 5000.00
        assert "小型微利" in data["result"]["reduction_item"]

    def test_07_income_tax_over_3m_no_reduction(self, client):
        """所得税:利润>300万 → 法定税率25%,无小微优惠"""
        r = client.get("/api/accounting/income-tax?profit=4000000&taxpayer_type=small_micro",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 200
        data = r.json()
        # 4000000 * 25% = 1000000
        assert float(data["result"]["tax_payable"]) == 1000000.00
        assert "不符合小型微利" in data["result"]["reduction_item"]

    def test_08_invoice_amounts_check_closed_loop(self, client):
        """会计预检查:发票金额三件套闭环(校验通过)"""
        r = client.get("/api/accounting/invoice-amounts?amount_with_tax=113&tax_rate=0.13",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        assert float(data["result"]["amount_without_tax"]) == 100.00
        assert float(data["result"]["tax_amount"]) == 13.00

    def test_09_depreciation_straight_line(self, client):
        """会计预检查:直线法折旧(原值10000,残值5%,60月)"""
        r = client.get("/api/accounting/depreciation?method=直线法&original_value=10000"
                       "&salvage_rate=0.05&useful_life=60&months_used=12",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 200
        data = r.json()
        assert data["valid"] is True
        # 月折旧 = 10000 * (1-0.05) / 60 = 158.33(quantize 到2位)
        assert float(data["result"]["monthly_depreciation"]) == 158.33
        # 累计12月 = 158.33 * 12 = 1899.96(每月已 quantize,故非 1900)
        assert float(data["result"]["accumulated_depreciation"]) == 1899.96

    def test_10_balance_sheet_check(self, client):
        """会计预检查:资产负债表平衡校验接口可达"""
        r = client.get("/api/accounting/balance-sheet?date=2026-06-30",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 200
        data = r.json()
        assert "valid" in data

    def test_11_income_tax_report_reachable(self, client):
        """所得税季度报表接口可达"""
        r = client.get("/api/income-tax-report?year=2026&quarter=2",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 200
        report = r.json()
        assert report["year"] == 2026
        assert report["quarter"] == 2


@pytest.mark.integration
class TestAccountingErrorGuidance:
    """会计错误引导闭环 — 实际场景下 AI 拿到结构化报错"""

    def test_invalid_tax_rate_guided(self, client):
        """非法纳税人类型 → 422 + 法规依据 + 计算明细"""
        r = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=invalid",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 422
        err = r.json()["error"]
        assert err["code"] == "VAT_TAXPAYER_TYPE_INVALID"
        assert "STOP_RETRYING" in err["ai_instruction"]
        # 法规依据透传(缺口1修复的核心价值)
        assert "accounting_rule" in err

    def test_negative_profit_guided(self, client):
        """利润为负 → 422 + 引导(不需缴税)"""
        r = client.get("/api/accounting/income-tax?profit=-500&taxpayer_type=small_micro",
                       headers={"X-Account-ID": str(_account_id())})
        assert r.status_code == 422
        err = r.json()["error"]
        assert err["code"] == "INCOME_TAX_PROFIT_NEGATIVE"
        assert "STOP_RETRYING" in err["ai_instruction"]
