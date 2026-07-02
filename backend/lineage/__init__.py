"""数据血缘装饰器框架

基于"数字源原则"（L1外部输入 / L2引擎计算 / L3政策配置 / L4派生汇总），
通过装饰器声明每个函数读/写哪些字段、属于哪个层级，自动构建数据链图。

核心组件：
- TIER_L1~L4: 层级常量
- FieldRef: 字段引用（Model.field → 字符串路径）
- Registry: 全局 writer/reader 注册表
- @writes / @reads / @derives: 函数装饰器
- build_lineage_graph(): 从注册表构建数据链图
- validate_invariants(): 校验层级单调、writer 唯一、禁止回写/分叉/跳层

用法：
    from lineage import writes, reads, TIER_L2

    @writes("StockMove.quantity_l1", tier=TIER_L1, source="external")
    @writes("StockMove.unit_cost_l2", tier=TIER_L2, source="engine")
    def inbound(self, ...): ...

    @reads("StockMove.unit_cost_l2", tier=TIER_L2, source="engine")
    def calc_cogs(...): ...
"""
from .registry import (
    TIER_L1, TIER_L2, TIER_L3, TIER_L4,
    TIER_ORDER, FieldRef, WriteRecord, ReadRecord,
    writes, reads, derives,
    REGISTRY, build_lineage_graph, validate_invariants,
    get_writers_for, get_readers_for, LineageViolation,
)

__all__ = [
    "TIER_L1", "TIER_L2", "TIER_L3", "TIER_L4", "TIER_ORDER",
    "FieldRef", "WriteRecord", "ReadRecord",
    "writes", "reads", "derives",
    "REGISTRY", "build_lineage_graph", "validate_invariants",
    "get_writers_for", "get_readers_for", "LineageViolation",
]
