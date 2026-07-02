"""
数据血缘回溯 v3 — 函数级分析 + 环检测
"""

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"


def get_function_body(pyfile, target_line):
    try:
        tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= target_line <= node.end_lineno:
                return node
    return None


def extract_field_refs(func_node):
    refs = set()
    for node in ast.walk(func_node):
        if isinstance(node, ast.Attribute):
            if node.attr.endswith(("_l1", "_l2", "_l3", "_l4")):
                refs.add(node.attr)
    return sorted(refs)


def find_writes(target_suffix):
    results = []
    for pyfile in sorted(BACKEND.rglob("*.py")):
        if "venv" in str(pyfile) or ".venv" in str(pyfile):
            continue
        try:
            tree = ast.parse(pyfile.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Attribute) and t.attr.endswith(target_suffix):
                        func = get_function_body(pyfile, node.lineno)
                        results.append({
                            "file": str(pyfile.relative_to(BACKEND.parent)),
                            "line": node.lineno,
                            "target": t.attr,
                            "context_refs": extract_field_refs(func) if func else [],
                        })
            if isinstance(node, ast.Call):
                # 构造函数/函数调用的关键字参数: StockMove(unit_cost_l2=xxx)
                for kw in node.keywords:
                    if kw.arg and kw.arg.endswith(target_suffix):
                        func = get_function_body(pyfile, node.lineno)
                        results.append({
                            "file": str(pyfile.relative_to(BACKEND.parent)),
                            "line": node.lineno,
                            "target": kw.arg,
                                "context_refs": extract_field_refs(func) if func else [],
                            })
    return results


SEEN = set()


def trace(field, depth=0, path=None):
    if path is None:
        path = []
    if field in path:
        return  # 环检测
    if field in SEEN:
        return
    SEEN.add(field)

    prefix = "  " * depth
    print(f"{prefix}{field}")
    writes = find_writes(field)
    upstream = set()
    for w in writes:
        label = f"  {w['file']}:{w['line']}"
        print(f"{prefix}{label}")
        for ref in w["context_refs"]:
            if ref == field:
                continue
            upstream.add(ref)
    if upstream:
        l4s = {r for r in upstream if r.endswith("_l4") and r != field}
        l2s = {r for r in upstream if r.endswith("_l2")}
        l1s = {r for r in upstream if r.endswith("_l1")}
        l3s = {r for r in upstream if r.endswith("_l3")}
        for kind, items in [("_l4", l4s), ("_l2", l2s), ("_l1", l1s), ("_l3", l3s)]:
            if items:
                print(f"{prefix}  \u2191 {kind}: {', '.join(sorted(items))}")
        for ref in sorted(l2s | l4s):
            trace(ref, depth + 2, path + [field])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    target = sys.argv[1]
    if not target.endswith(("_l1", "_l2", "_l3", "_l4")):
        print("字段名应以 _l1 / _l2 / _l3 / _l4 结尾")
        sys.exit(1)
    print(f"\n=== 血缘回溯: {target} ===\n")
    trace(target)
    print()


if __name__ == "__main__":
    main()
