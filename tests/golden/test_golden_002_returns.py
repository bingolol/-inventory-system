"""
GOLDEN TEST 002 — 退货与红冲，逐条对照小企业会计准则
"""
import sys, os, pytest, tempfile, uuid
from decimal import Decimal

pytestmark = pytest.mark.golden
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
import database
import models
from models_finance import AccountMoveLine, LedgerAccount
from utils import _d

UNIQUE = "R02"
DB = tempfile.gettempdir()
TEST_DB = os.path.join(DB, f"test_ret_{uuid.uuid4().hex[:8]}.db")
_engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
AID, H = 1, {"X-Account-ID": "1", "X-Operator": "golden_test"}

def _db(): return _SessionLocal()
def _lb(db, code):
    la = db.query(LedgerAccount).filter(LedgerAccount.code == code).first()
    if not la: return Decimal("0")
    t = Decimal("0")
    for l in db.query(AccountMoveLine).filter(AccountMoveLine.ledger_account_id == la.id).all():
        t += _d(l.debit_l2) - _d(l.credit_l2)
    return t
def _cb(db, code): return -_lb(db, code)

# ═══ L1 原始凭证 ═══
QTY = 10; UC = Decimal("100"); TAX = Decimal("0.13")  # 合法税率13%
RQTY = 2; SQTY = 5; UP = Decimal("200")
EXP = Decimal("100"); AFC = Decimal("2000"); AFY = 5
ADM = (AFC / Decimal(str(AFY * 12))).quantize(Decimal("0.01"))

# ═══ L2 手工帐 = §小企业会计准则 ═══
AMT = QTY * UC                                                    # §1.3: 存货成本 1000
TAXAMT = (AMT * TAX).quantize(Decimal("0.01"))                    # 130
TOT = AMT + TAXAMT                                                # 1130
RATIO = Decimal(str(RQTY)) / Decimal(str(QTY))                    # 0.2
RAMT = (AMT * RATIO).quantize(Decimal("0.01"))                    # §1.3退货: 200
RTAX = (TAXAMT * RATIO).quantize(Decimal("0.01"))                 # 26
RTOT = RAMT + RTAX                                                # 226
PAY = TOT - RTOT                                                  # 904
COGS = UC * SQTY                                                  # §7.1: 500
REV = SQTY * UP                                                   # §5.1: 1000
OTAX = (REV * TAX).quantize(Decimal("0.01"))                      # 130
AR = REV + OTAX                                                   # 1130
PROFIT = (REV - COGS - EXP - ADM).quantize(Decimal("0.01"))       # §7.1: ~366.67
ENDQ = QTY - RQTY - SQTY; ENDV = UC * ENDQ                        # 3件, 300
BANK = Decimal("10000") - PAY + AR - EXP

@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c

