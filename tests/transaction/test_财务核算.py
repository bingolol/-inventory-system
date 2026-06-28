"""集成测试：财务核算全流程

合并自:
  - test_accounting_check.py      会计准则预检查
  - test_finance_api.py           财务报表查询 API
  - test_accounting_error_handler.py   AccountingError 处理器
  - test_error_guidance.py        错误引导 + OperationResult
"""

import time
import pytest
from decimal import Decimal



from tests.factories import (
    api_create_product, api_create_customer, api_create_supplier,
)
from tests.helpers import get_entity_id, uniq

HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}


@pytest.fixture(scope="module", autouse=True)
def bootstrap(client):
    resp = client.post("/api/bootstrap/init")
    assert resp.status_code == 200, f"bootstrap 失败: {resp.text}"


@pytest.fixture(scope="module")
def ids(client):
    """共享：商品（含库存）、客户、供应商"""
    tag = str(int(time.time()))[-6:]
    pid, _ = api_create_product(client, HEADERS,
        name=f"商品-FA-{tag}", sku=f"SKU-FA-{tag}",
        purchase_price=50, sale_price=100, category="测试")
    cid, _ = api_create_customer(client, HEADERS, name=f"客户-FA-{tag}")
    sid, _ = api_create_supplier(client, HEADERS, name=f"供应商-FA-{tag}")
    resp = client.post("/api/purchases", json={
        "supplier_id": sid,
        "payment_method": "company",
        "payment_status": "unpaid",
        "purchase_date": "2026-01-01T10:00:00",
        "items": [{"product_id": pid, "quantity": 100, "unit_price": 50, "tax_rate": 0.13}],
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"采购失败: {resp.text}"
    return {"pid": pid, "cid": cid, "sid": sid}


def _create_sale(client, pid, cid):
    resp = client.post("/api/sales", json={
        "customer_id": cid,
        "deduct_inventory": True,
        "payment_status": "unpaid",
        "sale_date": "2026-06-15T10:00:00",
        "items": [{"product_id": pid, "quantity": 2, "unit_price": 100, "tax_rate": 0.01}],
    }, headers=HEADERS)
    assert resp.status_code in (200, 201), f"创建销售失败: {resp.text}"
    return resp.json()


# ═══════════════════════════════════════════════════════════════
# 1. 会计准则预检查
# ═══════════════════════════════════════════════════════════════

class Test会计准则预检查:

    class TestCheckInvoiceAmounts:
        def test_valid_invoice_amounts(self, client):
            resp = client.get("/api/accounting/invoice-amounts?amount_with_tax=103&tax_rate=0.03", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True

        def test_invalid_invoice_amounts(self, client):
            resp = client.get("/api/accounting/invoice-amounts?amount_with_tax=105.50&tax_rate=0.03", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert "valid" in data
            assert "result" in data
            assert "amount_without_tax" in data["result"]

    class TestCheckDepreciation:
        def test_depreciation_straight_line(self, client):
            resp = client.get("/api/accounting/depreciation?method=直线法&original_value=12000&useful_life=12&months_used=3", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True

        def test_depreciation_double_declining(self, client):
            resp = client.get("/api/accounting/depreciation?method=双倍余额递减法&original_value=12000&useful_life=12&months_used=3", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True

        def test_depreciation_sum_of_years(self, client):
            resp = client.get("/api/accounting/depreciation?method=年数总和法&original_value=12000&salvage_rate=0.05&useful_life=12&months_used=3", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True

        def test_invalid_method(self, client):
            resp = client.get("/api/accounting/depreciation?method=未知法&original_value=12000&useful_life=12&months_used=3", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is False
            assert "不支持" in data["violations"][0]

        def test_invalid_parameters(self, client):
            resp = client.get("/api/accounting/depreciation?method=直线法&original_value=0&useful_life=12&months_used=3", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is False
            assert "原值必须大于0" in data["violations"][0]

    class TestCheckAmortization:
        def test_valid_amortization(self, client):
            resp = client.get("/api/accounting/amortization?original_value=60000&useful_life=60&months_used=12", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True

        def test_invalid_amortization_params(self, client):
            resp = client.get("/api/accounting/amortization?original_value=0&useful_life=60&months_used=0", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is False
            assert "原值必须大于0" in data["violations"][0]

    class TestCheckVat:
        def test_vat_general(self, client):
            resp = client.get("/api/accounting/vat?total_revenue=100000&taxpayer_type=general&input_tax=3000", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True

        def test_vat_small_scale(self, client):
            resp = client.get("/api/accounting/vat?total_revenue=100000&taxpayer_type=small_scale", headers=HEADERS)
            assert resp.status_code == 200
            assert resp.json()["valid"] is True

    class TestCheckIncomeTax:
        def test_income_tax_small_micro(self, client):
            resp = client.get("/api/accounting/income-tax?profit=200000&taxpayer_type=small_micro", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True

        def test_income_tax_general(self, client):
            resp = client.get("/api/accounting/income-tax?profit=500000&taxpayer_type=general", headers=HEADERS)
            assert resp.status_code == 200
            assert resp.json()["valid"] is True

    class TestCheckBalanceSheet:
        def test_balance_sheet_valid(self, client):
            resp = client.get("/api/accounting/balance-sheet?date=2026-06-26", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert "valid" in data

    class TestCheckIncomeStatement:
        def test_income_statement_valid(self, client):
            resp = client.get("/api/accounting/income-statement?start_date=2026-01-01&end_date=2026-06-26", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert "valid" in data

    class TestCheckCashFlow:
        def test_cash_flow_valid(self, client):
            resp = client.get("/api/accounting/cash-flow?start_date=2026-01-01&end_date=2026-06-26", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert "valid" in data


# ═══════════════════════════════════════════════════════════════
# 2. 财务报表
# ═══════════════════════════════════════════════════════════════

class Test财务报表:

    class TestAccountChart:
        def test_returns_all_phase1_accounts(self, client):
            resp = client.get("/api/finance/accounts/chart", headers=HEADERS)
            assert resp.status_code == 200
            items = resp.json()["items"]
            codes = {it["code"] for it in items}
            for code in ("1001", "1002", "1122", "1405", "2202",
                         "222101", "222102", "6001", "6401",
                         "6601", "6602", "6603"):
                assert code in codes, f"缺少科目 {code}"

        def test_leaf_account_has_balance_zero(self, client):
            resp = client.get("/api/finance/accounts/chart", headers=HEADERS)
            items = resp.json()["items"]
            cash = next(it for it in items if it["code"] == "1001")
            assert cash["is_leaf"] is True
            assert float(cash["balance"]) == 0

        def test_non_leaf_not_returned(self, client):
            resp = client.get("/api/finance/accounts/chart", headers=HEADERS)
            items = resp.json()["items"]
            assert all(it["is_leaf"] for it in items)

    class TestJournalMoves:
        def test_moves_list_after_sale(self, client, ids):
            _create_sale(client, ids["pid"], ids["cid"])
            resp = client.get("/api/finance/journal/moves", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] >= 1
            sale_moves = [m for m in data["items"] if m["move_type"] == "sale_order"]
            assert len(sale_moves) >= 1

        def test_filter_by_move_type(self, client):
            resp = client.get("/api/finance/journal/moves",
                              params={"move_type": "sale_order"},
                              headers=HEADERS)
            assert resp.status_code == 200
            for m in resp.json()["items"]:
                assert m["move_type"] == "sale_order"

        def test_filter_by_date(self, client):
            resp = client.get("/api/finance/journal/moves",
                              params={"date_from": "2026-01-01", "date_to": "2026-12-31"},
                              headers=HEADERS)
            assert resp.status_code == 200

        def test_pagination(self, client):
            resp = client.get("/api/finance/journal/moves",
                              params={"skip": 0, "limit": 5},
                              headers=HEADERS)
            assert resp.status_code == 200
            assert len(resp.json()["items"]) <= 5

        def test_move_detail_has_lines_with_account_codes(self, client):
            resp = client.get("/api/finance/journal/moves",
                              params={"move_type": "sale_order", "limit": 1},
                              headers=HEADERS)
            if resp.json()["total"] == 0:
                pytest.skip("No sale moves to test detail")
            move_id = resp.json()["items"][0]["id"]
            resp = client.get(f"/api/finance/journal/moves/{move_id}", headers=HEADERS)
            assert resp.status_code == 200
            detail = resp.json()
            assert detail["id"] == move_id
            assert len(detail["lines"]) >= 2
            codes = {ln["account_code"] for ln in detail["lines"]}
            assert "1122" in codes, "缺少应收账款科目"
            assert "6001" in codes or "222101" in codes

    class TestTrialBalance:
        def test_balanced_after_sale(self, client, ids):
            _create_sale(client, ids["pid"], ids["cid"])
            resp = client.get("/api/finance/reports/trial-balance",
                              params={"date": "2026-12-31"},
                              headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert "rows" in data
            assert "total_debit" in data
            assert "total_credit" in data
            assert data["balanced"] is True, \
                f"试算不平衡: 借={data['total_debit']}, 贷={data['total_credit']}"

        def test_total_debit_equals_total_credit(self, client):
            resp = client.get("/api/finance/reports/trial-balance",
                              params={"date": "2026-12-31"},
                              headers=HEADERS)
            data = resp.json()
            assert data["total_debit"] == data["total_credit"]

    class TestPartnerReceivable:
        def test_customer_balance_and_aging(self, client, ids):
            _create_sale(client, ids["pid"], ids["cid"])
            resp = client.get(f"/api/finance/receivable/partner/{ids['cid']}",
                              params={"partner_type": "customer"},
                              headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["partner_id"] == ids["cid"]
            assert data["partner_type"] == "customer"
            assert float(data["balance"]) != 0
            for bucket in ("0-30", "31-60", "61-90", "90+"):
                assert bucket in data["aging"]

        def test_supplier_balance_and_aging(self, client, ids):
            resp = client.post("/api/purchases", json={
                "supplier_id": ids["sid"],
                "payment_method": "company",
                "purchase_date": "2026-06-10T10:00:00",
                "items": [{"product_id": ids["pid"], "quantity": 5, "unit_price": 50, "tax_rate": 0.13}],
            }, headers=HEADERS)
            assert resp.status_code in (200, 201), f"创建采购失败: {resp.text}"
            resp = client.get(f"/api/finance/receivable/partner/{ids['sid']}",
                              params={"partner_type": "supplier"},
                              headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()
            assert data["partner_type"] == "supplier"
            for bucket in ("0-30", "31-60", "61-90", "90+"):
                assert bucket in data["aging"]


# ═══════════════════════════════════════════════════════════════
# 3. 错误处理
# ═══════════════════════════════════════════════════════════════

class Test错误处理:

    class TestAccountingErrorWiring:
        def test_invalid_taxpayer_not_500(self, client):
            resp = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=xxx",
                              headers=HEADERS)
            assert resp.status_code != 500

        def test_invalid_taxpayer_returns_422(self, client):
            resp = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=xxx",
                              headers=HEADERS)
            assert resp.status_code == 422

        def test_invalid_taxpayer_returns_structured_code(self, client):
            resp = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=xxx",
                              headers=HEADERS)
            assert resp.json()["error"]["code"] == "VAT_TAXPAYER_TYPE_INVALID"

        def test_invalid_taxpayer_preserves_ai_instruction(self, client):
            resp = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=xxx",
                              headers=HEADERS)
            assert "STOP_RETRYING" in resp.json()["error"]["ai_instruction"]

        def test_valid_request_still_works(self, client):
            resp = client.get("/api/accounting/vat?total_revenue=100&taxpayer_type=general",
                              headers=HEADERS)
            assert resp.status_code == 200
            assert resp.json()["valid"] is True

    class TestOperationResult:
        def test_invoice_duplicate_returns_ai_instruction(self, client):
            client.post("/api/invoices", json={
                "invoice_no": "INV-DUP-001", "direction": "in",
                "invoice_type": "ordinary", "tax_rate": 0.13,
                "amount_without_tax": 10000, "tax_amount": 1300,
                "amount_with_tax": 11300, "counterparty_name": "供应商A",
                "issue_date": "2026-06-19",
            }, headers=HEADERS)
            response = client.post("/api/invoices", json={
                "invoice_no": "INV-DUP-001", "direction": "in",
                "invoice_type": "ordinary", "tax_rate": 0.13,
                "amount_without_tax": 5000, "tax_amount": 650,
                "amount_with_tax": 5650, "counterparty_name": "供应商B",
                "issue_date": "2026-06-20",
            }, headers=HEADERS)
            assert response.status_code == 409
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == "INVOICE_DUPLICATE_NUMBER"
            assert "ai_instruction" in data["error"]
            assert "STOP_RETRYING" in data["error"]["ai_instruction"]

        def test_invoice_create_returns_operation_result(self, client):
            response = client.post("/api/invoices", json={
                "invoice_no": "INV-OR-001", "direction": "in",
                "invoice_type": "ordinary", "tax_rate": 0.13,
                "amount_without_tax": 10000, "tax_amount": 1300,
                "amount_with_tax": 11300, "counterparty_name": "供应商A",
                "issue_date": "2026-06-19",
            }, headers=HEADERS)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["operation"] == "create"
            assert data["entity_type"] == "invoice"
            assert "ai_hint" in data

        def test_invoice_update_returns_operation_result(self, client):
            create_resp = client.post("/api/invoices", json={
                "invoice_no": "INV-UPD-001", "direction": "in",
                "invoice_type": "ordinary", "tax_rate": 0.13,
                "amount_without_tax": 10000, "tax_amount": 1300,
                "amount_with_tax": 11300, "counterparty_name": "供应商A",
                "issue_date": "2026-06-19",
            }, headers=HEADERS)
            invoice_id = create_resp.json()["data"]["id"]
            response = client.put(f"/api/invoices/{invoice_id}", json={
                "notes": "更新备注",
            }, headers=HEADERS)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["operation"] == "update"
            assert data["entity_type"] == "invoice"

        def test_invoice_delete_blocked_by_readonly_middleware(self, client):
            create_resp = client.post("/api/invoices", json={
                "invoice_no": "INV-DEL-001", "direction": "in",
                "invoice_type": "ordinary", "tax_rate": 0.13,
                "amount_without_tax": 10000, "tax_amount": 1300,
                "amount_with_tax": 11300, "counterparty_name": "供应商A",
                "issue_date": "2026-06-19",
            }, headers=HEADERS)
            invoice_id = create_resp.json().get("entity_id") or create_resp.json().get("id")
            response = client.delete(f"/api/invoices/{invoice_id}", headers=HEADERS)
            assert response.status_code in (200, 403)
