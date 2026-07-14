"""
GOLDEN TEST 004 — 个人垫付全流程 §48 其他应付款

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts, EmployeeFundedExpense

_engine, _SessionLocal = make_engine()
H = {"X-Account-ID": "1", "X-Operator": "golden_test"}

# ═══ L1 业务事实（硬编码）═══
BANK_OPEN = Decimal("10000")
ADV_AMOUNT = Decimal("2000")
REPAY_FIRST = Decimal("800")
REPAY_FULL = Decimal("2000")


class TestGolden004:
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

    def test_personal_advance_full_flow(self, client):
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

        # ═══ Step 1: 创建垫付 2000 §48 ═══
        r = c.post("/api/personal-advances", json={
            "advancer_name": "张老板", "amount": float(ADV_AMOUNT),
            "advance_date": "2026-01-10", "debit_account_code": "6601",
            "description": "垫付办公用品",
        }, headers=H)
        assert r.status_code == 200, r.text
        body = r.json()
        s["adv_id"] = _get_id(r, "advance")
        advance_data = body.get("entity", body).get("data", body.get("entity", body))
        assert advance_data.get("advance_no", "").startswith("PA-2026-")
        assert advance_data.get("repayment_status") == "unpaid"
        assert Decimal(str(advance_data.get("remaining_amount", 0))) == ADV_AMOUNT

        # ═══ Step 2: 偿还 800 §48 ═══
        r = c.post(f"/api/personal-advances/{s['adv_id']}/repay", json={
            "amount": float(REPAY_FIRST), "repayment_date": "2026-01-15",
            "bank_account_id": s["bank_id"],
        }, headers=H)
        assert r.status_code == 200, r.text
        body2 = r.json()
        ent2 = body2.get("entity", body2)
        rep_data = ent2.get("data", ent2)
        advance_after = rep_data.get("advance", rep_data)
        assert advance_after.get("repayment_status") == "partial"
        assert Decimal(str(advance_after.get("paid_amount", 0))) == REPAY_FIRST
        s["repay_id"] = body2.get("entity_id") or ent2.get("entity_id") or rep_data.get("id")

        # ═══ Step 3: 冲红偿还 §48 ═══
        r = c.post(f"/api/personal-advances/{s['adv_id']}/repayments/{s['repay_id']}/reverse",
                   headers=H)
        assert r.status_code == 200, r.text

        # ═══ Step 4: 全额偿还 2000 §48 ═══
        r = c.post(f"/api/personal-advances/{s['adv_id']}/repay", json={
            "amount": float(REPAY_FULL), "repayment_date": "2026-01-20",
            "bank_account_id": s["bank_id"],
        }, headers=H)
        assert r.status_code == 200, r.text

        # ═══ Step 5: 月结 §7.1 §84 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=H)
        assert r.status_code == 200, r.text

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=BANK_OPEN,
            opening_paid_in_capital=BANK_OPEN,
            income_tax_rate=Decimal("0.05"),  # 小微企业实际税负（独立从税务局核定单确认）
            employee_funded_expenses=[EmployeeFundedExpense(ADV_AMOUNT, reimbursed=REPAY_FIRST + REPAY_FULL, reversed_reimbursement=REPAY_FIRST)],
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
        assert abs(Decimal(str(bs["other_payable"])) - expected.balance_sheet.other_payable) <= tol, \
            f"§84其他应付款: 实际{bs['other_payable']} != 期望{expected.balance_sheet.other_payable}"
        assert abs(Decimal(str(bs["retained_earnings"])) - expected.balance_sheet.retained_earnings) <= tol, \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{expected.balance_sheet.retained_earnings}"

        assert abs(Decimal(str(pl["revenue"])) - expected.income_statement.revenue) <= tol, \
            f"§84营业收入: 实际{pl['revenue']} != 期望{expected.income_statement.revenue}"
        assert abs(Decimal(str(pl["net_profit"])) - expected.income_statement.net_profit) <= tol, \
            f"§84净利润: 实际{pl['net_profit']} != 期望{expected.income_statement.net_profit}"
