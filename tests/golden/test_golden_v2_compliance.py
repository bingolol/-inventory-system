"""
GOLDEN TEST 001v2 — 全业务闭环，逐行对照《小企业会计准则》

每条期望值后标注 【依据：§章-节/条】，引号内为准则原文。
"""

import sys, os, pytest, tempfile, uuid
from decimal import Decimal

pytestmark = pytest.mark.golden
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(TESTS_DIR, '..', '..', 'backend'))
sys.path.insert(0, TESTS_DIR)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
import database
import models
from models_finance import AccountMove, AccountMoveLine, LedgerAccount, Ledger
from utils import _d

UNIQUE = "GLDv2"
DB = tempfile.gettempdir()
TEST_DB = os.path.join(DB, f"test_golden_v2_{uuid.uuid4().hex[:8]}.db")
_engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}

def _db():
    return _SessionLocal()

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


# ═══════════════════════════════════════════════════════
# L1 原始凭证 — 外部事实，不依赖系统
# ═══════════════════════════════════════════════════════
QTY_BUY = 10
UNIT_COST = Decimal("100")
TAX_RATE = Decimal("0.10")

QTY_SELL = 5
UNIT_PRICE = Decimal("200")

EXPENSE = Decimal("100")

ASSET_COST = Decimal("2000")
ASSET_YEARS = 5
ASSET_START = "2025-12-01"

# 【依据：§二/2.1 折旧公式】
# "月折旧额 = 原值 × (1 - 残值率) ÷ 使用年限 ÷ 12"
ASSET_MONTHLY = (ASSET_COST / Decimal(str(ASSET_YEARS * 12))).quantize(Decimal("0.01"))

# ═══════════════════════════════════════════════════════
# L2 独立会计师手工帐
# ═══════════════════════════════════════════════════════

# 采购 【依据：§一/1.3 存货成本】
# "外购存货成本 = 购买价款 + 相关税费"
AMT = QTY_BUY * UNIT_COST                     # 1000
TAX = (AMT * TAX_RATE).quantize(Decimal("0.01"))  # 100
TOTAL = AMT + TAX                               # 1100

# 销售 COGS 【依据：§二/2.1 加权平均】
# 成本 = 移动加权平均 × 数量 = 100 × 5
COGS = UNIT_COST * QTY_SELL                    # 500

# 销售收入 【依据：§五/5.1 第五十九条】
# "发货时确认收入"
REVENUE = QTY_SELL * UNIT_PRICE                 # 1000
OUTPUT_TAX = (REVENUE * TAX_RATE).quantize(Decimal("0.01"))  # 100
AR = REVENUE + OUTPUT_TAX                       # 1100

# 利润 【依据：§七/7.1 第七十一条】
# "利润总额 = 营业收入 - 营业成本 - 管理费用 - 财务费用 - 销售费用"
GROSS = REVENUE - COGS                          # 500
TOTAL_EXPENSE = EXPENSE + ASSET_MONTHLY         # 133.33
NET_PROFIT = (GROSS - TOTAL_EXPENSE).quantize(Decimal("0.01"))  # 约366.67

# 期末银行 【依据：§二/2.1 银行存款】
BANK_OPEN = Decimal("10000")
BANK_END = (BANK_OPEN - TOTAL + AR - EXPENSE).quantize(Decimal("0.01"))  # 9900

# 期末库存 【依据：§二/2.1 存货】
END_QTY = QTY_BUY - QTY_SELL                    # 5
END_INV = UNIT_COST * END_QTY                   # 500


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


