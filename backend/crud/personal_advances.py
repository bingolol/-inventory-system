"""其他应付款/个人垫付 — 查询与统计 CRUD

写操作（create/repay/reverse）保留在 routers/personal_advances.py 内编排，
因为偿还流程需要 post_journal + BankTransaction + 状态更新三件事原子完成，
与 expenses/payments 现有模式一致。
本模块只负责读取查询与汇总报表。
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, and_
import models
import schemas

from accounting_engine import _d
from utils import Q2, get_or_404
from utils.sequencer import next_advance_no

# 保持对外兼容的别名
generate_advance_no = next_advance_no


def list_personal_advances(
    db: Session,
    account_id: int,
    skip: int = 0,
    limit: int = 100,
    advancer_name: str = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
):
    """列出垫付单（含分页与过滤），返回 (total, items)"""
    q = db.query(models.PersonalAdvance).filter(
        models.PersonalAdvance.account_id == account_id
    )
    if advancer_name:
        q = q.filter(models.PersonalAdvance.advancer_name.like(f"%{advancer_name}%"))
    if status:
        q = q.filter(models.PersonalAdvance.repayment_status == status)
    if start_date:
        q = q.filter(models.PersonalAdvance.advance_date_l1 >= start_date)
    if end_date:
        q = q.filter(models.PersonalAdvance.advance_date_l1 <= end_date)
    # 已冲红单据默认仍然展示（便于审计追溯），由前端标识
    total = q.count()
    items = q.order_by(models.PersonalAdvance.advance_date_l1.desc()).offset(skip).limit(limit).all()
    return total, items


def get_personal_advance(db: Session, account_id: int, advance_id: int):
    """获取单笔垫付单（含多租户过滤），不存在则抛 BusinessError"""
    return get_or_404(db, models.PersonalAdvance, advance_id, account_id)


def list_repayments_by_advance(db: Session, account_id: int, advance_id: int):
    """列出某笔垫付单的全部偿还记录（按时间正序）"""
    return db.query(models.PersonalAdvanceRepayment).filter(
        models.PersonalAdvanceRepayment.account_id == account_id,
        models.PersonalAdvanceRepayment.advance_id == advance_id,
    ).order_by(models.PersonalAdvanceRepayment.repayment_date_l1.asc()).all()


def get_repayment(db: Session, account_id: int, repayment_id: int):
    """获取单笔偿还记录，不存在则抛 BusinessError"""
    return get_or_404(db, models.PersonalAdvanceRepayment, repayment_id, account_id)


def get_personal_advance_summary(db: Session, account_id: int):
    """按垫付人聚合的汇总报表

    只统计未冲红的垫付单（is_reversed=False）。
    返回每位的：垫付笔数、累计金额、已还金额、未还余额。
    """
    rows = db.query(
        models.PersonalAdvance.advancer_name.label("advancer_name"),
        sqlfunc.count(models.PersonalAdvance.id).label("advance_count"),
        sqlfunc.sum(models.PersonalAdvance.amount_l1).label("total_amount"),
        sqlfunc.sum(models.PersonalAdvance.paid_amount_l4).label("paid_amount"),
    ).filter(
        models.PersonalAdvance.account_id == account_id,
        models.PersonalAdvance.is_reversed == False,
    ).group_by(models.PersonalAdvance.advancer_name).all()

    result = []
    for r in rows:
        total = _d(r.total_amount or 0).quantize(Q2)
        paid = _d(r.paid_amount or 0).quantize(Q2)
        result.append(schemas.PersonalAdvanceSummary(
            advancer_name=r.advancer_name,
            advance_count=int(r.advance_count or 0),
            total_amount=total,
            paid_amount=paid,
            remaining_amount=(total - paid).quantize(Q2),
        ))
    return result


def get_personal_advance_totals(db: Session, account_id: int):
    """汇总：未冲红垫付的总金额、已还金额、未还余额

    用于列表页顶部统计卡片，以及作为 2241 科目余额的对照（应相等）。
    """
    row = db.query(
        sqlfunc.sum(models.PersonalAdvance.amount_l1).label("total_amount"),
        sqlfunc.sum(models.PersonalAdvance.paid_amount_l4).label("paid_amount"),
    ).filter(
        models.PersonalAdvance.account_id == account_id,
        models.PersonalAdvance.is_reversed == False,
    ).first()

    total = _d(row.total_amount or 0).quantize(Q2)
    paid = _d(row.paid_amount or 0).quantize(Q2)
    return {
        "total_amount": total,
        "paid_amount": paid,
        "remaining_amount": (total - paid).quantize(Q2),
    }
