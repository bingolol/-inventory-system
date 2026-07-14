"""层 2：主体画像（Entity Profile）— 一次计算处处复用

统一的小规模↔小微映射、纳税人类型归类。
surcharge_halved_l3（附加税减半）来自 Account 配置，独立于 income_type，消除循环依赖。
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from models import Account

# 保持向后兼容（accounting_engine.py 仍引用）
SURCHARGE_HALVED_TYPES = frozenset({"small_scale", "small_micro", "personal"})


@dataclass(frozen=True)
class EntityProfile:
    vat_type: str        # small_scale / general
    income_type: str     # personal / small_micro / general（仅用于所得税）
    surcharge_halved_l3: bool  # 来自 Account.surcharge_halved_l3，独立于 income_type
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
                  vat_type_override: Optional[str] = None,
                  surcharge_halved_l3: Optional[bool] = None) -> EntityProfile:
    """从 Account 构建主体画像。

    surcharge_halved_l3 与 income_type 独立：
    - surcharge_halved_l3 来自 Account 配置（创建账本时设定，年末评估更新）
    - income_type 由纳税人类型 + 利润精炼决定，仅用于所得税

    vat_type_override: 覆盖纳税人类型（用于历史月份回溯）。
    surcharge_halved_l3: 覆盖附加税减半标志。为 None 时使用 account.surcharge_halved_l3。
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

    # surcharge_halved_l3 从 Account 配置读取，不依赖 income_type
    if surcharge_halved_l3 is None:
        surcharge_halved_l3 = account.surcharge_halved_l3 if account else False

    return EntityProfile(
        vat_type=vat_type,
        income_type=income_type,
        surcharge_halved_l3=surcharge_halved_l3,
        effective_date=effective_date,
    )


def refine_small_micro(profile: EntityProfile, profit: "Decimal", threshold: "Decimal") -> EntityProfile:
    """对一般纳税人进一步判定小型微利企业身份（利润门槛）。

    仅影响 income_type（所得税税率），不影响 surcharge_halved_l3。
    """
    if profile.income_type != "general":
        return profile
    if profit <= threshold:
        return EntityProfile(
            vat_type=profile.vat_type,
            income_type="small_micro",
            surcharge_halved_l3=profile.surcharge_halved_l3,  # 保持原值，不覆盖
            effective_date=profile.effective_date,
        )
    return profile
