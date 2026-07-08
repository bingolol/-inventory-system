"""层 1：附加税（城建税 / 教育费附加 / 地方教育附加）政策事实源 — 唯一真相源

所有附加税税率/减征规则集中于此。每个常量带生效起止日期 + 法规文号。
业务代码不得硬编码 Decimal("0.07") / Decimal("0.12") 等字面量。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from policy.vat_facts import PolicyFact, PolicyExpiredError


# ═══════════════ 城建税 ═══════════════

URBAN_CONSTRUCTION_TAX_RATE_CITY = PolicyFact(
    value=Decimal("0.07"),
    effective_from=date(2021, 9, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="《城市维护建设税法》第二条第一档",
    note="市区城建税率 7%"
)

URBAN_CONSTRUCTION_TAX_RATE_COUNTY = PolicyFact(
    value=Decimal("0.05"),
    effective_from=date(2021, 9, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="《城市维护建设税法》第二条第二档",
    note="县城、建制镇城建税率 5%"
)

URBAN_CONSTRUCTION_TAX_RATE_OTHER = PolicyFact(
    value=Decimal("0.01"),
    effective_from=date(2021, 9, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="《城市维护建设税法》第二条第三档",
    note="其他地区城建税率 1%"
)


# ═══════════════ 教育费附加 ═══════════════

EDUCATION_SURCHARGE_RATE = PolicyFact(
    value=Decimal("0.03"),
    effective_from=date(1986, 7, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="《征收教育费附加暂行规定》第三条",
    note="教育费附加 3%"
)


# ═══════════════ 地方教育附加 ═══════════════

LOCAL_EDUCATION_SURCHARGE_RATE = PolicyFact(
    value=Decimal("0.02"),
    effective_from=date(2011, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="财税〔2010〕103 号 / 财税〔2011〕13 号",
    note="地方教育附加 2%"
)


# ═══════════════ 六税两费减半 ═══════════════

SURCHARGE_HALVING_FACTOR = PolicyFact(
    value=Decimal("0.5"),
    effective_from=date(2022, 1, 1),
    effective_to=date(2027, 12, 31),
    legal_basis="财政部 税务总局公告 2022 年第 10 号 / 财政部 税务总局公告 2023 年第 18 号（延期）",
    note="六税两费减半征收，小型微利企业/个体工商户/小规模纳税人适用，2027 年底前有效"
)


# ═══════════════ 合计税率 ═══════════════

SURCHARGE_TOTAL_RATE = (
    URBAN_CONSTRUCTION_TAX_RATE_CITY.value
    + EDUCATION_SURCHARGE_RATE.value
    + LOCAL_EDUCATION_SURCHARGE_RATE.value
)


@dataclass(frozen=True)
class SurchargeFacts:
    """某一时点的有效附加税政策快照"""
    urban_construction_tax_rate: Decimal
    education_surcharge_rate: Decimal
    local_education_surcharge_rate: Decimal
    total_rate: Decimal
    halving_factor: Optional[Decimal]
    ref_date: date


def load_surcharge_facts(
    ref_date: Optional[date] = None,
    urban_rate: Optional[PolicyFact] = None,
) -> SurchargeFacts:
    """加载某一时点有效的附加税政策。

    Args:
        ref_date: 参考日期，默认今天。
        urban_rate: 城建税档次，默认使用市区 7%。
                    传入 URBAN_CONSTRUCTION_TAX_RATE_COUNTY / _OTHER 可切换档次。
    """
    ref = ref_date or date.today()
    urban_fact = urban_rate or URBAN_CONSTRUCTION_TAX_RATE_CITY

    facts = [
        ("URBAN_CONSTRUCTION_TAX_RATE", urban_fact),
        ("EDUCATION_SURCHARGE_RATE", EDUCATION_SURCHARGE_RATE),
        ("LOCAL_EDUCATION_SURCHARGE_RATE", LOCAL_EDUCATION_SURCHARGE_RATE),
    ]

    for name, fact in facts:
        if not fact.is_effective(ref):
            raise PolicyExpiredError(name, fact.effective_to, ref)

    halving = SURCHARGE_HALVING_FACTOR if SURCHARGE_HALVING_FACTOR.is_effective(ref) else None

    total = urban_fact.value + EDUCATION_SURCHARGE_RATE.value + LOCAL_EDUCATION_SURCHARGE_RATE.value

    return SurchargeFacts(
        urban_construction_tax_rate=urban_fact.value,
        education_surcharge_rate=EDUCATION_SURCHARGE_RATE.value,
        local_education_surcharge_rate=LOCAL_EDUCATION_SURCHARGE_RATE.value,
        total_rate=total,
        halving_factor=halving.value if halving else None,
        ref_date=ref,
    )
