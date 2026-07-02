"""IntangibleAssetEngine 单元测试 — 日期规则：当月增加当月摊；处置当月不再摊"""
from datetime import date
from decimal import Decimal
import pytest
import models
from models import IntangibleAsset, Account
from models_finance import Ledger, LedgerAccount
from engine_intangible_asset import IntangibleAssetEngine


@pytest.fixture
def account(db):
    a = Account(id=1, name="测试", type="company", code="test")
    db.add(a)
    db.commit()
    return a


@pytest.fixture
def ledger(db, account):
    l = Ledger(id=1, name="测试账本", type="company", code="test")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def accts(db, ledger):
    seed = [
        ("1701", "无形资产", "asset"),
        ("1702", "累计摊销", "asset"),
        ("6601", "管理费用", "expense"),
        ("6301", "营业外收入", "income"),
        ("6701", "营业外支出", "expense"),
    ]
    result = {}
    for code, name, atype in seed:
        a = LedgerAccount(ledger_id=ledger.id, code=code, name=name, account_type=atype, is_leaf=True)
        db.add(a)
        db.flush()
        result[code] = a
    db.commit()
    return result


def _create_asset(db, **overrides):
    defaults = dict(
        account_id=1,
        asset_code="IA-TEST-001",
        name="测试软件",
        category="软件",
        original_value_l1=Decimal("120000"),
        useful_life_l3=60,
        start_date_l1=date(2025, 1, 1),
        accumulated_amortization_l4=Decimal("0"),
        status="使用中",
    )
    defaults.update(overrides)
    asset = IntangibleAsset(**defaults)
    db.add(asset)
    db.flush()
    return asset


class TestMonthlyAmortizationCalculation:

    def test_straight_line_basic(self, db, account, accts):
        asset = _create_asset(db)
        eng = IntangibleAssetEngine(db, account_id=1)
        result = eng.calculate_monthly(asset)
        assert result == Decimal("2000.00")

    def test_already_fully_amortized(self, db, account, accts):
        asset = _create_asset(db, accumulated_amortization_l4=Decimal("120000"))
        eng = IntangibleAssetEngine(db, account_id=1)
        result = eng.calculate_monthly(asset)
        assert result == Decimal("0")


class TestRecordAmortizationDateLogic:
    """核心日期规则：当月增加当月摊；处置当月不再摊"""

    def test_amortize_in_month_added(self, db, account, accts):
        """2025-06-15 新增，2025-06 应计提"""
        asset = _create_asset(db, start_date_l1=date(2025, 6, 15))
        eng = IntangibleAssetEngine(db, account_id=1)
        amort = eng.record_amortization(asset.id, period="2025-06")
        assert amort is not None
        assert amort.amount_l2 == Decimal("2000.00")

    def test_skip_period_before_start(self, db, account, accts):
        """2025-06 新增，2025-05 不计提"""
        asset = _create_asset(db, start_date_l1=date(2025, 6, 15))
        eng = IntangibleAssetEngine(db, account_id=1)
        amort = eng.record_amortization(asset.id, period="2025-05")
        assert amort is None

    def test_amortize_after_start(self, db, account, accts):
        """2025-01 新增，2025-06 计提"""
        asset = _create_asset(db, start_date_l1=date(2025, 1, 10))
        eng = IntangibleAssetEngine(db, account_id=1)
        amort = eng.record_amortization(asset.id, period="2025-06")
        assert amort is not None
        assert amort.amount_l2 == Decimal("2000.00")

    def test_skip_retired_asset(self, db, account, accts):
        """已报废资产不计提"""
        asset = _create_asset(db, status="已报废")
        eng = IntangibleAssetEngine(db, account_id=1)
        amort = eng.record_amortization(asset.id, period="2025-06")
        assert amort is None

    def test_updates_accumulated_amortization(self, db, account, accts):
        asset = _create_asset(db)
        eng = IntangibleAssetEngine(db, account_id=1)
        eng.record_amortization(asset.id, period="2025-06")
        db.refresh(asset)
        assert asset.accumulated_amortization_l4 == Decimal("2000.00")

    def test_idempotent_same_period(self, db, account, accts):
        asset = _create_asset(db)
        eng = IntangibleAssetEngine(db, account_id=1)
        amort1 = eng.record_amortization(asset.id, period="2025-06")
        amort2 = eng.record_amortization(asset.id, period="2025-06")
        assert amort1.id == amort2.id
        db.refresh(asset)
        assert asset.accumulated_amortization_l4 == Decimal("2000.00")

    def test_multiple_periods(self, db, account, accts):
        asset = _create_asset(db)
        eng = IntangibleAssetEngine(db, account_id=1)
        eng.record_amortization(asset.id, period="2025-06")
        eng.record_amortization(asset.id, period="2025-07")
        db.refresh(asset)
        assert asset.accumulated_amortization_l4 == Decimal("4000.00")


class TestBatchAmortize:

    def test_batch_processes_all_active(self, db, account, accts):
        _create_asset(db, asset_code="IA-001")
        _create_asset(db, asset_code="IA-002", original_value_l1=Decimal("60000"), useful_life_l3=36)
        eng = IntangibleAssetEngine(db, account_id=1)
        results = eng.batch_amortize(period="2025-06")
        assert len(results) == 2

    def test_batch_skips_retired(self, db, account, accts):
        _create_asset(db, asset_code="IA-001")
        _create_asset(db, asset_code="IA-002", status="已报废")
        eng = IntangibleAssetEngine(db, account_id=1)
        results = eng.batch_amortize(period="2025-06")
        assert len(results) == 1


class TestRecordDisposal:

    def test_disposal_scrap(self, db, account, accts):
        """报废（无处置收入）→ 状态变为已报废"""
        asset = _create_asset(db, accumulated_amortization_l4=Decimal("100000"))
        eng = IntangibleAssetEngine(db, account_id=1)
        eng.record_disposal(asset.id, disposal_date=date(2025, 6, 30))
        db.refresh(asset)
        assert asset.status == "已报废"
