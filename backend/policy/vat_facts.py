"""层 1：增值税政策事实源 — 唯一真相源

所有增值税税率/门槛/减免规则集中于此。每个常量带生效起止日期 + 法规文号。
业务代码不得硬编码 Decimal("0.01") / Decimal("0.13") / Decimal("300000") 等字面量。
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, Optional


@dataclass(frozen=True)
class PolicyFact:
    """不可变政策事实"""
    value: Decimal
    effective_from: date
    effective_to: date
    legal_basis: str
    note: str

    def is_effective(self, ref_date: Optional[date] = None) -> bool:
        ref = ref_date or date.today()
        return self.effective_from <= ref <= self.effective_to


# ═══════════════ 小规模纳税人 ═══════════════

VAT_SMALL_SCALE_SYNDICATED_RATE = PolicyFact(
    value=Decimal("0.03"),
    effective_from=date(2009, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="增值税暂行条例第十二条",
    note="小规模纳税人法定征收率 3%"
)

VAT_SMALL_SCALE_REDUCED_RATE = PolicyFact(
    value=Decimal("0.01"),
    effective_from=date(2023, 1, 1),
    effective_to=date(2027, 12, 31),
    legal_basis="财政部 税务总局公告 2023 年第 19 号",
    note="小规模纳税人减按 1% 征收增值税，2027 年底前有效"
)

VAT_SMALL_SCALE_QUARTERLY_EXEMPTION = PolicyFact(
    value=Decimal("300000"),
    effective_from=date(2023, 1, 1),
    effective_to=date(2027, 12, 31),
    legal_basis="财政部 税务总局公告 2023 年第 19 号",
    note="季度销售额 ≤30 万元普票免征增值税"
)

VAT_SMALL_SCALE_ANNUAL_THRESHOLD = PolicyFact(
    value=Decimal("5000000"),
    effective_from=date(2018, 5, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="财税〔2018〕33 号",
    note="年应征增值税销售额 ≤500 万可认定为小规模纳税人"
)


# ═══════════════ 一般纳税人 ═══════════════

VAT_GENERAL_DEFAULT_RATE = PolicyFact(
    value=Decimal("0.13"),
    effective_from=date(2019, 4, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="财政部 税务总局 海关总署公告 2019 年第 39 号",
    note="一般纳税人增值税基本税率 13%"
)

VAT_GENERAL_RATE_9 = PolicyFact(
    value=Decimal("0.09"),
    effective_from=date(2019, 4, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="财政部 税务总局 海关总署公告 2019 年第 39 号",
    note="一般纳税人 9% 税率（农产品/不动产/运输等）"
)

VAT_GENERAL_RATE_6 = PolicyFact(
    value=Decimal("0.06"),
    effective_from=date(2016, 5, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="财税〔2016〕36 号",
    note="一般纳税人 6% 税率（现代服务业/金融服务等）"
)

VAT_ZERO_RATE = PolicyFact(
    value=Decimal("0"),
    effective_from=date(1994, 1, 1),
    effective_to=date(2099, 12, 31),
    legal_basis="增值税暂行条例第二条",
    note="零税率（出口/免税项目）"
)


# ═══════════════ 合法税率集合 ═══════════════

VAT_LEGAL_RATES: Dict[str, PolicyFact] = {
    "0.13": VAT_GENERAL_DEFAULT_RATE,
    "0.09": VAT_GENERAL_RATE_9,
    "0.06": VAT_GENERAL_RATE_6,
    "0.03": VAT_SMALL_SCALE_SYNDICATED_RATE,
    "0.01": VAT_SMALL_SCALE_REDUCED_RATE,
    "0": VAT_ZERO_RATE,
}


def get_legal_rate_values() -> set:
    """返回合法税率 Decimal 值集合（供 runtime_checks 使用）"""
    return {fact.value for fact in VAT_LEGAL_RATES.values()}


# ═══════════════ 时效守护 ═══════════════

class PolicyExpiredError(Exception):
    """政策已到期"""
    def __init__(self, fact_name: str, effective_to: date, ref_date: date):
        self.fact_name = fact_name
        self.effective_to = effective_to
        self.ref_date = ref_date
        super().__init__(
            f"政策 {fact_name} 已于 {effective_to} 到期，当前日期 {ref_date} 超出有效期。"
            f"请更新政策事实源或确认是否延续。"
        )


@dataclass(frozen=True)
class VATFacts:
    """某一时点的有效增值税政策快照"""
    small_scale_syndicated_rate: Decimal
    small_scale_reduced_rate: Decimal
    small_scale_quarterly_exemption: Decimal
    general_default_rate: Decimal
    legal_rates: dict
    ref_date: date


def load_vat_facts(ref_date: Optional[date] = None) -> VATFacts:
    """加载某一时点有效的增值税政策。到期政策抛出 PolicyExpiredError。"""
    ref = ref_date or date.today()

    facts = [
        ("VAT_SMALL_SCALE_SYNDICATED_RATE", VAT_SMALL_SCALE_SYNDICATED_RATE),
        ("VAT_SMALL_SCALE_REDUCED_RATE", VAT_SMALL_SCALE_REDUCED_RATE),
        ("VAT_SMALL_SCALE_QUARTERLY_EXEMPTION", VAT_SMALL_SCALE_QUARTERLY_EXEMPTION),
        ("VAT_GENERAL_DEFAULT_RATE", VAT_GENERAL_DEFAULT_RATE),
    ]

    for name, fact in facts:
        if not fact.is_effective(ref):
            raise PolicyExpiredError(name, fact.effective_to, ref)

    effective_legal_rates = {
        str(k): v for k, v in VAT_LEGAL_RATES.items() if v.is_effective(ref)
    }

    return VATFacts(
        small_scale_syndicated_rate=VAT_SMALL_SCALE_SYNDICATED_RATE.value,
        small_scale_reduced_rate=VAT_SMALL_SCALE_REDUCED_RATE.value,
        small_scale_quarterly_exemption=VAT_SMALL_SCALE_QUARTERLY_EXEMPTION.value,
        general_default_rate=VAT_GENERAL_DEFAULT_RATE.value,
        legal_rates=effective_legal_rates,
        ref_date=ref,
    )
