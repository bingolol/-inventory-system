"""DSL 数据结构定义

Rule dataclass: 会计准则规则的声明式描述
RuleViolation: 校验违规结果
"""
from dataclasses import dataclass, field as dc_field
from typing import List, Optional, Callable, Any

# 严重程度
SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"

# 规则类别
CATEGORY_ACCOUNTING = "accounting"        # 会计实务基石
CATEGORY_IMPLEMENTATION = "implementation"  # 系统实现约定


@dataclass
class Rule:
    """会计准则规则 DSL 模板

    7 个核心字段(对应 DSL 设计):
    1. id: 规则ID (AS-01 ~ AS-15)
    2. name: 规则名称
    3. source: 准则出处 (《小企业会计准则》第X条 / 系统设计决策 D-X)
    4. trigger: 触发事件 (什么场景下需要校验)
    5. expected_chain: 期望数据链 (L1→L2→L4 等流向描述)
    6. invariants: 不变量列表 (必须成立的等式/不等式/约束)
    7. prohibited: 禁止项列表 (反模式描述)

    附加字段:
    - severity: 严重程度 (ERROR/WARNING)
    - category: 类别 (accounting/implementation)
    - check_fn: 校验函数 (可选,由 validator 调用)
    - related_fields: 相关字段路径列表 (用于与装饰器注册表交叉校验)
    """
    id: str
    name: str
    source: str
    trigger: str
    expected_chain: str
    invariants: List[str] = dc_field(default_factory=list)
    prohibited: List[str] = dc_field(default_factory=list)
    severity: str = SEVERITY_ERROR
    category: str = CATEGORY_ACCOUNTING
    check_fn: Optional[Callable] = None
    related_fields: List[str] = dc_field(default_factory=list)

    def __post_init__(self):
        """注册到全局 RULES 注册表"""
        RULES.append(self)


@dataclass
class RuleViolation:
    """规则校验违规结果"""
    rule_id: str
    rule_name: str
    severity: str
    message: str
    field: Optional[str] = None
    fix_hint: Optional[str] = None
    detail: Optional[Any] = None


# 全局规则注册表
RULES: List[Rule] = []


def register_rule(rule: Rule) -> Rule:
    """显式注册规则(也可通过 Rule 实例化自动注册)"""
    if rule not in RULES:
        RULES.append(rule)
    return rule
