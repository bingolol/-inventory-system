"""层 1：附加税政策事实源 — 唯一真相源

所有附加税税率/减半规则集中于此。每个常量带生效起止日期 + 法规文号。
业务代码不得硬编码 Decimal("0.07") / Decimal("0.03") / Decimal("0.5") 等字面量。

模块级导出：PolicyFact 对象，.value 属性可直接用于算术运算。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from policy.vat_facts import PolicyFact, PolicyExpiredError


_SURCHARGE_RATE_URBAN_CONSTRUCTION = PolicyFact(
    value=Decimal("0.07"),
    effective_from=date(1985, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="城市维护建设税法第四条",
    note="城市维护建设税 7%（市区）"
)

_SURCHARGE_RATE_EDUCATION = PolicyFact(
    value=Decimal("0.03"),
    effective_from=date(1994, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="国务院关于教育费附加征收问题的紧急通知",
    note="教育费附加 3%"
)

_SURCHARGE_RATE_LOCAL_EDUCATION = PolicyFact(
    value=Decimal("0.02"),
    effective_from=date(2010, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="财综〔2010〕98 号",
    note="地方教育附加 2%"
)

_SURCHARGE_SMALL_MICRO_REDUCTION = PolicyFact(
    value=Decimal("0.5"),
    effective_from=date(2022, 1, 1),
    effective_to=date(2027, 12, 31),
    legal_basis="财税〔2022〕10 号",
    note="六税两费减半：适用小规模纳税人、小型微利企业、个体工商户"
)

_SURCHARGE_NO_REDUCTION = PolicyFact(
    value=Decimal("1"),
    effective_from=date(1994, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="（无减免政策）",
    note="附加税全额征收（不享受六税两费减半）"
)

# Public API
SURCHARGE_RATE_URBAN_CONSTRUCTION = _SURCHARGE_RATE_URBAN_CONSTRUCTION
SURCHARGE_RATE_EDUCATION = _SURCHARGE_RATE_EDUCATION
SURCHARGE_RATE_LOCAL_EDUCATION = _SURCHARGE_RATE_LOCAL_EDUCATION
SURCHARGE_SMALL_MICRO_REDUCTION = _SURCHARGE_SMALL_MICRO_REDUCTION
SURCHARGE_NO_REDUCTION = _SURCHARGE_NO_REDUCTION


@dataclass(frozen=True)
class SurchargeFacts:
    rate_urban_construction: Decimal
    rate_education: Decimal
    rate_local_education: Decimal
    reduction_rate: Decimal
    no_reduction: Decimal
    ref_date: date


def load_surcharge_facts(ref_date: Optional[date] = None) -> SurchargeFacts:
    ref = ref_date or date.today()

    facts = [
        ("SURCHARGE_RATE_URBAN_CONSTRUCTION", _SURCHARGE_RATE_URBAN_CONSTRUCTION),
        ("SURCHARGE_RATE_EDUCATION", _SURCHARGE_RATE_EDUCATION),
        ("SURCHARGE_RATE_LOCAL_EDUCATION", _SURCHARGE_RATE_LOCAL_EDUCATION),
        ("SURCHARGE_SMALL_MICRO_REDUCTION", _SURCHARGE_SMALL_MICRO_REDUCTION),
    ]

    for name, fact in facts:
        if not fact.is_effective(ref):
            raise PolicyExpiredError(name, fact.effective_to, ref)

    return SurchargeFacts(
        rate_urban_construction=_SURCHARGE_RATE_URBAN_CONSTRUCTION.value,
        rate_education=_SURCHARGE_RATE_EDUCATION.value,
        rate_local_education=_SURCHARGE_RATE_LOCAL_EDUCATION.value,
        reduction_rate=_SURCHARGE_SMALL_MICRO_REDUCTION.value,
        no_reduction=_SURCHARGE_NO_REDUCTION.value,
        ref_date=ref,
    )