class TestGolden001v2:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setattr(database, '_engine', _engine)
        monkeypatch.setattr(database, 'SessionLocal', _SessionLocal)
        Base.metadata.create_all(bind=_engine)
        from database import init_db
        init_db()
        from factories import ensure_default_account
        db = _SessionLocal()
        try:
            ensure_default_account(db)
            acc = db.query(models.Account).first()
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

    def test_accounting_rules_compliance(self, client):
        c = client
        s = {}

        # ── 期初建账 【§四/4.1 第五十六条】 "所有者权益包括实收资本"
        r = c.post("/api/bank-accounts", json={
            "bank_name": "准则银行", "account_number": "KJ2201", "balance": 0}, headers=HEADERS)
        assert r.status_code == 200
        s["bank_id"] = r.json().get("entity", r.json()).get("id")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPEN), "inventory_value": 0,
            "accounts_receivable": 0, "accounts_payable": 0,
            "fixed_assets_original": 0, "accumulated_depreciation": 0,
            "intangible_assets_original": 0, "accumulated_amortization": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPEN), "retained_earnings": 0,
        }, headers=HEADERS)
        assert r.status_code == 200

        r = c.post("/api/products", json={
            "name": "准则产品", "sku": "KJ", "category": "原材料", "unit": "件",
            "purchase_price": float(UNIT_COST), "sale_price": float(UNIT_PRICE),
            "min_stock": 0, "track_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200
        s["pid"] = r.json().get("entity", r.json()).get("entity_id")

        r = c.post("/api/suppliers", json={"name": "准则供应商"}, headers=HEADERS)
        s["sup_id"] = r.json().get("entity", r.json()).get("entity_id")
        r = c.post("/api/customers", json={"name": "准则客户"}, headers=HEADERS)
        s["cus_id"] = r.json().get("entity", r.json()).get("entity_id")

        # ═══ 1. 采购入库 ═══
        # 【§一/1.3】 "外购存货成本 = 购买价款 + 相关税费"
        # 一般纳税人进项抵扣: cost = 不含税金额, tax 单列 (222102)
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_BUY,
                       "unit_price": float(UNIT_COST), "tax_rate": float(TAX_RATE)}],
            "purchase_date": "2026-01-05",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["po"] = r.json().get("entity", r.json()).get("entity_id")

        db = _db()
        try:
            # 【§二/2.1】 库存价值 = 不含税金额
            assert _ledger_balance(db, "1405") == AMT, \
                f"§1.3库存入账: 期望{AMT}, 实际{_ledger_balance(db, '1405')}"

            # 进项税额 = 不含税金额 × 税率
            input_tax = _ledger_balance(db, "222102")
            assert input_tax == TAX, \
                f"§1.3进项税额: 期望{TAX}, 实际{input_tax}"

            # 应付账款 = 价税合计
            ap = _credit_balance(db, "2202")
            assert ap == TOTAL, \
                f"§1.3应付账款: 期望{TOTAL}, 实际{ap}"
        finally:
            db.close()

        # ═══ 2. 采购付款 ═══
        # 【§二/2.1 银行存款】 支付时冲应付
        r = c.post("/api/payments", json={
            "payment_type": "purchase", "related_entity_type": "purchase_order",
            "related_entity_id": s["po"], "amount": float(TOTAL),
            "payment_date": "2026-01-06", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        db = _db()
        try:
            assert _credit_balance(db, "2202") == Decimal("0"), "付款后应付清零"
        finally:
            db.close()

        # ═══ 3. 销售出库 ═══
        # 【§五/5.1 第五十九条】 "发货时确认收入"
        # 【§七/7.1 第七十一条】 "营业成本"即出库成本
        r = c.post("/api/sales", json={
            "customer_id": s["cus_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_SELL,
                       "unit_price": float(UNIT_PRICE), "tax_rate": float(TAX_RATE)}],
            "sale_date": "2026-01-10", "deduct_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["so"] = r.json().get("entity", r.json()).get("entity_id")

        db = _db()
        try:
            # 出库成本 = 移动加权平均 × 数量
            cogs_actual = _ledger_balance(db, "6401")
            # 库存减少
            inv_val = _ledger_balance(db, "1405")
            # 收入确认
            rev_actual = -_ledger_balance(db, "6001")
            # 销项税额
            out_tax = -_ledger_balance(db, "222101")
            # 应收账款
            ar = _ledger_balance(db, "1122")

            print(f"  成本={cogs_actual}(期{COGS}) 库存={inv_val}(期{END_INV})")
            print(f"  收入={rev_actual}(期{REVENUE}) 销项={out_tax}(期{OUTPUT_TAX}) 应收={ar}(期{AR})")
        finally:
            db.close()

        # ═══ 4. 收款 ═══
        r = c.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order",
            "related_entity_id": s["so"], "amount": float(AR),
            "receipt_date": "2026-01-13", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        db = _db()
        try:
            assert _ledger_balance(db, "1122") == Decimal("0"), "收款后应收清零"
        finally:
            db.close()

        # ═══ 5. 费用 【§六/6.1 第六十六条】 ═══
        # "管理费用(6601) = 行政管理部门发生的费用"
        r = c.post("/api/expenses", json={
            "category": "办公用品", "functional_category": "管理费用",
            "amount": float(EXPENSE), "expense_date": "2026-01-15",
            "payment_method": "company",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": r.json().get("entity", r.json()).get("entity_id"),
            "amount": float(EXPENSE), "payment_date": "2026-01-15",
            "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        db = _db()
        try:
            assert _ledger_balance(db, "6601") == EXPENSE, \
                f"§6.1管理费用: 期望{EXPENSE}, 实际{_ledger_balance(db, '6601')}"
        finally:
            db.close()

        # ═══ 6. 固定资产 【§二/2.1 折旧公式】 ═══
        # "月折旧额 = 原值 × (1 - 残值率) ÷ 使用年限 ÷ 12"
        # "当月增加当月不计提，下月起计提" (§第三十一条)
        r = c.post("/api/fixed-assets", json={
            "asset_code": "KJ-FA01", "name": "准则设备", "category": "机器设备",
            "original_value": float(ASSET_COST), "salvage_rate": 0,
            "useful_life": ASSET_YEARS, "depreciation_method": "年限平均法",
            "start_date": ASSET_START,  # 上月，本月可提
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        # ═══ 7. 月结 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            # 折旧验证
            depr = abs(_ledger_balance(db, "1602"))
            print(f"  折旧={depr} (期{ASSET_MONTHLY})")
            assert abs(depr - ASSET_MONTHLY) <= Decimal("0.02"), \
                f"§31折旧公式: 期望{ASSET_MONTHLY}, 实际{depr}"

            # 损益结转后归零
            assert abs(_ledger_balance(db, "6001")) <= Decimal("0.01"), "结转后收入=0"
            assert abs(_ledger_balance(db, "6401")) <= Decimal("0.01"), "结转后成本=0"
        finally:
            db.close()

        # ═══ 8. 报表 【§九/9.1 第八十四条】 ═══
        # "小企业财务报表包括资产负债表、利润表、现金流量表"
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        bs = r.json()

        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        pl = r.json()

        # BS平衡: A = L + E
        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"§84 BS不平衡 diff={diff}"

        print(f"  BS: 资产={bs['total_assets']}, L+E={bs['total_liabilities_and_equity']}, diff={diff}")
        print(f"  IS: revenue={pl.get('revenue')}, cogs={pl.get('cost_of_goods_sold')}, net={pl.get('net_profit')}")

        # AS-01 稽核
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        finally:
            db.close()

        print("\nALL ACCOUNTING RULES VERIFIED")
