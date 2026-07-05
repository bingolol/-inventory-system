"""层 1：企业所得税政策事实源 — 唯一真相源

所有企业所得税税率/门槛/减免规则集中于此。每个常量带生效起止日期 + 法规文号。
业务代码不得硬编码 Decimal("0.25") / Decimal("3000000") 等字面量。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from policy.vat_facts import PolicyFact, PolicyExpiredError


INCOME_TAX_STATUTORY_RATE = PolicyFact(
    value=Decimal("0.25"),
    effective_from=date(2008, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="企业所得税法第四条",
    note="企业所得税法定税率 25%"
)

INCOME_TAX_SMALL_MICRO_DEDUCTION_RATE = PolicyFact(
    value=Decimal("0.25"),
    effective_from=date(2023, 1, 1),
    effective_to=date(2027, 12, 31),
    legal_basis="财政部 税务总局公告 2023 年第 12 号",
    note="小型微利企业减按 25% 计入应纳税所得额"
)

INCOME_TAX_SMALL_MICRO_RATE = PolicyFact(
    value=Decimal("0.20"),
    effective_from=date(2019, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="企业所得税法第二十八条",
    note="小型微利企业适用 20% 优惠税率"
)

INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE = PolicyFact(
    value=Decimal("0.05"),
    effective_from=date(2023, 1, 1),
    effective_to=date(2027, 12, 31),
    legal_basis="财政部 税务总局公告 2023 年第 12 号",
    note="小型微利企业实际税负 5%（25%×20%）"
)

INCOME_TAX_SMALL_MICRO_THRESHOLD = PolicyFact(
    value=Decimal("3000000"),
    effective_from=date(2023, 1, 1),
    effective_to=date(2027, 12, 31),
    legal_basis="财政部 税务总局公告 2023 年第 12 号",
    note="小型微利企业年应纳税所得额 ≤300 万元适用优惠"
)


@dataclass(frozen=True)
class IncomeTaxFacts:
    statutory_rate: Decimal
    small_micro_deduction_rate: Decimal
    small_micro_rate: Decimal
    small_micro_effective_rate: Decimal
    small_micro_threshold: Decimal
    ref_date: date


def load_income_tax_facts(ref_date: Optional[date] = None) -> IncomeTaxFacts:
    ref = ref_date or date.today()

    facts = [
        ("INCOME_TAX_STATUTORY_RATE", INCOME_TAX_STATUTORY_RATE),
        ("INCOME_TAX_SMALL_MICRO_DEDUCTION_RATE", INCOME_TAX_SMALL_MICRO_DEDUCTION_RATE),
        ("INCOME_TAX_SMALL_MICRO_RATE", INCOME_TAX_SMALL_MICRO_RATE),
        ("INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE", INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE),
        ("INCOME_TAX_SMALL_MICRO_THRESHOLD", INCOME_TAX_SMALL_MICRO_THRESHOLD),
    ]

    for name, fact in facts:
        if not fact.is_effective(ref):
            raise PolicyExpiredError(name, fact.effective_to, ref)

    return IncomeTaxFacts(
        statutory_rate=INCOME_TAX_STATUTORY_RATE.value,
        small_micro_deduction_rate=INCOME_TAX_SMALL_MICRO_DEDUCTION_RATE.value,
        small_micro_rate=INCOME_TAX_SMALL_MICRO_RATE.value,
        small_micro_effective_rate=INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE.value,
        small_micro_threshold=INCOME_TAX_SMALL_MICRO_THRESHOLD.value,
        ref_date=ref,
    )
