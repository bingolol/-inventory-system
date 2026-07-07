"""税务申报声明 API — VAT + 附加税申报入口"""

from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from account_dep import get_account_id, get_operator
from uow import unit_of_work
from commands.base import dispatch
from commands.tax_declaration_commands import DeclareVAT, DeclareSurcharge
from crud.base import log_op
from models_finance import VATDeclaration, SurchargeDeclaration
from schemas.finance import (
    VATDeclarationCreate, VATDeclarationOut,
    SurchargeDeclarationCreate, SurchargeDeclarationOut,
    DeclaredPeriodOut,
)

router = APIRouter()


@router.post("/declare", response_model=dict)
def declare_vat(
    body: VATDeclarationCreate,
    force: bool = Query(False, description="覆盖已存在的 VAT 声明"),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """提交 VAT 申报声明（锁定快照）"""
    if force:
        existing = db.query(VATDeclaration).filter(
            VATDeclaration.account_id == account_id,
            VATDeclaration.period == body.period,
        ).first()
        if existing:
            # BR-REV: 删除前冲红 vat_transfer_out 凭证，避免 dangling AccountMove 导致 BS 不平
            from finance_integration import reverse_journal
            from utils.period import period_hash
            reverse_journal(
                db, account_id, "vat_transfer_out",
                period_hash(body.period, "vat_xfer"), force=True,
            )
            log_op(db, account_id, "delete", "vat_declaration", existing.id,
                 f"VAT 申报覆盖删除: 期间={body.period}", operator=operator)
            db.delete(existing)
            db.flush()

    with unit_of_work(db):
        result = dispatch(DeclareVAT(
            account_id=account_id,
            operator=operator,
            period=body.period,
            taxpayer_type=body.taxpayer_type,
        ), db)
    return {"ok": True, "data": result}


@router.post("/surcharge-declaration", response_model=dict)
def declare_surcharge(
    body: SurchargeDeclarationCreate,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """录入附加税声明（录入即过账 + 级联修正）"""
    with unit_of_work(db):
        result = dispatch(DeclareSurcharge(
            account_id=account_id,
            operator=operator,
            period=body.period,
            urban_construction_tax=body.urban_construction_tax,
            education_surcharge=body.education_surcharge,
            local_education_surcharge=body.local_education_surcharge,
            notes=body.notes,
        ), db)
    return {"ok": True, "data": result}


@router.get("/pending-declarations", response_model=list)
def get_pending_declarations(
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """查询待申报期间列表（首页待办用）"""
    import models

    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        return []

    taxpayer_type = account.taxpayer_type_l3 or "small_scale"
    today = date.today()
    pending = []

    if taxpayer_type == "small_scale":
        current_q = (today.month - 1) // 3 + 1
        for q in range(1, current_q + 1):
            period = f"{today.year}-Q{q}"
            start_month = (q - 1) * 3 + 1
            end_month = q * 3
            import calendar
            last_day = calendar.monthrange(today.year, end_month)[1]
            period_end = date(today.year, end_month, last_day)
            deadline_month = end_month + 1
            deadline_year = today.year
            if deadline_month > 12:
                deadline_month -= 12
                deadline_year += 1
            deadline = date(deadline_year, deadline_month, 15)

            vat_decl = db.query(VATDeclaration).filter(
                VATDeclaration.account_id == account_id,
                VATDeclaration.period == period,
            ).first()
            sur_decl = db.query(SurchargeDeclaration).filter(
                SurchargeDeclaration.account_id == account_id,
                SurchargeDeclaration.period == period,
            ).first()

            status = "pending"
            if sur_decl:
                status = "surcharge_declared"
            elif vat_decl:
                status = "vat_declared"

            pending.append({
                "period": period,
                "period_start": f"{today.year}-{start_month:02d}-01",
                "period_end": f"{today.year}-{end_month:02d}-{last_day}",
                "due_date": deadline.isoformat(),
                "taxpayer_type": taxpayer_type,
                "vat_declared": vat_decl is not None,
                "surcharge_declared": sur_decl is not None,
                "status": status,
            })
    else:
        for m in range(1, today.month + 1):
            period = f"{today.year}-{m:02d}"
            import calendar
            last_day = calendar.monthrange(today.year, m)[1]
            period_end = date(today.year, m, last_day)
            deadline_month = m + 1
            deadline_year = today.year
            if deadline_month > 12:
                deadline_month -= 12
                deadline_year += 1
            deadline = date(deadline_year, deadline_month, 15)

            vat_decl = db.query(VATDeclaration).filter(
                VATDeclaration.account_id == account_id,
                VATDeclaration.period == period,
            ).first()
            sur_decl = db.query(SurchargeDeclaration).filter(
                SurchargeDeclaration.account_id == account_id,
                SurchargeDeclaration.period == period,
            ).first()

            status = "pending"
            if sur_decl:
                status = "surcharge_declared"
            elif vat_decl:
                status = "vat_declared"

            pending.append({
                "period": period,
                "period_start": f"{today.year}-{m:02d}-01",
                "period_end": f"{today.year}-{m:02d}-{last_day}",
                "due_date": deadline.isoformat(),
                "taxpayer_type": taxpayer_type,
                "vat_declared": vat_decl is not None,
                "surcharge_declared": sur_decl is not None,
                "status": status,
            })

    return pending


@router.get("/declarations", response_model=list)
def list_declarations(
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """列出所有 VAT 声明"""
    decls = db.query(VATDeclaration).filter(
        VATDeclaration.account_id == account_id,
    ).order_by(VATDeclaration.id.desc()).all()
    results = []
    for d in decls:
        sur = db.query(SurchargeDeclaration).filter(
            SurchargeDeclaration.account_id == account_id,
            SurchargeDeclaration.period == d.period,
        ).first()
        results.append({
            "id": d.id,
            "period": d.period,
            "taxpayer_type": d.taxpayer_type,
            "vat_payable": float(d.vat_payable),
            "total_revenue": float(d.total_revenue),
            "snapshot_at": d.snapshot_at.isoformat() if d.snapshot_at else None,
            "surcharge_declared": sur is not None,
            "surcharge_total": float(sur.total) if sur else 0,
        })
    return results