"""其他应付款/个人垫付路由

写操作全部下沉到 commands.personal_advance_commands，
router 只负责 HTTP 解析 + dispatch。

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

from database import get_db
from schemas import (
    PersonalAdvanceCreate, PersonalAdvanceOut,
    PersonalAdvanceRepaymentCreate, PersonalAdvanceRepaymentOut,
    PersonalAdvanceSummary, PaginatedResponse,
)
from account_dep import get_account_id, get_operator
from errors import BusinessError, ErrorCode
from uow import unit_of_work
import crud
from commands.base import dispatch
from commands.personal_advance_commands import (
    CreatePersonalAdvance,
    RepayPersonalAdvance,
    ReversePersonalAdvance,
    ReversePersonalAdvanceRepayment,
)

router = APIRouter()


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

@router.post("")
def create_personal_advance(
    data: PersonalAdvanceCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
):
    """创建垫付单"""
    with unit_of_work(db):
        return dispatch(CreatePersonalAdvance(
            account_id=account_id,
            operator=operator,
            data=data,
        ), db)


# ── 偿还垫付 ──

@router.post("/{advance_id}/repay")
def repay_personal_advance(
    advance_id: int,
    data: PersonalAdvanceRepaymentCreate,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
):
    """偿还垫付单（支持部分偿还）"""
    with unit_of_work(db):
        return dispatch(RepayPersonalAdvance(
            account_id=account_id,
            operator=operator,
            advance_id=advance_id,
            data=data,
        ), db)


# ── 红冲垫付单 ──

@router.post("/{advance_id}/reverse")
def reverse_personal_advance(
    advance_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
):
    """红冲垫付单"""
    with unit_of_work(db):
        return dispatch(ReversePersonalAdvance(
            account_id=account_id,
            operator=operator,
            advance_id=advance_id,
        ), db)


# ── 红冲单笔偿还 ──

@router.post("/{advance_id}/repayments/{repayment_id}/reverse")
def reverse_repayment(
    advance_id: int,
    repayment_id: int,
    db: Session = Depends(get_db),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
):
    """红冲单笔偿还记录"""
    with unit_of_work(db):
        return dispatch(ReversePersonalAdvanceRepayment(
            account_id=account_id,
            operator=operator,
            advance_id=advance_id,
            repayment_id=repayment_id,
        ), db)
