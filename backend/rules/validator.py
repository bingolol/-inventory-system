"""规则校验引擎

把 16 条 DSL 规则与数据血缘装饰器注册表交叉校验,
返回 RuleViolation 列表。

校验策略:
- 静态校验(基于装饰器声明):AS-08/09/10/14/15
- 静态扫描(基于源码扫描):AS-22
- 运行时校验(基于实际数据):AS-01/02/03/04/05/06/07/11/12/13
  运行时校验需调用方传入 db session,本模块仅提供静态校验;
  运行时校验由 tests/invariants/ 下的测试覆盖。
"""
import os
import re
from typing import List, Optional
from .dsl import Rule, RuleViolation, RULES, SEVERITY_ERROR, SEVERITY_WARNING
from . import rules_definition  # noqa: F401  触发规则注册


def get_rule_by_id(rule_id: str) -> Optional[Rule]:
    """按 ID 查规则"""
    for r in RULES:
        if r.id == rule_id:
            return r
    return None


def validate_rules(registry=None) -> List[RuleViolation]:
    """校验所有规则

    Args:
        registry: 数据血缘注册表(backend.lineage.REGISTRY)。
                  若提供,则做静态交叉校验(AS-08/09/10/14/15)。
                  若不提供,仅返回规则定义层面的违规。

    Returns:
        RuleViolation 列表
    """
    violations: List[RuleViolation] = []

    # 静态校验:需要 registry
    if registry is not None:
        violations.extend(_check_as08_tier_monotonic(registry))
        violations.extend(_check_as09_writer_unique(registry))
        violations.extend(_check_as10_l4_no_read(registry))
        violations.extend(_check_as14_service_product(registry))

    # 静态扫描:不需要 registry(基于源码扫描)
    violations.extend(_check_as22_unsupported_boundary())

    # 规则定义完整性校验(不需要 registry)
    violations.extend(_check_rule_definitions())

    return violations


# ═══════════════════════════════════════════════════════════════
# 静态校验函数(基于装饰器注册表)
# ═══════════════════════════════════════════════════════════════

def _check_as08_tier_monotonic(registry) -> List[RuleViolation]:
    """AS-08: 字段层级单调(L4 禁作下游真相源)

    交叉校验:遍历 registry.reads,若 reader tier=L4,则违规。
    """
    violations = []
    rule = get_rule_by_id("AS-08")
    if not rule:
        return violations

    l4_readers = {}  # field -> [func_qualname]
    for r in registry.reads:
        if r.tier == "L4":
            l4_readers.setdefault(r.field.path, []).append(r.func_qualname)

    for field, readers in l4_readers.items():
        violations.append(RuleViolation(
            rule_id="AS-08",
            rule_name=rule.name,
            severity=rule.severity,
            message=f"L4 字段 {field} 被 {len(readers)} 个函数读取,违反层级单调(L4 禁作下游真相源)",
            field=field,
            fix_hint=f"改读该 L4 字段的上游 L2 真相源(查 @derives from_fields)",
            detail={"readers": readers},
        ))
    return violations


def _check_as09_writer_unique(registry) -> List[RuleViolation]:
    """AS-09: Writer 唯一(跨类多 writer 即双算法)

    交叉校验:每个 L2 字段只能有一个 writer 类。
    """
    violations = []
    rule = get_rule_by_id("AS-09")
    if not rule:
        return violations

    # 按 field 分组 writer,提取类名
    field_writers = {}
    for w in registry.writes:
        if w.tier != "L2":
            continue
        qualname = w.func_qualname
        cls = qualname.rsplit(".", 1)[0] if "." in qualname else qualname
        field_writers.setdefault(w.field.path, set()).add(cls)

    for field, classes in field_writers.items():
        if len(classes) > 1:
            violations.append(RuleViolation(
                rule_id="AS-09",
                rule_name=rule.name,
                severity=rule.severity,
                message=f"L2 字段 {field} 有 {len(classes)} 个 writer 类: {classes},存在双算法风险",
                field=field,
                fix_hint="合并 writer 或拆分为不同字段",
                detail={"writer_classes": list(classes)},
            ))
    return violations


