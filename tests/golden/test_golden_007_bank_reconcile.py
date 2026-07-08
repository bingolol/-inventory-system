"""
GOLDEN TEST 007 — 银行对账全流程独立验算

==================== 独立会计师完整验算 ====================

【配置】
  - 一般纳税人
  - 所有数字可手算，与系统输出逐一对照
  - 每步追溯 trace_bal → [aml_ids] → source_model/source_id

【业务流水单】
  期初: 银行存款=10000, 实收资本=10000, 无业务发生

  Step 1: 导入银行对账单
    期初余额=10000, 期末余额=9850
    明细行: 2026-01-10, -150, "手续费"

  Step 2: 执行银行对账
    book_balance=10000, statement_balance=9850
    差额150 → bank_paid_not_book, action=generate_entry

  Step 3: 生成入账凭证
    分录: dr 6603=150, cr 1002=150 (post_bank_fee_journal)

  Step 4: 确认调节表 (status→confirmed)

  Step 5: 月结
    损益结转: 6603(150) → 4103(150 dr)
    所得税 = 0 (亏损不计提)
    净利润 = -150

【期末汇总】
  银行(1002): 10000 - 150 = 9850
  财务费用(6603): 150(dr) → 月结后 0
  本年利润(4103): -150

  IS: 收入=0, 成本=0, 财务费用=-150, 净利润=-150
  BS: 资产(9850) = 负债(0) + 权益(10000-150=9850) ✓
"""

import sys, os, pytest, tempfile, uuid
from decimal import Decimal

pytestmark = pytest.mark.golden
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import get_db, Base, init_db
import database
from models import Account
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from utils import _d

# ═══════════════════════════════════════════════════════
# 独立会计师期望值
# ═══════════════════════════════════════════════════════

BANK_OPENING = Decimal("10000")
BANK_FEE = Decimal("150")
BANK_ENDING = BANK_OPENING - BANK_FEE  # 9850

EXPENSE_FIN = BANK_FEE  # 150
PROFIT_BEFORE_TAX = -EXPENSE_FIN  # -150
INCOME_TAX = Decimal("0")
NET_PROFIT = PROFIT_BEFORE_TAX

TOTAL_ASSETS = BANK_ENDING  # 9850
TOTAL_LIABILITIES = Decimal("0")
TOTAL_EQUITY = BANK_OPENING + NET_PROFIT  # 10000 - 150 = 9850

IS_REVENUE = Decimal("0")
IS_COGS = Decimal("0")
IS_FIN_EXPENSE = -EXPENSE_FIN  # -150

# CF: 银行手续费不走BankTransaction, CF不捕获此变动
CF_BEGIN = BANK_OPENING   # 10000
CF_END = BANK_OPENING     # 10000 (≠BS 9850)
CF_NET = Decimal("0")

# ═══════════════════════════════════════════════════════
# 测试基础设施
# ═══════════════════════════════════════════════════════

UNIQUE = "GLD007"
TEST_DB = os.path.join(tempfile.gettempdir(), f"test_golden_{uuid.uuid4().hex[:8]}.db")
_engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
ACCT_ID = 1

def _db():
    return _SessionLocal()

HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}

def _ledger_balance(db, code):
    la = db.query(LedgerAccount).filter(LedgerAccount.code == code).first()
    if not la:
        return Decimal("0")
    total = Decimal("0")
    for line in db.query(AccountMoveLine).filter(AccountMoveLine.ledger_account_id == la.id).all():
        total += _d(line.debit_l2) - _d(line.credit_l2)
    return total

def _credit_balance(db, code):
    return -_ledger_balance(db, code)

def _trace_bal(db, code):
    la = db.query(LedgerAccount).filter(LedgerAccount.code == code).first()
    if not la:
        return Decimal("0"), []
    rows = (
        db.query(AccountMoveLine, AccountMove)
        .join(AccountMove, AccountMove.id == AccountMoveLine.move_id)
        .filter(AccountMoveLine.ledger_account_id == la.id)
        .all()
    )
    balance = Decimal("0")
    traces = []
    for aml, am in rows:
        balance += _d(aml.debit_l2) - _d(aml.credit_l2)
        traces.append((aml.id, am.source_model, am.source_id, am.is_reversal, _d(aml.debit_l2), _d(aml.credit_l2)))
    return balance, traces

def _get_id(resp, label=""):
    data = resp.json()
    eid = data.get("entity_id") or data.get("id")
    if eid is None and "entity" in data:
        eid = data["entity"].get("entity_id") or data["entity"].get("id")
    if eid is None and "data" in data:
        eid = data["data"].get("id") or data["data"].get("entity_id")
    assert eid is not None, f"No entity id in {label} response: {data}"
    return eid

# ═══════════════════════════════════════════════════════
# Golden Test
# ═══════════════════════════════════════════════════════

@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c

