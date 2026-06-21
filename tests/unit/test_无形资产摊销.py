"""无形资产摊销计算单元测试（TDD）

依据：《小企业会计准则》第四十一条 + §二/2.3 无形资产摊销
公式：
  - 月摊销额 = 原值 ÷ 使用寿命(月)
  - 累计摊销 = 月摊销额 × min(已用月数, 使用寿命)
  - 净值 = 原值 - 累计摊销

不依赖数据库 / app，只测 AccountingEngine 纯计算逻辑。
"""
import sys
import os
import pytest
from decimal import Decimal

# 将 backend 加入 sys.path（与 tests/conftest.py 一致）
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from accounting_engine import AccountingEngine, AccountingError, AccountingErrorCode

_engine = AccountingEngine()


@pytest.mark.unit
class TestIntangibleAmortization:
    """无形资产年限平均法摊销 — 《小企业会计准则》§二/2.3"""

    def test_basic_amortization(self):
        """正常路径：120,000 元 / 60 月 / 已用 12 月

        月摊销 = 120,000 / 60 = 2,000.00
        累计摊销 = 2,000.00 × 12 = 24,000.00
        净值 = 120,000 - 24,000 = 96,000.00
        """
        result = _engine.calculate_intangible_amortization(
            original_value=Decimal("120000"),
            useful_life=60,
            months_used=12,
        )
        assert result.monthly_amortization == Decimal("2000.00")
        assert result.accumulated_amortization == Decimal("24000.00")
        assert result.net_value == Decimal("96000.00")

    def test_q2_quantization(self):
        """金额精度：10000 / 36 月 = 277.78（不是 277.777...，遵循 AP-7 金额精度规范）

        累计摊销 = 277.78 × 6 = 1666.68
        净值 = 10000 - 1666.68 = 8333.32
        """
        result = _engine.calculate_intangible_amortization(
            original_value=Decimal("10000"),
            useful_life=36,
            months_used=6,
        )
        assert result.monthly_amortization == Decimal("277.78")
        assert result.accumulated_amortization == Decimal("1666.68")
        assert result.net_value == Decimal("8333.32")

    def test_months_used_exceeds_useful_life(self):
        """已用月数超过使用寿命：累计摊销封顶为原值，净值归 0

        120,000 / 60 月，已用 72 月（超过 60 月）
        月摊销 = 2,000.00
        累计摊销 = 2,000.00 × min(72, 60) = 2,000.00 × 60 = 120,000.00
        净值 = 120,000 - 120,000 = 0
        """
        result = _engine.calculate_intangible_amortization(
            original_value=Decimal("120000"),
            useful_life=60,
            months_used=72,
        )
        assert result.monthly_amortization == Decimal("2000.00")
        assert result.accumulated_amortization == Decimal("120000.00")
        assert result.net_value == Decimal("0")

    def test_zero_months_used(self):
        """已用 0 月：累计摊销 = 0，净值 = 原值

        月摊销仍可计算（用于后续期间预测），但累计为 0。
        """
        result = _engine.calculate_intangible_amortization(
            original_value=Decimal("120000"),
            useful_life=60,
            months_used=0,
        )
        assert result.monthly_amortization == Decimal("2000.00")
        assert result.accumulated_amortization == Decimal("0")
        assert result.net_value == Decimal("120000.00")

    def test_invalid_original_value_zero(self):
        """原值 = 0：抛 AccountingError(AMORTIZATION_ORIGINAL_VALUE_INVALID)"""
        with pytest.raises(AccountingError) as exc_info:
            _engine.calculate_intangible_amortization(
                original_value=Decimal("0"),
                useful_life=60,
                months_used=12,
            )
        assert exc_info.value.code == AccountingErrorCode.AMORTIZATION_ORIGINAL_VALUE_INVALID

    def test_invalid_original_value_negative(self):
        """原值 < 0：抛 AccountingError(AMORTIZATION_ORIGINAL_VALUE_INVALID)"""
        with pytest.raises(AccountingError) as exc_info:
            _engine.calculate_intangible_amortization(
                original_value=Decimal("-100"),
                useful_life=60,
                months_used=12,
            )
        assert exc_info.value.code == AccountingErrorCode.AMORTIZATION_ORIGINAL_VALUE_INVALID

    def test_invalid_useful_life_zero(self):
        """使用寿命 = 0：抛 AccountingError(AMORTIZATION_USEFUL_LIFE_ZERO)"""
        with pytest.raises(AccountingError) as exc_info:
            _engine.calculate_intangible_amortization(
                original_value=Decimal("120000"),
                useful_life=0,
                months_used=12,
            )
        assert exc_info.value.code == AccountingErrorCode.AMORTIZATION_USEFUL_LIFE_ZERO

    def test_invalid_useful_life_negative(self):
        """使用寿命 < 0：抛 AccountingError(AMORTIZATION_USEFUL_LIFE_ZERO)"""
        with pytest.raises(AccountingError) as exc_info:
            _engine.calculate_intangible_amortization(
                original_value=Decimal("120000"),
                useful_life=-5,
                months_used=12,
            )
        assert exc_info.value.code == AccountingErrorCode.AMORTIZATION_USEFUL_LIFE_ZERO
