"""声明式报表 DSL — 类型定义

Field = 数据，不是代码。
每个字段声明取数来源（Source）+ 可选变换（Transform）+ 可选校验（Check）。
ReportEngine 统一执行。
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════
# 公式类型
# ═══════════════════════════════════════════════════════════════

class Formula(Enum):
    CUM_BALANCE         = auto()   # 资产余额 = 累计(借-贷)
    CUM_CREDIT          = auto()   # 负债余额 = 累计(贷-借)
    PERIOD_NET          = auto()   # 期间净额 (借-贷)
    COMPOSITE           = auto()   # 多科目多方向组合
    SUM_FIELDS          = auto()   # 引用其他字段求和
    INVOICE_TAX_NET     = auto()   # 发票表：销项税额 - 进项税额
    STOCK_MOVES         = auto()   # 库存流水聚合
    BANK_TXNS           = auto()   # 银行流水
    CASH_TXNS           = auto()   # 现金流水
    CLASSIFIED_SUM      = auto()   # 现金流分类聚合：从 classified_cache 按 cf_code 取数
    OPENING             = auto()   # 期初余额字段
    ESCAPE_HATCH        = auto()   # 逃生口：自定义 resolver
    POSITIVE_PART       = auto()   # max(value, 0)
    NEGATIVE_PART       = auto()   # max(-value, 0)
    OPENING_FALLBACK    = auto()   # 值=0 时兜底到期初
    SUBACCOUNT_FALLBACK = auto()   # 主科目=0 时回退子科目
    NEGATE              = auto()   # 取反：-value
    DUAL_SOURCE         = auto()   # 双口径 (internal wrapper)

# ═══════════════════════════════════════════════════════════════
# 凭证过滤桶
# ═══════════════════════════════════════════════════════════════

class Bucket(Enum):
    ALL             = "all"
    PNL_EXCLUDED    = "pnl_excluded"     # 排除 period_close/year_close
    BUSINESS_ONLY   = "business_only"    # 排除所有内部结转
    INTERNAL_ONLY   = "internal_only"    # 只要内部结转


# ═══════════════════════════════════════════════════════════════
# Source — 取数来源
# ═══════════════════════════════════════════════════════════════

@dataclass
class Part:
    """COMPOSITE 的一个组成部分"""
    codes: List[str]
    side: str       # "debit" | "credit"
    sign: int = 1   # +1 或 -1
    prefix_match: bool = False  # True=前缀匹配(含子科目,如 6001 匹配 600101/600102...)
                                 # False=精确匹配科目编码


@dataclass
class Source:
    """字段的取数来源"""
    formula: Formula
    codes: List[str] = field(default_factory=list)
    parts: List[Part] = field(default_factory=list)
    deps: List[str] = field(default_factory=list)
    bucket: Bucket = Bucket.PNL_EXCLUDED
    subaccount_codes: List[str] = field(default_factory=list)
    resolver: Optional[Callable] = None
    opening_key: str = ""
    key: str = ""                        # OPENING 用
    source_models: List[str] = field(default_factory=list)
    abs: bool = False                    # NegativePart 用
    primary: Optional["Source"] = None   # DualSource 用
    secondary: Optional["Source"] = None # DualSource 用
    ref: List[str] = field(default_factory=list)  # SUM_FIELDS deps 别名
    signs: Dict[str, int] = field(default_factory=dict)  # SUM_FIELDS 带符号


@dataclass
class Field:
    """报表字段"""
    key: str
    label: str
    source: Source
    transform: Optional[Source] = None   # PositivePart / NegativePart / etc.
    section: str = ""
    visible: bool = True


@dataclass
class Check:
    """跨字段公式校验"""
    left: List[str]
    op: str            # "==" | "!="
    right: List[str]
    desc: str = ""
    tolerance: Decimal = Decimal("0.01")


# ═══════════════════════════════════════════════════════════════
# Source 工厂函数
# ═══════════════════════════════════════════════════════════════

def LEDGER_BALANCE(codes: List[str], bucket: Bucket = Bucket.PNL_EXCLUDED) -> Source:
    """资产余额 = 累计(借-贷)"""
    return Source(formula=Formula.CUM_BALANCE, codes=list(codes), bucket=bucket)


def LEDGER_CREDIT(codes: List[str], bucket: Bucket = Bucket.PNL_EXCLUDED) -> Source:
    """负债/权益/收入余额 = 累计(贷-借)"""
    return Source(formula=Formula.CUM_CREDIT, codes=list(codes), bucket=bucket)


def LEDGER_PERIOD(codes: List[str], bucket: Bucket = Bucket.PNL_EXCLUDED) -> Source:
    """期间净额（借-贷）"""
    return Source(formula=Formula.PERIOD_NET, codes=list(codes), bucket=bucket)


def LEDGER_COMPOSITE(parts: List[Part], bucket: Bucket = Bucket.PNL_EXCLUDED) -> Source:
    """多科目多方向自由组合"""
    return Source(formula=Formula.COMPOSITE, parts=list(parts), bucket=bucket)


def SUM_FIELDS(deps: List) -> Source:
    """引用其他字段求和，支持带符号

    deps 元素可以是：
      - str            : "revenue"          → +revenue
      - (str, int)     : ("cogs", -1)       → -cogs
    """
    normalized = []
    signs: Dict[str, int] = {}
    for d in deps:
        if isinstance(d, (list, tuple)):
            key, sign = d[0], d[1]
            normalized.append(key)
            signs[key] = sign
        else:
            normalized.append(d)
            signs[d] = 1
    s = Source(formula=Formula.SUM_FIELDS, deps=normalized)
    s.signs = signs
    return s


def INVOICE_TAX_NET() -> Source:
    """发票表：销项税额 - 进项税额（已认证专票）"""
    return Source(formula=Formula.INVOICE_TAX_NET)


def STOCK_MOVES() -> Source:
    """库存流水聚合"""
    return Source(formula=Formula.STOCK_MOVES)


def BANK_TXNS() -> Source:
    """银行流水期末余额"""
    return Source(formula=Formula.BANK_TXNS)


def CASH_TXNS() -> Source:
    """现金流水期末余额"""
    return Source(formula=Formula.CASH_TXNS)


def OPENING(key: str) -> Source:
    """期初余额字段"""
    return Source(formula=Formula.OPENING, key=key)


def ESCAPE_HATCH(resolver: Callable) -> Source:
    """逃生口：resolver(snapshot) -> (value, [ids])"""
    return Source(formula=Formula.ESCAPE_HATCH, resolver=resolver)


def SUM_CLASSIFIED(codes: List[str]) -> Source:
    """现金流分类聚合：从 engine._classified_cache 按 cf_code 取数求和"""
    return Source(formula=Formula.CLASSIFIED_SUM, codes=list(codes))


def DualSource(primary: Source, secondary: Source) -> Source:
    """双口径：primary 默认，secondary 对账用"""
    return Source(formula=Formula.DUAL_SOURCE, primary=primary, secondary=secondary)


# ═══════════════════════════════════════════════════════════════
# Transform 工厂函数
# ═══════════════════════════════════════════════════════════════

def PositivePart() -> Source:
    """max(value, 0)"""
    return Source(formula=Formula.POSITIVE_PART)


def NegativePart(*, abs: bool = False) -> Source:
    """max(-value, 0)，abs=True 返回绝对值"""
    return Source(formula=Formula.NEGATIVE_PART, abs=abs)


def OpeningFallback(opening_key: str) -> Source:
    """值=0 时兜底到期初"""
    return Source(formula=Formula.OPENING_FALLBACK, opening_key=opening_key)


def SubaccountFallback(sub_codes: List[str]) -> Source:
    """主科目=0 时回退子科目合计"""
    return Source(formula=Formula.SUBACCOUNT_FALLBACK, subaccount_codes=list(sub_codes))


def Negate() -> Source:
    """取反：value = -value"""
    return Source(formula=Formula.NEGATE)
