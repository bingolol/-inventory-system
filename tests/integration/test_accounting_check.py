"""集成测试：会计准则检查 (routers/accounting_check.py)"""
import pytest

HEADERS = {"X-Account-ID": "1", "X-Operator": "test"}


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


@pytest.mark.golden
class TestCheckVat:
    def test_vat_general(self, client):
        resp = client.get("/api/accounting/vat?total_revenue=100000&taxpayer_type=general&input_tax=3000&output_tax=13000", headers=HEADERS)
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
