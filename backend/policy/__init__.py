"""政策引擎 — 五层架构根治税率散落

层 1：政策事实源（vat_facts / income_tax_facts / surcharge_facts）
层 2：主体画像（entity_profile）
层 3：政策引擎（policy_engine）
层 4：申报表映射器（declaration_mapper）
层 5：守护层（lineage_lint + test）

所有税率/门槛/减免规则从 policy/ 导入，禁止业务代码硬编码 Decimal("0.13") 等字面量。
"""

from policy.vat_facts import (
    VAT_SMALL_SCALE_SYNDICATED_RATE,
    VAT_SMALL_SCALE_REDUCED_RATE,
    VAT_SMALL_SCALE_QUARTERLY_EXEMPTION,
    VAT_GENERAL_DEFAULT_RATE,
    VAT_LEGAL_RATES,
    load_vat_facts,
    get_legal_rate_values,
    PolicyExpiredError,
)
from policy.income_tax_facts import (
    INCOME_TAX_STATUTORY_RATE,
    INCOME_TAX_SMALL_MICRO_DEDUCTION_RATE,
    INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE,
    INCOME_TAX_SMALL_MICRO_THRESHOLD,
    load_income_tax_facts,
)
from policy.entity_profile import (
    EntityProfile,
    build_profile,
    resolve_taxpayer_type_by_date,
    refine_small_micro,
    SURCHARGE_HALVED_TYPES,
)
from policy.policy_engine import (
    PolicyEngine,
    calculate_vat,
    calculate_income_tax,
    VATResult,
    IncomeTaxResult,
)
from policy.surcharge_facts import (
    URBAN_CONSTRUCTION_TAX_RATE_CITY,
    URBAN_CONSTRUCTION_TAX_RATE_COUNTY,
    URBAN_CONSTRUCTION_TAX_RATE_OTHER,
    EDUCATION_SURCHARGE_RATE,
    LOCAL_EDUCATION_SURCHARGE_RATE,
    SURCHARGE_HALVING_FACTOR,
    SURCHARGE_TOTAL_RATE,
    load_surcharge_facts,
)
from policy.declaration_mapper import (
    map_vat_to_main_form,
    map_income_tax_to_prepayment_form,
)

__all__ = [
    # VAT facts
    "VAT_SMALL_SCALE_SYNDICATED_RATE", "VAT_SMALL_SCALE_REDUCED_RATE",
    "VAT_SMALL_SCALE_QUARTERLY_EXEMPTION", "VAT_GENERAL_DEFAULT_RATE",
    "VAT_LEGAL_RATES", "load_vat_facts", "get_legal_rate_values", "PolicyExpiredError",
    # Income tax facts
    "INCOME_TAX_STATUTORY_RATE", "INCOME_TAX_SMALL_MICRO_DEDUCTION_RATE",
    "INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE", "INCOME_TAX_SMALL_MICRO_THRESHOLD",
    "load_income_tax_facts",
    # Entity profile
    "EntityProfile", "build_profile", "resolve_taxpayer_type_by_date", "refine_small_micro", "SURCHARGE_HALVED_TYPES",
    # Policy engine
    "PolicyEngine", "calculate_vat", "calculate_income_tax",
    "VATResult", "IncomeTaxResult",
    # Surcharge facts
    "URBAN_CONSTRUCTION_TAX_RATE_CITY", "URBAN_CONSTRUCTION_TAX_RATE_COUNTY",
    "URBAN_CONSTRUCTION_TAX_RATE_OTHER", "EDUCATION_SURCHARGE_RATE",
    "LOCAL_EDUCATION_SURCHARGE_RATE", "SURCHARGE_HALVING_FACTOR",
    "SURCHARGE_TOTAL_RATE", "load_surcharge_facts",
    # Declaration mapper
    "map_vat_to_main_form", "map_income_tax_to_prepayment_form",
]
