"""集成测试：小企业会计准则财务报表接口"""
from decimal import Decimal
import xlrd
from io import BytesIO

HEADERS = {"X-Account-ID": "1", "X-Operator": "test"}


def _find_line(data, sheet, line_no):
    for item in data[sheet]:
        if item["line_no"] == line_no:
            return item
    return None


class TestCWBBXQYKJZZ:
    def test_get_cwbb_data(self, client):
        resp = client.get("/api/financial-reports/cwbb-xqykjzz?report_type=monthly&date=2026-06-30", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_type"] == "monthly"
        assert len(data["balance_sheet"]) == 53
        assert len(data["income_statement"]) == 32
        assert len(data["cash_flow_statement"]) == 22

    def test_export_cwbb_monthly_xls(self, client):
        resp = client.get("/api/export/cwbb-xqykjzz?report_type=monthly&date=2026-06-30", headers=HEADERS)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.ms-excel"
        book = xlrd.open_workbook(file_contents=resp.content)
        assert "资产负债表" in book.sheet_names()
        assert "利润表_月季报" in book.sheet_names()
        assert "现金流量表_月季报" in book.sheet_names()

    def test_export_cwbb_annual_xls(self, client):
        resp = client.get("/api/export/cwbb-xqykjzz?report_type=annual&date=2026-12-31", headers=HEADERS)
        assert resp.status_code == 200
        book = xlrd.open_workbook(file_contents=resp.content)
        assert "利润表_年" in book.sheet_names()
        assert "现金流量表_年" in book.sheet_names()

    def test_invalid_report_type(self, client):
        resp = client.get("/api/financial-reports/cwbb-xqykjzz?report_type=weekly&date=2026-06-30", headers=HEADERS)
        assert resp.status_code == 422

    def test_cash_flow_classification(self, client):
        """验证收付款自动分类到现金流量表项目"""
        import uuid as _uuid
        tag = _uuid.uuid4().hex[:8]
        bank_no = f"CF-{tag}"
        ids_to_clean = {}

        def _cf_amount(data, line_no):
            line = _find_line(data, "cash_flow_statement", line_no)
            return line["period_amount"] if line else 0.0

        try:
            # 先取基线，避免其他测试残留数据影响绝对值断言
            resp_before = client.get("/api/financial-reports/cwbb-xqykjzz?report_type=monthly&date=2026-06-30", headers=HEADERS)
            assert resp_before.status_code == 200
            before = resp_before.json()
            cf01_base = _cf_amount(before, 1)
            cf04_base = _cf_amount(before, 4)
            cf06_base = _cf_amount(before, 6)

            # 创建银行账户
            bank_resp = client.post("/api/bank-accounts", json={
                "bank_name": "测试银行", "account_number": bank_no, "description": ""
            }, headers=HEADERS)
            assert bank_resp.status_code in (200, 201)
            bank_account_id = bank_resp.json()["entity"]["id"]
            ids_to_clean["bank_account"] = bank_account_id

            # 销售收款 -> CF01
            receipt_resp = client.post("/api/receipts", json={
                "receipt_type": "sale", "related_entity_type": "sale_order", "related_entity_id": 1,
                "amount": 1000, "receipt_method": "company", "receipt_date": "2026-06-15",
                "bank_account_id": bank_account_id, "description": "销售收款"
            }, headers=HEADERS)
            assert receipt_resp.status_code in (200, 201)
            ids_to_clean["receipt"] = receipt_resp.json()["entity"]["entity_id"]

            # 费用付款 -> CF06
            payment_resp = client.post("/api/payments", json={
                "payment_type": "expense", "related_entity_type": "expense", "related_entity_id": 1,
                "amount": 200, "payment_method": "company", "payment_date": "2026-06-16",
                "bank_account_id": bank_account_id, "description": "办公费"
            }, headers=HEADERS)
            assert payment_resp.status_code in (200, 201)
            ids_to_clean["payment_expense"] = payment_resp.json()["entity"]["entity_id"]

            # 工资付款 -> CF04
            salary_resp = client.post("/api/payments", json={
                "payment_type": "salary", "related_entity_type": "expense", "related_entity_id": 1,
                "amount": 500, "payment_method": "company", "payment_date": "2026-06-17",
                "bank_account_id": bank_account_id, "description": "工资", "withholding_tax_amount": 0
            }, headers=HEADERS)
            assert salary_resp.status_code in (200, 201)
            ids_to_clean["payment_salary"] = salary_resp.json()["entity"]["entity_id"]

            resp = client.get("/api/financial-reports/cwbb-xqykjzz?report_type=monthly&date=2026-06-30", headers=HEADERS)
            assert resp.status_code == 200
            data = resp.json()

            cf01 = _cf_amount(data, 1)
            cf04 = _cf_amount(data, 4)
            cf06 = _cf_amount(data, 6)
            assert cf01 - cf01_base == 1000.0, f"CF01 增量应为 1000, 实际 {cf01 - cf01_base}"
            assert cf04 - cf04_base == 500.0, f"CF04 增量应为 500, 实际 {cf04 - cf04_base}"
            assert cf06 - cf06_base == 200.0, f"CF06 增量应为 200, 实际 {cf06 - cf06_base}"
        finally:
            # 清理本测试创建的数据，避免持久化测试库累积
            if "receipt" in ids_to_clean:
                client.delete(f"/api/receipts/{ids_to_clean['receipt']}", headers=HEADERS)
            if "payment_expense" in ids_to_clean:
                client.delete(f"/api/payments/{ids_to_clean['payment_expense']}", headers=HEADERS)
            if "payment_salary" in ids_to_clean:
                client.delete(f"/api/payments/{ids_to_clean['payment_salary']}", headers=HEADERS)
            if "bank_account" in ids_to_clean:
                client.delete(f"/api/bank-accounts/{ids_to_clean['bank_account']}", headers=HEADERS)

    # 附加税已迁移至 SurchargeDeclaration L1 录入，不再由 TaxAccrualEngine 自动计提
