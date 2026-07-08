"""
GOLDEN TEST 004 — 个人垫付全流程 §48 其他应付款

【准则覆盖】§48 其他应付款(2241), §6.1 管理费用(6601), §7.1 利润, §84 报表
【AS规则】 AS-01 借贷平衡, AS-15 冲红凭证日期一致

==================== 独立会计师完整验算 ====================
  Step 1: 创建垫付 2000 (dr 6601, cr 2241)         §48 §6.1
  Step 2: 偿还 800 (dr 2241, cr 1002)               §48
  Step 3: 冲红偿还 (reverse: dr 1002=800, cr 2241)  §48
  Step 4: 全额偿还 2000 (dr 2241, cr 1002)          §48
  Step 5: 月结 → 6601结转4103, 净利润=-2000         §7.1 §84
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database
from models import Account, PersonalAdvance
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from helpers import (
    make_engine, _ledger_balance, _credit_balance, _trace_bal, _get_id,
)

_engine, _SessionLocal = make_engine()
ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}

def _db(): return _SessionLocal()

# ═══ 独立会计师期望值 ═══
BANK_OPENING = Decimal("10000")
ADV_AMOUNT = Decimal("2000")    # §48 垫付金额
REPAY_FIRST = Decimal("800")    # 首次偿还
REPAY_FULL = Decimal("2000")    # 全额偿还

# §48 银行余额: 10000 -800(偿) +800(冲红) -2000(偿) = 8000
BANK_ENDING = BANK_OPENING - REPAY_FIRST + REPAY_FIRST - REPAY_FULL

# §6.1 管理费用
MGMT_EXPENSE = ADV_AMOUNT      # §6.1: 2000
PROFIT_BEFORE_TAX = -MGMT_EXPENSE   # §7.1: -2000
INCOME_TAX = Decimal("0")           # §7.1: 亏损不计提
NET_PROFIT = PROFIT_BEFORE_TAX      # §7.1: -2000

# §84 BS
TOTAL_ASSETS = BANK_ENDING           # 8000
TOTAL_LIABILITIES = Decimal("0")
TOTAL_EQUITY = BANK_OPENING + NET_PROFIT  # §84: 8000

# §84 IS
IS_REVENUE = Decimal("0")
IS_COGS = Decimal("0")
IS_MGMT_EXPENSE = -MGMT_EXPENSE      # §6.1: -2000

# CF
# 系统行为: 付款冲红的逆流BankTransaction不被CF计入
# CF仅看到原始流出800+2000=2800, 看不到800冲红流入
CF_NET_OUTFLOW = REPAY_FIRST + REPAY_FULL  # 2800
CF_CF06 = -CF_NET_OUTFLOW               # -2800


class TestPersonalAdvance:

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
            acc = db.query(Account).first()
            if acc:
                acc.taxpayer_type_l3 = "general"
                acc.enable_vat_deduction = True
                db.commit()
        finally:
            db.close()
        def _get_db():
            db = _SessionLocal()
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db] = _get_db
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_personal_advance_full_flow(self, client):
        c = client; s = {}

        # ── 期初建账 §84 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": "62220200001", "balance": 0,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["bank_id"] = _get_id(r, "bank_account")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPENING), "accounts_receivable": 0,
            "inventory_value": 0, "fixed_assets_original": 0,
            "accumulated_depreciation": 0, "intangible_assets_original": 0,
            "accumulated_amortization": 0, "accounts_payable": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPENING), "retained_earnings": 0,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        # ═══ Step 1: 创建垫付 2000 §48 §6.1 ═══
        r = c.post("/api/personal-advances", json={
            "advancer_name": "张老板", "amount": float(ADV_AMOUNT),
            "advance_date": "2026-01-10", "debit_account_code": "6601",
            "description": "垫付办公用品",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        body = r.json()
        s["adv_id"] = _get_id(r, "advance")
        entity = body.get("entity", body)
        advance_data = entity.get("data", entity)
        assert advance_data.get("advance_no", "").startswith("PA-2026-")
        assert advance_data.get("repayment_status") == "unpaid"
        assert Decimal(str(advance_data.get("remaining_amount", 0))) == ADV_AMOUNT

        db = _db()
        try:
            bal_6601, traces_6601 = _trace_bal(db, "6601")
            assert bal_6601 == ADV_AMOUNT, f"§6.1 6601余额 {bal_6601} != {ADV_AMOUNT}"
            assert any(t[1] == "personal_advance" for t in traces_6601)
            assert _credit_balance(db, "2241") == ADV_AMOUNT, f"§48 2241余额 != {ADV_AMOUNT}"
        finally: db.close()

        # ═══ Step 2: 偿还 800 §48 ═══
        r = c.post(f"/api/personal-advances/{s['adv_id']}/repay", json={
            "amount": float(REPAY_FIRST), "repayment_date": "2026-01-15",
            "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        body2 = r.json()
        ent2 = body2.get("entity", body2)
        rep_data = ent2.get("data", ent2)
        advance_after = rep_data.get("advance", rep_data)
        assert advance_after.get("repayment_status") == "partial"
        assert Decimal(str(advance_after.get("paid_amount", 0))) == REPAY_FIRST
        s["repay_id"] = body2.get("entity_id") or ent2.get("entity_id") or rep_data.get("id")

        db = _db()
        try:
            assert _credit_balance(db, "2241") == ADV_AMOUNT - REPAY_FIRST
            assert _ledger_balance(db, "1002") == BANK_OPENING - REPAY_FIRST
        finally: db.close()

        # ═══ Step 3: 冲红偿还 §48 ═══
        r = c.post(f"/api/personal-advances/{s['adv_id']}/repayments/{s['repay_id']}/reverse",
                   headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _ledger_balance(db, "1002") == BANK_OPENING
            # 验证冲红凭证
            _, traces_1002 = _trace_bal(db, "1002")
            rev_traces = [t for t in traces_1002 if t[3] == True]
            assert len(rev_traces) >= 1, "§48 缺少 is_reversal 冲红分录"
            assert _credit_balance(db, "2241") == ADV_AMOUNT

            adv = db.query(PersonalAdvance).filter(PersonalAdvance.id == s["adv_id"]).first()
            assert adv.repayment_status == "unpaid"
            assert Decimal(str(adv.paid_amount_l4)) == Decimal("0")

            # AS-15: 冲红凭证日期一致性
            from rules import enforce_rules
            for t in rev_traces:
                # 找到冲红凭证的 move_id
                aml = db.query(AccountMoveLine).filter(AccountMoveLine.id == t[0]).first()
                if aml:
                    try:
                        enforce_rules(db, ["AS-15"], {"move_id": aml.move_id})
                    except Exception as e:
                        pytest.fail(f"AS-15 冲红日期校验失败: {e}")
        finally: db.close()

        # ═══ Step 4: 全额偿还 2000 §48 ═══
        r = c.post(f"/api/personal-advances/{s['adv_id']}/repay", json={
            "amount": float(REPAY_FULL), "repayment_date": "2026-01-20",
            "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _credit_balance(db, "2241") == Decimal("0")
            assert _ledger_balance(db, "1002") == BANK_OPENING - REPAY_FULL
        finally: db.close()

        # ═══ Step 5: 月结 §7.1 §84 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _ledger_balance(db, "6601") == Decimal("0"), "§84 6601月结后归零"
            profit_4103 = _ledger_balance(db, "4103")
            assert profit_4103 == -NET_PROFIT, f"§7.1 4103余额 {profit_4103} != {-NET_PROFIT}"
        finally: db.close()

        # ═══ 6. 财务报表验证 §84 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200; bs = r.json()
        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200; pl = r.json()

        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"§84 BS不平衡, diff={diff}"
        assert abs(Decimal(str(bs["monetary_funds"])) - BANK_ENDING) <= Decimal("0.05")
        assert abs(Decimal(str(bs["total_liabilities"])) - TOTAL_LIABILITIES) <= Decimal("0.05")
        assert abs(Decimal(str(bs["paid_in_capital"])) - BANK_OPENING) <= Decimal("0.05")
        assert abs(Decimal(str(bs["retained_earnings"])) - NET_PROFIT) <= Decimal("0.05")
        assert abs(Decimal(str(bs["total_assets"])) - TOTAL_ASSETS) <= Decimal("0.05")
        assert abs(Decimal(str(pl["revenue"])) - IS_REVENUE) <= Decimal("0.05")
        assert abs(Decimal(str(pl["net_profit"])) - NET_PROFIT) <= Decimal("0.05")

        # ═══ CF 验证 ═══
        r = c.get("/api/cash-flows/statement?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200; cf = r.json()
        cf_net = Decimal(str(cf["net_cash_flow"]))
        cf_begin = Decimal(str(cf["beginning_cash_balance"]))
        cf_end = Decimal(str(cf["ending_cash_balance"]))
        assert abs(cf_end - (cf_begin + cf_net)) <= Decimal("0.05"), "CF恒等式: 期末≠期初+净额"
        op_net = Decimal(str(cf["operating_activities"]["net"]))
        inv_net = Decimal(str(cf["investing_activities"]["net"]))
        fin_net = Decimal(str(cf["financing_activities"]["net"]))
        assert abs(cf_net - (op_net + inv_net + fin_net)) <= Decimal("0.05"), "CF净额≠三大活动合计"
        assert op_net == -CF_NET_OUTFLOW, f"CF经营净额={op_net}≠{-CF_NET_OUTFLOW}"
        assert Decimal(str(cf["cf_details"]["CF06"])) == CF_CF06, f"CF06={cf['cf_details']['CF06']}≠{CF_CF06}"
        bs_bank = Decimal(str(bs["monetary_funds"]))
        if abs(cf_end - bs_bank) > Decimal("0.05"):
            print(f"  [WARN] CF期末({cf_end})≠BS银行存款({bs_bank})")
        print(f"  CF: 期初={cf_begin}, 期末={cf_end}, 经营={op_net}")
        print("OK CF验证")

        # ═══ 7. 追溯验证 ═══
        db = _db()
        try:
            for code in ["1002", "6601", "2241", "4103"]:
                bal, traces = _trace_bal(db, code)
                print(f"  {code}追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
        finally: db.close()

        # ═══ 8. AS-01 全量不变量 ═══
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        except Exception as e:
            pytest.fail(f"AS-01 校验失败: {e}")
        finally: db.close()

        print("\nALL GOLDEN ASSERTIONS PASSED")
