"""会计准则规则 DSL (Domain-Specific Language)

将《小企业会计准则》及系统设计决策编码为可执行的规则,
与数据血缘装饰器框架(@writes/@reads/@derives)交叉校验,
确保代码实现符合会计业务指导。

15 条规则分两类:
- AS-01~AS-07 会计实务基石(借贷平衡、价税分离、移动加权平均等)
- AS-08~AS-15 系统实现约定(层级单调、Writer 唯一、L4 禁读等)

每条规则用 Rule dataclass 定义,7 个字段:
- id: 规则ID (AS-XX)
- name: 规则名称
- source: 准则出处
- trigger: 触发事件(什么场景下校验)
- expected_chain: 期望数据链(L1→L2→L4 等)
- invariants: 不变量(必须成立的等式/不等式)
- prohibited: 禁止项(反模式)
- severity: 严重程度(ERROR/WARNING)
- category: 类别(accounting/implementation)

校验引擎 validate_rules() 遍历规则,根据 trigger 调用对应校验函数,
违规返回 RuleViolation 列表。
"""
from .dsl import (
    Rule,
    RuleViolation,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    CATEGORY_ACCOUNTING,
    CATEGORY_IMPLEMENTATION,
    RULES,
    register_rule,
)
from .rules_definition import load_all_rules
from .validator import validate_rules, get_rule_by_id
from .runtime_checks import (
    validate_rules_runtime,
    validate_all_runtime,
    enforce_rules,
    RUNTIME_CHECKS,
    check_global_balance,
    check_accounting_equation,
)
from .journal_rules import (
    AccountPattern,
    JournalRule,
    register_journal_rule,
    get_journal_rule,
    all_journal_rules,
    check_journal_rule,
    enforce_journal_rules,
)

__all__ = [
    "Rule",
    "RuleViolation",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "CATEGORY_ACCOUNTING",
    "CATEGORY_IMPLEMENTATION",
    "RULES",
    "register_rule",
    "load_all_rules",
    "validate_rules",
    "get_rule_by_id",
    "validate_rules_runtime",
    "validate_all_runtime",
    "enforce_rules",
    "RUNTIME_CHECKS",
    "check_global_balance",
    "check_accounting_equation",
    "AccountPattern",
    "JournalRule",
    "register_journal_rule",
    "get_journal_rule",
    "all_journal_rules",
    "check_journal_rule",
    "enforce_journal_rules",
]
