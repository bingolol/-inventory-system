"""数据血缘装饰器注册表与校验逻辑

设计基于数字源原则四层级：
- L1 外部输入（发票金额、银行流水、用户录入）
- L2 引擎计算（移动加权平均成本、税额、凭证金额）
- L3 政策配置（税率、纳税人类型、主数据价格）
- L4 派生汇总（科目余额、库存缓存、报表数字）

合法数据链规则：
- 层级单调不降：L1→L2→L4 合法；L4→L2 非法（回写）
- writer 唯一：每个 L2 真相源字段只能由一个 writer 写入（避免双算法）
- 禁止跳层：L1 直写 L4 缺少 L2 计算环节属可疑（除期初余额等例外）
- L4 不可作为下游真相源：L4 字段被 @reads 引用即为违规
"""
from __future__ import annotations
import functools
import inspect
from collections import defaultdict
from dataclasses import dataclass, field as dc_field
from typing import Callable, Optional


# ═══════════════════════════════════════════════════════════════
# 层级常量
# ═══════════════════════════════════════════════════════════════
TIER_L1 = "L1"  # 外部输入
TIER_L2 = "L2"  # 引擎计算
TIER_L3 = "L3"  # 政策配置
TIER_L4 = "L4"  # 派生汇总

TIER_ORDER = {TIER_L1: 1, TIER_L2: 2, TIER_L3: 2, TIER_L4: 3}
# L3 与 L2 同序：L3 是政策输入，不参与 L1→L2→L4 的派生链，
# 但 L3 不能由 L4 派生（回写禁止）


@dataclass(frozen=True)
class FieldRef:
    """字段引用：Model.field_name 字符串路径"""
    path: str  # 例如 "StockMove.unit_cost_l2"

    @property
    def model_name(self) -> str:
        return self.path.split(".")[0]

    @property
    def field_name(self) -> str:
        return self.path.split(".", 1)[1]

    @property
    def tier_from_suffix(self) -> Optional[str]:
        """从字段名后缀推断层级（_l1~_l4）"""
        for suffix, tier in [("_l1", TIER_L1), ("_l2", TIER_L2),
                              ("_l3", TIER_L3), ("_l4", TIER_L4)]:
            if self.field_name.endswith(suffix):
                return tier
        return None


@dataclass
class WriteRecord:
    """函数对某字段的写入声明"""
    field: FieldRef
    tier: str           # 声明的层级
    source: str         # external / engine / policy / derived
    func_qualname: str  # 函数完整限定名
    func_module: str
    is_derived: bool = False  # @derives 装饰的派生写入（L4 缓存更新）
    from_fields: list = None  # @derives 的源字段路径列表（仅 is_derived=True 时有效）


@dataclass
class ReadRecord:
    """函数对某字段的读取声明"""
    field: FieldRef
    tier: str
    source: str
    func_qualname: str
    func_module: str


@dataclass
class LineageViolation:
    """数据链违规"""
    code: str           # TS01~TS99
    severity: str       # ERROR / WARNING
    rule: str           # 规则名
    message: str
    field: Optional[str] = None
    writers: list = dc_field(default_factory=list)
    readers: list = dc_field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# 全局注册表
# ═══════════════════════════════════════════════════════════════
class _LineageRegistry:
    """writer/reader 全局注册表"""

    def __init__(self):
        self._writes: list[WriteRecord] = []
        self._reads: list[ReadRecord] = []

    def add_write(self, rec: WriteRecord) -> None:
        self._writes.append(rec)

    def add_read(self, rec: ReadRecord) -> None:
        self._reads.append(rec)

    @property
    def writes(self) -> list[WriteRecord]:
        return list(self._writes)

    @property
    def reads(self) -> list[ReadRecord]:
        return list(self._reads)

    def writers_for(self, field_path: str) -> list[WriteRecord]:
        return [w for w in self._writes if w.field.path == field_path]

    def readers_for(self, field_path: str) -> list[ReadRecord]:
        return [r for r in self._reads if r.field.path == field_path]

    def all_written_fields(self) -> set[str]:
        return {w.field.path for w in self._writes}

    def all_read_fields(self) -> set[str]:
        return {r.field.path for r in self._reads}

    def reset(self) -> None:
        """测试用：清空注册表"""
        self._writes.clear()
        self._reads.clear()


REGISTRY = _LineageRegistry()


