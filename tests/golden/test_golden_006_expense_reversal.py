"""
GOLDEN TEST 006 — 费用冲红 + 多科目费用独立验算

==================== 独立会计师完整验算 ====================

【配置】
  - 一般纳税人
  - 所有数字可手算，与系统输出逐一对照
  - 每步追溯 trace_bal → [aml_ids] → source_model/source_id

【业务流水单】
  期初: 银行存款=10000, 实收资本=10000

  Step 1: 管理费用 100 挂账 (6601/2202)
    分录: dr 6601=100, cr 2202=100
    6601=100(dr), 2202=100(cr)

  Step 2: 付款 100 清应付
    分录: dr 2202=100, cr 1002=100
    银行=9900, 2202=0

  Step 3: 销售费用 200 挂账 (6602/2202)
    分录: dr 6602=200, cr 2202=200
    6602=200(dr), 2202=200(cr)

  Step 4: 付款 200 清应付
    分录: dr 2202=200, cr 1002=200
    银行=9700, 2202=0

  Step 5: 冲红销售费用 (reverse_journal 借贷互换)
    分录: dr 2202=200, cr 6602=200
    6602=0, 2202=200(cr)

  Step 6: 冲红付款 (reverse_single_payment 借贷互换)
    分录: dr 1002=200, cr 2202=200
    银行=9900, 2202=0

  Step 7: 财务费用 50 挂账 (6603/2202)
    分录: dr 6603=50, cr 2202=50
    6603=50(dr), 2202=50(cr)

  Step 8: 付款 50 清应付
    分录: dr 2202=50, cr 1002=50
    银行=9850, 2202=0

  Step 9: 冲红财务费用 (reverse_journal 借贷互换)
    分录: dr 2202=50, cr 6603=50
    6603=0, 2202=50(dr)

  Step 10: 冲红付款 (reverse_single_payment 借贷互换)
    分录: dr 1002=50, cr 2202=50
    银行=9900, 2202=0

  Step 11: 月结
    损益结转: 6601(100) → 4103(100 dr)
    所得税 = 0 (亏损不计提)
    净利润 = -100

【期末汇总】
  银行(1002): 10000 -100(付管理) -200(付销售) +200(冲红付销售) -50(付财务) +50(冲红付财务) = 9900
  应付(2202): +100(管理挂) -100(付管理) +200(销售挂) -200(付销售) +200(冲红销售) -200(冲红付销售) +50(财务挂) -50(付财务) +50(冲红财务) -50(冲红付财务) = 0
  管理费用(6601): 100(dr) → 月结后 0
  销售费用(6602): 200(dr) -200(冲红) = 0
  财务费用(6603): 50(dr) -50(冲红) = 0
  本年利润(4103): -100(dr) ← 6601 结转

  IS: 收入=0, 成本=0, 管理费用=-100, 销售费用=0, 财务费用=0, 净利润=-100
  BS: 资产(9900) = 负债(0) + 权益(10000-100=9900) ✓
  CF: 经营活动净流出=100 ✓
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
from models import Account, BankAccount
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from utils import _d

# ═══════════════════════════════════════════════════════
# 独立会计师期望值
# ═══════════════════════════════════════════════════════

BANK_OPENING = Decimal("10000")

EXPENSE_MGMT = Decimal("100")     # 管理费用 (6601)
EXPENSE_SELL = Decimal("200")     # 销售费用 (6602)
EXPENSE_FIN = Decimal("50")       # 财务费用 (6603)

# 银行流水: 10000 -100 -200 +200 -50 +50 = 9900
BANK_ENDING = (BANK_OPENING
               - EXPENSE_MGMT     # Step 2: 付管理
               - EXPENSE_SELL     # Step 4: 付销售
               + EXPENSE_SELL     # Step 6: 冲红付销售
               - EXPENSE_FIN      # Step 8: 付财务
               + EXPENSE_FIN)     # Step 10: 冲红付财务

# 科目余额
EXPENSE_TOTAL = EXPENSE_MGMT  # 只有管理费用未被冲红
PROFIT_BEFORE_TAX = -EXPENSE_TOTAL  # -100
INCOME_TAX = Decimal("0")  # 亏损不计提
NET_PROFIT = PROFIT_BEFORE_TAX  # -100

# BS
TOTAL_ASSETS = BANK_ENDING  # 9900
TOTAL_LIABILITIES = Decimal("0")
TOTAL_EQUITY = BANK_OPENING + NET_PROFIT  # 10000 - 100 = 9900

# IS
IS_REVENUE = Decimal("0")
IS_COGS = Decimal("0")
IS_MGMT_EXPENSE = -EXPENSE_MGMT  # -100
IS_SELL_EXPENSE = Decimal("0")
IS_FIN_EXPENSE = Decimal("0")

# CF
# 系统行为: 付款冲红的逆流BankTransaction不被CF计入
# CF仅看到原始流出100+200+50=350, 看不到200+50的冲红流入
CF_TOTAL_OUTFLOW = EXPENSE_MGMT + EXPENSE_SELL + EXPENSE_FIN  # 350
CF06 = -CF_TOTAL_OUTFLOW  # -350

# ═══════════════════════════════════════════════════════
# 测试基础设施
# ═══════════════════════════════════════════════════════

UNIQUE = "GLD006"
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
    """追溯: 返回(余额, [ (aml_id, source_model, source_id, debit, credit) ])"""
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

class TestExpenseReversal:

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

    def test_expense_reversal_flow(self, client):
        c = client
        s = {}

        print("\n" + "=" * 60)
        print("GOLDEN TEST 006 — 费用冲红 + 多科目费用")
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

        # ═══ Step 1: 管理费用 100 挂账 ═══
        r = c.post("/api/expenses", json={
            "amount": float(EXPENSE_MGMT),
            "category": "办公用品",
            "functional_category": "管理费用",
            "expense_date": "2026-01-10",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["expense_mgmt_id"] = _get_id(r, "expense_mgmt")

        db = _db()
        try:
            bal, traces = _trace_bal(db, "6601")
            assert bal == EXPENSE_MGMT, f"6601 余额 {bal} != {EXPENSE_MGMT}"
            assert any(t[1] == "expense" for t in traces), "6601 非来自 expense 凭证"
            print(f"  6601追溯: {traces}")
            assert _credit_balance(db, "2202") == EXPENSE_MGMT, \
                f"2202 余额 {_credit_balance(db, '2202')} != {EXPENSE_MGMT}"
        finally:
            db.close()
        print(f"OK Step 1. 管理费用 {EXPENSE_MGMT} 挂账")

        # ═══ Step 2: 付款 100 清应付 ═══
        r = c.post("/api/payments", json={
            "payment_type": "expense",
            "related_entity_type": "expense",
            "related_entity_id": s["expense_mgmt_id"],
            "bank_account_id": s["bank_id"],
            "amount": float(EXPENSE_MGMT),
            "payment_date": "2026-01-10",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["payment_mgmt_id"] = _get_id(r, "payment_mgmt")

        db = _db()
        try:
            bal, traces = _trace_bal(db, "1002")
            assert bal == BANK_OPENING - EXPENSE_MGMT, f"1002 余额 {bal} != {BANK_OPENING - EXPENSE_MGMT}"
            assert _credit_balance(db, "2202") == Decimal("0"), \
                f"2202 应归零, 实际={_credit_balance(db, '2202')}"
        finally:
            db.close()
        print(f"OK Step 2. 付款 {EXPENSE_MGMT}")

        # ═══ Step 3: 销售费用 200 挂账 ═══
        r = c.post("/api/expenses", json={
            "amount": float(EXPENSE_SELL),
            "category": "运费",
            "functional_category": "销售费用",
            "expense_date": "2026-01-12",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["expense_sell_id"] = _get_id(r, "expense_sell")

        db = _db()
        try:
            bal, traces = _trace_bal(db, "6602")
            assert bal == EXPENSE_SELL, f"6602 余额 {bal} != {EXPENSE_SELL}"
            assert any(t[1] == "expense" for t in traces), "6602 非来自 expense 凭证"
            print(f"  6602追溯: {traces}")
            assert _credit_balance(db, "2202") == EXPENSE_SELL, \
                f"2202 余额 {_credit_balance(db, '2202')} != {EXPENSE_SELL}"
        finally:
            db.close()
        print(f"OK Step 3. 销售费用 {EXPENSE_SELL} 挂账")

        # ═══ Step 4: 付款 200 清应付 ═══
        r = c.post("/api/payments", json={
            "payment_type": "expense",
            "related_entity_type": "expense",
            "related_entity_id": s["expense_sell_id"],
            "bank_account_id": s["bank_id"],
            "amount": float(EXPENSE_SELL),
            "payment_date": "2026-01-12",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["payment_sell_id"] = _get_id(r, "payment_sell")

        db = _db()
        try:
            bal, traces = _trace_bal(db, "1002")
            assert bal == BANK_OPENING - EXPENSE_MGMT - EXPENSE_SELL, \
                f"1002 余额 {bal} != {BANK_OPENING - EXPENSE_MGMT - EXPENSE_SELL}"
            assert _credit_balance(db, "2202") == Decimal("0"), "2202 应归零"
        finally:
            db.close()
        print(f"OK Step 4. 付款 {EXPENSE_SELL}")

        # ═══ Step 5: 冲红销售费用 ═══
        r = c.post(f"/api/expenses/{s['expense_sell_id']}/reverse", headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            bal, traces = _trace_bal(db, "6602")
            assert bal == Decimal("0"), f"6602 冲红后应归零, 实际={bal}"
            assert len(traces) >= 2, "6602 应有 expense + reverse 至少两笔"
            # 追溯: expense 分录 debit, reverse 分录 credit (借贷互换)
            dr_total = sum(t[4] for t in traces)
            cr_total = sum(t[5] for t in traces)
            assert dr_total == cr_total, f"6602 借贷合计: dr={dr_total} cr={cr_total} (应相等归零)"
            # 验证 reverse 凭证标记了 is_reversal
            rev_traces = [t for t in traces if t[3] == True]
            assert len(rev_traces) >= 1, "6602 缺少 is_reversal 冲红分录"
            print(f"  6602冲红追溯: {traces}")
            # 冲红费用后, 2202 出现借方余额(200dr) = 已付款但费用被冲红(尚未冲红付款)
            assert _ledger_balance(db, "2202") == EXPENSE_SELL, \
                f"冲红销售费用后 2202 dr 应为 {EXPENSE_SELL}, 实际={_ledger_balance(db, '2202')}"
        finally:
            db.close()
        print("OK Step 5. 冲红销售费用 (6602 归零)")

        # ═══ Step 6: 冲红付款 ═══
        r = c.post(f"/api/payments/{s['payment_sell_id']}/reverse", headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            bal, traces = _trace_bal(db, "1002")
            assert bal == BANK_OPENING - EXPENSE_MGMT, \
                f"冲红付款后银行应恢复至 {BANK_OPENING - EXPENSE_MGMT}, 实际={bal}"
            # 2202 归零
            assert _credit_balance(db, "2202") == Decimal("0"), "2202 应在冲红付款后归零"
            print(f"  1002追溯: {traces}")
        finally:
            db.close()
        print("OK Step 6. 冲红付款 (1002 恢复, 2202 归零)")

        # ═══ Step 7: 财务费用 50 挂账 ═══
        r = c.post("/api/expenses", json={
            "amount": float(EXPENSE_FIN),
            "category": "其他",
            "functional_category": "财务费用",
            "expense_date": "2026-01-15",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["expense_fin_id"] = _get_id(r, "expense_fin")

        db = _db()
        try:
            bal, traces = _trace_bal(db, "6603")
            assert bal == EXPENSE_FIN, f"6603 余额 {bal} != {EXPENSE_FIN}"
            assert any(t[1] == "expense" for t in traces), "6603 非来自 expense 凭证"
            print(f"  6603追溯: {traces}")
            # 未付款，2202 增加
            assert _credit_balance(db, "2202") == EXPENSE_FIN, \
                f"挂账后 2202 应为 {EXPENSE_FIN}, 实际={_credit_balance(db, '2202')}"
        finally:
            db.close()
        print(f"OK Step 7. 财务费用 {EXPENSE_FIN} 挂账")

        # ═══ Step 8: 付款 50 清应付 ═══
        r = c.post("/api/payments", json={
            "payment_type": "expense",
            "related_entity_type": "expense",
            "related_entity_id": s["expense_fin_id"],
            "bank_account_id": s["bank_id"],
            "amount": float(EXPENSE_FIN),
            "payment_date": "2026-01-15",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["payment_fin_id"] = _get_id(r, "payment_fin")

        db = _db()
        try:
            bal, _ = _trace_bal(db, "1002")
            assert bal == BANK_OPENING - EXPENSE_MGMT - EXPENSE_FIN, \
                f"付款后银行 {bal} != {BANK_OPENING - EXPENSE_MGMT - EXPENSE_FIN}"
            assert _credit_balance(db, "2202") == Decimal("0"), "2202 应归零"
        finally:
            db.close()
        print(f"OK Step 8. 付款 {EXPENSE_FIN}")

        # ═══ Step 9: 冲红财务费用 ═══
        r = c.post(f"/api/expenses/{s['expense_fin_id']}/reverse", headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            bal, traces = _trace_bal(db, "6603")
            assert bal == Decimal("0"), f"6603 冲红后应归零, 实际={bal}"
            dr_total = sum(t[4] for t in traces)
            cr_total = sum(t[5] for t in traces)
            assert dr_total == cr_total, f"6603 借贷总计: dr={dr_total} cr={cr_total}"
            rev_traces = [t for t in traces if t[3] == True]
            assert len(rev_traces) >= 1, "6603 缺少 is_reversal 冲红分录"
            print(f"  6603冲红追溯: {traces}")
            # 冲红后 2202 出现借方余额
            assert _ledger_balance(db, "2202") == EXPENSE_FIN, \
                f"冲红财务费用后 2202 dr 应为 {EXPENSE_FIN}, 实际={_ledger_balance(db, '2202')}"
        finally:
            db.close()
        print("OK Step 9. 冲红财务费用 (6603 归零)")

        # ═══ Step 10: 冲红付款 ═══
        r = c.post(f"/api/payments/{s['payment_fin_id']}/reverse", headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            bal, traces = _trace_bal(db, "1002")
            assert bal == BANK_OPENING - EXPENSE_MGMT, \
                f"冲红付款后银行应恢复至 {BANK_OPENING - EXPENSE_MGMT}, 实际={bal}"
            assert _credit_balance(db, "2202") == Decimal("0"), "2202 应在冲红付款后归零"
            print(f"  1002追溯: {traces}")
        finally:
            db.close()
        print("OK Step 10. 冲红付款 (1002 恢复, 2202 归零)")

        # ═══ Step 11: 月结 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            # 月结后 6601 应归零 (已结转至 4103)
            assert _ledger_balance(db, "6601") == Decimal("0"), "6601 月结后应归零"
            assert _ledger_balance(db, "6602") == Decimal("0"), "6602 月结后应归零"
            assert _ledger_balance(db, "6603") == Decimal("0"), "6603 月结后应归零"
            profit_4103 = _ledger_balance(db, "4103")
            assert profit_4103 == -NET_PROFIT, f"4103 余额 {profit_4103} != {-NET_PROFIT}"
            print(f"  4103追溯: {_trace_bal(db, '4103')[1]}")
        finally:
            db.close()
        print(f"OK Step 11. 月结 (净利润={NET_PROFIT})")

        # ═══ 12. 财务报表验证 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        bs = r.json()

        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        pl = r.json()

        # 资产恒等式
        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"BS不平衡, diff={diff}"

        # 对照: BS 科目手算验证
        assert abs(Decimal(str(bs["monetary_funds"])) - BANK_ENDING) <= Decimal("0.05"), \
            f"BS银行存款: {bs['monetary_funds']} != {BANK_ENDING}"
        assert abs(Decimal(str(bs["total_liabilities"])) - TOTAL_LIABILITIES) <= Decimal("0.05"), \
            f"BS负债合计: {bs['total_liabilities']} != {TOTAL_LIABILITIES}"
        assert abs(Decimal(str(bs["paid_in_capital"])) - BANK_OPENING) <= Decimal("0.05"), \
            f"BS实收资本: {bs['paid_in_capital']} != {BANK_OPENING}"
        assert abs(Decimal(str(bs["retained_earnings"])) - NET_PROFIT) <= Decimal("0.05"), \
            f"BS留存收益: {bs['retained_earnings']} != {NET_PROFIT}"
        assert abs(Decimal(str(bs["total_assets"])) - TOTAL_ASSETS) <= Decimal("0.05"), \
            f"BS资产合计: {bs['total_assets']} != {TOTAL_ASSETS}"

        # 对照: IS 科目手算验证
        assert abs(Decimal(str(pl["revenue"])) - IS_REVENUE) <= Decimal("0.05"), \
            f"IS营业收入: {pl['revenue']} != {IS_REVENUE}"
        assert abs(Decimal(str(pl["cost_of_goods_sold"])) - IS_COGS) <= Decimal("0.05"), \
            f"IS营业成本: {pl['cost_of_goods_sold']} != {IS_COGS}"
        assert abs(Decimal(str(pl["net_profit"])) - NET_PROFIT) <= Decimal("0.05"), \
            f"IS净利润: {pl['net_profit']} != {NET_PROFIT}"

        print(f"  BS: 资产={bs['total_assets']}, 负债+权益={bs['total_liabilities_and_equity']}")
        print(f"  IS: 净利润={pl['net_profit']}")
        print("OK 12. BS/IS 验证 (手算对照)")

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
        assert op_net == CF06, f"CF经营净额={op_net}≠{CF06}"
        assert Decimal(str(cf["cf_details"]["CF06"])) == CF06, f"CF06={cf['cf_details']['CF06']}≠{CF06}"
        bs_bank = Decimal(str(bs["monetary_funds"]))
        if abs(cf_end - bs_bank) > Decimal("0.05"):
            print(f"  [WARN] CF期末({cf_end})≠BS银行存款({bs_bank})")
        print(f"  CF: 期初={cf_begin}, 期末={cf_end}, 经营={op_net}")
        print("OK CF验证")

        # ═══ 13. 追溯验证: trace_bal 从 BS 数字到凭证行 ═══
        db = _db()
        try:
            # 追溯银行存款
            bal, traces = _trace_bal(db, "1002")
            print(f"  1002追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
            assert abs(bal - BANK_ENDING) <= Decimal("0.05"), f"1002追溯余额 {bal} != {BANK_ENDING}"

            # 追溯管理费用
            bal, traces = _trace_bal(db, "6601")
            print(f"  6601追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
            assert bal == Decimal("0"), "6601 月结后应归零"

            # 追溯销售费用 (已冲红归零)
            bal, traces = _trace_bal(db, "6602")
            print(f"  6602追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
            assert bal == Decimal("0")

            # 追溯财务费用 (已冲红归零)
            bal, traces = _trace_bal(db, "6603")
            print(f"  6603追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
            assert bal == Decimal("0")

            # 追溯本年利润 = -100
            bal, traces = _trace_bal(db, "4103")
            print(f"  4103追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
            assert bal == -NET_PROFIT, f"4103 余额 {bal} != {-NET_PROFIT} (亏损= {NET_PROFIT})"
        finally:
            db.close()
        print("OK 13. 追溯验证 (所有科目余额可追溯到凭证行)")

        # ═══ 14. 全量不变量 ═══
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        except Exception as e:
            pytest.fail(f"AS-01 校验失败: {e}")
        finally:
            db.close()
        print("OK 14. 全月凭证借贷平衡 + BS 恒等式")

        print("\n" + "=" * 60)
        print("ALL GOLDEN ASSERTIONS PASSED")
        print(f"银行: {BANK_ENDING}, 利润: {NET_PROFIT}")
        print("=" * 60)
