"""个人流水 Command + Handler — 3个命令覆盖个人流水全部写操作

从 crud/personal.py 提取，Command 模式封装。
每个 Handler 包含：数据校验 → ORM 操作 → 日志记录（可选）。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import models

from .base import Command, CommandHandler, register


# ═══════════════════════════════════════════════════════════
# 1. CreatePersonalTransaction — 创建个人流水
# ═══════════════════════════════════════════════════════════

@dataclass
class CreatePersonalTransaction(Command):
    type: str = ""                # "income" or "expense"
    amount: float = 0.0
    category: str = ""
    description: str = ""
    image_url: str = ""
    date: str = ""                # YYYY-MM-DD


@register(CreatePersonalTransaction)
class CreatePersonalTransactionHandler(CommandHandler):
    def handle(self, cmd: CreatePersonalTransaction, db: Any) -> Any:
        # 日期解析
        tx_date = datetime.strptime(cmd.date, "%Y-%m-%d") if cmd.date else datetime.now()

        tx = models.PersonalTransaction(
            account_id=cmd.account_id,
            type=cmd.type,
            amount_l1=cmd.amount,
            category=cmd.category,
            description=cmd.description,
            image_url=cmd.image_url,
            date_l1=tx_date,
        )
        db.add(tx)
        db.flush()
        return tx


# ═══════════════════════════════════════════════════════════
# 2. UpdatePersonalTransaction — 更新个人流水
# ═══════════════════════════════════════════════════════════

@dataclass
class UpdatePersonalTransaction(Command):
    tx_id: int = 0
    type: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    date: Optional[str] = None      # YYYY-MM-DD


@register(UpdatePersonalTransaction)
class UpdatePersonalTransactionHandler(CommandHandler):
    def handle(self, cmd: UpdatePersonalTransaction, db: Any) -> Any:
        # 1. 查询流水
        tx = db.query(models.PersonalTransaction).filter(
            models.PersonalTransaction.account_id == cmd.account_id,
            models.PersonalTransaction.id == cmd.tx_id,
        ).first()
        if not tx:
            return None

        # 2. 部分更新
        updates = {
            'type': cmd.type,
            'amount_l1': cmd.amount,
            'category': cmd.category,
            'description': cmd.description,
            'image_url': cmd.image_url,
        }
        for k, v in updates.items():
            if v is not None:
                setattr(tx, k, v)

        # 日期字段特殊处理（字符串 → datetime）
        if cmd.date is not None:
            tx.date_l1 = datetime.strptime(cmd.date, "%Y-%m-%d")

        db.flush()
        return tx


# ═══════════════════════════════════════════════════════════
# 3. DeletePersonalTransaction — 删除个人流水
# ═══════════════════════════════════════════════════════════

@dataclass
class DeletePersonalTransaction(Command):
    tx_id: int = 0


@register(DeletePersonalTransaction)
class DeletePersonalTransactionHandler(CommandHandler):
    def handle(self, cmd: DeletePersonalTransaction, db: Any) -> bool:
        # 1. 查询流水
        tx = db.query(models.PersonalTransaction).filter(
            models.PersonalTransaction.account_id == cmd.account_id,
            models.PersonalTransaction.id == cmd.tx_id,
        ).first()
        if not tx:
            return False

        # 2. 删除
        db.delete(tx)
        db.flush()
        return True
