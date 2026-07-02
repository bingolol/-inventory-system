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
        # 1. 查询旧流水
        old_tx = db.query(models.PersonalTransaction).filter(
            models.PersonalTransaction.account_id == cmd.account_id,
            models.PersonalTransaction.id == cmd.tx_id,
            models.PersonalTransaction.is_reversed == False,
        ).first()
        if not old_tx:
            return None

        # 2. 组装新值（旧值兜底）
        tx_date = datetime.strptime(cmd.date, "%Y-%m-%d") if cmd.date is not None else old_tx.date_l1
        new_type = cmd.type if cmd.type is not None else old_tx.type
        new_amount = cmd.amount if cmd.amount is not None else old_tx.amount_l1
        new_category = cmd.category if cmd.category is not None else old_tx.category
        new_description = cmd.description if cmd.description is not None else old_tx.description
        new_image_url = cmd.image_url if cmd.image_url is not None else old_tx.image_url

        # 3. 标记旧流水作废
        old_tx.is_reversed = True

        # 4. 创建新流水
        new_tx = models.PersonalTransaction(
            account_id=cmd.account_id,
            type=new_type,
            amount_l1=new_amount,
            category=new_category,
            description=new_description,
            image_url=new_image_url,
            date_l1=tx_date,
        )
        db.add(new_tx)
        db.flush()
        return new_tx


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
            models.PersonalTransaction.is_reversed == False,
        ).first()
        if not tx:
            return False

        # 2. 标记作废，保留审计轨迹
        tx.is_reversed = True
        db.flush()
        return True
