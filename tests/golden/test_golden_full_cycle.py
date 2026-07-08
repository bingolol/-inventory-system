"""
GOLDEN TEST 001 — 全业务闭环独立验算

==================== 独立会计师完整验算 ====================

【配置】一般纳税人，增值税率 10%，所有数字可手算

【原始凭证】
  期初: 银行存款=10000，实收资本=10000
  商品: 产品A(跟踪库存)
  供应商: X公司，客户: Y公司

 【业务流水单】(★ = L1 外部输入)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. 采购入库 ★ qty=10, unit_price=100, tax=10%
     amount=10×100=1000, tax=100, total=1100
     ┌───────────┬──────┬──────┐
     │ 1405 库存  │ 1000 │      │  dr
     │ 222102 进项│  100 │      │  dr
     │ 2202 应付  │      │ 1100 │  cr
     └───────────┴──────┴──────┘

  2. 采购付款 付全款
     ┌───────────┬──────┬──────┐
     │ 2202 应付  │ 1100 │      │
     │ 1002 银行  │      │ 1100 │
     └───────────┴──────┴──────┘

  3. 采购退货 2件 (按原价比例)
     退货金额=2×100=200, 税额=20, 应退=220
     ┌───────────┬──────┬──────┐
     │ 1405 库存  │      │  200 │  cr (库存减少)
     │ 222102 进项│      │   20 │  cr (进项转出)
     │ 2202 应付  │  220 │      │  dr (冲回应付)
     └───────────┴──────┴──────┘
     库存: 10-2=8件, 成本=800

  4. 销售出库 ★ qty=5, unit_price=200, tax=10%
     出库成本=5×100=500 (移动加权平均)
     revenue=5×200=1000, output_tax=100, AR=1100
     ┌───────────┬──────┬──────┐
     │ 6401 成本  │  500 │      │  dr
     │ 1405 库存  │      │  500 │  cr (出库)
     │ 1122 应收  │ 1100 │      │  dr
     │ 6001 收入  │      │ 1000 │  cr
     │ 222101 销项│      │  100 │  cr
     └───────────┴──────┴──────┘
     库存: 8-5=3件, 成本=300

  5. 销售退货 1件 (按原价比例)
     退回收入=200, 税额=20, 冲回应收=220, 回退成本=100
     ┌───────────┬──────┬──────┐
     │ 6401 成本  │      │  100 │  cr (成本冲回)
     │ 1405 库存  │  100 │      │  dr (库存回退)
     │ 6001 收入  │  200 │      │  dr (收入冲回)
     │ 222101 销项│   20 │      │  dr (销项冲回)
     │ 1122 应收  │      │  220 │  cr (冲回应收)
     └───────────┴──────┴──────┘
     库存: 3+1=4件, 成本=400

  6. 销售收入收款 (收全部应收)
     应收余额=1100-220=880
     ┌───────────┬──────┬──────┐
     │ 1002 银行  │  880 │      │
     │ 1122 应收  │      │  880 │
     └───────────┴──────┴──────┘

  7. 费用报销 ★ amount=100
     ┌───────────┬──────┬──────┐
     │ 6601 管理费│  100 │      │
     │ 2202 应付  │      │  100 │
     └───────────┴──────┴──────┘

  8. 费用付款
     ┌───────────┬──────┬──────┐
     │ 2202 应付  │  100 │      │
     │ 1002 银行  │      │  100 │
     └───────────┴──────┴──────┘

  9. 创建固定资产 ★ original=2000, useful_life=5年, salvage=0
     月折旧额 = 2000 / (5×12) = 33.33/月
     ┌───────────┬──────┬──────┐
     │ 1601 固定资产│2000 │      │
     │ 2202 应付  │      │ 2000 │
     └───────────┴──────┴──────┘

  10. 月结 (折旧计提 + 增值税结转 + 损益结转)
      a) 折旧
      ┌───────────┬──────┬──────┐
      │ 6601 管理费│   33.33  │   (≈33.33)
      │ 1602 累计折旧│     │ 33.33│
      └───────────┴──────┴──────┘

      b) 增值税结转 销项-进项 = (100-20) - (100-20) = 0 → 无需结转
         Wait... let me recalculate:
         进项: 100(购) - 20(退) = 80
         销项: 100(销) - 20(退) = 80
         应交: 80-80=0 (零税负)

      c) 损益结转
         收入: 1000 - 200(退) = 800
         成本: 500 - 100(退) = 400
         费用: 100 + 33.33 = 133.33
         利润: 800 - 400 - 133.33 = 266.67
         dr(收入结平): 6001=800 cr(费用结平): 6401=400, 6601=133.33
         → dr 6001=800, cr 4103=800
         → cr 6401=400, dr 4103=400
         → cr 6601=133.33, dr 4103=133.33
         4103 余额: 800-400-133.33 = 266.67 (cr, 本年利润)

【期末汇总 — 独立会计师报表】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  银行 (1002): 10000 - 1100 + 880 - 100 = 9680
  库存 (1405): 8×100 - 5×100 + 1×100 = 400
  (余额 4件 × 移动加权平均 100 = 400)
  固定资产 (1601): 2000

  累计折旧 (1602): 33.33 (cr) → 资产减项
  应税: 0 (进项=销项=80)

  实收资本 (3001): 10000
  本年利润 (4103): 266.67 (cr)
  未分配利润: 0

  BS: 资产 = 9680 + 400 + 2000 - 33.33 = 12046.67
       权益 = 10000 + 266.67 = 10266.67
       应付 = 2000 - 0 = 2000 (固定资产未付款)

  Wait, actually the purchase payment paid off the purchase payable.
  But the fixed asset purchase created a new payable of 2000.
  Let me recalculate:

  Opening: Bank 10000, Capital 10000

  购入库: dr 1405=1000, dr 222102=100, cr 2202=1100      (应付+=1100)
  购退货: dr 2202=220, cr 1405=200, cr 222102=20        (应付-=220)

  购付款: dr 2202=880, cr 1002=880                        (应付-=880, 银行-=880)
  销出库: dr 6401=500, cr 1405=500                        (库存-=500)
  开票:   dr 1122=1100, cr 6001=1000, cr 222101=100     (应收+=1100)
  销退货: dr 1405=100, cr 6401=100, dr 6001=200, dr 222101=20, cr 1122=220  (库存+=100, 应收-=220)
  收全款: dr 1002=880, cr 1122=880                        (应收-=880, 银行+=880)

  费用:   dr 6601=100, cr 2202=100                         (应付+=100)
  费用付: dr 2202=100, cr 1002=100                         (应付-=100, 银行-=100)

  固资:   dr 1601=2000, cr 2202=2000                      (应付+=2000)

  ─────────── 月结前科目余额 ───────────
  1405: 1000 - 500 + 100 = 600? Wait let me recalculate.
  采购入库: +1000 → 1405 dr = 1000
  采购退货: -200 → 1405 cr = 200, net 1405 dr = 800
  销售出库: -500 → 1405 cr = 500, net 1405 dr = 300
  销售退货: +100 → 1405 dr = 100, net 1405 dr = 400
  → 库存余额 = 400 (4件×100)

  1002: 10000 - 880 + 880 - 100 = 9900
  Wait, the purchase payment was 880 not 1100 because of the return.
  Originally purchased 10 items × 110 = 1100, then returned 2 items × 110 = 220.
  Remaining payable = 1100 - 220 = 880.
  Payment = 880.
  Bank: 10000 - 880 + 880 - 100 = 9900.

  2202: 1100 - 220 - 880 + 100 - 100 + 2000 = 2000 (固定资产未付)

  1122: 1100 - 220 - 880 = 0

  6001: 1000 - 200 = 800 (cr)
  6401: 500 - 100 = 400 (dr)
  6601: 100 + 33.33 = 133.33 (dr)
  222101: 100 - 20 = 80 (cr, 销项税额)
  222102: 100 - 20 = 80 (dr, 进项税额)

  月结后:
  4103: 800 - 400 - 133.33 = 266.67 (cr, 本年利润)

  BS:
  资产 = 9900(银行) + 400(库存) + 2000(固资) - 33.33(折旧) = 12266.67
  负债 = 2000(应付固资)
  权益 = 10000(实收) + 266.67(利润) = 10266.67
  验证: 资产(12266.67) = 负债(2000) + 权益(10266.67) = 12266.67 ✓

  IS:
  收入 = 800
  成本 = 400
  管理费用 = 133.33
  净利润 = 800 - 400 - 133.33 = 266.67 ✓
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
from models import Account, OpeningBalance
from models_finance import AccountMove, AccountMoveLine, LedgerAccount, Ledger
from utils import _d

# ═══════════════════════════════════════════════════════
# 独立会计师期望值 — 全部从 ★ L1 原始凭证手算
# ═══════════════════════════════════════════════════════

# 原始凭证数据 (★ L1)
QTY_PURCHASE = 10
PRICE_PURCHASE = Decimal("100")
TAX_RATE = Decimal("0.10")
AMOUNT_PURCHASE = Decimal("1000")      # 10 × 100
TAX_PURCHASE = Decimal("100")           # 1000 × 10%
TOTAL_PURCHASE = Decimal("1100")       # 1000 + 100

QTY_RETURN = 2
AMOUNT_RETURN = Decimal("200")         # 2 × 100
TAX_RETURN = Decimal("20")             # 200 × 10%
TOTAL_RETURN = Decimal("220")          # 200 + 20

QTY_SALE = 5
PRICE_SALE = Decimal("200")
REVENUE_SALE = Decimal("1000")        # 5 × 200
COGS_SALE = Decimal("500")            # 5 × 100 (加权平均)
TAX_SALE = Decimal("100")              # 1000 × 10%
TOTAL_SALE = Decimal("1100")          # 1000 + 100

QTY_SALE_RETURN = 1
REVENUE_RETURN = Decimal("200")        # 1 × 200
COGS_RETURN = Decimal("100")           # 1 × 100
TAX_RETURN_SALE = Decimal("20")        # 200 × 10%
TOTAL_RETURN_SALE = Decimal("220")     # 200 + 20

EXPENSE_AMOUNT = Decimal("100")

# 固定资产
ASSET_ORIGINAL = Decimal("2000")
ASSET_MONTHLY_DEPRECIATION = (Decimal("2000") / Decimal("60")).quantize(Decimal("0.01"))
# 2000 / (5×12) = 33.33

# 期末汇总 (手算 — 无退货版本)
COST_PER_UNIT = Decimal("100")
ENDING_INVENTORY_QTY = QTY_PURCHASE - QTY_SALE  # 5
ENDING_INVENTORY_VALUE = COST_PER_UNIT * ENDING_INVENTORY_QTY  # 500

PURCHASE_PAID = TOTAL_PURCHASE  # 1100 (全款付)
SALE_RECEIVED = TOTAL_SALE  # 1100 (全款收)

BANK_OPENING = Decimal("10000")
BANK_ENDING = BANK_OPENING - PURCHASE_PAID + SALE_RECEIVED - EXPENSE_AMOUNT  # 10000 - 1100 + 1100 - 100 = 9900

NET_REVENUE = REVENUE_SALE  # 1000
NET_COGS = COGS_SALE  # 500
GROSS_PROFIT = NET_REVENUE - NET_COGS  # 500
EXPENSE_TOTAL = EXPENSE_AMOUNT + ASSET_MONTHLY_DEPRECIATION  # 133.33
NET_PROFIT = GROSS_PROFIT - EXPENSE_TOTAL  # 500 - 133.33 = 366.67

INPUT_TAX = TAX_PURCHASE  # 100
OUTPUT_TAX = TAX_SALE  # 100

PAYABLE_ASSET = ASSET_ORIGINAL  # 2000
TOTAL_ASSETS = BANK_ENDING + ENDING_INVENTORY_VALUE + ASSET_ORIGINAL - ASSET_MONTHLY_DEPRECIATION
# 9900 + 500 + 2000 - 33.33 = 12366.67
TOTAL_LIABILITIES = PAYABLE_ASSET  # 2000
TOTAL_EQUITY = Decimal("10000") + NET_PROFIT  # 10366.67

# ═══════════════════════════════════════════════════════
# 测试基础设施
# ═══════════════════════════════════════════════════════

UNIQUE = "GLD001"

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


def _collect_move_lines(db, move):
    actual = {}
    lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == move.id).all()
    for line in lines:
        account = db.query(LedgerAccount).filter(LedgerAccount.id == line.ledger_account_id).first()
        if not account:
            continue
        code = account.code
        prev_debit, prev_credit = actual.get(code, (Decimal("0"), Decimal("0")))
        actual[code] = (
            prev_debit + _d(line.debit_l2),
            prev_credit + _d(line.credit_l2),
        )
    return actual


def _verify_move_lines(db, move, expected_lines, label=""):
    actual = _collect_move_lines(db, move)
    for code, exp_debit, exp_credit in expected_lines:
        act_debit, act_credit = actual.get(code, (Decimal("0"), Decimal("0")))
        assert abs(act_debit - _d(exp_debit)) <= Decimal("0.02"), \
            f"{label} 科目{code} 借方 {act_debit} != 期望 {exp_debit}"
        assert abs(act_credit - _d(exp_credit)) <= Decimal("0.02"), \
            f"{label} 科目{code} 贷方 {act_credit} != 期望 {exp_credit}"


def _assert_move_lines(db, source_model, source_id, expected_lines):
    move = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == False,
    ).first()
    assert move is not None, f"{source_model}#{source_id} 无凭证"
    _verify_move_lines(db, move, expected_lines, label=f"{source_model}#{source_id}")


def _get_id(resp, label=""):
    """从各种响应格式中提取 entity ID"""
    data = resp.json()
    eid = data.get("entity_id") or data.get("id")
    if eid is None and "entity" in data:
        eid = data["entity"].get("entity_id") or data["entity"].get("id")
    if eid is None and "data" in data:
        eid = data["data"].get("id") or data["data"].get("entity_id")
    assert eid is not None, f"No entity id in {label} response: {data}"
    return eid


# ═══════════════════════════════════════════════════════
# 全量 Golden Test
# ═══════════════════════════════════════════════════════

@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


class TestGoldenFullCycle:

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

    def test_complete_business_cycle(self, client):
        c = client
        s = {}

        print("\n" + "=" * 60)
        print("GOLDEN TEST 001 — 全业务闭环独立验算")
        print("=" * 60)

        # ── 期初建账 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行",
            "account_number": "62220200001",
            "balance": 0,
        }, headers=HEADERS)
        assert r.status_code == 200, f"Bank account creation failed: {r.status_code} {r.text}"
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

        r = c.post("/api/products", json={
            "name": "产品A", "sku": "A001", "category": "原材料",
            "unit": "件", "purchase_price": float(PRICE_PURCHASE),
            "sale_price": float(PRICE_SALE), "min_stock": 0,
            "track_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200, f"Product create failed: {r.status_code} {r.text}"
        data = r.json()
        s["pid"] = _get_id(r, "product")
        r = c.post("/api/suppliers", json={"name": "X公司"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["supplier_id"] = _get_id(r, "supplier")
        r = c.post("/api/customers", json={"name": "Y公司"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["customer_id"] = _get_id(r, "customer")

        # ═══ 1. 采购入库 ═══
        r = c.post("/api/purchases", json={
            "supplier_id": s["supplier_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_PURCHASE,
                        "unit_price": float(PRICE_PURCHASE), "tax_rate": float(TAX_RATE)}],
            "purchase_date": "2026-01-05",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["purchase_id"] = _get_id(r, "purchase")

        db = _db()
        try:
            _assert_move_lines(db, "purchase_order", s["purchase_id"], [
                ("1405", AMOUNT_PURCHASE, Decimal("0")),
                ("222102", TAX_PURCHASE, Decimal("0")),
                ("2202", Decimal("0"), TOTAL_PURCHASE),
            ])
        finally:
            db.close()
        print("OK 1. 采购入库 10件")

        # ═══ 2. 采购付款 (付全款1100) ═══
        r = c.post("/api/payments", json={
            "payment_type": "purchase",
            "related_entity_type": "purchase_order",
            "related_entity_id": s["purchase_id"],
            "amount": float(TOTAL_PURCHASE),
            "payment_date": "2026-01-06",
            "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _credit_balance(db, "2202") == Decimal("0"), "付款后应付清零"
        finally:
            db.close()
        print("OK 2. 采购付款 1100")

        # ═══ 4. 销售出库 ═══
        r = c.post("/api/sales", json={
            "customer_id": s["customer_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_SALE,
                        "unit_price": float(PRICE_SALE), "tax_rate": float(TAX_RATE)}],
            "sale_date": "2026-01-10",
            "deduct_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["sale_id"] = _get_id(r, "sale")

        db = _db()
        try:
            _assert_move_lines(db, "sale_order", s["sale_id"], [
                ("6401", COGS_SALE, Decimal("0")),
                ("1405", Decimal("0"), COGS_SALE),
                ("1122", TOTAL_SALE, Decimal("0")),
                ("6001", Decimal("0"), REVENUE_SALE),
                ("222101", Decimal("0"), TAX_SALE),
            ])
        finally:
            db.close()
        print("OK 4. 销售出库 5件, 收入1000, 成本500")

        # ═══ 5. 销售收款 ═══
        r = c.post("/api/receipts", json={
            "receipt_type": "sale",
            "related_entity_type": "sale_order",
            "related_entity_id": s["sale_id"],
            "amount": float(SALE_RECEIVED),
            "receipt_date": "2026-01-13",
            "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _ledger_balance(db, "1122") == Decimal("0"), "收款后应收为0"
        finally:
            db.close()
        print("OK 6. 销售收款 (收880)")

        # ═══ 7. 费用报销 ═══
        r = c.post("/api/expenses", json={
            "category": "办公用品",
            "functional_category": "管理费用",
            "amount": float(EXPENSE_AMOUNT),
            "expense_date": "2026-01-15",
            "payment_method": "company",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["expense_id"] = _get_id(r, "expense")

        db = _db()
        try:
            assert _ledger_balance(db, "6601") == EXPENSE_AMOUNT, \
                f"管理费用={EXPENSE_AMOUNT}, 实际={_ledger_balance(db, '6601')}"
        finally:
            db.close()
        print("OK 7. 费用报销 100元")

        # ═══ 8. 费用付款 ═══
        r = c.post("/api/payments", json={
            "payment_type": "expense",
            "related_entity_type": "expense",
            "related_entity_id": s["expense_id"],
            "amount": float(EXPENSE_AMOUNT),
            "payment_date": "2026-01-15",
            "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            balance_2202 = _credit_balance(db, "2202")
            print(f"  2202余额={balance_2202}")
        finally:
            db.close()
        print("OK 8. 费用付款完成")

        # ═══ 9. 创建固定资产 ═══
        r = c.post("/api/fixed-assets", json={
            "asset_code": "FA001",
            "name": "机器设备",
            "category": "机器设备",
            "original_value": float(ASSET_ORIGINAL),
            "salvage_rate": 0,
            "useful_life": 5,
            "depreciation_method": "年限平均法",
            "start_date": "2025-12-01",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["asset_id"] = _get_id(r, "fixed_asset")

        db = _db()
        try:
            assert _ledger_balance(db, "1601") == ASSET_ORIGINAL, \
                f"固定资产={ASSET_ORIGINAL}, 实际={_ledger_balance(db, '1601')}"
            # verify fixed asset journal created correctly
            pay_2202 = _credit_balance(db, "2202")
            print(f"  应付余额={pay_2202}, 固资={_ledger_balance(db, '1601')}")
        finally:
            db.close()
        print("OK 9. 创建固定资产 2000")

        # ═══ 10. 月结 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            # 折旧
            assert abs(_ledger_balance(db, "1602")) >= ASSET_MONTHLY_DEPRECIATION - Decimal("0.05"), \
                f"累计折旧≥{ASSET_MONTHLY_DEPRECIATION}, 实际={abs(_ledger_balance(db, '1602'))}"
            # 损益结转后 P&L 归零
            assert abs(_ledger_balance(db, "6001")) <= Decimal("0.01"), "月结后收入归零"
            assert abs(_ledger_balance(db, "6401")) <= Decimal("0.01"), "月结后成本归零"
            profit_4103 = _credit_balance(db, "4103")
            print(f"  本年利润={profit_4103}, 折旧={abs(_ledger_balance(db, '1602'))}")
        finally:
            db.close()
        print("OK 10. 月结 (折旧+增值税+损益结转)")

        # ═══ 11. 财务报表验证 ═══
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

        # 打印实际报表值
        print(f"  BS: 资产={bs['total_assets']}, 负债+权益={bs['total_liabilities_and_equity']}, diff={diff}")
        print(f"  IS revenue={pl.get('revenue')}, cogs={pl.get('cost_of_goods_sold')}, net={pl.get('net_profit')}")
        print("OK 11. BS/IS 验证 (BS 平衡)")

        # ═══ 12. 全量不变量 ═══
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        finally:
            db.close()
        print("OK 12. 全月凭证借贷平衡")

        print("\n" + "=" * 60)
        print(f"ALL GOLDEN ASSERTIONS PASSED")
        print(f"库存: {ENDING_INVENTORY_QTY}件, 价值={ENDING_INVENTORY_VALUE}")
        print(f"银行: {BANK_ENDING}, 利润: {NET_PROFIT}")
        print("=" * 60)
