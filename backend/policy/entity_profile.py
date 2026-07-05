"""层 2：主体画像（Entity Profile）— 一次计算处处复用

统一的小规模↔小微映射、附加税减半判定、纳税人类型归类。
替代散落在 4 个调用点的重复映射逻辑。
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models import Account

SURCHARGE_HALVED_TYPES = frozenset({"small_scale", "small_micro", "personal"})


@dataclass(frozen=True)
class EntityProfile:
    vat_type: str        # small_scale / general
    income_type: str     # personal / small_micro / general
    surcharge_halved: bool
    effective_date: date


def resolve_taxpayer_type_by_date(account: "Account", db: "Session", ref_date: date) -> str:
    """根据 TaxpayerTypeHistory 确定指定日期适用的纳税人类型。

    以 effective_period（YYYY-MM）为准，查询 <= ref_date 的最新历史记录。
    无历史记录时回退到 account.taxpayer_type_l3（当前类型）。
    用于历史月份月结/报表回溯正确的纳税人类型。
    """
    from models import TaxpayerTypeHistory
    ref_period = ref_date.strftime("%Y-%m")
    result = db.query(TaxpayerTypeHistory).filter(
        TaxpayerTypeHistory.account_id == account.id,
        TaxpayerTypeHistory.effective_period <= ref_period,
    ).order_by(TaxpayerTypeHistory.effective_period.desc()).first()
    if result:
        return result.taxpayer_type_l3
    return account.taxpayer_type_l3 if account and account.taxpayer_type_l3 else "small_scale"


def build_profile(account: "Account", ref_date: Optional[date] = None,
                  vat_type_override: Optional[str] = None) -> EntityProfile:
    """从 Account 构建主体画像。

    统一映射规则：
    - small_scale → income_type=small_micro, surcharge_halved=True
    - personal → income_type=personal, surcharge_halved=True
    - general → income_type=general（需额外利润判定 small_micro）

    vat_type_override: 覆盖纳税人类型（用于历史月份回溯）。
        来自 resolve_taxpayer_type_by_date 的返回值。
        为 None 时使用 account.taxpayer_type_l3（当前类型）。
    """
    effective_date = ref_date or date.today()
    vat_type = vat_type_override if vat_type_override is not None else (
        account.taxpayer_type_l3 if account and account.taxpayer_type_l3 else "small_scale"
    )
    entity_type = account.type if account and account.type else "company"

    if entity_type == "personal":
        income_type = "personal"
    elif vat_type == "small_scale":
        income_type = "small_micro"
    else:
        income_type = "general"

    surcharge_halved = income_type in SURCHARGE_HALVED_TYPES

    return EntityProfile(
        vat_type=vat_type,
        income_type=income_type,
        surcharge_halved=surcharge_halved,
        effective_date=effective_date,
    )


def refine_small_micro(profile: EntityProfile, profit: "Decimal", threshold: "Decimal") -> EntityProfile:
    """对一般纳税人进一步判定小型微利企业身份（利润门槛）。"""
    if profile.income_type != "general":
        return profile
    if profit <= threshold:
        return EntityProfile(
            vat_type=profile.vat_type,
            income_type="small_micro",
            surcharge_halved=True,
            effective_date=profile.effective_date,
        )
    return profile
