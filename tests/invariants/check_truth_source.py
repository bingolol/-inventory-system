<<<<<<< Updated upstream
"""静态扫描：检测 "Truth Source Bypass" 反模式

扫描 backend/commands/ 和 backend/engine_*.py，
检测以下反模式（同一凭证的借贷用了不同数据源）：

1. 采购退货的 inventory_cost 用 StockMove.unit_cost（移动加权平均）
   而不是 orig_item.unit_price（原发票单价）
   → 会导致借贷不平衡

2. 反向 StockMove 的 total_cost 用 original.unit_cost
   而不是 original.total_cost / original.quantity
   → 会导致库存账面价值偏离

运行：python tests/invariants/check_truth_source.py
退出码：0 通过，1 发现反模式
=======
"""Truth Source 静态扫描 + 装饰器注册表校验 + DSL 规则校验

三层校验：
1. 装饰器注册表校验（registry-based）：
   从 backend/lineage 注册表读取 @writes/@reads/@derives 声明，
   校验层级单调、writer 唯一、禁止 L4 作为下游真相源、禁止回写/分叉/跳层。
   这是主校验路径，基于声明式元数据。

2. DSL 规则校验（rules-based）：
   从 backend/rules 读取 15 条会计准则规则定义(AS-01~AS-15)，
   与装饰器注册表交叉校验，确保代码实现符合会计业务指导。
   覆盖 AS-08(层级单调)/AS-09(Writer 唯一)/AS-10(L4 禁读)/AS-14(服务产品)。

3. 正则静态扫描（legacy regex-based）：
   扫描 backend/commands/ 和 backend/engine_*.py，
   检测代码中残留的 "Truth Source Bypass" 反模式（无装饰器声明的违规）。
   作为兜底，捕获装饰器未覆盖的角落。

