"""AccountingEngine 测试 - TDD 循环

Behavior 1: 发票金额自动计算（含税→不含税+税额）
Behavior 2: 发票金额平衡校验
Behavior 3: 固定资产折旧-年限平均法
Behavior 4: 固定资产折旧-双倍余额递减法
Behavior 5: 固定资产折旧-年数总和法
Behavior 6: 增值税计算（小规模纳税人）
Behavior 7: 企业所得税计算（小微企业优惠）
Behavior 8: 资产负债表平衡校验
Behavior 9: 利润表验证
"""

import sys
import os
import pytest
from decimal import Decimal
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from accounting_engine import AccountingEngine, InvoiceAmounts, AccountingError, AccountingErrorCode


@pytest.fixture
def engine():
    return AccountingEngine()


# ═══════════════════════════════════════════════════════════
# Behavior 1: 发票金额自动计算（Critical）
# ═══════════════════════════════════════════════════════════

def test_calculate_invoice_amounts_13_percent(engine):
    """13%税率：含税11300 → 不含税10000 + 税额1300"""
    result = engine.calculate_invoice_amounts(
        amount_with_tax=Decimal('11300'),
        tax_rate=Decimal('0.13')
    )
    assert result.amount_without_tax == Decimal('10000.00')
    assert result.tax_amount == Decimal('1300.00')
    assert result.amount_with_tax == Decimal('11300')


def test_calculate_invoice_amounts_9_percent(engine):
    """9%税率：含税10900 → 不含税10000 + 税额900"""
    result = engine.calculate_invoice_amounts(
        amount_with_tax=Decimal('10900'),
        tax_rate=Decimal('0.09')
    )
    assert result.amount_without_tax == Decimal('10000.00')
    assert result.tax_amount == Decimal('900.00')


def test_calculate_invoice_amounts_1_percent(engine):
    """1%税率：含税10100 → 不含税10000 + 税额100"""
    result = engine.calculate_invoice_amounts(
        amount_with_tax=Decimal('10100'),
        tax_rate=Decimal('0.01')
    )
    assert result.amount_without_tax == Decimal('10000.00')
    assert result.tax_amount == Decimal('100.00')


def test_calculate_invoice_amounts_3_percent(engine):
    """3%税率：含税10300 → 不含税10000 + 税额300"""
    result = engine.calculate_invoice_amounts(
        amount_with_tax=Decimal('10300'),
        tax_rate=Decimal('0.03')
    )
    assert result.amount_without_tax == Decimal('10000.00')
    assert result.tax_amount == Decimal('300.00')


# ═══════════════════════════════════════════════════════════
# Behavior 2: 发票金额平衡校验（Critical）
# ═══════════════════════════════════════════════════════════

def test_validate_invoice_amounts_balanced(engine):
    """平衡的情况：10000 + 1300 = 11300 → 通过"""
    # 不应抛出异常
    engine.validate_invoice_amounts(
        amount_without_tax=Decimal('10000.00'),
        tax_amount=Decimal('1300.00'),
        amount_with_tax=Decimal('11300.00')
    )


def test_validate_invoice_amounts_unbalanced(engine):
    """不平衡的情况：10000 + 1300 = 11400 → 抛出异常"""
    with pytest.raises(AccountingError) as exc_info:
        engine.validate_invoice_amounts(
            amount_without_tax=Decimal('10000.00'),
            tax_amount=Decimal('1300.00'),
            amount_with_tax=Decimal('11400.00')
        )
    assert exc_info.value.code == AccountingErrorCode.INVOICE_AMOUNTS_NOT_BALANCED
    assert "STOP_RETRYING" in exc_info.value.ai_instruction


# ═══════════════════════════════════════════════════════════
# Behavior 3: 固定资产折旧-年限平均法（High）
# ═══════════════════════════════════════════════════════════

def test_depreciation_straight_line_basic(engine):
    """年限平均法：原值10000，残值率5%，寿命60个月，已用12个月"""
    result = engine.calculate_depreciation_straight_line(
        original_value=Decimal('10000'),
        salvage_rate=Decimal('0.05'),
        useful_life=60,
        months_used=12
    )
    # 月折旧 = 10000 * (1 - 0.05) / 60 = 158.33
    # 累计折旧 = 158.33 * 12 = 1899.96
    assert result.monthly_depreciation == Decimal('158.33')
    assert result.accumulated_depreciation == Decimal('1899.96')
    assert result.net_value == Decimal('8100.04')


def test_depreciation_straight_line_full_life(engine):
    """年限平均法：已用时间超过使用寿命，折旧到残值"""
    result = engine.calculate_depreciation_straight_line(
        original_value=Decimal('10000'),
        salvage_rate=Decimal('0.05'),
        useful_life=60,
        months_used=72  # 超过60个月
    )
    # 累计折旧 = 158.33 * 60 = 9499.80
    assert result.accumulated_depreciation == Decimal('9499.80')
    assert result.net_value == Decimal('500.20')