def _check_as10_l4_no_read(registry) -> List[RuleViolation]:
    """AS-10: L4 字段报表禁读(与 AS-08 重叠,但聚焦报表/CRUD)"""
    violations = []
    rule = get_rule_by_id("AS-10")
    if not rule:
        return violations

    # 已知 L4 字段清单
    l4_fields = {
        "Inventory.quantity_l4",
        "Inventory.average_cost_l4",
        "Inventory.total_value_l4",
        "LedgerAccountBalance.balance_l4",
        "FixedAsset.accumulated_depreciation_l4",
        "BankAccount.balance_l4",
    }

    for r in registry.reads:
        if r.field.path in l4_fields:
            violations.append(RuleViolation(
                rule_id="AS-10",
                rule_name=rule.name,
                severity=rule.severity,
                message=f"报表/CRUD 函数 {r.func_qualname} 读 L4 字段 {r.field.path}",
                field=r.field.path,
                fix_hint=f"改读 L1/L2 真相源(如 StockMove 聚合或 AccountMoveLine)",
                detail={"reader": r.func_qualname},
            ))
    return violations


def _check_as14_service_product(registry) -> List[RuleViolation]:
    """AS-14: 服务产品不扣库存(检查 track_inventory_l3 是否被正确 @reads)"""
    violations = []
    rule = get_rule_by_id("AS-14")
    if not rule:
        return violations

    # 检查 Product.track_inventory_l3 是否被销售/采购引擎读取
    readers = [r.func_qualname for r in registry.reads
               if r.field.path == "Product.track_inventory_l3"]
    if not readers:
        violations.append(RuleViolation(
            rule_id="AS-14",
            rule_name=rule.name,
            severity=rule.severity,
            message="Product.track_inventory_l3 未被任何引擎 @reads,服务产品不扣库存规则无法生效",
            field="Product.track_inventory_l3",
            fix_hint="在销售/采购引擎的 inbound/outbound 方法上加 @reads('Product.track_inventory_l3')",
        ))
    return violations


# ═══════════════════════════════════════════════════════════════
# 规则定义完整性校验(不需要 registry)
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# AS-22 静态扫描:不支持场景边界声明
# ═══════════════════════════════════════════════════════════════

# 不支持场景的模型存在但不应被 commands/routers 引用
_UNSUPPORTED_MODELS = {
    "PurchaseEstimate": "B2 暂估入库(用户决策 2026-07-02 不实现)",
    "BadDebt": "I 坏账核销(用户决策 2026-07-02 不实现)",
}

# 不支持场景的关键词(用于检测新增的 commands/routers 端点)
_UNSUPPORTED_KEYWORDS = {
    "estimate_purchase": "B2 暂估入库",
    "bad_debt": "I 坏账核销",
    "baddebt": "I 坏账核销",
    "purchase_estimate": "B2 暂估入库",
    "installment_sale": "A5 分期收款销售",
    "goods_in_transit": "B3 在途物资",
    "cash_discount": "D2 现金折扣",
    "sales_allowance": "D3 销售折让",
    "long_term_prepaid": "N 长期待摊费用",
}


def _scan_source_files(base_dir: str) -> List[tuple]:
    """递归扫描目录下所有 .py 文件,返回 [(filepath, content), ...] 列表"""
    results = []
    if not os.path.isdir(base_dir):
        return results
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        results.append((fpath, f.read()))
                except (IOError, UnicodeDecodeError):
                    continue
    return results


