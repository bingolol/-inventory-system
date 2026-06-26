"""FixedAssetEngine 单元测试 — TDD RED → GREEN → Refactor"""
from datetime import date
from decimal import Decimal
import pytest
import models
import models_finance
from models import FixedAsset, Account
from models_finance import Ledger, LedgerAccount
from engine_fixed_asset import FixedAssetEngine


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
        ("1002", "银行存款", "asset"),
        ("1601", "固定资产", "asset"),
        ("1602", "累计折旧", "asset"),
        ("6602", "管理费用", "expense"),
        ("6111", "资产处置收益", "income"),
        ("6711", "营业外支出", "expense"),
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
        asset_code="FA-TEST-001",
        name="测试设备",
        category="机器设备",
        original_value=Decimal("120000"),
        salvage_rate=Decimal("0.05"),
        useful_life=60,
        depreciation_method="年限平均法",
        start_date=date(2025, 1, 1),
        accumulated_depreciation=Decimal("0"),
        status="在用",
    )
    defaults.update(overrides)
    asset = FixedAsset(**defaults)
    db.add(asset)
    db.flush()
    return asset


class TestMonthlyDepreciationCalculation:

    def test_straight_line_basic(self, db, account, accts):
        asset = _create_asset(db)
        eng = FixedAssetEngine(db, account_id=1)
        result = eng.calculate_monthly(asset)
        assert result == Decimal("1900.00")

    def test_straight_line_partial_year(self, db, account, accts):
        asset = _create_asset(db, original_value=Decimal("60000"),
                              salvage_rate=Decimal("0"), useful_life=36,
                              asset_code="FA-TEST-002")
        eng = FixedAssetEngine(db, account_id=1)
        result = eng.calculate_monthly(asset)
        assert result == Decimal("1666.67")

    def test_already_fully_depreciated(self, db, account, accts):
        asset = _create_asset(db, accumulated_depreciation=Decimal("114000"))
        eng = FixedAssetEngine(db, account_id=1)
        result = eng.calculate_monthly(asset)
        assert result == Decimal("0")


class TestRecordDepreciation:

    def test_creates_journal_entry(self, db, account, accts):
        asset = _create_asset(db)
        eng = FixedAssetEngine(db, account_id=1)
        dep = eng.record_depreciation(asset.id, period="2025-06")
        assert dep is not None
        assert dep.asset_id == asset.id
        assert dep.period == "2025-06"
        assert dep.amount == Decimal("1900.00")

    def test_updates_accumulated_depreciation(self, db, account, accts):
        asset = _create_asset(db)
        eng = FixedAssetEngine(db, account_id=1)
        eng.record_depreciation(asset.id, period="2025-06")
        db.refresh(asset)
        assert asset.accumulated_depreciation == Decimal("1900.00")

    def test_idempotent_same_period(self, db, account, accts):
        asset = _create_asset(db)
        eng = FixedAssetEngine(db, account_id=1)
        dep1 = eng.record_depreciation(asset.id, period="2025-06")
        dep2 = eng.record_depreciation(asset.id, period="2025-06")
        assert dep1.id == dep2.id
        db.refresh(asset)
        assert asset.accumulated_depreciation == Decimal("1900.00")

    def test_multiple_periods(self, db, account, accts):
        asset = _create_asset(db)
        eng = FixedAssetEngine(db, account_id=1)
        eng.record_depreciation(asset.id, period="2025-06")
        eng.record_depreciation(asset.id, period="2025-07")
        db.refresh(asset)
        assert asset.accumulated_depreciation == Decimal("3800.00")

    def test_skip_retired_asset(self, db, account, accts):
        asset = _create_asset(db, status="报废")
        eng = FixedAssetEngine(db, account_id=1)
        dep = eng.record_depreciation(asset.id, period="2025-06")
        assert dep is None

    def test_stop_at_salvage_value(self, db, account, accts):
        asset = _create_asset(db, accumulated_depreciation=Decimal("113000"))
        eng = FixedAssetEngine(db, account_id=1)
        dep = eng.record_depreciation(asset.id, period="2025-06")
        assert dep.amount == Decimal("1000.00")
        db.refresh(asset)
        assert asset.accumulated_depreciation == Decimal("114000.00")


class TestBatchDepreciate:

    def test_batch_processes_all_active(self, db, account, accts):
        _create_asset(db, asset_code="FA-001")
        _create_asset(db, asset_code="FA-002",
                      original_value=Decimal("60000"),
                      useful_life=36)
        eng = FixedAssetEngine(db, account_id=1)
        results = eng.batch_depreciate(period="2025-06")
        assert len(results) == 2

    def test_batch_skips_retired(self, db, account, accts):
        _create_asset(db, asset_code="FA-001")
        _create_asset(db, asset_code="FA-002", status="报废")
        eng = FixedAssetEngine(db, account_id=1)
        results = eng.batch_depreciate(period="2025-06")
        assert len(results) == 1


class TestRecordDisposal:

    def test_disposal_scrap(self, db, account, accts):
        """报废（处置价格=0）→ 借:6711 营业外支出"""
        asset = _create_asset(db, accumulated_depreciation=Decimal("100000"))
        eng = FixedAssetEngine(db, account_id=1)
        eng.record_disposal(asset.id, disposal_price=Decimal("0"))
        db.refresh(asset)
        assert asset.status == "报废"

    def test_disposal_profit(self, db, account, accts):
        """处置价格 > 净值 → 贷:6111 资产处置收益"""
        asset = _create_asset(db, accumulated_depreciation=Decimal("100000"),
                              asset_code="FA-PROFIT")
        # 净值 = 120000 - 100000 = 20000，卖 30000，赚 10000
        eng = FixedAssetEngine(db, account_id=1)
        eng.record_disposal(asset.id, disposal_price=Decimal("30000"))
        db.refresh(asset)
        assert asset.status == "报废"

    def test_disposal_loss(self, db, account, accts):
        """处置价格 < 净值 → 借:6711 营业外支出"""
        asset = _create_asset(db, accumulated_depreciation=Decimal("100000"),
                              asset_code="FA-LOSS")
        # 净值 = 20000，卖 5000，亏 15000
        eng = FixedAssetEngine(db, account_id=1)
        eng.record_disposal(asset.id, disposal_price=Decimal("5000"))
        db.refresh(asset)
        assert asset.status == "报废"

    def test_disposal_break_even(self, db, account, accts):
        """处置价格 = 净值 → 无损益科目"""
        asset = _create_asset(db, accumulated_depreciation=Decimal("100000"),
                              asset_code="FA-BREAK")
        # 净值 = 20000，卖 20000，不赚不亏
        eng = FixedAssetEngine(db, account_id=1)
        eng.record_disposal(asset.id, disposal_price=Decimal("20000"))
        db.refresh(asset)
        assert asset.status == "报废"