def test_depreciation_straight_line_zero_life(engine):
    """年限平均法：使用寿命为0 → 抛出异常"""
    with pytest.raises(AccountingError) as exc_info:
        engine.calculate_depreciation_straight_line(
            original_value=Decimal('10000'),
            salvage_rate=Decimal('0.05'),
            useful_life=0,
            months_used=12
        )
    assert exc_info.value.code == AccountingErrorCode.DEPRECIATION_USEFUL_LIFE_ZERO


# ═══════════════════════════════════════════════════════════
# Behavior 4: 固定资产折旧-双倍余额递减法（High）
# ═══════════════════════════════════════════════════════════

def test_depreciation_double_declining_basic(engine):
    """双倍余额递减法：原值10000，寿命60个月，已用12个月"""
    result = engine.calculate_depreciation_double_declining(
        original_value=Decimal('10000'),
        useful_life=60,
        months_used=12
    )
    # 月折旧率 = 2 / 60 = 0.0333
    # 逐月递减，第11个月(0-indexed)折旧 = close to 229.57
    assert result.monthly_depreciation == Decimal('229.57')
    assert result.accumulated_depreciation == Decimal('3342.34')
    assert result.net_value == Decimal('6657.66')


def test_depreciation_double_declining_zero_life(engine):
    """双倍余额递减法：使用寿命为0 → 抛出异常"""
    with pytest.raises(AccountingError) as exc_info:
        engine.calculate_depreciation_double_declining(
            original_value=Decimal('10000'),
            useful_life=0,
            months_used=12
        )
    assert exc_info.value.code == AccountingErrorCode.DEPRECIATION_USEFUL_LIFE_ZERO


# ═══════════════════════════════════════════════════════════
# Behavior 5: 固定资产折旧-年数总和法（High）
# ═══════════════════════════════════════════════════════════

def test_depreciation_sum_of_years_basic(engine):
    """年数总和法：原值10000，残值率5%，寿命5年(60月)，已用12个月"""
    result = engine.calculate_depreciation_sum_of_years(
        original_value=Decimal('10000'),
        salvage_rate=Decimal('0.05'),
        useful_life=60,
        months_used=12
    )
    # 应计折旧总额 = 10000 * (1 - 0.05) = 9500
    # 年数总和 = 5 * 6 / 2 = 15（使用年数，非月数）
    # 第1年(月0~11): 剩余年数 5~4.08, 末月折旧≈215.51
    assert result.monthly_depreciation == Decimal('215.51')
    assert result.accumulated_depreciation == Decimal('2876.39')
    assert result.net_value == Decimal('7123.61')


def test_depreciation_sum_of_years_zero_life(engine):
    """年数总和法：使用寿命为0 → 抛出异常"""
    with pytest.raises(AccountingError) as exc_info:
        engine.calculate_depreciation_sum_of_years(
            original_value=Decimal('10000'),
            salvage_rate=Decimal('0.05'),
            useful_life=0,
            months_used=12
        )
    assert exc_info.value.code == AccountingErrorCode.DEPRECIATION_USEFUL_LIFE_ZERO


# ═══════════════════════════════════════════════════════════
# Behavior 6: 增值税计算（High）
# ═══════════════════════════════════════════════════════════

@pytest.mark.golden
def test_calculate_vat_small_scale_basic(engine):
    """小规模纳税人：不含税销售额100000，征收率3%，减按1%"""
    result = engine.calculate_vat(
        total_revenue=Decimal('100000'),
        taxpayer_type='small_scale'
    )
    # 季度≤30万：普票免税，未传 ordinary/special 默认全部为普票 → tax_payable=0
    assert result.tax_payable == Decimal('0.00')
    assert result.tax_rate == Decimal('0.03')
    assert result.reduction_amount > Decimal('0')
    assert "免征增值税" in result.reduction_item


def test_calculate_vat_small_scale_monthly_exemption(engine):
    """小规模纳税人：季度销售额≤30万，普票免征增值税"""
    result = engine.calculate_vat(
        total_revenue=Decimal('300000'),  # 季度30万
        taxpayer_type='small_scale'
    )
    # 季度≤30万：普票免税 → 应纳税额=0，附加税=0
    assert result.tax_payable == Decimal('0.00')
    assert result.surcharge_education == Decimal('0')
    assert result.surcharge_local_education == Decimal('0')
    assert result.surcharge_urban_construction == Decimal('0')


def test_calculate_vat_invalid_type(engine):
    """无效纳税人类型 → 抛出异常"""
    with pytest.raises(AccountingError) as exc_info:
        engine.calculate_vat(
            total_revenue=Decimal('100000'),
            taxpayer_type='invalid'
        )
    assert exc_info.value.code == AccountingErrorCode.VAT_TAXPAYER_TYPE_INVALID


# ═══════════════════════════════════════════════════════════
# Behavior 1: 一般纳税人增值税计算（销项-进项）
# ═══════════════════════════════════════════════════════════

