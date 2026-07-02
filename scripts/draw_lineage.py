"""数据来源链可视化脚本（增强版）

从 backend/lineage REGISTRY 读取所有 @writes/@reads/@derives 声明，
生成数据来源链图，支持：
- 违规高亮（TS02 违规边红色标注）
- 按模型分组（subgraph）
- 路径追踪（给定字段高亮其完整上游溯源链）
- 字段详情面板（点击节点显示 writer/reader 详情）
- JSON 导出（方便其他工具消费）

用法：
    python scripts/draw_lineage.py                       # mermaid 到 stdout
    python scripts/draw_lineage.py --html out.html       # 可交互的 HTML
    python scripts/draw_lineage.py --dot out.dot         # Graphviz DOT
    python scripts/draw_lineage.py --json out.json       # JSON 数据
    python scripts/draw_lineage.py --trace StockMove.unit_cost_l2  # 追踪字段上游
    python scripts/draw_lineage.py --stats               # 统计
"""
import sys
import json
import importlib
import argparse
from pathlib import Path
from collections import defaultdict

# 把 backend 加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_registry():
    """导入所有声明了装饰器的模块，返回 REGISTRY"""
    from lineage import REGISTRY
    REGISTRY.reset()

    modules = [
        # 引擎层
        "engine_inventory",
        "engine_journal",
        "engine_ledger",
        "engine_bank",
        "engine_fixed_asset",
        "engine_finance",
        "engine_tax",
        "finance_integration",
        # 命令层（含 L3 政策字段 @writes/@reads）
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
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            print(f"[WARN] 导入 {mod_name} 失败: {e}", file=sys.stderr)
    return REGISTRY


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════
TIER_COLOR = {
    "L1": "#c8e6c9",  # 绿
    "L2": "#bbdefb",  # 蓝
    "L3": "#ffe0b2",  # 橙
    "L4": "#e1bee7",  # 紫
}
TIER_LABEL = {
    "L1": "L1 外部输入",
    "L2": "L2 引擎计算",
    "L3": "L3 政策配置",
    "L4": "L4 派生汇总",
}
VIOLATION_COLOR = "#ffcdd2"  # 浅红 - 违规节点


def field_tier(path: str) -> str:
    for suffix, tier in [("_l1", "L1"), ("_l2", "L2"), ("_l3", "L3"), ("_l4", "L4")]:
        if path.endswith(suffix):
            return tier
    return "L2"


def shorten_path(path: str) -> str:
    # 直接返回原路径（Mermaid 节点标签对 HTML 标签兼容性差，改用纯文本）
    return path


def safe_id(path: str) -> str:
    return path.replace(".", "_").replace("-", "_")


def model_of(path: str) -> str:
    return path.split(".", 1)[0]


def get_violations(registry) -> list:
    """从注册表获取违规列表"""
    from lineage import validate_invariants
    return validate_invariants()


def get_violation_fields(registry) -> set:
    """获取所有违规涉及的字段路径"""
    violations = get_violations(registry)
    fields = set()
    for v in violations:
        if v.field:
            fields.add(v.field)
        if hasattr(v, "writers"):
            for w in v.writers:
                # writers 是 func_qualname，不是字段，跳过
                pass
        if hasattr(v, "readers"):
            for r in v.readers:
                pass
    return fields


def get_violation_read_edges(registry) -> set:
    """获取违规的 read 边（L4 字段被读）"""
    violations = get_violations(registry)
    edges = set()
    for v in violations:
        if v.code == "TS02" and v.field:
            # L4 字段被读取，找到所有读取该字段的 reader
            for r in registry.reads:
                if r.field.path == v.field:
                    # 找该 reader 的上游 writer（即 L4 writer）
                    for w in registry.writers_for(v.field):
                        if w.field.path != r.field.path:
                            edges.add((w.field.path, r.field.path))
    return edges


def get_violation_reader_funcs(registry) -> set:
    """获取违规读取的 (field_path, func_qualname) 对集合

    用于在 Mermaid 图中高亮「L4 字段 → reader 函数」的违规读取边。
    """
    violations = get_violations(registry)
    pairs = set()
    for v in violations:
        if v.code == "TS02" and v.field:
            for r in registry.reads:
                if r.field.path == v.field:
                    pairs.add((r.field.path, r.func_qualname))
    return pairs


# ═══════════════════════════════════════════════════════════════
# 路径追踪：给定字段，找完整上游溯源链
# ═══════════════════════════════════════════════════════════════
def trace_upstream(registry, field_path: str) -> dict:
    """追踪某字段的完整上游溯源链

    追踪规则：
    - @derives 声明的字段：从 from_fields 追溯（L4 ← L2）
    - @writes 声明的字段：该字段由引擎直接生成，无字段级上游（源头）
    - @reads 声明的字段：追溯该字段的 writer（writer → reader 边）

    返回:
    {
        "target": "LedgerAccountBalance.balance_l4",
        "upstream_fields": ["AccountMoveLine.debit_l2", "AccountMoveLine.credit_l2"],
        "edges": [(src, dst, func), ...],
    }
    """
    visited = set()
    edges = []
    upstream_fields = set()

    def _trace(path: str, depth: int):
        if path in visited or depth > 10:
            return
        visited.add(path)

        # 找谁写了这个字段
        for w in registry.writers_for(path):
            if w.is_derived and w.from_fields:
                # 派生：从 from_fields 追溯（L4 ← L2）
                for src in w.from_fields:
                    edges.append((src, path, w.func_qualname))
                    upstream_fields.add(src)
                    _trace(src, depth + 1)
            # 纯 @writes 不追溯：引擎直接生成的字段无字段级上游

    _trace(field_path, 0)
    return {
        "target": field_path,
        "upstream_fields": sorted(upstream_fields),
        "edges": edges,
    }


def trace_downstream(registry, field_path: str) -> dict:
    """追踪某字段的下游消费链"""
    visited = set()
    edges = []
    downstream_fields = set()

    def _trace(path: str, depth: int):
        if path in visited or depth > 10:
            return
        visited.add(path)

        # 找谁读了这个字段
        readers = registry.readers_for(path)
        for r in readers:
            # 找该 reader 写了什么
            for w in registry.writes:
                if w.func_qualname == r.func_qualname and w.field.path != path:
                    edges.append((path, w.field.path, r.func_qualname))
                    downstream_fields.add(w.field.path)
                    _trace(w.field.path, depth + 1)

    _trace(field_path, 0)
    return {
        "source": field_path,
        "downstream_fields": sorted(downstream_fields),
        "edges": edges,
    }


# ═══════════════════════════════════════════════════════════════
# Mermaid 生成
def generate_mermaid(registry, trace_field: str = None) -> str:
    """生成 Mermaid 流程图

    节点类型：
    - 字段节点（矩形）：按 Model 分组，按 tier 着色
    - 函数节点（圆角）：单独分组，作为数据流中转

    边类型：
    - 写入边：func --> field（实线）
    - 读取边：field --> func（实线）
    - 派生边：field -.-> field（虚线，L2→L4）
    - 违规读取边：field ==> func（红色粗线，L4 被读）

    Args:
        trace_field: 若指定，只高亮该字段的上游溯源链
    """
    violation_fields = get_violation_fields(registry)
    violation_readers = get_violation_reader_funcs(registry)  # (field, func) 集合

    # 若指定追踪字段，计算高亮集合
    highlight_nodes = set()
    highlight_edges = set()
    if trace_field:
        trace = trace_upstream(registry, trace_field)
        highlight_nodes.add(trace_field)
        highlight_nodes.update(trace["upstream_fields"])
        for src, dst, _ in trace["edges"]:
            highlight_edges.add((src, dst))

    lines = ["graph LR"]

    # 1. 字段节点 - 按模型分组
    all_fields = set()
    for w in registry.writes:
        all_fields.add(w.field.path)
    for r in registry.reads:
        all_fields.add(r.field.path)

    by_model = defaultdict(list)
    for path in sorted(all_fields):
        by_model[model_of(path)].append(path)

    for model_name in sorted(by_model.keys()):
        lines.append(f'    subgraph {model_name} ["{model_name}"]')
        for path in by_model[model_name]:
            nid = safe_id(path)
            label = shorten_path(path)
            tier = field_tier(path)
            is_violation = path in violation_fields
            is_highlight = path in highlight_nodes

            if is_violation:
                lines.append(f'    {nid}["{label}"]:::violation')
            elif is_highlight:
                lines.append(f'    {nid}["{label}"]:::highlight')
            else:
                lines.append(f'    {nid}["{label}"]:::tier{tier}')
        lines.append("    end")
        lines.append("")

    # 2. 函数节点 - 单独分组
    all_funcs = set()
    for w in registry.writes:
        all_funcs.add(w.func_qualname)
    for r in registry.reads:
        all_funcs.add(r.func_qualname)

    lines.append('    subgraph Functions ["函数 / 引擎"]')
    for func in sorted(all_funcs):
        # 优化标签：XxxHandler.handle → XxxHandler；Class.method → method；func → func
        if "." in func:
            cls, method = func.rsplit(".", 1)
            if method == "handle":
                label = cls  # 取类名
            else:
                label = method  # 取方法名
        else:
            label = func
        nid = safe_id("func_" + func)
        lines.append(f'    {nid}("{label}"):::func')
    lines.append("    end")
    lines.append("")

    # 3. 写入边：func --> field
    seen_edges = set()
    lines.append("    %% 写入边：func --> field")
    for w in registry.writes:
        func_nid = safe_id("func_" + w.func_qualname)
        field_nid = safe_id(w.field.path)
        edge = (w.func_qualname, w.field.path, "write")
        if edge in seen_edges:
            continue
        seen_edges.add(edge)
        is_highlight = w.field.path in highlight_nodes
        if is_highlight:
            lines.append(f'    {func_nid} ==> {field_nid}')
        else:
            lines.append(f'    {func_nid} --> {field_nid}')

    # 4. 读取边：field --> func
    lines.append("")
    lines.append("    %% 读取边：field --> func")
    for r in registry.reads:
        field_nid = safe_id(r.field.path)
        func_nid = safe_id("func_" + r.func_qualname)
        edge = (r.field.path, r.func_qualname, "read")
        if edge in seen_edges:
            continue
        seen_edges.add(edge)
        is_violation_read = (r.field.path, r.func_qualname) in violation_readers
        is_highlight = r.field.path in highlight_nodes
        if is_violation_read:
            lines.append(f'    {field_nid} ==> {func_nid}:::violationEdge')
        elif is_highlight:
            lines.append(f'    {field_nid} ==> {func_nid}')
        else:
            lines.append(f'    {field_nid} --> {func_nid}')

    # 5. 派生边：field -.-> field（L2 → L4）
    lines.append("")
    lines.append("    %% 派生关系：L2 source -.-> L4 derived")
    for w in registry.writes:
        if not w.is_derived or not w.from_fields:
            continue
        for src_path in w.from_fields:
            edge = (src_path, w.field.path, "derive")
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            src = safe_id(src_path)
            dst = safe_id(w.field.path)
            is_highlight = (src_path, w.field.path) in highlight_edges
            if is_highlight:
                lines.append(f'    {src} ==> {dst}')
            else:
                lines.append(f'    {src} -.-> {dst}')

    # 6. 样式
    lines.append("")
    lines.append("    %% 层级样式")
    for tier, color in TIER_COLOR.items():
        lines.append(f"    classDef tier{tier} fill:{color},stroke:#333,stroke-width:1px")
    lines.append(f"    classDef violation fill:{VIOLATION_COLOR},stroke:#f44336,stroke-width:3px")
    lines.append("    classDef highlight fill:#fff9c4,stroke:#f57f17,stroke-width:3px")
    lines.append("    classDef func fill:#fff,stroke:#666,stroke-width:1px")
    lines.append("    classDef violationEdge stroke:#f44336,stroke-width:3px")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# JSON 导出
# ═══════════════════════════════════════════════════════════════
def generate_json(registry) -> dict:
    """生成数据链 JSON 结构"""
    violations = get_violations(registry)

    # 节点
    all_fields = set()
    for w in registry.writes:
        all_fields.add(w.field.path)
    for r in registry.reads:
        all_fields.add(r.field.path)

    violation_fields = {v.field for v in violations if v.field}

    nodes = []
    for path in sorted(all_fields):
        writers = [
            {
                "func": w.func_qualname,
                "tier": w.tier,
                "source": w.source,
                "is_derived": w.is_derived,
                "from_fields": w.from_fields or [],
            }
            for w in registry.writers_for(path)
        ]
        readers = [
            {
                "func": r.func_qualname,
                "tier": r.tier,
                "source": r.source,
            }
            for r in registry.readers_for(path)
        ]
        nodes.append({
            "id": path,
            "model": model_of(path),
            "field": path.split(".", 1)[1] if "." in path else path,
            "tier": field_tier(path),
            "is_violation": path in violation_fields,
            "writers": writers,
            "readers": readers,
        })

    # 边：与 Mermaid 一致的三种边类型
    edges = []
    seen = set()

    # 写入边：func → field
    for w in registry.writes:
        edge_key = (w.func_qualname, w.field.path, "write")
        if edge_key in seen:
            continue
        seen.add(edge_key)
        edges.append({
            "source": w.func_qualname,
            "target": w.field.path,
            "func": w.func_qualname,
            "type": "write",
        })

    # 读取边：field → func
    for r in registry.reads:
        edge_key = (r.field.path, r.func_qualname, "read")
        if edge_key in seen:
            continue
        seen.add(edge_key)
        edges.append({
            "source": r.field.path,
            "target": r.func_qualname,
            "func": r.func_qualname,
            "type": "read",
        })

    # 派生边：field → field（L2 → L4）
    for w in registry.writes:
        if not w.is_derived or not w.from_fields:
            continue
        for src in w.from_fields:
            edge_key = (src, w.field.path, "derive")
            if edge_key in seen:
                continue
            seen.add(edge_key)
            edges.append({
                "source": src,
                "target": w.field.path,
                "func": w.func_qualname,
                "type": "derive",
            })

    # 函数节点（与字段节点并列）
    all_funcs = set()
    for w in registry.writes:
        all_funcs.add(w.func_qualname)
    for r in registry.reads:
        all_funcs.add(r.func_qualname)

    func_nodes = []
    for func in sorted(all_funcs):
        if "." in func:
            cls, method = func.rsplit(".", 1)
            label = cls if method == "handle" else method
        else:
            label = func
        func_nodes.append({
            "id": func,
            "type": "function",
            "label": label,
        })

    return {
        "nodes": nodes,
        "functions": func_nodes,
        "edges": edges,
        "violations": [
            {
                "code": v.code,
                "severity": v.severity,
                "rule": v.rule,
                "message": v.message,
                "field": v.field,
            }
            for v in violations
        ],
        "stats": {
            "total_writes": len(registry.writes),
            "total_reads": len(registry.reads),
            "unique_written_fields": len(registry.all_written_fields()),
            "unique_read_fields": len(registry.all_read_fields()),
            "total_violations": len(violations),
            "error_violations": sum(1 for v in violations if v.severity == "ERROR"),
            "warning_violations": sum(1 for v in violations if v.severity == "WARNING"),
        },
    }


# ═══════════════════════════════════════════════════════════════
# HTML 生成（交互式）
# ═══════════════════════════════════════════════════════════════
def generate_html(registry) -> str:
    mermaid = generate_mermaid(registry)
    data = generate_json(registry)
    data_json = json.dumps(data, ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>数据来源链图</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; margin: 0; background: #fafafa; }}
.header {{ background: #fff; padding: 16px 24px; border-bottom: 1px solid #e0e0e0; position: sticky; top: 0; z-index: 100; }}
.header h1 {{ margin: 0 0 8px 0; color: #333; font-size: 20px; }}
.stats {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: #666; }}
.stats span {{ background: #f5f5f5; padding: 4px 10px; border-radius: 12px; }}
.stats .error {{ background: #ffebee; color: #c62828; }}
.stats .warning {{ background: #fff8e1; color: #f57f17; }}
.legend {{ display: flex; gap: 12px; margin-top: 8px; }}
.legend-item {{ display: flex; align-items: center; gap: 4px; font-size: 12px; }}
.legend-color {{ width: 14px; height: 14px; border-radius: 3px; border: 1px solid #333; }}
.container {{ display: flex; height: calc(100vh - 140px); }}
.graph-container {{ flex: 1; overflow: auto; padding: 20px; background: #fff; }}
.graph-container .mermaid {{ background: #fff; padding: 20px; border-radius: 8px; }}
.sidebar {{ width: 400px; border-left: 1px solid #e0e0e0; background: #fff; overflow-y: auto; padding: 16px; }}
.sidebar h2 {{ font-size: 16px; margin: 0 0 12px 0; color: #333; }}
.search-box {{ width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; margin-bottom: 12px; }}
.field-card {{ background: #f9f9f9; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; margin-bottom: 8px; cursor: pointer; transition: background 0.2s; }}
.field-card:hover {{ background: #e3f2fd; }}
.field-card.selected {{ background: #fff9c4; border-color: #f57f17; }}
.field-card .field-name {{ font-weight: 600; font-size: 14px; }}
.field-card .field-tier {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-left: 6px; }}
.tier-L1 {{ background: #c8e6c9; }}
.tier-L2 {{ background: #bbdefb; }}
.tier-L3 {{ background: #ffe0b2; }}
.tier-L4 {{ background: #e1bee7; }}
.field-card .violation-badge {{ background: #ffcdd2; color: #c62828; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-left: 6px; }}
.detail-section {{ margin-top: 12px; }}
.detail-section h3 {{ font-size: 13px; color: #666; margin: 8px 0 4px 0; }}
.detail-section .item {{ background: #f5f5f5; padding: 6px 10px; border-radius: 4px; margin-bottom: 4px; font-size: 12px; font-family: monospace; }}
.violations-list {{ margin-top: 16px; }}
.violation-item {{ background: #ffebee; border-left: 3px solid #f44336; padding: 8px 12px; margin-bottom: 8px; font-size: 12px; }}
.violation-item .code {{ font-weight: bold; color: #c62828; }}
.empty-state {{ color: #999; text-align: center; padding: 40px 20px; font-size: 14px; }}
</style>
</head>
<body>
<div class="header">
    <h1>数据来源链图</h1>
    <div class="stats">
        <span>字段: {data['stats']['unique_written_fields']} 写 / {data['stats']['unique_read_fields']} 读</span>
        <span>声明: {data['stats']['total_writes']} @writes + {data['stats']['total_reads']} @reads</span>
        <span class="error">违规: {data['stats']['error_violations']} ERROR</span>
        <span class="warning">{data['stats']['warning_violations']} WARNING</span>
    </div>
    <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background:{TIER_COLOR['L1']}"></div>L1 外部输入</div>
        <div class="legend-item"><div class="legend-color" style="background:{TIER_COLOR['L2']}"></div>L2 引擎计算</div>
        <div class="legend-item"><div class="legend-color" style="background:{TIER_COLOR['L3']}"></div>L3 政策配置</div>
        <div class="legend-item"><div class="legend-color" style="background:{TIER_COLOR['L4']}"></div>L4 派生汇总</div>
        <div class="legend-item"><div class="legend-color" style="background:{VIOLATION_COLOR};border-color:#f44336"></div>违规字段</div>
    </div>
</div>
<div class="container">
    <div class="graph-container">
        <div class="mermaid">
{mermaid}
        </div>
    </div>
    <div class="sidebar">
        <h2>字段搜索</h2>
        <input type="text" class="search-box" id="searchBox" placeholder="输入字段名搜索（如 unit_cost）...">
        <div id="fieldList"></div>
        <div id="fieldDetail"></div>
        <div class="violations-list" id="violationsList"></div>
    </div>
</div>
<script>
mermaid.initialize({{ startOnLoad: true, theme: 'default', flowchart: {{ curve: 'basis', useMaxWidth: false }} }});

const lineageData = {data_json};

// 渲染字段列表
function renderFieldList(filter = '') {{
    const list = document.getElementById('fieldList');
    const filtered = lineageData.nodes.filter(n =>
        n.id.toLowerCase().includes(filter.toLowerCase())
    );

    if (filtered.length === 0) {{
        list.innerHTML = '<div class="empty-state">无匹配字段</div>';
        return;
    }}

    list.innerHTML = filtered.map(n => `
        <div class="field-card" onclick="selectField('${{n.id}}')">
            <span class="field-name">${{n.field}}</span>
            <span class="field-tier tier-${{n.tier}}">${{n.tier}}</span>
            ${{n.is_violation ? '<span class="violation-badge">违规</span>' : ''}}
            <div style="font-size:11px;color:#999;margin-top:4px">${{n.model}}</div>
        </div>
    `).join('');
}}

// 选中字段显示详情
function selectField(fieldId) {{
    const node = lineageData.nodes.find(n => n.id === fieldId);
    if (!node) return;

    // 高亮选中
    document.querySelectorAll('.field-card').forEach(c => c.classList.remove('selected'));
    event.target.closest('.field-card').classList.add('selected');

    const detail = document.getElementById('fieldDetail');
    detail.innerHTML = `
        <div class="detail-section">
            <h3>字段路径</h3>
            <div class="item">${{node.id}}</div>
            <h3>层级</h3>
            <div class="item"><span class="field-tier tier-${{node.tier}}">${{node.tier}}</span> ${{{{'L1':'外部输入','L2':'引擎计算','L3':'政策配置','L4':'派生汇总'}}[node.tier]}}</div>
            ${{node.writers.length > 0 ? `<h3>写入方 (${{node.writers.length}})</h3>` + node.writers.map(w => `<div class="item">${{w.func}}<br><small>${{w.is_derived ? '派生自: ' + w.from_fields.join(', ') : w.source}}</small></div>`).join('') : ''}}
            ${{node.readers.length > 0 ? `<h3>读取方 (${{node.readers.length}})</h3>` + node.readers.map(r => `<div class="item">${{r.func}}</div>`).join('') : ''}}
            ${{node.is_violation ? '<div class="violation-badge">⚠️ 此字段涉及违规</div>' : ''}}
        </div>
    `;
}}

// 渲染违规列表
function renderViolations() {{
    const list = document.getElementById('violationsList');
    if (lineageData.violations.length === 0) {{
        list.innerHTML = '<h2>违规检查</h2><div class="empty-state">✅ 无违规</div>';
        return;
    }}
    list.innerHTML = '<h2>违规检查 (' + lineageData.violations.length + ')</h2>' +
        lineageData.violations.map(v => `
            <div class="violation-item">
                <span class="code">${{v.code}}</span> ${{v.severity}}
                <div style="margin-top:4px"><strong>${{v.rule}}</strong></div>
                <div style="margin-top:4px;color:#666">${{v.message}}</div>
                ${{v.field ? `<div style="margin-top:4px;font-family:monospace">字段: ${{v.field}}</div>` : ''}}
            </div>
        `).join('');
}}

// 搜索
document.getElementById('searchBox').addEventListener('input', e => {{
    renderFieldList(e.target.value);
}});

// 初始渲染
renderFieldList();
renderViolations();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# DOT 生成
# ═══════════════════════════════════════════════════════════════
def generate_dot(registry) -> str:
    violation_fields = get_violation_fields(registry)

    lines = ["digraph lineage {", "    rankdir=LR;", "    node [shape=box, style=filled];", ""]

    # 字段节点
    all_fields = set()
    for w in registry.writes:
        all_fields.add(w.field.path)
    for r in registry.reads:
        all_fields.add(r.field.path)

    for path in sorted(all_fields):
        tier = field_tier(path)
        nid = safe_id(path)
        if path in violation_fields:
            color = VIOLATION_COLOR
        else:
            color = TIER_COLOR.get(tier, "#ffffff")
        label = path.replace("_", "\\n")
        lines.append(f'    {nid} [label="{label}", fillcolor="{color}"];')

    # 函数节点（椭圆形）
    all_funcs = set()
    for w in registry.writes:
        all_funcs.add(w.func_qualname)
    for r in registry.reads:
        all_funcs.add(r.func_qualname)

    lines.append("")
    lines.append('    // 函数节点')
    for func in sorted(all_funcs):
        if "." in func:
            cls, method = func.rsplit(".", 1)
            label = cls if method == "handle" else method
        else:
            label = func
        nid = safe_id("func_" + func)
        lines.append(f'    {nid} [label="{label}", shape=ellipse, fillcolor="#ffffff"];')

    # 写入边：func → field
    seen = set()
    lines.append("")
    lines.append('    // 写入边')
    for w in registry.writes:
        edge = (w.func_qualname, w.field.path, "write")
        if edge in seen:
            continue
        seen.add(edge)
        src = safe_id("func_" + w.func_qualname)
        dst = safe_id(w.field.path)
        lines.append(f'    {src} -> {dst};')

    # 读取边：field → func
    lines.append("")
    lines.append('    // 读取边')
    for r in registry.reads:
        edge = (r.field.path, r.func_qualname, "read")
        if edge in seen:
            continue
        seen.add(edge)
        src = safe_id(r.field.path)
        dst = safe_id("func_" + r.func_qualname)
        lines.append(f'    {src} -> {dst};')

    # 派生边：field → field
    lines.append("")
    lines.append('    // 派生边')
    for w in registry.writes:
        if not w.is_derived or not w.from_fields:
            continue
        for src_path in w.from_fields:
            edge = (src_path, w.field.path, "derive")
            if edge in seen:
                continue
            seen.add(edge)
            src = safe_id(src_path)
            dst = safe_id(w.field.path)
            lines.append(f'    {src} -> {dst} [style=dashed];')

    lines.append("}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="生成数据来源链图")
    parser.add_argument("--html", metavar="FILE", help="输出交互式 HTML")
    parser.add_argument("--dot", metavar="FILE", help="输出 Graphviz DOT")
    parser.add_argument("--json", metavar="FILE", help="输出 JSON 数据")
    parser.add_argument("--trace", metavar="FIELD", help="追踪字段的上游溯源链")
    parser.add_argument("--stats", action="store_true", help="输出统计")
    args = parser.parse_args()

    registry = load_registry()

    if args.stats:
        data = generate_json(registry)
        s = data["stats"]
        print("=== 数据链注册表统计 ===")
        print(f"写入声明 (@writes/@derives): {s['total_writes']}")
        print(f"读取声明 (@reads): {s['total_reads']}")
        print(f"唯一写入字段: {s['unique_written_fields']}")
        print(f"唯一读取字段: {s['unique_read_fields']}")
        print(f"\n违规: {s['total_violations']} ({s['error_violations']} ERROR, {s['warning_violations']} WARNING)")
        by_tier_w = defaultdict(int)
        by_tier_r = defaultdict(int)
        for w in registry.writes:
            by_tier_w[w.tier] += 1
        for r in registry.reads:
            by_tier_r[r.tier] += 1
        print(f"\n按层级分布:")
        for tier in ["L1", "L2", "L3", "L4"]:
            print(f"  {tier}: writes={by_tier_w.get(tier,0)}, reads={by_tier_r.get(tier,0)}")
        return

    if args.trace:
        trace = trace_upstream(registry, args.trace)
        print(f"=== 上游溯源链: {args.trace} ===")
        print(f"上游字段 ({len(trace['upstream_fields'])}):")
        for f in trace["upstream_fields"]:
            tier = field_tier(f)
            print(f"  [{tier}] {f}")
        print(f"\n溯源边 ({len(trace['edges'])}):")
        for src, dst, func in trace["edges"]:
            print(f"  {src} --{func.split('.')[-1]}--> {dst}")
        return

    if args.json:
        data = generate_json(registry)
        Path(args.json).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"JSON 已写入 {args.json}")
        return

    if args.dot:
        dot = generate_dot(registry)
        Path(args.dot).write_text(dot, encoding="utf-8")
        print(f"DOT 已写入 {args.dot}")
        return

    if args.html:
        html = generate_html(registry)
        Path(args.html).write_text(html, encoding="utf-8")
        print(f"HTML 已写入 {args.html}")
        return

    print(generate_mermaid(registry))


if __name__ == "__main__":
    main()