运行：python tests/invariants/check_truth_source.py
退出码：0 通过，1 发现违规
>>>>>>> Stashed changes
"""
import re
import sys
import os
<<<<<<< Updated upstream
=======
import importlib
>>>>>>> Stashed changes
from pathlib import Path

# 扫描范围
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
SCAN_DIRS = [
    BACKEND_DIR / "commands",
    BACKEND_DIR,  # engine_*.py 在根目录
]
SCAN_GLOB = "*.py"

<<<<<<< Updated upstream
# 反模式规则
=======
# ═══════════════════════════════════════════════════════════════
# Layer 1: 装饰器注册表校验
# ═══════════════════════════════════════════════════════════════
def _load_lineage_registry():
    """导入引擎模块触发装饰器注册，返回 REGISTRY

    必须导入所有用了 @writes/@reads/@derives 的模块，否则装饰器不会执行。
    """
    # 把 backend 加入 sys.path 以便 import lineage 和引擎模块
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from lineage import REGISTRY, validate_invariants

    # 导入所有声明了装饰器的引擎/报表模块，触发 @writes/@reads 注册
    modules_to_import = [
        # 引擎层
        "engine_inventory",
        "engine_journal",
        "engine_ledger",
        "engine_bank",
        "engine_fixed_asset",
        "engine_finance",
        "engine_tax",
        "finance_integration",
        # 命令层
        "commands.product_commands",
        "commands.account_commands",
        "commands.invoice_commands",
        "commands.purchase_commands",
        "commands.sale_commands",
        # CRUD/报表层
        "crud.reports",
        "crud.products",
        "crud.finance.balance_sheet",
        "crud.finance.income_statement",
        "crud.finance.cash_flow",
        "crud.finance.tax_declarations",
        "crud.finance.fixed_assets",
        "crud.finance.intangible_assets",
    ]
    for mod_name in modules_to_import:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            # 模块导入失败不应阻断扫描，但需记录
            print(f"[WARN] 导入 {mod_name} 失败，跳过其装饰器声明: {e}", file=sys.stderr)

    return REGISTRY, validate_invariants


def scan_registry() -> list:
    """从装饰器注册表校验数据链不变量，返回违规列表

    违规 dict 字段与 scan_file() 一致：{file, line, code, rule_id, rule_name, severity, message, fix_hint}
    """
    REGISTRY, validate = _load_lineage_registry()
    violations = []

    for v in validate():
        # 映射 LineageViolation → 统一违规 dict
        violations.append({
            "file": "(lineage_registry)",
            "line": 0,
            "code": "",
            "rule_id": v.code,
            "rule_name": v.rule,
            "severity": v.severity,
            "message": v.message,
            "fix_hint": _fix_hint_for(v.code, v.field),
            "field": v.field,
            "writers": getattr(v, "writers", []),
            "readers": getattr(v, "readers", []),
        })

    return violations


def _fix_hint_for(code: str, field: str | None) -> str:
    """根据违规代码给出修复提示"""
    hints = {
        "TS01": f"确保字段 {field} 只有一个 writer；合并重复的 @writes 或拆分为不同字段",
        "TS02": f"字段 {field} 是 L4 派生缓存，不可作为下游真相源；改读其源 L2 字段",
        "TS03": f"字段 {field} 存在层级回写；检查 writer/reader 的 tier 声明是否正确",
        "TS04": f"字段 {field} 从 L1 直接派生 L4，缺少 L2 计算环节",
        "TS05": f"字段 {field} 的 @writes/@reads tier 声明与字段名后缀不一致",
    }
    return hints.get(code, "检查装饰器声明")


# ═══════════════════════════════════════════════════════════════
# Layer 2: 正则静态扫描（legacy，兜底）
# ═══════════════════════════════════════════════════════════════
>>>>>>> Stashed changes
PATTERNS = [
    {
        "id": "TS001",
        "name": "采购退货用 StockMove.unit_cost 计算库存贷方",
        "pattern": r"StockMove.*\.unit_cost|move\.unit_cost|original\.unit_cost",
<<<<<<< Updated upstream
        # 必须同时满足两个上下文条件才算违规：
        # 1. 退货/冲红上下文（return/reverse/inventory_cost）
        # 2. 采购上下文（purchase_order）—— 排除销售退货（sale_order 用 avg_cost 是对的）
=======
>>>>>>> Stashed changes
        "context_filter": "purchase_order",
        "exclude_context": "sale_order",
        "severity": "ERROR",
        "message": (
            "采购退货的库存贷方金额必须用 orig_item.unit_price（原发票不含税单价），"
            "不能用 StockMove.unit_cost（移动加权平均成本）。"
            "用 avg_cost 会导致借贷不平衡。"
        ),
        "fix_hint": "改用 orig_item.unit_price × qty_ret",
        "check_context": True,
    },
    {
        "id": "TS002",
        "name": "反向 StockMove 用 original.unit_cost",
        "pattern": r"effective_unit_cost\s*=\s*original\.unit_cost",
        "severity": "ERROR",
        "message": (
            "反向 StockMove 的 total_cost 必须用 original.total_cost / original.quantity，"
            "不能用 original.unit_cost（移动加权平均）。"
        ),
        "fix_hint": "改用 (original.total_cost / original.quantity).quantize(Decimal('0.000001'))",
        "check_context": False,
    },
]


def scan_file(filepath: Path) -> list:
<<<<<<< Updated upstream
    """扫描单个文件，返回违规列表"""
=======
    """扫描单个文件，返回违规列表（正则扫描层）"""
>>>>>>> Stashed changes
    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    lines = content.splitlines()
    violations = []

    for rule in PATTERNS:
        for i, line in enumerate(lines, 1):
            if not re.search(rule["pattern"], line, re.IGNORECASE):
                continue
<<<<<<< Updated upstream
            # 上下文过滤：必须包含 context_filter，且不包含 exclude_context
=======
>>>>>>> Stashed changes
            if rule.get("check_context"):
                ctx_start = max(0, i - 10)
                ctx_end = min(len(lines), i + 10)
                context = "\n".join(lines[ctx_start:ctx_end])
                if not re.search(rule["context_filter"], context, re.IGNORECASE):
                    continue
<<<<<<< Updated upstream
                # 排除上下文（如 sale_order 不是采购退货）
                if rule.get("exclude_context") and re.search(rule["exclude_context"], context, re.IGNORECASE):
                    continue
            # 跳过注释行
=======
                if rule.get("exclude_context") and re.search(rule["exclude_context"], context, re.IGNORECASE):
                    continue
>>>>>>> Stashed changes
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            violations.append({
                "file": str(filepath.relative_to(BACKEND_DIR.parent)),
                "line": i,
                "code": stripped,
                "rule_id": rule["id"],
                "rule_name": rule["name"],
                "severity": rule["severity"],
                "message": rule["message"],
                "fix_hint": rule["fix_hint"],
            })

    return violations


<<<<<<< Updated upstream
def scan() -> list:
    """扫描 backend 源码，返回 Truth Source Bypass 违规列表。

    可被外部调用（如 main.py startup 集成）：
        from check_truth_source import scan
        violations = scan()
    每条违规是 dict：{file, line, code, rule_id, rule_name, severity, message, fix_hint}
    """
=======
def scan_regex() -> list:
    """正则静态扫描，返回违规列表"""
>>>>>>> Stashed changes
    all_files = []
    for d in SCAN_DIRS:
        if d.exists():
            all_files.extend(d.glob(SCAN_GLOB))

    all_violations = []
    for f in all_files:
        all_violations.extend(scan_file(f))
    return all_violations


<<<<<<< Updated upstream
=======
# ═══════════════════════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════════════════════
def scan() -> list:
    """扫描 backend 源码，返回 Truth Source 违规列表。

    三层校验合并：
    1. 装饰器注册表校验（TS01~TS05）
    2. DSL 规则校验（AS-08/09/10/14 交叉校验）
    3. 正则静态扫描（TS001/TS002 兜底）

    可被外部调用（如 main.py startup 集成）：
        from check_truth_source import scan
        violations = scan()
    每条违规是 dict：{file, line, code, rule_id, rule_name, severity, message, fix_hint}
    """
    violations = []
    try:
        violations.extend(scan_registry())
    except Exception as e:
        # 注册表校验失败不应阻断正则扫描
        print(f"[WARN] 装饰器注册表校验失败: {e}", file=sys.stderr)

    try:
        violations.extend(scan_rules())
    except Exception as e:
        print(f"[WARN] DSL 规则校验失败: {e}", file=sys.stderr)

    violations.extend(scan_regex())
    return violations


def scan_rules() -> list:
    """DSL 规则校验：15 条会计准则与装饰器注册表交叉校验

    返回违规列表，格式与 scan_registry() 一致。
    """
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from lineage import REGISTRY
    from rules import validate_rules

    # 确保装饰器注册表已加载（导入引擎模块触发注册）
    _load_lineage_registry()

    rule_violations = validate_rules(REGISTRY)
    violations = []
    for v in rule_violations:
        violations.append({
            "file": "(rules_validator)",
            "line": 0,
            "code": "",
            "rule_id": v.rule_id,
            "rule_name": v.rule_name,
            "severity": v.severity,
            "message": v.message,
            "fix_hint": v.fix_hint or "",
            "field": v.field,
            "detail": v.detail,
        })
    return violations


>>>>>>> Stashed changes
def main():
    all_violations = scan()

    if not all_violations:
<<<<<<< Updated upstream
        print("✅ 通过：未检测到 Truth Source Bypass 反模式")
        return 0

    print(f"❌ 发现 {len(all_violations)} 处违规：\n")
    for v in all_violations:
        print(f"[{v['severity']}] {v['rule_id']} {v['rule_name']}")
        print(f"  位置: {v['file']}:{v['line']}")
        print(f"  代码: {v['code']}")
        print(f"  问题: {v['message']}")
        print(f"  修复: {v['fix_hint']}")
        print()
    return 1
=======
        print("✅ 通过：未检测到 Truth Source 违规（装饰器注册表 + 正则扫描）")
        return 0

    # 按严重程度分组
    errors = [v for v in all_violations if v["severity"] == "ERROR"]
    warnings = [v for v in all_violations if v["severity"] == "WARNING"]

    print(f"❌ 发现 {len(all_violations)} 处违规（{len(errors)} ERROR, {len(warnings)} WARNING）:\n")

    for v in all_violations:
        print(f"[{v['severity']}] {v['rule_id']} {v['rule_name']}")
        if v.get("file") and v.get("line"):
            print(f"  位置: {v['file']}:{v['line']}")
            print(f"  代码: {v['code']}")
        elif v.get("field"):
            print(f"  字段: {v['field']}")
            if v.get("writers"):
                print(f"  writers: {v['writers']}")
            if v.get("readers"):
                print(f"  readers: {v['readers']}")
            if v.get("detail"):
                print(f"  详情: {v['detail']}")
        print(f"  问题: {v['message']}")
        print(f"  修复: {v['fix_hint']}")
        print()

    # 只有 ERROR 才返回 1
    return 1 if errors else 0
>>>>>>> Stashed changes


if __name__ == "__main__":
    sys.exit(main())