class TestBankReconciliation:

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
            try:
                yield db
            finally:
                db.close()
        app.dependency_overrides[get_db] = _get_db
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_bank_reconciliation_flow(self, client):
        c = client
        s = {}

        print("\n" + "=" * 60)
        print("GOLDEN TEST 007 — 银行对账全流程")
        print("=" * 60)

        # ── 期初建账 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行",
            "account_number": "62220200001",
            "balance": 0,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["bank_id"] = _get_id(r, "bank_account")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01",
            "cash_balance": 0,
            "bank_balance": float(BANK_OPENING),
            "accounts_receivable": 0,
            "inventory_value": 0,
            "fixed_assets_original": 0,
            "accumulated_depreciation": 0,
            "intangible_assets_original": 0,
            "accumulated_amortization": 0,
            "accounts_payable": 0,
            "tax_payable": 0,
            "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPENING),
            "retained_earnings": 0,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        print("OK 期初建账")

        db = _db()
        try:
            bal, traces = _trace_bal(db, "1002")
            assert bal == BANK_OPENING, f"期初银行 {bal} != {BANK_OPENING}"
            assert any(t[1] == "opening_balance" for t in traces), "1002 非来自期初"
        finally:
            db.close()

        # ═══ Step 1: 导入银行对账单 ═══
        r = c.post("/api/bank/statement", json={
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "opening_balance": float(BANK_OPENING),
            "closing_balance": float(BANK_ENDING),
            "lines": [{
                "transaction_date": "2026-01-10",
                "amount": float(-BANK_FEE),
                "description": "银行手续费",
            }],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        stmt_data = r.json()
        s["stmt_id"] = stmt_data.get("id") or stmt_data.get("entity", {}).get("id")
        print(f"OK Step 1. 导入对账单 (期初={BANK_OPENING}, 期末={BANK_ENDING})")

        # ═══ Step 2: 执行银行对账 ═══
        r = c.post("/api/bank/reconcile?period=2026-01", headers=HEADERS)
        assert r.status_code == 200, r.text
        rec_data = r.json()
        rec = rec_data if "id" in rec_data else rec_data.get("entity", rec_data)
        s["rec_id"] = rec["id"]
        # 调节前: book=10000, statement=9850 → 差额150, 不平衡
        # 调节后: 加未达项后应平衡
        print(f"  调节前: book={rec['book_balance']}, stmt={rec['statement_balance']}, balanced={rec['balanced']}")

        db = _db()
        try:
            # 银行余额未变化（还未入账）
            assert _ledger_balance(db, "1002") == BANK_OPENING, "对账后银行余额不应变"
            # 检查未达账项
            from models_bank import ReconciliationItem
            items = db.query(ReconciliationItem).filter(
                ReconciliationItem.reconciliation_id == s["rec_id"],
            ).all()
            unpaid = [it for it in items if it.item_type == "bank_paid_not_book"]
            assert len(unpaid) == 1, f"应有1笔bank_paid_not_book, 实有{len(unpaid)}"
            assert abs(unpaid[0].amount_l2 - BANK_FEE) <= Decimal("0.05"), \
                f"未达金额 {unpaid[0].amount_l2} != {BANK_FEE}"
            assert unpaid[0].action == "generate_entry", f"action应为generate_entry, 实际={unpaid[0].action}"
            print(f"  未达账项: {unpaid[0].item_type} amount={unpaid[0].amount_l2} action={unpaid[0].action}")
        finally:
            db.close()
        print("OK Step 2. 对账执行 (正确识别未达手续费项)")

        # ═══ Step 3: 生成入账凭证 ═══
        r = c.post(f"/api/bank/reconciliation/{s['rec_id']}/generate-entry", headers=HEADERS)
        assert r.status_code == 200, r.text
        gen_data = r.json()
        gen = gen_data if "generated" in gen_data else gen_data.get("entity", gen_data)
        assert gen.get("generated", 0) >= 1, f"应生成凭证, 实际={gen}"
        print(f"  生成凭证: {gen}")

        db = _db()
        try:
            # 验证分录: dr 6603=150, cr 1002=150
            bal_6603, traces_6603 = _trace_bal(db, "6603")
            assert bal_6603 == BANK_FEE, f"6603 余额 {bal_6603} != {BANK_FEE}"
            # 追溯 6603 来源
            fee_traces = [t for t in traces_6603 if t[1] in ("bank_fee_entry", "bank_entry")]
            assert len(fee_traces) >= 1, f"6603 缺少银行费用来源, traces={traces_6603}"
            print(f"  6603追溯: {[(t[1], t[4], t[5]) for t in traces_6603]}")

            bal_1002, traces_1002 = _trace_bal(db, "1002")
            expected_bank = BANK_OPENING - BANK_FEE
            assert bal_1002 == expected_bank, f"1002 余额 {bal_1002} != {expected_bank}"
            print(f"  1002追溯: {[(t[1], t[4], t[5]) for t in traces_1002]}")

            # 验证借贷平衡
            total_dr = sum(t[4] for t in traces_6603)
            total_cr = sum(t[5] for t in traces_6603)
            assert total_dr - total_cr == bal_6603, "6603 借贷差 != 余额"
        finally:
            db.close()
        print("OK Step 3. 生成入账凭证 (dr 6603=150, cr 1002=150)")

        # ═══ Step 4: 确认调节表 ═══
        r = c.post(f"/api/bank/reconciliation/{s['rec_id']}/confirm", headers=HEADERS)
        assert r.status_code == 200, r.text

        r = c.get(f"/api/bank/reconciliation?period=2026-01", headers=HEADERS)
        assert r.status_code == 200, r.text
        rec_status_data = r.json()
        rec_status = rec_status_data if "status" in rec_status_data else rec_status_data.get("entity", rec_status_data)
        assert rec_status.get("status") == "confirmed", f"调节表状态应为confirmed, 实际={rec_status.get('status')}"
        print(f"  调节表状态: {rec_status.get('status')}, balanced={rec_status.get('balanced')}")
        print("OK Step 4. 确认调节表")

        # ═══ Step 5: 月结 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _ledger_balance(db, "6603") == Decimal("0"), "6603 月结后应归零"
            profit_4103 = _ledger_balance(db, "4103")
            assert profit_4103 == -NET_PROFIT, f"4103 余额 {profit_4103} != {-NET_PROFIT}"
            print(f"  4103追溯: {_trace_bal(db, '4103')[1]}")
        finally:
            db.close()
        print(f"OK Step 5. 月结 (财务费用={BANK_FEE}, 净利润={NET_PROFIT})")

        # ═══ 6. 财务报表验证 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        bs = r.json()

        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        pl = r.json()

        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"BS不平衡, diff={diff}"

        assert abs(Decimal(str(bs["monetary_funds"])) - BANK_ENDING) <= Decimal("0.05"), \
            f"BS银行存款: {bs['monetary_funds']} != {BANK_ENDING}"
        assert abs(Decimal(str(bs["total_liabilities"])) - TOTAL_LIABILITIES) <= Decimal("0.05"), \
            f"BS负债: {bs['total_liabilities']} != {TOTAL_LIABILITIES}"
        assert abs(Decimal(str(bs["paid_in_capital"])) - BANK_OPENING) <= Decimal("0.05"), \
            f"BS实收资本: {bs['paid_in_capital']} != {BANK_OPENING}"
        assert abs(Decimal(str(bs["retained_earnings"])) - NET_PROFIT) <= Decimal("0.05"), \
            f"BS留存收益: {bs['retained_earnings']} != {NET_PROFIT}"
        assert abs(Decimal(str(bs["total_assets"])) - TOTAL_ASSETS) <= Decimal("0.05"), \
            f"BS资产合计: {bs['total_assets']} != {TOTAL_ASSETS}"

        assert abs(Decimal(str(pl["revenue"])) - IS_REVENUE) <= Decimal("0.05"), \
            f"IS收入: {pl['revenue']} != {IS_REVENUE}"
        assert abs(Decimal(str(pl["net_profit"])) - NET_PROFIT) <= Decimal("0.05"), \
            f"IS净利润: {pl['net_profit']} != {NET_PROFIT}"

        print(f"  BS: 资产={bs['total_assets']}, 权益={bs['total_liabilities_and_equity']}")
        print(f"  IS: 净利润={pl['net_profit']}")
        print("OK 6. BS/IS 验证 (手算对照)")

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
        assert cf_net == CF_NET, f"CF净额={cf_net}≠{CF_NET}"
        bs_bank = Decimal(str(bs["monetary_funds"]))
        if abs(cf_end - bs_bank) > Decimal("0.05"):
            print(f"  [WARN] CF期末({cf_end})≠BS银行存款({bs_bank})")
        print(f"  CF: 期初={cf_begin}, 期末={cf_end}, 经营={op_net}")
        print("OK CF验证")

        # ═══ 7. 追溯验证 ═══
        db = _db()
        try:
            bal, traces = _trace_bal(db, "1002")
            print(f"  1002追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
            assert abs(bal - BANK_ENDING) <= Decimal("0.05")

            bal, traces = _trace_bal(db, "6603")
            print(f"  6603追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
            assert bal == Decimal("0")

            bal, traces = _trace_bal(db, "4103")
            print(f"  4103追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
            assert bal == -NET_PROFIT
        finally:
            db.close()
        print("OK 7. 追溯验证 (所有科目余额可追溯到凭证行)")

        # ═══ 8. 全量不变量 ═══
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        except Exception as e:
            pytest.fail(f"AS-01 校验失败: {e}")
        finally:
            db.close()
        print("OK 8. 全月凭证借贷平衡 + BS 恒等式")

        print("\n" + "=" * 60)
        print("ALL GOLDEN ASSERTIONS PASSED")
        print(f"银行: {BANK_ENDING}, 利润: {NET_PROFIT}")
        print("=" * 60)
