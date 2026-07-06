"""小企业会计准则统一计算引擎

所有会计计算集中于此模块，确保：
1. 计算规则单一来源
2. 统一错误处理
3. 统一验证逻辑

⚠️ DEPRECATION NOTICE:
calculate_vat / calculate_income_tax 已迁移至 policy.policy_engine。
本模块保留旧方法作为桥接（委托至新引擎 + deprecation warning）。
L3 政策常量已迁移至 policy/ 目录，此处仅做向后兼容 re-export。
"""

import warnings
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from enum import Enum
from utils import _d
# split removed — tax is external input (BR-27)

# 金额精度：保留2位小数
Q2 = Decimal('0.01')


class AccountingErrorCode(str, Enum):
    """会计错误码"""
    # 发票相关
    INVOICE_AMOUNTS_NOT_BALANCED = "INVOICE_AMOUNTS_NOT_BALANCED"
    INVOICE_TAX_RATE_INVALID = "INVOICE_TAX_RATE_INVALID"

    # 增值税相关
    VAT_REVENUE_NEGATIVE = "VAT_REVENUE_NEGATIVE"
    VAT_TAXPAYER_TYPE_INVALID = "VAT_TAXPAYER_TYPE_INVALID"
    VAT_INPUT_TAX_NEGATIVE = "VAT_INPUT_TAX_NEGATIVE"
    VAT_CALCULATION_INVALID = "VAT_CALCULATION_INVALID"
    VAT_OUTPUT_TAX_MISSING = "VAT_OUTPUT_TAX_MISSING"

    # 所得税相关
    INCOME_TAX_PROFIT_NEGATIVE = "INCOME_TAX_PROFIT_NEGATIVE"
    INCOME_TAX_TAXPAYER_TYPE_INVALID = "INCOME_TAX_TAXPAYER_TYPE_INVALID"
    INCOME_TAX_CALCULATION_INVALID = "INCOME_TAX_CALCULATION_INVALID"

    # 折旧相关
    DEPRECIATION_METHOD_NOT_IMPLEMENTED = "DEPRECIATION_METHOD_NOT_IMPLEMENTED"
    DEPRECIATION_USEFUL_LIFE_ZERO = "DEPRECIATION_USEFUL_LIFE_ZERO"
    DEPRECIATION_SALVAGE_RATE_INVALID = "DEPRECIATION_SALVAGE_RATE_INVALID"
    DEPRECIATION_ORIGINAL_VALUE_INVALID = "DEPRECIATION_ORIGINAL_VALUE_INVALID"
    DEPRECIATION_CALCULATION_INVALID = "DEPRECIATION_CALCULATION_INVALID"

    # 无形资产摊销相关
    AMORTIZATION_ORIGINAL_VALUE_INVALID = "AMORTIZATION_ORIGINAL_VALUE_INVALID"
    AMORTIZATION_USEFUL_LIFE_ZERO = "AMORTIZATION_USEFUL_LIFE_ZERO"
    AMORTIZATION_CALCULATION_INVALID = "AMORTIZATION_CALCULATION_INVALID"

    # 凭证/科目 (引擎内部)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    BALANCE_NOT_EQUAL = "BALANCE_NOT_EQUAL"
    FIELD_REQUIRED = "FIELD_REQUIRED"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    NON_LEAF_ACCOUNT = "NON_LEAF_ACCOUNT"
    LINE_NOT_FOUND = "LINE_NOT_FOUND"
    UNKNOWN_MOVE_TYPE = "UNKNOWN_MOVE_TYPE"

    # 报表验证
    BALANCE_SHEET_UNBALANCED = "BALANCE_SHEET_UNBALANCED"
    INCOME_STATEMENT_INVALID = "INCOME_STATEMENT_INVALID"
    CASH_FLOW_STATEMENT_INVALID = "CASH_FLOW_STATEMENT_INVALID"


