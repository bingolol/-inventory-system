"""GOLDEN TEST 003 — 固定资产全流程 §29 入账 §31 折旧 §84 报表

验证方式：只通过报表 API 比对系统输出与独立计算引擎的预期值。
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from golden_helpers import make_engine, _get_id
from independent_accounting_engine import calculate, Facts, FixedAsset

_engine, _SessionLocal = make_engine()
H = {"X-Account-ID":"1","X-Operator":"golden_test"}

# ═══ L1 业务事实（硬编码）═══
ORIGINAL = Decimal("60000"); SALVAGE = Decimal("0.05"); MONTHS = 60
PERIODS = 2  # 2026-01 和 2026-02 两期折旧


class TestGolden003:
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

    def test_fixed_asset_lifecycle(self, client):
        c = client; s = {}

        # ── 期初建账 §84 ──
        c.post("/api/bank-accounts", json={
            "bank_name":"B","account_number":"62233","balance":0}, headers=H)
        c.post("/api/opening-balances", json={
            "date":"2026-01-01","cash_balance":0,"bank_balance":100000,
            "accounts_receivable":0,"inventory_value":0,"fixed_assets_original":0,
            "accumulated_depreciation":0,"intangible_assets_original":0,
            "accumulated_amortization":0,"accounts_payable":0,"tax_payable":0,
            "long_term_borrowings":0,"paid_in_capital":100000,"retained_earnings":0,
        }, headers=H)
        c.post("/api/suppliers", json={"name":"S"}, headers=H)

        # 1. 创建固定资产 §29
        r = c.post("/api/fixed-assets", json={
            "asset_code":"FA001","name":"钻孔机","category":"机器设备",
            "original_value":float(ORIGINAL),"salvage_rate":float(SALVAGE),
            "useful_life":MONTHS,"depreciation_method":"年限平均法",
            "start_date":"2025-12-01",
        }, headers=H)
        assert r.status_code == 200, f"FA create: {r.text}"
        s["fa"] = _get_id(r, "fixed_asset")

        # 2. 一月月结
        r = c.post("/api/finance/month-close", json={"period":"2026-01"}, headers=H)
        assert r.status_code == 200

        # 3. 二月月结
        r = c.post("/api/finance/month-close", json={"period":"2026-02"}, headers=H)
        assert r.status_code == 200

        # ═══ L2 独立计算期望值 ═══
        expected = calculate(Facts(
            opening_bank=Decimal("100000"),
            opening_paid_in_capital=Decimal("100000"),
            income_tax_rate=Decimal("0.05"),  # 小微企业实际税负（独立从税务局核定单确认）
            fixed_assets=[FixedAsset(ORIGINAL, MONTHS, periods_depreciated=PERIODS, salvage_rate=SALVAGE)],
        ))
        assert expected.interlock_ok, expected.interlock_messages

        # ═══ L3 报表 API 验证 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-02-28", headers=H)
        assert r.status_code == 200, r.text
        bs = r.json()

        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-02-28", headers=H)
        assert r.status_code == 200, r.text
        pl = r.json()

        tol = Decimal("0.05")
        assert abs(Decimal(str(bs["total_assets"])) - expected.balance_sheet.total_assets) <= tol, \
            f"§84资产总计: 实际{bs['total_assets']} != 期望{expected.balance_sheet.total_assets}"
        assert abs(Decimal(str(bs["total_liabilities"])) - expected.balance_sheet.total_liabilities) <= tol, \
            f"§84负债合计: 实际{bs['total_liabilities']} != 期望{expected.balance_sheet.total_liabilities}"
        assert abs(Decimal(str(bs["total_equity"])) - expected.balance_sheet.total_equity) <= tol, \
            f"§84权益合计: 实际{bs['total_equity']} != 期望{expected.balance_sheet.total_equity}"
        assert abs(Decimal(str(bs["monetary_funds"])) - expected.balance_sheet.monetary_funds) <= tol, \
            f"§84货币资金: 实际{bs['monetary_funds']} != 期望{expected.balance_sheet.monetary_funds}"
        assert abs(Decimal(str(bs["fixed_assets_net"])) - expected.balance_sheet.fixed_assets_net) <= tol, \
            f"§84固定资产净值: 实际{bs['fixed_assets_net']} != 期望{expected.balance_sheet.fixed_assets_net}"
        assert abs(Decimal(str(bs["accounts_payable"])) - expected.balance_sheet.accounts_payable) <= tol, \
            f"§84应付账款: 实际{bs['accounts_payable']} != 期望{expected.balance_sheet.accounts_payable}"
        assert abs(Decimal(str(bs["retained_earnings"])) - expected.balance_sheet.retained_earnings) <= tol, \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{expected.balance_sheet.retained_earnings}"

        assert abs(Decimal(str(pl["revenue"])) - expected.income_statement.revenue) <= tol, \
            f"§84营业收入: 实际{pl['revenue']} != 期望{expected.income_statement.revenue}"
        assert abs(Decimal(str(pl["net_profit"])) - expected.income_statement.net_profit) <= tol, \
            f"§84净利润: 实际{pl['net_profit']} != 期望{expected.income_statement.net_profit}"
