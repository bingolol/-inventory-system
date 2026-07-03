"""其他应付款/个人垫付路由

业务编排模式与 expenses/payments 一致：在 unit_of_work 内完成
"实体写 + 总账过账 + 银行流水 + 状态更新" 四件事的原子提交。
不使用 Command 层，因为偿还流程的多步原子性与现有 finance 路由风格一致。

端点：
- GET    /api/personal-advances                       列表（分页+过滤）
- GET    /api/personal-advances/totals                汇总卡片
- GET    /api/personal-advances/summary               按垫付人聚合
- GET    /api/personal-advances/{id}                  单笔详情
- POST   /api/personal-advances                       创建垫付
- POST   /api/personal-advances/{id}/repay            偿还（支持部分偿还）
- POST   /api/personal-advances/{id}/reverse          红冲垫付单
- GET    /api/personal-advances/{id}/repayments       偿还明细列表
- POST   /api/personal-advances/{id}/repayments/{rid}/reverse  红冲单笔偿还
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from decimal import Decimal

from database import get_db
from models import PersonalAdvance, PersonalAdvanceRepayment, BankAccount, BankTransaction
from schemas import (
    PersonalAdvanceCreate, PersonalAdvanceOut,
    PersonalAdvanceRepaymentCreate, PersonalAdvanceRepaymentOut,
    PersonalAdvanceSummary, PaginatedResponse,
)
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
from crud.base import _log
import crud
from utils import _d, Q2
from operation_result import OperationResult, EntityType, OperationType
from finance_integration import post_journal, reverse_journal
from enums import PersonalAdvanceStatus
from lineage import writes, TIER_L1, TIER_L4

router = APIRouter()


# ── 内部辅助：状态计算 ──

def _compute_status(amount: Decimal, paid: Decimal) -> str:
    """根据 amount 和 paid_amount 计算还款状态"""
    amount = _d(amount)
    paid = _d(paid)
    if paid <= 0:
        return PersonalAdvanceStatus.UNPAID
    if paid >= amount:
        return PersonalAdvanceStatus.PAID
    return PersonalAdvanceStatus.PARTIAL


# ── 列表与查询 ──

@router.get("", response_model=PaginatedResponse)
def list_personal_advances(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    advancer_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """列表（分页+过滤）"""
    total, items = crud.list_personal_advances(
        db, account_id, skip=skip, limit=limit,
        advancer_name=advancer_name, status=status,
        start_date=start_date, end_date=end_date,
    )
    return PaginatedResponse(
        total=total,
        items=[PersonalAdvanceOut.model_validate(it).model_dump() for it in items],
    )


@router.get("/totals")
def get_totals(
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """汇总卡片：总垫付、已还、未还"""
    return crud.get_personal_advance_totals(db, account_id)


@router.get("/summary", response_model=list[PersonalAdvanceSummary])
def get_summary(
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """按垫付人聚合"""
    return crud.get_personal_advance_summary(db, account_id)


@router.get("/{advance_id}", response_model=PersonalAdvanceOut)
def get_personal_advance(
    advance_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """单笔详情"""
    advance = crud.get_personal_advance(db, account_id, advance_id)
    if not advance:
        raise BusinessError(
            code=ErrorCode.ORDER_NOT_FOUND,
            data={"order_type": "个人垫付单", "order_id": advance_id},
        )
    return PersonalAdvanceOut.model_validate(advance)


@router.get("/{advance_id}/repayments", response_model=list[PersonalAdvanceRepaymentOut])
def list_repayments(
    advance_id: int,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """偿还明细列表"""
    advance = crud.get_personal_advance(db, account_id, advance_id)
    if not advance:
        raise BusinessError(
            code=ErrorCode.ORDER_NOT_FOUND,
            data={"order_type": "个人垫付单", "order_id": advance_id},
        )
    items = crud.list_repayments_by_advance(db, account_id, advance_id)
    return [PersonalAdvanceRepaymentOut.model_validate(it) for it in items]


# ── 创建垫付 ──

@writes("PersonalAdvance.amount_l1", tier=TIER_L1, source="external")
@writes("PersonalAdvance.advance_date_l1", tier=TIER_L1, source="external")
@writes("PersonalAdvance.paid_amount_l4", tier=TIER_L4, source="engine")
@router.post("")
def create_personal_advance(
    data: PersonalAdvanceCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
):
    """创建垫付单：dr debit_account_code(默认6601) cr 2241 其他应付款"""
    with unit_of_work(db):
        advance_no = crud.generate_advance_no(db, account_id)
        advance = PersonalAdvance(
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

        # 总账凭证：dr 借方科目 / cr 2241 其他应付款
        # source_model + source_id 提供幂等防御（重复提交不会重复过账）
        post_journal(db, account_id, "personal_advance", {
            "amount": advance.amount_l1,
            "debit_account_code": advance.debit_account_code,
            "date": data.advance_date.isoformat(),
            "partner_id": None,        # 个人垫付无独立 partner 表，留空
            "partner_type": "advancer",
            "source_model": "personal_advance",
            "source_id": advance.id,
        })

        log_op(db, account_id, "create", "personal_advance", advance.id,
             f"创建个人垫付:{advance.advance_no} {advance.advancer_name} {advance.amount_l1}",
             operator=operator)

    db.refresh(advance)
    out = PersonalAdvanceOut.model_validate(advance).model_dump()

    result = OperationResult(
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
    )
    return result.to_dict()


# ── 偿还垫付 ──

@writes("PersonalAdvanceRepayment.amount_l1", tier=TIER_L1, source="external")
@writes("PersonalAdvanceRepayment.repayment_date_l1", tier=TIER_L1, source="external")
@writes("PersonalAdvance.paid_amount_l4", tier=TIER_L4, source="engine")
@router.post("/{advance_id}/repay")
def repay_personal_advance(
    advance_id: int,
    data: PersonalAdvanceRepaymentCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
):
    """偿还垫付单（支持部分偿还）

    流程：
    1. 锁垫付单 → 校验未冲红 + 未超额
    2. 锁银行账户（如有） → 校验余额 + 创建 BankTransaction + 扣减余额
    3. 写 PersonalAdvanceRepayment
    4. post_journal: dr 2241 / cr 1002(银行) 或 1001(现金)
    5. 累加 advance.paid_amount_l4 + 重算 repayment_status
    """
    with unit_of_work(db):
        # 1. 锁垫付单
        advance = db.query(PersonalAdvance).filter(
            PersonalAdvance.id == advance_id,
            PersonalAdvance.account_id == account_id,
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

        # 2. 银行账户处理
        bank_account_id = data.bank_account_id
        bank_transaction_id = None
        if bank_account_id is not None:
            from engine_bank import BankEngine
            # 经 BankEngine.record_transaction 统一入口写入（含行锁、透支校验、余额同步）
            bank_tx = BankEngine(db, account_id).record_transaction(
                bank_account_id=bank_account_id,
                transaction_type="outflow",
                amount=repay_amount,
                transaction_date=datetime.combine(data.repayment_date, datetime.min.time()),
                description=f"偿还个人垫付: {advance.advancer_name} {advance.advance_no} {data.description}".strip(),
                flow_category="operating",
                related_entity_type="personal_advance_repayment",
                related_entity_id=None,  # 回写下方
            )
            bank_transaction_id = bank_tx.id

        # 3. 写偿还记录
        repayment = PersonalAdvanceRepayment(
            account_id=account_id,
            advance_id=advance_id,
            amount_l1=repay_amount,
            repayment_date_l1=datetime.combine(data.repayment_date, datetime.min.time()),
            bank_account_id=bank_account_id,
            bank_transaction_id=bank_transaction_id,
            description=data.description,
            is_reversed=False,
        )
        db.add(repayment)
        db.flush()

        # 回写 bank_transaction.related_entity_id
        if bank_transaction_id is not None:
            bank_tx.related_entity_id = repayment.id

        # 4. 总账：dr 2241 / cr 1002(银行) 或 1001(现金)
        post_journal(db, account_id, "personal_advance_repay", {
            "amount": repay_amount,
            "date": data.repayment_date.isoformat(),
            "bank_account_id": bank_account_id,
            "partner_id": None,
            "partner_type": "advancer",
            "source_model": "personal_advance_repay",
            "source_id": repayment.id,
        })

        # 5. 累加 paid_amount + 重算状态
        advance.paid_amount_l4 = (_d(advance.paid_amount_l4) + repay_amount).quantize(Q2)
        advance.repayment_status = _compute_status(advance.amount_l1, advance.paid_amount_l4)

        log_op(db, account_id, "create", "personal_advance_repayment", repayment.id,
             f"偿还个人垫付 {advance.advance_no}: {repay_amount}", operator=operator)

    db.refresh(repayment)
    db.refresh(advance)
    out = PersonalAdvanceRepaymentOut.model_validate(repayment).model_dump()
    advance_out = PersonalAdvanceOut.model_validate(advance).model_dump()

    result = OperationResult(
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
    )
    return result.to_dict()


# ── 红冲垫付单 ──

@router.post("/{advance_id}/reverse")
def reverse_personal_advance(
    advance_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
):
    """红冲垫付单（不物理删除，保留审计轨迹）

    规则：
    - 已有非冲红的偿还记录时禁止红冲（须先红冲所有偿还记录）
    - 红冲总账凭证 + 标记 is_reversed=True
    """
    with unit_of_work(db):
        advance = db.query(PersonalAdvance).filter(
            PersonalAdvance.id == advance_id,
            PersonalAdvance.account_id == account_id,
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

        # 校验无未冲红的偿还记录
        active_repayments = db.query(PersonalAdvanceRepayment).filter(
            PersonalAdvanceRepayment.advance_id == advance_id,
            PersonalAdvanceRepayment.is_reversed == False,
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

        # 红冲原始凭证（reverse_journal 自带幂等）
        reverse_journal(db, account_id, "personal_advance", advance_id)

        advance.is_reversed = True
        advance.reversed_at = datetime.now()
        # 冲红后状态语义上仍保留原值，剩余额由 remaining_amount 属性处理（返回 0）

        log_op(db, account_id, "reverse", "personal_advance", advance_id,
             f"红冲个人垫付 {advance.advance_no}", operator=operator)

    db.refresh(advance)
    out = PersonalAdvanceOut.model_validate(advance).model_dump()

    result = OperationResult(
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
    )
    return result.to_dict()


# ── 红冲单笔偿还 ──

@router.post("/{advance_id}/repayments/{repayment_id}/reverse")
def reverse_repayment(
    advance_id: int,
    repayment_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
):
    """红冲单笔偿还记录

    规则：
    - 红冲总账凭证 + 标记 repayment.is_reversed=True
    - 如有 bank_transaction：反向流水 + 恢复银行账户余额
    - 累减 advance.paid_amount_l4 + 重算 repayment_status
    """
    with unit_of_work(db):
        repayment = db.query(PersonalAdvanceRepayment).filter(
            PersonalAdvanceRepayment.id == repayment_id,
            PersonalAdvanceRepayment.account_id == account_id,
            PersonalAdvanceRepayment.advance_id == advance_id,
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

        # 锁垫付单
        advance = db.query(PersonalAdvance).filter(
            PersonalAdvance.id == advance_id,
            PersonalAdvance.account_id == account_id,
        ).with_for_update().first()
        if not advance:
            raise BusinessError(
                code=ErrorCode.ORDER_NOT_FOUND,
                data={"order_type": "个人垫付单", "order_id": advance_id},
            )

        repay_amount = _d(repayment.amount_l1)

        # 反向银行流水（如有）
        if repayment.bank_transaction_id is not None:
            from crud.reversal import reverse_bank_transaction
            reversal_tx = reverse_bank_transaction(db, account_id, repayment.bank_transaction_id)
            # reverse_bank_transaction 已自带幂等：已冲销过则返回旧记录，余额已回滚

        # 红冲总账凭证（reverse_journal 自带幂等）
        reverse_journal(db, account_id, "personal_advance_repay", repayment_id)

        # 标记已冲红
        repayment.is_reversed = True
        repayment.reversed_at = datetime.now()

        # 重算 paid_amount（只减去本次偿还金额，其他未冲红偿还仍累计）
        new_paid = _d(advance.paid_amount_l4) - repay_amount
        if new_paid < 0:
            new_paid = Decimal("0")
        advance.paid_amount_l4 = new_paid.quantize(Q2)
        advance.repayment_status = _compute_status(advance.amount_l1, advance.paid_amount_l4)

        log_op(db, account_id, "reverse", "personal_advance_repayment", repayment_id,
             f"红冲偿还记录 #{repayment_id}: {repay_amount}", operator=operator)

    db.refresh(advance)
    db.refresh(repayment)
    advance_out = PersonalAdvanceOut.model_validate(advance).model_dump()

    result = OperationResult(
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
    )
    return result.to_dict()