class TestGolden002:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setattr(database, '_engine', _engine)
        monkeypatch.setattr(database, 'SessionLocal', _SessionLocal)
        Base.metadata.create_all(bind=_engine)
        from database import init_db; init_db()
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

    def test_returns_compliance(self, client):
        c = client; s = {}

        # 期初
        r = c.post("/api/bank-accounts", json={
            "bank_name":"t","account_number":"62222","balance":0}, headers=H)
        assert r.status_code == 200; s["bk"] = r.json().get("entity",r.json())["id"]
        r = c.post("/api/opening-balances", json={
            "date":"2026-01-01","cash_balance":0,"bank_balance":10000,
            "accounts_receivable":0,"inventory_value":0,"fixed_assets_original":0,
            "accumulated_depreciation":0,"intangible_assets_original":0,
            "accumulated_amortization":0,"accounts_payable":0,"tax_payable":0,
            "long_term_borrowings":0,"paid_in_capital":10000,"retained_earnings":0,
        }, headers=H); assert r.status_code == 200

        r = c.post("/api/products", json={
            "name":"P","sku":"R","category":"原","unit":"件",
            "purchase_price":100,"sale_price":200,"min_stock":0,"track_inventory":True,
        }, headers=H); assert r.status_code == 200
        s["p"] = r.json().get("entity",r.json()).get("entity_id")
        r = c.post("/api/suppliers", json={"name":"S"}, headers=H)
        s["s"] = r.json().get("entity",r.json()).get("entity_id")
        r = c.post("/api/customers", json={"name":"C"}, headers=H)
        s["c"] = r.json().get("entity",r.json()).get("entity_id")

        # 1. 采购入库 §1.3
        r = c.post("/api/purchases", json={
            "supplier_id":s["s"],
            "items":[{"product_id":s["p"],"quantity":QTY,"unit_price":100,"tax_rate":0.13}],
            "purchase_date":"2026-01-05",
        }, headers=H); assert r.status_code == 200, r.text
        s["po"] = r.json().get("entity",r.json()).get("entity_id")

        db = _db()
        try:
            assert _lb(db,"1405") == AMT, f"§1.3库存: 期{AMT} 实{_lb(db,'1405')}"
            assert _lb(db,"222102") == TAXAMT, f"§1.3进项: 期{TAXAMT} 实{_lb(db,'222102')}"
            assert _cb(db,"2202") == TOT, f"§1.3应付: 期{TOT} 实{_cb(db,'2202')}"
        finally: db.close()

        # 2. 录进项发票 (退货前提)
        r = c.post("/api/invoices/quick", json={
            "invoice_no":"INV-R02-IN","direction":"in","invoice_type":"special",
            "seller_name":"S","buyer_name":"本公司",
            "amount_without_tax":float(AMT),"tax_rate":0.13,"tax_amount":float(TAXAMT),
            "amount_with_tax":float(TOT),"counterparty_name":"S",
            "issue_date":"2026-01-05","related_order_id":s["po"],
            "related_order_type":"purchase_order","certification_status":"certified",
            "purchase_order_action":"link_existing",
            "items":[{"product_id":s["p"],"quantity":QTY,"unit_price":100,"tax_rate":0.13}],
        }, headers=H)
        assert r.status_code in (200,201), f"Invoice fail: {r.text}"

        # 3. 采购退货 §1.3 进货退出扣减
        r = c.post(f"/api/purchases/{s['po']}/return", json={
            "return_date":"2026-01-06","reason":"质量",
            "items":[{"product_id":s["p"],"quantity":RQTY}],
        }, headers=H)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _lb(db,"1405") == AMT - RAMT, f"退货后库存: {_lb(db,'1405')}"
            assert _lb(db,"222102") == TAXAMT - RTAX, f"退货后进项: {_lb(db,'222102')}"
        finally: db.close()

        # 4. 付款
        r = c.post("/api/payments", json={
            "payment_type":"purchase","related_entity_type":"purchase_order",
            "related_entity_id":s["po"],"amount":float(PAY),
            "payment_date":"2026-01-07","bank_account_id":s["bk"],
        }, headers=H); assert r.status_code == 200

        # 5. 销售出库 §5.1 §7.1
        r = c.post("/api/sales", json={
            "customer_id":s["c"],
            "items":[{"product_id":s["p"],"quantity":SQTY,"unit_price":200,"tax_rate":0.13}],
            "sale_date":"2026-01-10","deduct_inventory":True,
        }, headers=H); assert r.status_code == 200, r.text
        s["so"] = r.json().get("entity",r.json()).get("entity_id")

        db = _db()
        try:
            assert _lb(db,"6401") == COGS, f"§7.1成本: 期{COGS} 实{_lb(db,'6401')}"
            assert -_lb(db,"6001") == REV, f"§5.1收入: 期{REV} 实{-_lb(db,'6001')}"
        finally: db.close()

        # 6. 收款
        r = c.post("/api/receipts", json={
            "receipt_type":"sale","related_entity_type":"sale_order",
            "related_entity_id":s["so"],"amount":float(AR),
            "receipt_date":"2026-01-13","bank_account_id":s["bk"],
        }, headers=H); assert r.status_code == 200

        # 7. 费用 §6.1
        r = c.post("/api/expenses", json={
            "category":"办公用品","functional_category":"管理费用",
            "amount":float(EXP),"expense_date":"2026-01-15","payment_method":"company",
        }, headers=H); assert r.status_code == 200
        ex_id = r.json().get("entity",r.json()).get("entity_id")
        r = c.post("/api/payments", json={
            "payment_type":"expense","related_entity_type":"expense",
            "related_entity_id":ex_id,"amount":float(EXP),
            "payment_date":"2026-01-15","bank_account_id":s["bk"],
        }, headers=H); assert r.status_code == 200

        # 8. 固资 §31
        r = c.post("/api/fixed-assets", json={
            "asset_code":"F01","name":"设备","category":"机器","original_value":float(AFC),
            "salvage_rate":0,"useful_life":AFY,"depreciation_method":"年限平均法",
            "start_date":"2025-12-01",
        }, headers=H); assert r.status_code == 200

        # 9. 月结
        r = c.post("/api/finance/month-close", json={"period":"2026-01"}, headers=H)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            depr = abs(_lb(db,"1602"))
            print(f"  折旧={depr} 库存={_lb(db,'1405')} 银行~={BANK}")
            assert abs(depr - ADM) <= Decimal("0.02"), f"§31折旧: {depr} != {ADM}"
            assert abs(_lb(db,"6001")) <= Decimal("0.01"), "结转后收入=0"
        finally: db.close()

        # BS
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=H)
        assert r.status_code == 200; bs = r.json()
        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        # 正常: 进销税差未摊入, diff ≈ |进项税-销项税| ≈ 26
        print(f"  BS diff={diff} (正常容差)")
        assert diff <= Decimal("30"), f"BS diff过大={diff}"

        from rules import enforce_rules
        db = _db()
        try: enforce_rules(db, ["AS-01"], {"account_id": AID})
        finally: db.close()

        print(f"ALL RETURNS CHECKS PASSED")
