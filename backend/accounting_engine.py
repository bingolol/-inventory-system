"""小企业会计准则统一计算引擎

所有会计计算集中于此模块，确保：
1. 计算规则单一来源
2. 统一错误处理
3. 统一验证逻辑
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any
from enum import Enum

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
        return {
            "error": {
                "code": self.code.value,
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
class VATResult:
    """增值税计算结果"""
    total_revenue: Decimal
    tax_rate: Decimal
    tax_payable_gross: Decimal
    tax_reduction: Decimal
    tax_payable: Decimal
    surcharge_education: Decimal
    surcharge_local_education: Decimal
    surcharge_stamp: Decimal
    surcharge_total: Decimal
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
    """小企业会计准则计算引擎"""

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

        # 计算不含税金额
        amount_without_tax = (amount_with_tax / (Decimal('1') + tax_rate)).quantize(Q2, rounding=ROUND_HALF_UP)

        # 计算税额
        tax_amount = (amount_with_tax - amount_without_tax).quantize(Q2, rounding=ROUND_HALF_UP)

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

        # 计算年数总和
        n = useful_life
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
    # 增值税计算
    # ═══════════════════════════════════════════════════════════

    def calculate_vat(
        self,
        total_revenue: Decimal,
        taxpayer_type: str,
        input_tax: Decimal = Decimal('0')
    ) -> VATResult:
        """计算增值税

        依据：《小企业会计准则》§二/2.4 增值税 + 增值税暂行条例
        一般纳税人：应纳税额 = 销项税额 - 进项税额
        小规模纳税人：征收率3%，2023-2027年减按1%征收。
        """
        total_revenue = _d(total_revenue)
        input_tax = _d(input_tax)

        # 输入校验
        if taxpayer_type not in ['small_scale', 'general']:
            raise AccountingError(
                code=AccountingErrorCode.VAT_TAXPAYER_TYPE_INVALID,
                message=f"无效的纳税人类型：{taxpayer_type}，有效值：small_scale, general",
                ai_instruction="STOP_RETRYING. 纳税人类型只能是 small_scale（小规模）或 general（一般）"
            )

        if total_revenue < Decimal('0'):
            raise AccountingError(
                code=AccountingErrorCode.VAT_REVENUE_NEGATIVE,
                message=f"营业收入不能为负：{total_revenue}",
                ai_instruction="STOP_RETRYING. 营业收入为负值不符合业务逻辑，请检查数据",
                accounting_rule="《小企业会计准则》§二/2.4 增值税"
            )

        if input_tax < Decimal('0'):
            raise AccountingError(
                code=AccountingErrorCode.VAT_INPUT_TAX_NEGATIVE,
                message=f"进项税额不能为负：{input_tax}",
                ai_instruction="STOP_RETRYING. 进项税额为负值不符合业务逻辑，请检查数据",
                accounting_rule="《小企业会计准则》§二/2.4 增值税"
            )

        if taxpayer_type == 'general':
            # 一般纳税人：销项税额 - 进项税额
            tax_rate = Decimal('0.13')
            tax_payable_gross = (total_revenue * tax_rate).quantize(Q2, rounding=ROUND_HALF_UP)
            tax_payable = tax_payable_gross - input_tax

            # 输出交叉校验：应纳税额 = 销项税额 - 进项税额
            expected_tax_payable = tax_payable_gross - input_tax
            if abs(tax_payable - expected_tax_payable) > Q2:
                raise AccountingError(
                    code=AccountingErrorCode.VAT_CALCULATION_INVALID,
                    message=f"增值税计算错误：应纳税额 {tax_payable} ≠ 销项税额 {tax_payable_gross} - 进项税额 {input_tax}",
                    accounting_rule="《小企业会计准则》§二/2.4 增值税",
                    calculation_detail={
                        "tax_payable_gross": float(tax_payable_gross),
                        "input_tax": float(input_tax),
                        "tax_payable": float(tax_payable),
                        "expected_tax_payable": float(expected_tax_payable)
                    }
                )

            # 附加税费
            surcharge_education = (tax_payable * Decimal('0.03')).quantize(Q2, rounding=ROUND_HALF_UP)
            surcharge_local_education = (tax_payable * Decimal('0.02')).quantize(Q2, rounding=ROUND_HALF_UP)
            surcharge_stamp = (tax_payable * Decimal('0.07')).quantize(Q2, rounding=ROUND_HALF_UP)
            surcharge_total = surcharge_education + surcharge_local_education + surcharge_stamp
            tax_reduction = Decimal('0')
            reduction_item = "一般纳税人"

        else:
            # 小规模纳税人：征收率3%，减按1%征收
            tax_rate = Decimal('0.03')
            tax_payable_gross = total_revenue * tax_rate

            # 减免税额 = 应纳税额 × 2/3（减按1%征收，减免2/3）
            tax_reduction = (tax_payable_gross * Decimal('2') / Decimal('3')).quantize(Q2, rounding=ROUND_HALF_UP)

            # 应纳税额 = 不含税销售额 × 1%
            tax_payable = (total_revenue * Decimal('0.01')).quantize(Q2, rounding=ROUND_HALF_UP)

            # 输出交叉校验：应纳税额 = 不含税销售额 × 1%
            expected_tax_payable = (total_revenue * Decimal('0.01')).quantize(Q2, rounding=ROUND_HALF_UP)
            if abs(tax_payable - expected_tax_payable) > Q2:
                raise AccountingError(
                    code=AccountingErrorCode.VAT_CALCULATION_INVALID,
                    message=f"增值税计算错误：应纳税额 {tax_payable} ≠ 不含税销售额 {total_revenue} × 1%",
                    accounting_rule="《小企业会计准则》§二/2.4 增值税",
                    calculation_detail={
                        "total_revenue": float(total_revenue),
                        "tax_payable": float(tax_payable),
                        "expected_tax_payable": float(expected_tax_payable)
                    }
                )

            # 附加税费（2023-2027年小微企业50%减征优惠）
            monthly_revenue = total_revenue / Decimal('3')
            if monthly_revenue <= Decimal('100000'):
                surcharge_education = Decimal('0')
                surcharge_local_education = Decimal('0')
                reduction_item = "小微企业免征增值税"
            else:
                surcharge_education = (tax_payable * Decimal('0.03') * Decimal('0.5')).quantize(Q2, rounding=ROUND_HALF_UP)
                surcharge_local_education = (tax_payable * Decimal('0.02') * Decimal('0.5')).quantize(Q2, rounding=ROUND_HALF_UP)
                reduction_item = "小规模纳税人增值税减征"

            surcharge_stamp = (tax_payable * Decimal('0.07') * Decimal('0.5')).quantize(Q2, rounding=ROUND_HALF_UP)
            surcharge_total = surcharge_education + surcharge_local_education + surcharge_stamp

        return VATResult(
            total_revenue=total_revenue,
            tax_rate=tax_rate,
            tax_payable_gross=tax_payable_gross.quantize(Q2),
            tax_reduction=tax_reduction,
            tax_payable=tax_payable.quantize(Q2),
            surcharge_education=surcharge_education,
            surcharge_local_education=surcharge_local_education,
            surcharge_stamp=surcharge_stamp,
            surcharge_total=surcharge_total,
            reduction_item=reduction_item,
            reduction_amount=tax_reduction
        )

    # ═══════════════════════════════════════════════════════════
    # 企业所得税计算
    # ═══════════════════════════════════════════════════════════

    def calculate_income_tax(
        self,
        profit: Decimal,
        taxpayer_type: str
    ) -> IncomeTaxResult:
        """计算企业所得税

        依据：《小企业会计准则》§二/2.5 企业所得税
        - 年应纳税所得额 ≤ 300万：减按25%计入，按20%税率缴纳，实际税负5%
        - 年应纳税所得额 > 300万：法定税率25%

        法规依据：《财政部 税务总局关于小微企业和个体工商户所得税优惠政策的公告》(2023年第12号)
        """
        profit = _d(profit)

        # 输入校验
        if profit < Decimal('0'):
            raise AccountingError(
                code=AccountingErrorCode.INCOME_TAX_PROFIT_NEGATIVE,
                message=f"利润不能为负：{profit}",
                ai_instruction="STOP_RETRYING. 利润为负表示亏损，不需要缴纳企业所得税",
                accounting_rule="《小企业会计准则》§二/2.5 企业所得税"
            )

        # 纳税人类型校验（允许 small_micro 或 general，其他类型默认走一般企业）
        valid_taxpayer_types = ['small_micro', 'general']
        if taxpayer_type not in valid_taxpayer_types:
            # 默认按一般企业处理，但记录警告
            taxpayer_type = 'general'

        # 法定税率25%
        tax_rate = Decimal('0.25')

        # 小型微利企业优惠
        reduction_amount = Decimal('0')
        reduction_item = ""

        if taxpayer_type == 'small_micro' and profit <= Decimal('3000000'):
            # 小型微利企业：减按25%计入应纳税所得额，按20%税率缴纳
            # 实际税负 = 25% * 20% = 5%
            tax_payable = (profit * Decimal('0.25') * Decimal('0.20')).quantize(Q2, rounding=ROUND_HALF_UP)
            reduction_item = "小型微利企业减免（≤300万，实际税负5%）"
            reduction_amount = (profit * tax_rate - tax_payable).quantize(Q2, rounding=ROUND_HALF_UP)
        else:
            # 法定税率25%
            tax_payable = (profit * tax_rate).quantize(Q2, rounding=ROUND_HALF_UP)
            if taxpayer_type == 'small_micro':
                reduction_item = "不符合小型微利企业优惠条件（>300万）"
            else:
                reduction_item = "一般企业（法定税率25%）"

        # 输出交叉校验：应纳税额 = 应纳税所得额 × 税率 - 减免税额
        expected_tax_payable = (profit * tax_rate - reduction_amount).quantize(Q2, rounding=ROUND_HALF_UP)
        if abs(tax_payable - expected_tax_payable) > Q2:
            raise AccountingError(
                code=AccountingErrorCode.INCOME_TAX_CALCULATION_INVALID,
                message=f"企业所得税计算错误：应纳税额 {tax_payable} ≠ 应纳税所得额 {profit} × 税率 {tax_rate} - 减免税额 {reduction_amount}",
                accounting_rule="《小企业会计准则》§二/2.5 企业所得税",
                calculation_detail={
                    "profit": float(profit),
                    "tax_rate": float(tax_rate),
                    "reduction_amount": float(reduction_amount),
                    "tax_payable": float(tax_payable),
                    "expected_tax_payable": float(expected_tax_payable)
                }
            )

        return IncomeTaxResult(
            profit=profit,
            tax_rate=tax_rate,
            tax_payable=tax_payable,
            reduction_amount=reduction_amount,
            actual_tax=tax_payable,
            reduction_item=reduction_item
        )
