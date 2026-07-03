"""个人垫付 Command + Handler

原 routers/personal_advances.py 中的 4 个写端点下沉到本模块，
router 只负责 HTTP 解析 + dispatch。
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import models
from commands.base import Command, CommandHandler, register
from crud.base import log_op
from engine_bank import BankEngine
from enums import PersonalAdvanceStatus
from errors import BusinessError, ErrorCode
from finance_integration import post_journal, reverse_journal
from lineage import writes, TIER_L1, TIER_L4
from operation_result import EntityType, OperationResult, OperationType
from schemas import (
    PersonalAdvanceCreate,
    PersonalAdvanceRepaymentCreate,
)
from utils import _d, Q2


def _compute_status(amount: Decimal, paid: Decimal) -> str:
    """根据 amount 和 paid_amount 计算还款状态"""
    amount = _d(amount)
    paid = _d(paid)
    if paid <= 0:
        return PersonalAdvanceStatus.UNPAID
    if paid >= amount:
        return PersonalAdvanceStatus.PAID
    return PersonalAdvanceStatus.PARTIAL


# ═══════════════════════════════════════════════════════════
# 1. CreatePersonalAdvance — 创建垫付单
# ═══════════════════════════════════════════════════════════

@dataclass
class CreatePersonalAdvance(Command):
    data: Optional[PersonalAdvanceCreate] = None


@register(CreatePersonalAdvance)
class CreatePersonalAdvanceHandler(CommandHandler):
    @writes("PersonalAdvance.amount_l1", tier=TIER_L1, source="external")
    @writes("PersonalAdvance.advance_date_l1", tier=TIER_L1, source="external")
    @writes("PersonalAdvance.paid_amount_l4", tier=TIER_L4, source="engine")
    def handle(self, cmd: CreatePersonalAdvance, db: Any) -> Any:
        from crud.personal_advances import generate_advance_no

        account_id = cmd.account_id
        data = cmd.data
        advance_no = generate_advance_no(db, account_id)

        advance = models.PersonalAdvance(
            account_id=account_id,
            advance_no=advance_no,
            advancer_name=data.advancer_name.strip(),
            amount_l1=_d(data.amount).quantize(Q2),
            advance_date_l1=datetime.combine(data.advance_date, datetime.min.time()),
            debit_account_code=data.debit_account_code,
            description=data.description,
            image_url=data.image_url or "",
            repayment_status=PersonalAdvanceStatus.UNPAID,
            paid_amount_l4=Decimal("0"),
            is_reversed=False,
        )
        db.add(advance)
        db.flush()

        post_journal(db, account_id, "personal_advance", {
            "amount": advance.amount_l1,
            "debit_account_code": advance.debit_account_code,
            "date": data.advance_date.isoformat(),
            "partner_id": None,
            "partner_type": "advancer",
            "source_model": "personal_advance",
            "source_id": advance.id,
        })

        log_op(db, account_id, "create", "personal_advance", advance.id,
               f"创建个人垫付:{advance.advance_no} {advance.advancer_name} {advance.amount_l1}",
               operator=cmd.operator)

        from schemas import PersonalAdvanceOut
        db.refresh(advance)
        out = PersonalAdvanceOut.model_validate(advance).model_dump()

        return OperationResult(
            operation=OperationType.CREATE,
            entity_type=EntityType.PERSONAL_ADVANCE,
            entity_id=advance.id,
            summary=f"个人垫付单 {advance.advance_no} 创建成功，{advance.advancer_name} 垫付 {advance.amount_l1}",
            ai_hint=f"已形成 {advance.amount_l1} 其他应付款负债。偿还时调用 POST /api/personal-advances/{advance.id}/repay。",
            data=out,
            changes={
                "other_payable": {"amount": f"+{advance.amount_l1}"},
                "advance_id": advance.id,
                "advance_no": advance.advance_no,
            },
        ).to_dict()


# ═══════════════════════════════════════════════════════════
# 2. RepayPersonalAdvance — 偿还垫付单
# ═══════════════════════════════════════════════════════════

@dataclass
class RepayPersonalAdvance(Command):
    advance_id: int = 0
    data: Optional[PersonalAdvanceRepaymentCreate] = None


@register(RepayPersonalAdvance)
class RepayPersonalAdvanceHandler(CommandHandler):
    @writes("PersonalAdvanceRepayment.amount_l1", tier=TIER_L1, source="external")
    @writes("PersonalAdvanceRepayment.repayment_date_l1", tier=TIER_L1, source="external")
    @writes("PersonalAdvance.paid_amount_l4", tier=TIER_L4, source="engine")
    def handle(self, cmd: RepayPersonalAdvance, db: Any) -> Any:
        from schemas import PersonalAdvanceOut, PersonalAdvanceRepaymentOut

        account_id = cmd.account_id
        advance_id = cmd.advance_id
        data = cmd.data

        advance = db.query(models.PersonalAdvance).filter(
            models.PersonalAdvance.id == advance_id,
            models.PersonalAdvance.account_id == account_id,
        ).with_for_update().first()
        if not advance:
            raise BusinessError(
                code=ErrorCode.ORDER_NOT_FOUND,
                data={"order_type": "个人垫付单", "order_id": advance_id},
            )
        if advance.is_reversed:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"垫付单 #{advance_id} 已冲红，不可偿还",
                ai_instruction="STOP_RETRYING. 该垫付单已冲红。",
            )

        repay_amount = _d(data.amount).quantize(Q2)
        remaining = _d(advance.amount_l1) - _d(advance.paid_amount_l4)
        if repay_amount > remaining:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(
                    f"偿还金额 {repay_amount} 超过未还余额 {remaining}。"
                    f"垫付单 {advance.advance_no} 总额 {advance.amount_l1}，已还 {advance.paid_amount_l4}。"
                ),
                ai_instruction=(
                    f"STOP_RETRYING. 垫付单 #{advance_id} 最大可偿还金额为 {remaining}，"
                    f"请减少偿还金额。"
                ),
            )
        if repay_amount <= 0:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message="偿还金额必须大于 0",
            )

        bank_account_id = data.bank_account_id

        # 先创建 repayment 拿到 id，再创建 bank_transaction，避免后续 UPDATE BankTransaction
        # （BankTransaction 是真相源表，禁止 UPDATE）
        repayment = models.PersonalAdvanceRepayment(
            account_id=account_id,
            advance_id=advance_id,
            amount_l1=repay_amount,
            repayment_date_l1=datetime.combine(data.repayment_date, datetime.min.time()),
            bank_account_id=bank_account_id,
            bank_transaction_id=None,
            description=data.description,
            is_reversed=False,
        )
        db.add(repayment)
        db.flush()

        if bank_account_id is not None:
            bank_tx = BankEngine(db, account_id).record_transaction(
                bank_account_id=bank_account_id,
                transaction_type="outflow",
                amount=repay_amount,
                transaction_date=datetime.combine(data.repayment_date, datetime.min.time()),
                description=f"偿还个人垫付: {advance.advancer_name} {advance.advance_no} {data.description}".strip(),
                flow_category="operating",
                related_entity_type="personal_advance_repayment",
                related_entity_id=repayment.id,
            )
            repayment.bank_transaction_id = bank_tx.id

        post_journal(db, account_id, "personal_advance_repay", {
            "amount": repay_amount,
            "date": data.repayment_date.isoformat(),
            "bank_account_id": bank_account_id,
            "partner_id": None,
            "partner_type": "advancer",
            "source_model": "personal_advance_repay",
            "source_id": repayment.id,
        })

        advance.paid_amount_l4 = (_d(advance.paid_amount_l4) + repay_amount).quantize(Q2)
        advance.repayment_status = _compute_status(advance.amount_l1, advance.paid_amount_l4)

        log_op(db, account_id, "create", "personal_advance_repayment", repayment.id,
               f"偿还个人垫付 {advance.advance_no}: {repay_amount}", operator=cmd.operator)

        db.refresh(repayment)
        db.refresh(advance)
        out = PersonalAdvanceRepaymentOut.model_validate(repayment).model_dump()
        advance_out = PersonalAdvanceOut.model_validate(advance).model_dump()

        return OperationResult(
            operation=OperationType.CREATE,
            entity_type=EntityType.PERSONAL_ADVANCE_REPAYMENT,
            entity_id=repayment.id,
            summary=(
                f"偿还个人垫付 {advance.advance_no} 成功，金额 {repay_amount}，"
                f"状态: {advance.repayment_status}"
            ),
            ai_hint=(
                f"其他应付款已减少 {repay_amount}，未还余额 "
                f"{advance_out['remaining_amount']}。"
                + ("已还清。" if advance.repayment_status == PersonalAdvanceStatus.PAID else "")
            ),
            data={"repayment": out, "advance": advance_out},
            changes={
                "other_payable": {"amount": f"-{repay_amount}"},
                "advance_id": advance_id,
                "repayment_status": advance.repayment_status,
                "remaining_amount": advance_out["remaining_amount"],
            },
        ).to_dict()


# ═══════════════════════════════════════════════════════════
# 3. ReversePersonalAdvance — 红冲垫付单
# ═══════════════════════════════════════════════════════════

@dataclass
class ReversePersonalAdvance(Command):
    advance_id: int = 0


@register(ReversePersonalAdvance)
class ReversePersonalAdvanceHandler(CommandHandler):
    @writes("PersonalAdvance.is_reversed", tier=TIER_L1, source="external")
    def handle(self, cmd: ReversePersonalAdvance, db: Any) -> Any:
        from schemas import PersonalAdvanceOut

        account_id = cmd.account_id
        advance_id = cmd.advance_id

        advance = db.query(models.PersonalAdvance).filter(
            models.PersonalAdvance.id == advance_id,
            models.PersonalAdvance.account_id == account_id,
        ).with_for_update().first()
        if not advance:
            raise BusinessError(
                code=ErrorCode.ORDER_NOT_FOUND,
                data={"order_type": "个人垫付单", "order_id": advance_id},
            )
        if advance.is_reversed:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"垫付单 #{advance_id} 已冲红，不可重复操作",
                ai_instruction="STOP_RETRYING. 该垫付单已冲红。",
            )

        active_repayments = db.query(models.PersonalAdvanceRepayment).filter(
            models.PersonalAdvanceRepayment.advance_id == advance_id,
            models.PersonalAdvanceRepayment.is_reversed == False,
        ).count()
        if active_repayments > 0:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(
                    f"垫付单 #{advance_id} 存在 {active_repayments} 笔未冲红的偿还记录，"
                    f"请先红冲所有偿还记录后再红冲垫付单。"
                ),
                ai_instruction=(
                    f"STOP_RETRYING. 先调用 "
                    f"POST /api/personal-advances/{advance_id}/repayments/{{rid}}/reverse "
                    f"红冲所有偿还记录，再红冲垫付单。"
                ),
            )

        reverse_journal(db, account_id, "personal_advance", advance_id)

        advance.is_reversed = True
        advance.reversed_at = datetime.now()

        log_op(db, account_id, "reverse", "personal_advance", advance_id,
               f"红冲个人垫付 {advance.advance_no}", operator=cmd.operator)

        db.refresh(advance)
        out = PersonalAdvanceOut.model_validate(advance).model_dump()

        return OperationResult(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PERSONAL_ADVANCE,
            entity_id=advance_id,
            summary=f"个人垫付单 {advance.advance_no} 已红冲",
            ai_hint="垫付凭证已冲红，原记录保留（审计可追溯）。",
            data=out,
            changes={
                "other_payable": {"amount": f"-{advance.amount_l1}"},
                "is_reversed": True,
            },
        ).to_dict()


# ═══════════════════════════════════════════════════════════
# 4. ReversePersonalAdvanceRepayment — 红冲单笔偿还
# ═══════════════════════════════════════════════════════════

@dataclass
class ReversePersonalAdvanceRepayment(Command):
    advance_id: int = 0
    repayment_id: int = 0


@register(ReversePersonalAdvanceRepayment)
class ReversePersonalAdvanceRepaymentHandler(CommandHandler):
    @writes("PersonalAdvanceRepayment.is_reversed", tier=TIER_L1, source="external")
    @writes("PersonalAdvance.paid_amount_l4", tier=TIER_L4, source="engine")
    def handle(self, cmd: ReversePersonalAdvanceRepayment, db: Any) -> Any:
        from schemas import PersonalAdvanceOut

        account_id = cmd.account_id
        advance_id = cmd.advance_id
        repayment_id = cmd.repayment_id

        repayment = db.query(models.PersonalAdvanceRepayment).filter(
            models.PersonalAdvanceRepayment.id == repayment_id,
            models.PersonalAdvanceRepayment.account_id == account_id,
            models.PersonalAdvanceRepayment.advance_id == advance_id,
        ).with_for_update().first()
        if not repayment:
            raise BusinessError(
                code=ErrorCode.ORDER_NOT_FOUND,
                data={"order_type": "个人垫付偿还记录", "order_id": repayment_id},
            )
        if repayment.is_reversed:
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"偿还记录 #{repayment_id} 已冲红，不可重复操作",
                ai_instruction="STOP_RETRYING. 该偿还记录已冲红。",
            )

        advance = db.query(models.PersonalAdvance).filter(
            models.PersonalAdvance.id == advance_id,
            models.PersonalAdvance.account_id == account_id,
        ).with_for_update().first()
        if not advance:
            raise BusinessError(
                code=ErrorCode.ORDER_NOT_FOUND,
                data={"order_type": "个人垫付单", "order_id": advance_id},
            )

        repay_amount = _d(repayment.amount_l1)

        if repayment.bank_transaction_id is not None:
            from crud.reversal import reverse_bank_transaction
            reverse_bank_transaction(db, account_id, repayment.bank_transaction_id)

        reverse_journal(db, account_id, "personal_advance_repay", repayment_id)

        repayment.is_reversed = True
        repayment.reversed_at = datetime.now()

        new_paid = _d(advance.paid_amount_l4) - repay_amount
        if new_paid < 0:
            new_paid = Decimal("0")
        advance.paid_amount_l4 = new_paid.quantize(Q2)
        advance.repayment_status = _compute_status(advance.amount_l1, advance.paid_amount_l4)

        log_op(db, account_id, "reverse", "personal_advance_repayment", repayment_id,
               f"红冲偿还记录 #{repayment_id}: {repay_amount}", operator=cmd.operator)

        db.refresh(advance)
        db.refresh(repayment)
        advance_out = PersonalAdvanceOut.model_validate(advance).model_dump()

        return OperationResult(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PERSONAL_ADVANCE_REPAYMENT,
            entity_id=repayment_id,
            summary=f"偿还记录 #{repayment_id} 已红冲",
            ai_hint=(
                f"已冲回其他应付款 {repay_amount}，垫付单 {advance.advance_no} 状态: "
                f"{advance.repayment_status}，未还余额 {advance_out['remaining_amount']}。"
            ),
            data={"repayment_id": repayment_id, "is_reversed": True, "advance": advance_out},
            changes={
                "other_payable": {"amount": f"+{repay_amount}"},
                "advance_id": advance_id,
                "repayment_status": advance.repayment_status,
                "remaining_amount": advance_out["remaining_amount"],
            },
        ).to_dict()
