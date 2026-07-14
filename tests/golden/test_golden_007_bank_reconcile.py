"""
GOLDEN TEST 007 — 银行对账全流程独立验算

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts

_engine, _SessionLocal = make_engine()
H = {"X-Account-ID": "1", "X-Operator": "golden_test"}

# ═══ L1 业务事实（硬编码）═══
BANK_OPEN = Decimal("10000")
BANK_FEE = Decimal("150")


class TestGolden007:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setattr(database, '_engine', _engine)
        monkeypatch.setattr(database, 'SessionLocal', _SessionLocal)
        Base.metadata.create_all(bind=_engine)
        init_db()
        from factories import ensure_default_account
        db = _SessionLocal()
        try:
            ensure_default_account(db)
            acc = db.query(models.Account).first()
            acc.taxpayer_type_l3 = "general"; acc.enable_vat_deduction = True
            db.commit()
        finally: db.close()
        def _g():
            db = _SessionLocal()
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db] = _g
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_bank_reconciliation_flow(self, client):
        c = client; s = {}

        # ── 期初建账 §84 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": "62220200001", "balance": 0,
        }, headers=H)
        assert r.status_code == 200; s["bank_id"] = _get_id(r, "bank_account")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPEN), "accounts_receivable": 0,
            "inventory_value": 0, "fixed_assets_original": 0,
            "accumulated_depreciation": 0, "intangible_assets_original": 0,
            "accumulated_amortization": 0, "accounts_payable": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPEN), "retained_earnings": 0,
        }, headers=H)
        assert r.status_code == 200

        # Step 1: 导入银行对账单
        r = c.post("/api/bank/statement", json={
            "period_start": "2026-01-01", "period_end": "2026-01-31",
            "opening_balance": float(BANK_OPEN),
            "closing_balance": float(BANK_OPEN - BANK_FEE),
            "lines": [{
                "transaction_date": "2026-01-10",
                "amount": float(-BANK_FEE),
                "description": "银行手续费",
            }],
        }, headers=H)
        assert r.status_code == 200, r.text
        stmt_data = r.json()
        s["stmt_id"] = stmt_data.get("id") or stmt_data.get("entity", {}).get("id")

        # Step 2: 执行银行对账
        r = c.post("/api/bank/reconcile?period=2026-01", headers=H)
        assert r.status_code == 200, r.text
        rec_data = r.json()
        rec = rec_data if "id" in rec_data else rec_data.get("entity", rec_data)
        s["rec_id"] = rec["id"]

        # Step 3: 生成入账凭证
        r = c.post(f"/api/bank/reconciliation/{s['rec_id']}/generate-entry", headers=H)
        assert r.status_code == 200, r.text
        gen_data = r.json()
        gen = gen_data if "generated" in gen_data else gen_data.get("entity", gen_data)
        assert gen.get("generated", 0) >= 1, f"应生成凭证, 实际={gen}"

        # Step 4: 确认调节表
        r = c.post(f"/api/bank/reconciliation/{s['rec_id']}/confirm", headers=H)
        assert r.status_code == 200, r.text

        # Step 5: 月结
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=H)
        assert r.status_code == 200, r.text

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
            income_tax_rate=Decimal("0.05"),  # 小微企业实际税负（独立从税务局核定单确认）
            bank_fees=BANK_FEE,
        ))
        assert expected.interlock_ok, expected.interlock_messages

        # ═══ L3 报表 API 验证 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=H)
        assert r.status_code == 200; bs = r.json()
        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=H)
        assert r.status_code == 200; pl = r.json()

        tol = Decimal("0.05")
        assert abs(Decimal(str(bs["total_assets"])) - expected.balance_sheet.total_assets) <= tol, \
            f"§84资产总计: 实际{bs['total_assets']} != 期望{expected.balance_sheet.total_assets}"
        assert abs(Decimal(str(bs["total_liabilities"])) - expected.balance_sheet.total_liabilities) <= tol, \
            f"§84负债合计: 实际{bs['total_liabilities']} != 期望{expected.balance_sheet.total_liabilities}"
        assert abs(Decimal(str(bs["total_equity"])) - expected.balance_sheet.total_equity) <= tol, \
            f"§84权益合计: 实际{bs['total_equity']} != 期望{expected.balance_sheet.total_equity}"
        assert abs(Decimal(str(bs["monetary_funds"])) - expected.balance_sheet.monetary_funds) <= tol, \
            f"§84货币资金: 实际{bs['monetary_funds']} != 期望{expected.balance_sheet.monetary_funds}"
        assert abs(Decimal(str(bs["retained_earnings"])) - expected.balance_sheet.retained_earnings) <= tol, \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{expected.balance_sheet.retained_earnings}"

        assert abs(Decimal(str(pl["revenue"])) - expected.income_statement.revenue) <= tol, \
            f"§84营业收入: 实际{pl['revenue']} != 期望{expected.income_statement.revenue}"
        # 银行手续费必须被系统从对账单正确提取并计入财务费用
        assert abs(Decimal(str(pl["financial_expenses"])) - expected.income_statement.financial_expenses) <= tol, \
            f"§84财务费用: 实际{pl['financial_expenses']} != 期望{expected.income_statement.financial_expenses}"
        assert abs(Decimal(str(pl["net_profit"])) - expected.income_statement.net_profit) <= tol, \
            f"§84净利润: 实际{pl['net_profit']} != 期望{expected.income_statement.net_profit}"