# ═══════════════════════════════════════════════════════════════
# 装饰器
# ═══════════════════════════════════════════════════════════════
def writes(field_path: str, tier: str, source: str):
    """声明函数写入某真相源字段

    Args:
        field_path: "Model.field" 字符串，如 "StockMove.unit_cost_l2"
        tier: TIER_L1~L4 之一
        source: external / engine / policy

    用法:
        @writes("StockMove.quantity_l1", tier=TIER_L1, source="external")
        @writes("StockMove.unit_cost_l2", tier=TIER_L2, source="engine")
        def inbound(self, ...): ...
    """
    def decorator(func: Callable) -> Callable:
        ref = FieldRef(field_path)
        rec = WriteRecord(
            field=ref, tier=tier, source=source,
            func_qualname=func.__qualname__,
            func_module=getattr(func, "__module__", ""),
        )
        REGISTRY.add_write(rec)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._lineage_writes = getattr(func, "_lineage_writes", []) + [rec]
        return wrapper
    return decorator


def reads(field_path: str, tier: str, source: str):
    """声明函数读取某真相源字段

    用于报表/读取方，扫描器据此校验读取的字段是否合法真相源。

    Args:
        field_path: "Model.field" 字符串
        tier: 被读字段的层级
        source: 被读字段的来源

    用法:
        @reads("StockMove.unit_cost_l2", tier=TIER_L2, source="engine")
        def calc_cogs(...): ...
    """
    def decorator(func: Callable) -> Callable:
        ref = FieldRef(field_path)
        rec = ReadRecord(
            field=ref, tier=tier, source=source,
            func_qualname=func.__qualname__,
            func_module=getattr(func, "__module__", ""),
        )
        REGISTRY.add_read(rec)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._lineage_reads = getattr(func, "_lineage_reads", []) + [rec]
        return wrapper
    return decorator


def derives(derived_path: str, from_fields: list[str], derived_tier: str = TIER_L4):
    """声明函数计算某派生字段（L4 缓存）来自哪些源字段

    用于 LedgerEngine.update_balance / InventoryEngine._update_cache 等
    L4 缓存更新方法，显式声明 L4 ← L2 的派生关系。

    Args:
        derived_path: 派生字段路径，如 "LedgerAccountBalance.balance_l4"
        from_fields: 源字段路径列表，如 ["AccountMoveLine.debit_l2", "AccountMoveLine.credit_l2"]
        derived_tier: 派生字段层级，默认 L4

    用法:
        @derives("LedgerAccountBalance.balance_l4",
                 from_fields=["AccountMoveLine.debit_l2", "AccountMoveLine.credit_l2"])
        def update_balance(self, line): ...
    """
    def decorator(func: Callable) -> Callable:
        # 注册派生写入
        ref = FieldRef(derived_path)
        rec = WriteRecord(
            field=ref, tier=derived_tier, source="derived",
            func_qualname=func.__qualname__,
            func_module=getattr(func, "__module__", ""),
            is_derived=True,
            from_fields=list(from_fields),
        )
        REGISTRY.add_write(rec)

        # 注册对源字段的读取
        for src in from_fields:
            src_ref = FieldRef(src)
            src_tier = src_ref.tier_from_suffix or TIER_L2
            src_rec = ReadRecord(
                field=src_ref, tier=src_tier, source="engine",
                func_qualname=func.__qualname__,
                func_module=getattr(func, "__module__", ""),
            )
            REGISTRY.add_read(src_rec)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        wrapper._lineage_derives = getattr(func, "_lineage_derives", []) + [(derived_path, from_fields)]
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# 图构建与不变量校验
# ═══════════════════════════════════════════════════════════════
def build_lineage_graph() -> dict:
    """从注册表构建数据链图

    返回邻接表: {field_path: [downstream_field_paths]}
    边方向：write_field → read_field（数据流向下游）
    """
    graph: dict[str, list[str]] = defaultdict(list)

    # 写入→读取 边
    write_fields = REGISTRY.all_written_fields()
    for read_rec in REGISTRY.reads:
        if read_rec.field.path in write_fields:
            # 找出所有写该字段的 writer，建立 write→read 边
            for w in REGISTRY.writers_for(read_rec.field.path):
                # 同函数内的 @derives 已显式建边，这里避免重复
                if w.func_qualname != read_rec.func_qualname:
                    graph[w.field.path].append(read_rec.field.path)

    return dict(graph)


