"""GOLDEN TEST 004 — 个人垫付 §48 其他应付款"""
import sys, os, pytest, tempfile, uuid
from decimal import Decimal
pytestmark = pytest.mark.golden
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
import database, models
from models_finance import AccountMoveLine, LedgerAccount
from utils import _d

DB = tempfile.gettempdir(); H = {"X-Account-ID":"1","X-Operator":"golden_test"}
TEST_DB = os.path.join(DB, f"test_adv_{uuid.uuid4().hex[:8]}.db")
_engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
def _db(): return _SessionLocal()
def _lb(db, code):
    la = db.query(LedgerAccount).filter(LedgerAccount.code == code).first()
    if not la: return Decimal("0")
    t = Decimal("0")
    for l in db.query(AccountMoveLine).filter(AccountMoveLine.ledger_account_id == la.id).all():
        t += _d(l.debit_l2) - _d(l.credit_l2)
    return t

# ═══ L1 原始凭证 ═══
ADV_AMT = Decimal("500")     # 垫付金额
REPAY_AMT = Decimal("300")   # 部分偿还
# §48 其他应付款(2241): 垫付时 cr 2241, 偿还时 dr 2241
# 借方科目: 6601(管理费用) 或 1405(库存商品) 等白名单

@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c

class TestGolden004:
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

    def test_personal_advance_repay(self, client):
        c = client

        # 期初建账
        c.post("/api/bank-accounts", json={
            "bank_name":"B","account_number":"62244","balance":0}, headers=H)
        c.post("/api/opening-balances", json={
            "date":"2026-01-01","cash_balance":0,"bank_balance":5000,
            "accounts_receivable":0,"inventory_value":0,"fixed_assets_original":0,
            "accumulated_depreciation":0,"intangible_assets_original":0,
            "accumulated_amortization":0,"accounts_payable":0,"tax_payable":0,
            "long_term_borrowings":0,"paid_in_capital":5000,"retained_earnings":0,
        }, headers=H)
        ba = c.get("/api/bank-accounts", headers=H).json()
        items = ba.get("items", ba.get("entity", [ba]))
        bk_id = items[0].get("id", 1) if isinstance(items, list) else items.get("id", 1)

        # 1. 创建垫付 §48: dr 6601, cr 2241
        r = c.post("/api/personal-advances", json={
            "advancer_name":"张老板","amount":float(ADV_AMT),
            "advance_date":"2026-01-10","debit_account_code":"6601",
            "description":"垫付办公用品",
        }, headers=H)
        assert r.status_code == 200, r.text
        adv_id = r.json().get("entity",r.json()).get("entity_id", r.json().get("id"))

        db = _db()
        try:
            fee = _lb(db,"6601")
            credit_2241 = -_lb(db,"2241")
            print(f"  垫付: 费用={fee} (期{ADV_AMT}), 欠款={credit_2241} (期{ADV_AMT})")
            assert fee == ADV_AMT, f"§48借费用: 期{ADV_AMT} 实{fee}"
        finally: db.close()

        # 2. 部分偿还 §48: dr 2241, cr 1002
        r = c.post(f"/api/personal-advances/{adv_id}/repay", json={
            "amount":float(REPAY_AMT),"repayment_date":"2026-01-15",
            "bank_account_id":bk_id,
        }, headers=H)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            remain = -_lb(db,"2241")
            expect = ADV_AMT - REPAY_AMT  # 200
            print(f"  偿还{REPAY_AMT}: 剩余欠款={remain} (期{expect})")
            assert remain == expect, f"§48偿还后余额: 期{expect} 实{remain}"
        finally: db.close()

        # 3. 全额偿还
        r = c.post(f"/api/personal-advances/{adv_id}/repay", json={
            "amount":float(ADV_AMT - REPAY_AMT),"repayment_date":"2026-01-20",
            "bank_account_id":bk_id,
        }, headers=H)
        assert r.status_code == 200

        db = _db()
        try:
            assert -_lb(db,"2241") == Decimal("0"), f"全额偿还后欠款归零"
            print("  全额偿还: 欠款=0 ✓")
        finally: db.close()

        from rules import enforce_rules
        db = _db()
        try: enforce_rules(db, ["AS-01"], {"account_id": 1})
        finally: db.close()
        print("ALL ADVANCE CHECKS PASSED")
