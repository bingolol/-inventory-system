"""财务引擎集成层 — 带防御性检查的 JournalEngine 封装

所有业务入口通过此模块调用会计引擎，而不是直接调用 JournalEngine。
"""
from decimal import Decimal
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from crud.base import get_account
from models_finance import (
    Ledger, AccountMove, AccountMoveLine, AccountingError,
)
from engine_journal import JournalEngine
from errors import BusinessError, ErrorCode
from utils import Q2


EXPENSE_ACCOUNT_CODE_MAP = {
    "销售费用": "5601",
    "管理费用": "5602",
    "财务费用": "5603",
}


def get_ledger_id(db: Session, account_id: int) -> int:
    """通过 account.code → ledger.code 的 1:1 映射获取 ledger_id"""
    account = get_account(db, account_id)
    if not account:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"账本不存在: account_id={account_id}",
        )
    ledger = db.query(Ledger).filter(Ledger.code == account.code).first()
    if not ledger:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"会计科目表未初始化: account_id={account_id}, code={account.code}",
        )
    return ledger.id


def _calc_tax_from_items(total_with_tax: Decimal, items: list) -> dict:
    """从 items 逐行计算税额，Decimal + quantize 精度保护

    items 每个元素需包含: total_price (含税小计), tax_rate
    返回: {"tax_amount": Decimal, "total_without_tax": Decimal}
    """
    tax_amount = Decimal("0")
    for item in items:
        tp = Decimal(str(item["total_price"]))
        rate = Decimal(str(item["tax_rate"]))
        line_tax = (tp * rate / (Decimal("1") + rate)).quantize(Q2)
        tax_amount += line_tax
    tax_amount = tax_amount.quantize(Q2)
    total_without_tax = (Decimal(str(total_with_tax)) - tax_amount).quantize(Q2)
    return {"tax_amount": tax_amount, "total_without_tax": total_without_tax}


def post_journal(
    db: Session,
    account_id: int,
    move_type: str,
    source: dict,
) -> AccountMove:
    """过账（带重复过账防御）

    若相同 source_model + source_id 且非冲红的凭证已存在，直接返回旧凭证。
    会计错误转为 BusinessError 保证事务回滚。
    """
    sm = source.get("source_model")
    si = source.get("source_id")
    if sm and si is not None:
        existing = db.query(AccountMove).filter(
            AccountMove.source_model == sm,
            AccountMove.source_id == si,
            AccountMove.is_reversal == False,
        ).first()
        if existing:
            return existing

    ledger_id = get_ledger_id(db, account_id)
    try:
        engine = JournalEngine(db)
        return engine.post(ledger_id, move_type, source)
    except AccountingError as e:
        raise BusinessError(
            code=ErrorCode.VALIDATION_ERROR,
            message=e.message,
            data={"accounting_code": e.code},
        )


def reverse_journal(
    db: Session,
    account_id: int,
    source_model: str,
    source_id: int,
    reversal_date: Optional[date] = None,
) -> Optional[AccountMove]:
    """冲红原凭证（带幂等防御）

    查找相同 source_model + source_id 的原凭证，借贷互换生成冲红凭证。
    已冲红过 → 返回 None；无原凭证 → 返回 None。
    """
    existing_reversal = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == True,
    ).first()
    if existing_reversal:
        return None

    original = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == False,
    ).first()
    if not original:
        return None

    engine = JournalEngine(db)

    reversal = AccountMove(
        ledger_id=original.ledger_id,
        name=f"冲红-{original.name}",
        move_type=original.move_type,
        date=reversal_date or date.today(),
        state="posted",
        source_model=source_model,
        source_id=source_id,
        amount_total=original.amount_total,
        reversed_entry_id=original.id,
        is_reversal=True,
    )
    db.add(reversal)
    db.flush()

    for ol in original.line_ids:
        rl = AccountMoveLine(
            move_id=reversal.id,
            ledger_account_id=ol.ledger_account_id,
            debit=ol.credit,
            credit=ol.debit,
            partner_id=ol.partner_id,
            partner_type=ol.partner_type,
            amount_residual=ol.credit or ol.debit,
        )
        db.add(rl)
        db.flush()
        engine.ledger_engine.update_balance(rl)

    return reversal