def validate_invariants() -> list[LineageViolation]:
    """校验数据链不变量，返回违规列表

    校验规则：
    - TS01 [ERROR] writer 唯一性：每个 L2 真相源字段只能有一个 writer
    - TS02 [ERROR] 禁止 L4 作为下游真相源：L4 字段不可被 @reads 引用
    - TS03 [ERROR] 层级回写禁止：writer 的 tier 低于同字段 reader 的 tier
    - TS04 [WARNING] 跳层警告：L1→L4 派生缺少 L2 中间环节
    - TS05 [ERROR] 字段后缀与声明 tier 不一致
    """
    violations: list[LineageViolation] = []

    # TS01: writer 唯一性（仅校验 L2 真相源，L4 派生允许多 writer）
    # 同一类内多方法写同字段合法（如 InventoryEngine.inbound/outbound/reverse 都写 StockMove），
    # 只有不同类写同字段才视为双算法违规
    field_writers: dict[str, list[WriteRecord]] = defaultdict(list)
    for w in REGISTRY.writes:
        if w.tier == TIER_L2 and not w.is_derived:
            field_writers[w.field.path].append(w)

    for path, writers in field_writers.items():
        # 提取类/模块唯一标识（ClassName.method 用 ClassName，module.func 用 module）
        owners = set()
        for w in writers:
            qualname = w.func_qualname
            if "." in qualname:
                owners.add(qualname.rsplit(".", 1)[0])
            else:
                owners.add(w.func_module)
        if len(owners) > 1:
            violations.append(LineageViolation(
                code="TS01", severity="ERROR",
                rule="writer_uniqueness",
                message=f"L2 真相源 {path} 有多个不同类的 writer（双算法风险）: "
                        + ", ".join(sorted(owners)),
                field=path,
                writers=[w.func_qualname for w in writers],
            ))

    # TS02: L4 不可作为下游真相源
    l4_fields = {w.field.path for w in REGISTRY.writes if w.tier == TIER_L4}
    for r in REGISTRY.reads:
        if r.field.path in l4_fields or r.tier == TIER_L4:
            violations.append(LineageViolation(
                code="TS02", severity="ERROR",
                rule="no_l4_as_truth_source",
                message=f"L4 派生字段 {r.field.path} 被 {r.func_qualname} 读取，"
                        f"L4 不可作为下游真相源",
                field=r.field.path,
                readers=[r.func_qualname],
            ))

    # TS03: 层级回写禁止（writer tier < reader tier）
    # 对每个被读字段，检查是否有更低层级 writer（回写）
    field_write_tier: dict[str, str] = {}
    for w in REGISTRY.writes:
        # 同字段取最高 tier（多个 writer 时 TS01 已报）
        if w.field.path not in field_write_tier or \
           TIER_ORDER.get(w.tier, 0) > TIER_ORDER.get(field_write_tier[w.field.path], 0):
            field_write_tier[w.field.path] = w.tier

    for r in REGISTRY.reads:
        wt = field_write_tier.get(r.field.path)
        if wt and TIER_ORDER.get(wt, 0) < TIER_ORDER.get(r.tier, 0):
            violations.append(LineageViolation(
                code="TS03", severity="ERROR",
                rule="no_reverse_write",
                message=f"{r.field.path} 被 {r.func_qualname} 以 {r.tier} 读取，"
                        f"但 writer 以 {wt} 写入（层级回写）",
                field=r.field.path,
            ))

    # TS04: 跳层警告（L1→L4 缺少 L2）
    derives_records = [w for w in REGISTRY.writes if w.is_derived]
    for d in derives_records:
        # 找该派生函数读取的源字段
        src_reads = [r for r in REGISTRY.reads if r.func_qualname == d.func_qualname]
        has_l1 = any(r.tier == TIER_L1 for r in src_reads)
        has_l2 = any(r.tier == TIER_L2 for r in src_reads)
        if has_l1 and not has_l2 and d.tier == TIER_L4:
            violations.append(LineageViolation(
                code="TS04", severity="WARNING",
                rule="no_skip_tier",
                message=f"{d.func_qualname} 直接从 L1 派生 L4 ({d.field.path})，"
                        f"缺少 L2 计算环节",
                field=d.field.path,
            ))

    # TS05: 字段后缀与声明 tier 不一致
    for w in REGISTRY.writes:
        suffix_tier = w.field.tier_from_suffix
        if suffix_tier and suffix_tier != w.tier:
            violations.append(LineageViolation(
                code="TS05", severity="ERROR",
                rule="tier_suffix_mismatch",
                message=f"{w.field.path} 后缀指示 {suffix_tier}，"
                        f"但 @writes/@derives 声明 {w.tier}",
                field=w.field.path,
                writers=[w.func_qualname],
            ))
    for r in REGISTRY.reads:
        suffix_tier = r.field.tier_from_suffix
        if suffix_tier and suffix_tier != r.tier:
            violations.append(LineageViolation(
                code="TS05", severity="ERROR",
                rule="tier_suffix_mismatch",
                message=f"{r.field.path} 后缀指示 {suffix_tier}，"
                        f"但 @reads 声明 {r.tier}",
                field=r.field.path,
                readers=[r.func_qualname],
            ))

    return violations


def get_writers_for(field_path: str) -> list[WriteRecord]:
    return REGISTRY.writers_for(field_path)


def get_readers_for(field_path: str) -> list[ReadRecord]:
    return REGISTRY.readers_for(field_path)