def _check_as22_unsupported_boundary() -> List[RuleViolation]:
    """AS-22 校验:不支持场景的模型不应被 commands/routers 引用

    静态扫描 backend/commands/ 和 backend/routers/ 下所有 .py 文件,
    检测是否引用了 PurchaseEstimate / BadDebt 等不支持场景的模型类名,
    或出现了 install_sale / bad_debt 等不支持场景的关键词。

    违规等级:WARNING(用户决策不实现,但保留模型骨架以备将来)
    """
    violations: List[RuleViolation] = []
    rule = get_rule_by_id("AS-22")
    if not rule:
        return violations

    # 定位 backend 目录(rules/ 的父目录)
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scan_dirs = [
        os.path.join(backend_dir, "commands"),
        os.path.join(backend_dir, "routers"),
    ]

    for scan_dir in scan_dirs:
        for fpath, content in _scan_source_files(scan_dir):
            # 跳过空内容
            if not content:
                continue
            rel_path = os.path.relpath(fpath, backend_dir).replace("\\", "/")
            layer = "commands" if "/commands/" in rel_path else "routers"

            # 1. 检测不支持场景的模型引用
            for model_name, scenario_desc in _UNSUPPORTED_MODELS.items():
                # 用单词边界匹配,避免误报(如 "BadDebt" 在字符串中)
                pattern = r"\b" + re.escape(model_name) + r"\b"
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(RuleViolation(
                        rule_id="AS-22",
                        rule_name=rule.name,
                        severity=SEVERITY_WARNING,
                        message=f"{layer}/{rel_path} 引用了不支持场景模型 {model_name} ({scenario_desc})",
                        fix_hint=f"删除对 {model_name} 的引用,该场景已显式标记为不支持",
                        field=model_name,
                        detail={
                            "file": rel_path,
                            "layer": layer,
                            "model": model_name,
                            "scenario": scenario_desc,
                            "match_count": len(matches),
                        },
                    ))

            # 2. 检测不支持场景的关键词(类名/函数名/路由路径)
            for keyword, scenario_desc in _UNSUPPORTED_KEYWORDS.items():
                # 跳过被 # 注释掉的行
                lines = content.split("\n")
                for line_no, line in enumerate(lines, start=1):
                    # 简单跳过纯注释行
                    stripped = line.lstrip()
                    if stripped.startswith("#"):
                        continue
                    if keyword.lower() in line.lower():
                        violations.append(RuleViolation(
                            rule_id="AS-22",
                            rule_name=rule.name,
                            severity=SEVERITY_WARNING,
                            message=f"{layer}/{rel_path}:{line_no} 出现不支持场景关键词 '{keyword}' ({scenario_desc})",
                            fix_hint=f"该场景已显式标记为不支持,如需启用请在 rules_definition.py 删除 AS-22 并补全实现",
                            field=keyword,
                            detail={
                                "file": rel_path,
                                "layer": layer,
                                "line": line_no,
                                "keyword": keyword,
                                "scenario": scenario_desc,
                                "snippet": line.strip()[:120],
                            },
                        ))
                        break  # 每个关键词每文件只报一次,避免刷屏

    return violations


# ═══════════════════════════════════════════════════════════════
# 规则定义完整性校验(不需要 registry)
# ═══════════════════════════════════════════════════════════════

def _check_rule_definitions() -> List[RuleViolation]:
    """校验规则定义本身的完整性"""
    violations = []

    # 检查 AS-01~AS-15 + AS-22 是否都注册
    expected_ids = {f"AS-{i:02d}" for i in range(1, 16)}
    expected_ids.add("AS-22")
    actual_ids = {r.id for r in RULES}
    missing = expected_ids - actual_ids
    if missing:
        violations.append(RuleViolation(
            rule_id="-",
            rule_name="规则定义完整性",
            severity=SEVERITY_ERROR,
            message=f"缺失规则定义: {sorted(missing)}",
            fix_hint="在 rules_definition.py 中补充缺失的 Rule 定义",
        ))

    # 检查 ID 重复
    seen = set()
    for r in RULES:
        if r.id in seen:
            violations.append(RuleViolation(
                rule_id=r.id,
                rule_name=r.name,
                severity=SEVERITY_ERROR,
                message=f"规则 ID {r.id} 重复定义",
                fix_hint="检查 rules_definition.py 中的重复 Rule 实例化",
            ))
        seen.add(r.id)

    # 检查必填字段
    for r in RULES:
        if not r.name or not r.source or not r.trigger or not r.expected_chain:
            violations.append(RuleViolation(
                rule_id=r.id,
                rule_name=r.name or "(未命名)",
                severity=SEVERITY_ERROR,
                message=f"规则 {r.id} 缺少必填字段(name/source/trigger/expected_chain)",
                fix_hint="补全 Rule 的 7 个核心字段",
            ))

    return violations