@pytest.mark.golden
def test_calculate_vat_general_taxpayer_basic(engine):
    """一般纳税人：销项税额 - 进项税额 = 应纳税额"""
    result = engine.calculate_vat(
        total_revenue=Decimal('100000'),  # 不含税销售额
        taxpayer_type='general',
        input_tax=Decimal('8000'),  # 进项税额
        output_tax=Decimal('13000'),  # 销项税额（发票明细汇总）
    )
    # 销项税额 = 13000
    # 应纳税额 = 13000 - 8000 = 5000
    assert result.tax_payable_gross == Decimal('13000.00')
    assert result.tax_payable == Decimal('5000.00')
    assert result.tax_rate == Decimal('0.13')


@pytest.mark.golden
def test_calculate_vat_general_taxpayer_zero_input(engine):
    """一般纳税人：无进项税额"""
    result = engine.calculate_vat(
        total_revenue=Decimal('100000'),
        taxpayer_type='general',
        input_tax=Decimal('0'),
        output_tax=Decimal('13000'),
    )
    # 销项税额 = 13000
    # 应纳税额 = 13000 - 0 = 13000
    assert result.tax_payable_gross == Decimal('13000.00')
    assert result.tax_payable == Decimal('13000.00')


@pytest.mark.golden
def test_calculate_vat_general_taxpayer_surcharge(engine):
    """一般纳税人：附加税计算"""
    result = engine.calculate_vat(
        total_revenue=Decimal('100000'),
        taxpayer_type='general',
        input_tax=Decimal('8000'),
        output_tax=Decimal('13000'),
    )
    # 应纳税额 = 5000
    # 城市维护建设税 = 5000 * 7% = 350
    # 教育费附加 = 5000 * 3% = 150
    # 地方教育附加 = 5000 * 2% = 100
    assert result.surcharge_urban_construction == Decimal('350.00')
    assert result.surcharge_education == Decimal('150.00')
    assert result.surcharge_local_education == Decimal('100.00')


@pytest.mark.golden
def test_calculate_vat_surcharge_uses_l3_policy_constants(engine, monkeypatch):
    """附加税必须从 policy/surcharge_facts.py 事实源读取，禁止硬编码"""
    from policy import policy_engine as pe
    from policy.entity_profile import EntityProfile
    from policy.policy_engine import calculate_vat
    from policy.surcharge_facts import SurchargeFacts

    mock_facts = SurchargeFacts(
        rate_urban_construction=Decimal('0.14'),
        rate_education=Decimal('0.06'),
        rate_local_education=Decimal('0.04'),
        reduction_rate=Decimal('0.5'),
        no_reduction=Decimal('1'),
        ref_date=date.today(),
    )
    monkeypatch.setattr(pe, "load_surcharge_facts", lambda ref_date=None: mock_facts)

    profile = EntityProfile(
        vat_type="general", income_type="general",
        surcharge_halved=False, effective_date=date.today(),
    )
    result = calculate_vat(profile=profile, total_revenue=Decimal('100000'),
                           input_tax=Decimal('8000'), output_tax=Decimal('13000'))
    assert result.surcharge_urban_construction == Decimal('700.00')
    assert result.surcharge_education == Decimal('300.00')
    assert result.surcharge_local_education == Decimal('200.00')


# ═══════════════════════════════════════════════════════════
# Behavior 7: 企业所得税计算（High）
# ═══════════════════════════════════════════════════════════

def test_calculate_income_tax_small_micro_50w(engine):
    """小型微利企业：利润50万，实际税率5%"""
    result = engine.calculate_income_tax(
        profit=Decimal('500000'),
        taxpayer_type='small_micro'
    )
    # 应纳税所得额 = 500000
    # 减按25%计入 = 500000 * 25% = 125000
    # 按20%税率 = 125000 * 20% = 25000
    # 实际税负 = 25000 / 500000 = 5%
    assert result.tax_payable == Decimal('25000.00')
    assert result.tax_rate == Decimal('0.25')  # 法定税率


def test_calculate_income_tax_small_micro_200w(engine):
    """小型微利企业：利润200万，实际税率5%"""
    result = engine.calculate_income_tax(
        profit=Decimal('2000000'),
        taxpayer_type='small_micro'
    )
    # 应纳税所得额 = 2000000
    # 减按25%计入 = 2000000 * 25% = 500000
    # 按20%税率 = 500000 * 20% = 100000
    # 实际税负 = 100000 / 2000000 = 5%
    assert result.tax_payable == Decimal('100000.00')


def test_calculate_income_tax_negative_profit(engine):
    """负利润（亏损）→ 不计提所得税，返回0（不抛异常）

    依据：《小企业会计准则》§5.5 亏损不缴税
    与 engine_tax.py 的 max(cumulative_profit * rate, 0) 逻辑一致
    """
    result = engine.calculate_income_tax(
        profit=Decimal('-100000'),
        taxpayer_type='small_micro'
    )
    assert result.tax_payable == Decimal('0')
    assert result.actual_tax == Decimal('0')
    assert "亏损" in result.reduction_item


def test_calculate_income_tax_general_25pct(engine):
    """一般企业：利润50万，税率25%"""
    result = engine.calculate_income_tax(
        profit=Decimal('500000'),
        taxpayer_type='general'
    )
    # 应纳税额 = 500000 × 25% = 125000
    assert result.tax_payable == Decimal('125000.00')
    assert result.tax_rate == Decimal('0.25')
