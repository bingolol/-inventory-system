"""Schema/Model 映射层

集中管理 Pydantic Schema 与 ORM/生命周期参数之间的字段映射，
消除 schemas 中重复的 to_orm_kwargs / to_lifecycle_kwargs 方法。
"""

from typing import Any, Callable, Dict, List, Optional


class FieldMap:
    """单个字段映射定义。"""

    def __init__(
        self,
        source: str,
        target: Optional[str] = None,
        transform: Optional[Callable[[Any], Any]] = None,
        nested: Optional["SchemaMapper"] = None,
    ):
        self.source = source
        self.target = target or source
        self.transform = transform
        self.nested = nested

    def apply(self, data: Dict[str, Any]) -> Any:
        value = data.get(self.source)
        if value is None:
            return None
        if self.nested:
            if isinstance(value, list):
                value = [self.nested.map(v) for v in value]
            else:
                value = self.nested.map(value)
        if self.transform:
            value = self.transform(value)
        return value


class SchemaMapper:
    """Schema → ORM kwargs / lifecycle kwargs 映射器。

    用法::

        item_mapper = SchemaMapper([
            FieldMap("quantity", "quantity_l1"),
            FieldMap("unit_price", "unit_price_l1"),
            FieldMap("tax_rate", "tax_rate_l1"),
        ])
        item_mapper.map({"quantity": 10, "unit_price": 100})
        # {"quantity_l1": 10, "unit_price_l1": 100}
    """

    def __init__(self, fields: List[FieldMap]):
        self.fields = fields

    def map(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for field in self.fields:
            value = field.apply(data)
            if value is not None or field.source in data:
                result[field.target] = value
        return result

    def map_many(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.map(it) for it in items]


def _items_to_orm(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """通用商品明细 → ORM kwargs 转换。"""
    mapper = SchemaMapper([
        FieldMap("product_id"),
        FieldMap("quantity", "quantity_l1"),
        FieldMap("unit_price", "unit_price_l1"),
        FieldMap("tax_rate", "tax_rate_l1"),
    ])
    return mapper.map_many(items)