class AccountingError(Exception):
    """会计计算错误"""

    # AccountingErrorCode → HTTP status(均为输入/校验类,统一 422)
    STATUS_MAP: Dict[AccountingErrorCode, int] = {
        code: 422 for code in AccountingErrorCode
    }

    def __init__(
        self,
        code: AccountingErrorCode,
        message: str,
        ai_instruction: str = "",
        accounting_rule: str = "",
        calculation_detail: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.ai_instruction = ai_instruction
        self.accounting_rule = accounting_rule
        self.calculation_detail = calculation_detail or {}
        self.http_status = self.STATUS_MAP.get(code, 422)
        super().__init__(message)

    @staticmethod
    def _convert_decimals(obj: Any) -> Any:
        """Decimal → float,确保 JSON 可序列化(与 BusinessError.to_dict 一致)"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: AccountingError._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [AccountingError._convert_decimals(v) for v in obj]
        return obj

    def to_dict(self) -> Dict[str, Any]:
        """序列化为与 BusinessError 一致的 error 包络,额外保留会计专属引导字段

        返回结构::

            {"error": {
                "code": "...",
                "message": "...",
                "ai_instruction": "...",
                "accounting_rule": "...",        # 会计错误专属:法规依据
                "calculation_detail": {...},     # 会计错误专属:数值明细
            }}
        """
        code_val = self.code.value if isinstance(self.code, AccountingErrorCode) else str(self.code)
        return {
            "error": {
                "code": code_val,
                "message": self.message,
                "ai_instruction": self.ai_instruction,
                "accounting_rule": self.accounting_rule,
                "calculation_detail": self._convert_decimals(self.calculation_detail),
            }
        }


def _d(value) -> Decimal:
    """安全转换为 Decimal，None → 0"""
    if value is None:
        return Decimal('0')
    return Decimal(str(value))


@dataclass
class InvoiceAmounts:
    """发票金额三件套"""
    amount_without_tax: Decimal
    tax_amount: Decimal
    amount_with_tax: Decimal


@dataclass
class DepreciationResult:
    """折旧计算结果"""
    monthly_depreciation: Decimal
    accumulated_depreciation: Decimal
    net_value: Decimal


@dataclass
class AmortizationResult:
    """无形资产摊销计算结果"""
    monthly_amortization: Decimal
    accumulated_amortization: Decimal
    net_value: Decimal


@dataclass
class VATResult:
    """增值税计算结果（附加税已迁移至 SurchargeDeclaration L1 录入）"""
    total_revenue: Decimal
    tax_rate: Decimal
    tax_payable_gross: Decimal
    tax_reduction: Decimal
    tax_payable: Decimal
    reduction_item: str
    reduction_amount: Decimal


@dataclass
class IncomeTaxResult:
    """企业所得税计算结果"""
    profit: Decimal
    tax_rate: Decimal
    tax_payable: Decimal
    reduction_amount: Decimal
    actual_tax: Decimal
    reduction_item: str


class AccountingEngine:
    """小企业会计准则计算引擎

    ⚠️ DEPRECATED: calculate_vat / calculate_income_tax 已迁移至 policy.policy_engine。
    旧方法保留为桥接，自动委托至新引擎。新代码请直接使用 policy_engine 模块函数。
    """

    # ═══════════════════════════════════════════════════════════
    # 发票计算
    # ═══════════════════════════════════════════════════════════

    def calculate_invoice_amounts(
        self,
        amount_with_tax: Decimal,
        tax_rate: Decimal
    ) -> InvoiceAmounts:
        """根据含税金额和税率，自动计算不含税金额和税额

        公式：
        - 不含税金额 = 含税金额 / (1 + 税率)
        - 税额 = 含税金额 - 不含税金额

        依据：《小企业会计准则》§二/2.1 发票金额计算
        """
        amount_with_tax = _d(amount_with_tax)
        tax_rate = _d(tax_rate)

        # BR-27: tax is external input, not derived
        # Caller must pass tax_amount if rate > 0
        amount_without_tax = amount_with_tax  # default: assume all is base
        tax_amount = Decimal('0')

        return InvoiceAmounts(
            amount_without_tax=amount_without_tax,
            tax_amount=tax_amount,
            amount_with_tax=amount_with_tax
        )

    def validate_invoice_amounts(
        self,
        amount_without_tax: Decimal,
        tax_amount: Decimal,
        amount_with_tax: Decimal
    ) -> None:
        """校验发票金额等式：不含税 + 税额 == 价税合计

        依据：《小企业会计准则》§二/2.1 发票金额计算
        """
        amount_without_tax = _d(amount_without_tax)
        tax_amount = _d(tax_amount)
        amount_with_tax = _d(amount_with_tax)

        diff = (amount_without_tax + tax_amount) - amount_with_tax
        if abs(diff) > Q2:
            raise AccountingError(
                code=AccountingErrorCode.INVOICE_AMOUNTS_NOT_BALANCED,
                message=f"发票金额不平衡：不含税 {amount_without_tax} + 税额 {tax_amount} ≠ 价税合计 {amount_with_tax}（差额 {diff}）",
                ai_instruction="STOP_RETRYING. 发票金额计算错误，请检查：1) 不含税金额 = 含税金额 / (1 + 税率)；2) 税额 = 含税金额 - 不含税金额",
                accounting_rule="《小企业会计准则》§二/2.1 发票金额计算",
                calculation_detail={
                    "amount_without_tax": float(amount_without_tax),
                    "tax_amount": float(tax_amount),
                    "amount_with_tax": float(amount_with_tax),
                    "diff": float(diff)
                }
            )

    # ═══════════════════════════════════════════════════════════
    # 固定资产折旧
    # ═══════════════════════════════════════════════════════════

    def calculate_depreciation_straight_line(
        self,
        original_value: Decimal,
        salvage_rate: Decimal,
        useful_life: int,
        months_used: int
    ) -> DepreciationResult:
        """年限平均法（直线法）折旧

        公式：月折旧 = 原值 × (1 - 残值率) / 使用寿命(月)
        依据：《小企业会计准则》§二/2.2 固定资产折旧
        """
        original_value = _d(original_value)
        salvage_rate = _d(salvage_rate)

        # 输入校验
        if original_value <= Decimal('0'):
            raise AccountingError(
                code=AccountingErrorCode.DEPRECIATION_ORIGINAL_VALUE_INVALID,
                message=f"固定资产原值必须大于0：{original_value}",
                ai_instruction="STOP_RETRYING. 原值必须是正数",
                accounting_rule="《小企业会计准则》§二/2.2 固定资产折旧"
            )

        if salvage_rate < Decimal('0') or salvage_rate > Decimal('1'):
            raise AccountingError(
                code=AccountingErrorCode.DEPRECIATION_SALVAGE_RATE_INVALID,
                message=f"残值率必须在0到1之间：{salvage_rate}",
                ai_instruction="STOP_RETRYING. 残值率必须是0到1之间的小数（如0.05表示5%）",
                accounting_rule="《小企业会计准则》§二/2.2 固定资产折旧"
            )

        if useful_life <= 0:
            raise AccountingError(
                code=AccountingErrorCode.DEPRECIATION_USEFUL_LIFE_ZERO,
                message="固定资产使用寿命必须大于0",
                ai_instruction="STOP_RETRYING. 使用寿命必须是正整数（单位：月）",
                accounting_rule="《小企业会计准则》§二/2.2 固定资产折旧"
            )

        # 计算月折旧
        depreciable_value = original_value * (Decimal('1') - salvage_rate)
        monthly_depreciation = (depreciable_value / Decimal(str(useful_life))).quantize(Q2, rounding=ROUND_HALF_UP)

        # 计算累计折旧（不能超过应计折旧总额）
        actual_months = min(months_used, useful_life)
        accumulated_depreciation = (monthly_depreciation * Decimal(str(actual_months))).quantize(Q2, rounding=ROUND_HALF_UP)

        # 计算净值
        net_value = original_value - accumulated_depreciation

        return DepreciationResult(
            monthly_depreciation=monthly_depreciation,
            accumulated_depreciation=accumulated_depreciation,
            net_value=net_value
        )

    def calculate_depreciation_double_declining(
        self,
        original_value: Decimal,
        useful_life: int,
        months_used: int
    ) -> DepreciationResult:
        """双倍余额递减法折旧

        公式：月折旧率 = 2 / 使用寿命(月)
              月折旧 = 期初净值 × 月折旧率
        依据：《小企业会计准则》§二/2.2 固定资产折旧
        """
        original_value = _d(original_value)

        # 输入校验
        if original_value <= Decimal('0'):
            raise AccountingError(
                code=AccountingErrorCode.DEPRECIATION_ORIGINAL_VALUE_INVALID,
                message=f"固定资产原值必须大于0：{original_value}",
                ai_instruction="STOP_RETRYING. 原值必须是正数",
                accounting_rule="《小企业会计准则》§二/2.2 固定资产折旧"
            )

        if useful_life <= 0:
            raise AccountingError(
                code=AccountingErrorCode.DEPRECIATION_USEFUL_LIFE_ZERO,
                message="固定资产使用寿命必须大于0",
                ai_instruction="STOP_RETRYING. 使用寿命必须是正整数（单位：月）",
                accounting_rule="《小企业会计准则》§二/2.2 固定资产折旧"
            )

        # 计算月折旧率
        monthly_rate = Decimal('2') / Decimal(str(useful_life))

        # 逐月计算折旧
        net_value = original_value
        total_depreciation = Decimal('0')
        monthly_depreciation = Decimal('0')

        for month in range(months_used):
            monthly_depreciation = (net_value * monthly_rate).quantize(Q2, rounding=ROUND_HALF_UP)
            net_value -= monthly_depreciation
            total_depreciation += monthly_depreciation

            # 净值不能低于0
            if net_value < Decimal('0'):
                net_value = Decimal('0')
                break

        return DepreciationResult(
            monthly_depreciation=monthly_depreciation,
            accumulated_depreciation=total_depreciation,
            net_value=net_value
        )

    def calculate_depreciation_sum_of_years(
        self,
        original_value: Decimal,
        salvage_rate: Decimal,
        useful_life: int,
        months_used: int
    ) -> DepreciationResult:
        """年数总和法折旧

        公式：年数总和 = n × (n + 1) / 2
              年折旧 = (原值 - 残值) × (剩余年限 / 年数总和)
        依据：《小企业会计准则》§二/2.2 固定资产折旧
        """
        original_value = _d(original_value)
        salvage_rate = _d(salvage_rate)

        # 输入校验
        if original_value <= Decimal('0'):
            raise AccountingError(
                code=AccountingErrorCode.DEPRECIATION_ORIGINAL_VALUE_INVALID,
                message=f"固定资产原值必须大于0：{original_value}",
                ai_instruction="STOP_RETRYING. 原值必须是正数",
                accounting_rule="《小企业会计准则》§二/2.2 固定资产折旧"
            )

        if salvage_rate < Decimal('0') or salvage_rate > Decimal('1'):
            raise AccountingError(
                code=AccountingErrorCode.DEPRECIATION_SALVAGE_RATE_INVALID,
                message=f"残值率必须在0到1之间：{salvage_rate}",
                ai_instruction="STOP_RETRYING. 残值率必须是0到1之间的小数（如0.05表示5%）",
                accounting_rule="《小企业会计准则》§二/2.2 固定资产折旧"
            )

        if useful_life <= 0:
            raise AccountingError(
                code=AccountingErrorCode.DEPRECIATION_USEFUL_LIFE_ZERO,
                message="固定资产使用寿命必须大于0",
                ai_instruction="STOP_RETRYING. 使用寿命必须是正整数（单位：月）",
                accounting_rule="《小企业会计准则》第三十条"
            )

        # 计算年数总和（useful_life 是月数，转为年数）
        n = useful_life // 12
        sum_of_years = n * (n + 1) // 2

        # 计算应计折旧总额
        depreciable_value = original_value * (Decimal('1') - salvage_rate)

        # 逐月计算折旧
        total_depreciation = Decimal('0')
        monthly_depreciation = Decimal('0')
        current_value = original_value

        for month in range(months_used):
            # 计算当前月份对应的剩余年限
            remaining_months = useful_life - month
            remaining_years = remaining_months / 12

            # 月折旧 = 应计折旧总额 × (剩余年限 / 年数总和) / 12
            monthly_depreciation = (depreciable_value * Decimal(str(remaining_years)) / Decimal(str(sum_of_years)) / Decimal('12')).quantize(Q2, rounding=ROUND_HALF_UP)

            current_value -= monthly_depreciation
            total_depreciation += monthly_depreciation

            # 净值不能低于残值
            salvage_value = original_value * salvage_rate
            if current_value < salvage_value:
                current_value = salvage_value
                break

        return DepreciationResult(
            monthly_depreciation=monthly_depreciation,
            accumulated_depreciation=total_depreciation,
            net_value=current_value
        )

    # ═══════════════════════════════════════════════════════════
    # 无形资产摊销
    # ═══════════════════════════════════════════════════════════

    def calculate_intangible_amortization(
        self,
        original_value: Decimal,
        useful_life: int,
        months_used: int
    ) -> AmortizationResult:
        """无形资产年限平均法摊销

        公式：
        - 月摊销额 = 原值 ÷ 使用寿命(月)
        - 累计摊销 = 月摊销额 × min(已用月数, 使用寿命)
        - 净值 = 原值 - 累计摊销

        依据：《小企业会计准则》§二/2.3 无形资产摊销 + 第四十一条
        > 无形资产应当在其使用寿命内采用年限平均法进行摊销。
        > 小企业不能可靠估计无形资产使用寿命的，摊销期不得低于 10 年。
        """
        original_value = _d(original_value)

        # 输入校验：原值必须大于 0
        if original_value <= Decimal('0'):
            raise AccountingError(
                code=AccountingErrorCode.AMORTIZATION_ORIGINAL_VALUE_INVALID,
                message=f"无形资产原值必须大于0：{original_value}",
                ai_instruction="STOP_RETRYING. 原值必须是正数",
                accounting_rule="《小企业会计准则》§二/2.3 无形资产摊销"
            )

        # 输入校验：使用寿命必须大于 0（单位：月）
        if useful_life <= 0:
            raise AccountingError(
                code=AccountingErrorCode.AMORTIZATION_USEFUL_LIFE_ZERO,
                message="无形资产使用寿命必须大于0",
                ai_instruction="STOP_RETRYING. 使用寿命必须是正整数（单位：月）",
                accounting_rule="《小企业会计准则》§二/2.3 无形资产摊销"
            )

        # 月摊销额 = 原值 ÷ 使用寿命(月)（Q2 量化，符合 AP-7 金额精度规范）
        monthly_amortization = (original_value / Decimal(str(useful_life))).quantize(Q2, rounding=ROUND_HALF_UP)

        # 累计摊销：已用月数不超过使用寿命，超出部分不再摊销
        actual_months = min(months_used, useful_life)
        accumulated_amortization = (monthly_amortization * Decimal(str(actual_months))).quantize(Q2, rounding=ROUND_HALF_UP)

        # 净值 = 原值 - 累计摊销
        net_value = original_value - accumulated_amortization

        return AmortizationResult(
            monthly_amortization=monthly_amortization,
            accumulated_amortization=accumulated_amortization,
            net_value=net_value
        )

    # ═══════════════════════════════════════════════════════════
    # 增值税计算
    # ═══════════════════════════════════════════════════════════

    def calculate_vat(
        self,
        total_revenue: Decimal,
        taxpayer_type: str,
        input_tax: Decimal = Decimal('0'),
        output_tax: Decimal = None,
        ordinary_revenue: Decimal = Decimal('0'),
        special_revenue: Decimal = Decimal('0'),
        carry_forward: Decimal = Decimal('0')
    ) -> VATResult:
        """[DEPRECATED] 计算增值税 — 已迁移至 policy.policy_engine.calculate_vat

        旧调用点自动桥接至新引擎。新代码请直接 import policy.calculate_vat。
        """
        if taxpayer_type not in ('small_scale', 'general'):
            raise AccountingError(
                code=AccountingErrorCode.VAT_TAXPAYER_TYPE_INVALID,
                message=f"无效的纳税人类型：{taxpayer_type}，有效值：small_scale, general",
                ai_instruction="STOP_RETRYING. 纳税人类型只能是 small_scale（小规模）或 general（一般）"
            )

        warnings.warn(
            "AccountingEngine.calculate_vat is deprecated. Use policy.policy_engine.calculate_vat instead.",
            DeprecationWarning, stacklevel=2,
        )
        from policy.entity_profile import EntityProfile
        from policy.policy_engine import calculate_vat as _new_calculate_vat
        from policy.entity_profile import SURCHARGE_HALVED_TYPES

        profile = EntityProfile(
            vat_type=taxpayer_type,
            income_type="small_micro" if taxpayer_type == "small_scale" else "general",
            surcharge_halved=taxpayer_type in SURCHARGE_HALVED_TYPES,
            effective_date=date.today(),
        )
        return _new_calculate_vat(
            profile=profile,
            total_revenue=total_revenue,
            input_tax=input_tax,
            output_tax=output_tax,
            ordinary_revenue=ordinary_revenue,
            special_revenue=special_revenue,
            carry_forward=carry_forward,
        )

    # ═══════════════════════════════════════════════════════════
    # 企业所得税计算
    # ═══════════════════════════════════════════════════════════

    def calculate_income_tax(
        self,
        profit: Decimal,
        taxpayer_type: str,
        entity_type: str = "company"
    ) -> IncomeTaxResult:
        """[DEPRECATED] 计算企业所得税 — 已迁移至 policy.policy_engine.calculate_income_tax

        旧调用点自动桥接至新引擎。新代码请直接 import policy.calculate_income_tax。
        """
        warnings.warn(
            "AccountingEngine.calculate_income_tax is deprecated.",
            DeprecationWarning, stacklevel=2,
        )
        from policy.entity_profile import EntityProfile
        from policy.policy_engine import calculate_income_tax as _new_calculate_income_tax

        profile = EntityProfile(
            vat_type="" if entity_type == "personal" else "general",
            income_type="personal" if entity_type == "personal"
                else ("small_micro" if taxpayer_type in ("small_scale", "small_micro") else "general"),
            surcharge_halved=taxpayer_type in ("small_scale", "small_micro") or entity_type == "personal",
            effective_date=date.today(),
        )
        return _new_calculate_income_tax(
            profile=profile,
            profit=profit,
        )
