"""领域模型基类 — 封装业务规则和不变量，与ORM模型解耦。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

TModel = TypeVar('TModel')


class DomainModel(ABC, Generic[TModel]):
    """领域模型基类 — 封装业务规则和不变量，与ORM模型解耦。

    子类必须实现：
    - from_orm(orm_obj): 从ORM对象构建Domain对象
    - validate(): 不变量校验，返回违规列表（空=通过）

    泛型参数 TModel 绑定对应的ORM模型类，用于类型提示。
    """

    @classmethod
    @abstractmethod
    def from_orm(cls, orm_obj: TModel) -> DomainModel[TModel]:
        """ORM对象 → Domain对象"""
        ...

    @abstractmethod
    def validate(self) -> list[str]:
        """不变量校验，返回违规列表（空列表=通过）"""
        ...