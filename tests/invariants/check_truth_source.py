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
"""
import re
import sys
import os
from pathlib import Path

# 扫描范围
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
SCAN_DIRS = [
    BACKEND_DIR / "commands",
    BACKEND_DIR,  # engine_*.py 在根目录
]
SCAN_GLOB = "*.py"

# 反模式规则
PATTERNS = [
    {
        "id": "TS001",
        "name": "采购退货用 StockMove.unit_cost 计算库存贷方",
        "pattern": r"StockMove.*\.unit_cost|move\.unit_cost|original\.unit_cost",
        # 必须同时满足两个上下文条件才算违规：
        # 1. 退货/冲红上下文（return/reverse/inventory_cost）
        # 2. 采购上下文（purchase_order）—— 排除销售退货（sale_order 用 avg_cost 是对的）
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
    """扫描单个文件，返回违规列表"""
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
            # 上下文过滤：必须包含 context_filter，且不包含 exclude_context
            if rule.get("check_context"):
                ctx_start = max(0, i - 10)
                ctx_end = min(len(lines), i + 10)
                context = "\n".join(lines[ctx_start:ctx_end])
                if not re.search(rule["context_filter"], context, re.IGNORECASE):
                    continue
                # 排除上下文（如 sale_order 不是采购退货）
                if rule.get("exclude_context") and re.search(rule["exclude_context"], context, re.IGNORECASE):
                    continue
            # 跳过注释行
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


def scan() -> list:
    """扫描 backend 源码，返回 Truth Source Bypass 违规列表。

    可被外部调用（如 main.py startup 集成）：
        from check_truth_source import scan
        violations = scan()
    每条违规是 dict：{file, line, code, rule_id, rule_name, severity, message, fix_hint}
    """
    all_files = []
    for d in SCAN_DIRS:
        if d.exists():
            all_files.extend(d.glob(SCAN_GLOB))

    all_violations = []
    for f in all_files:
        all_violations.extend(scan_file(f))
    return all_violations


def main():
    all_violations = scan()

    if not all_violations:
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


if __name__ == "__main__":
    sys.exit(main())
