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
        # 创建银行账户
        bank_resp = client.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": "TEST-9999", "description": ""
        }, headers=HEADERS)
        assert bank_resp.status_code in (200, 201)
        bank_account_id = bank_resp.json()["entity"]["id"]

        # 销售收款 -> CF01
        receipt_resp = client.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order", "related_entity_id": 1,
            "amount": 1000, "receipt_method": "company", "receipt_date": "2026-06-15",
            "bank_account_id": bank_account_id, "description": "销售收款"
        }, headers=HEADERS)
        assert receipt_resp.status_code in (200, 201)

        # 费用付款 -> CF06
        payment_resp = client.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense", "related_entity_id": 1,
            "amount": 200, "payment_method": "company", "payment_date": "2026-06-16",
            "bank_account_id": bank_account_id, "description": "办公费"
        }, headers=HEADERS)
        assert payment_resp.status_code in (200, 201)

        # 工资付款 -> CF04
        salary_resp = client.post("/api/payments", json={
            "payment_type": "salary", "related_entity_type": "expense", "related_entity_id": 1,
            "amount": 500, "payment_method": "company", "payment_date": "2026-06-17",
            "bank_account_id": bank_account_id, "description": "工资", "withholding_tax_amount": 0
        }, headers=HEADERS)
        assert salary_resp.status_code in (200, 201)

        resp = client.get("/api/financial-reports/cwbb-xqykjzz?report_type=monthly&date=2026-06-30", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()

        cf01 = _find_line(data, "cash_flow_statement", 1)
        cf04 = _find_line(data, "cash_flow_statement", 4)
        cf06 = _find_line(data, "cash_flow_statement", 6)
        assert cf01["period_amount"] == 1000.0, f"CF01 应为 1000, 实际 {cf01['period_amount']}"
        assert cf04["period_amount"] == 500.0, f"CF04 应为 500, 实际 {cf04['period_amount']}"
        assert cf06["period_amount"] == 200.0, f"CF06 应为 200, 实际 {cf06['period_amount']}"

    def test_tax_surcharge_detail(self, client, db):
        """验证附加税按最新政策计入明细科目"""
        from datetime import datetime
        from database import set_maintenance_mode
        from finance_integration import get_or_create_ledger_id
        from engine_tax import TaxAccrualEngine
        from models import Account
        from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine

        def _cleanup():
            # 清理本测试遗留的测试凭证及附加税计提凭证，保证幂等
            db.query(AccountMove).filter(
                AccountMove.source_model == "test",
                AccountMove.source_id == 1,
                AccountMove.name == "测试销项",
            ).delete(synchronize_session=False)
            db.query(AccountMove).filter(
                AccountMove.source_model == "tax_surcharge",
                AccountMove.source_id == 1,
            ).delete(synchronize_session=False)
            db.commit()

        set_maintenance_mode(True)
        try:
            # 确保测试账本及总账科目存在，并临时设为一般纳税人
            get_or_create_ledger_id(db, 1)
            account = db.query(Account).filter(Account.id == 1).first()
            assert account is not None
            original_taxpayer_type = account.taxpayer_type_l3
            account.taxpayer_type_l3 = "general"
            db.flush()

            engine = TaxAccrualEngine(db)

            # 直接通过 engine 模拟一般纳税人计提附加税（无需完整销售单）
            # 先手动写入一笔增值税销项，使 curr_vat > 0
            ledger = db.query(Ledger).filter(Ledger.code == account.code).first()
            assert ledger is not None
            vat_account = db.query(LedgerAccount).filter(
                LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "222101"
            ).first()
            assert vat_account is not None

            _cleanup()

            move = AccountMove(
                ledger_id=ledger.id, name="测试销项", move_type="manual", date_l1=datetime(2026, 6, 15).date(),
                state="posted", source_model="test", source_id=1, amount_total_l2=13000
            )
            db.add(move)
            db.flush()
            line_vat = AccountMoveLine(
                move_id=move.id, ledger_account_id=vat_account.id,
                debit_l2=0, credit_l2=13000, amount_residual_l2=13000
            )
            db.add(line_vat)
            db.flush()

            result = engine.execute(account_id=1, period="2026-06", taxpayer_type="general")
            assert result["status"] == "ok"

            # 恢复纳税人类型，避免影响后续测试
            account.taxpayer_type_l3 = original_taxpayer_type
            db.flush()
            db.commit()
        finally:
            _cleanup()
            set_maintenance_mode(False)

        resp = client.get("/api/financial-reports/cwbb-xqykjzz?report_type=monthly&date=2026-06-30", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()

        # 一般纳税人：城建 7% + 教育 3% + 地方教育 2% = 12%
        tax_line = _find_line(data, "income_statement", 3)
        urban = _find_line(data, "income_statement", 6)
        edu = _find_line(data, "income_statement", 10)
        assert tax_line["period_amount"] == 1560.0, f"附加税总额应为 1560, 实际 {tax_line['period_amount']}"
        assert urban["period_amount"] == 910.0, f"城建税应为 910, 实际 {urban['period_amount']}"
        assert edu["period_amount"] == 650.0, f"教育费附加+地方教育附加应为 650, 实际 {edu['period_amount']}"
