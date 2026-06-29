from fastapi import APIRouter, Depends, Query
from errors import BusinessError, ErrorCode, ActionType
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
from datetime import date

from database import get_db
from schemas import FixedAssetCreate, FixedAssetUpdate, FixedAssetOut, FixedAssetWithInvoiceUpdate, PaginatedResponse
from account_dep import get_account_id, get_operator
import crud
from uow import unit_of_work
from commands.base import dispatch
from engine_fixed_asset import FixedAssetEngine

router = APIRouter()


def _to_out(asset) -> FixedAssetOut:
    return FixedAssetOut(
        id=asset.id,
        account_id=asset.account_id,
        asset_code=asset.asset_code or "",
        name=asset.name,
        category=asset.category,
        original_value=asset.original_value,
        salvage_rate=asset.salvage_rate,
        useful_life=asset.useful_life,
        depreciation_method=asset.depreciation_method or "年限平均法",
        start_date=asset.start_date.isoformat() if asset.start_date else "",
        accumulated_depreciation=asset.accumulated_depreciation,
        status=asset.status or "在用",
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


@router.get("", response_model=PaginatedResponse)
def list_fixed_assets(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    account_id: int = Depends(get_account_id),
    db: Session = Depends(get_db),
):
    """获取固定资产列表，支持按状态筛选"""
    assets = crud.list_fixed_assets(db, account_id, status=status)
    total = len(assets)
    paged = assets[skip: skip + limit]
    return PaginatedResponse(total=total, items=[_to_out(a) for a in paged])


@router.post("", response_model=FixedAssetOut)
def create_fixed_asset(
    data: FixedAssetCreate,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """创建固定资产"""
    with unit_of_work(db):
        asset = crud.create_fixed_asset(db, account_id, data, operator=operator)
    db.refresh(asset)
    return _to_out(asset)


@router.put("/{asset_id}", response_model=FixedAssetOut)
def update_fixed_asset(
    asset_id: int,
    data: FixedAssetUpdate,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """更新固定资产"""
    with unit_of_work(db):
        asset = crud.update_fixed_asset(db, account_id, asset_id, data, operator=operator)
        if not asset:
            raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND, data={"asset_id": asset_id})
    db.refresh(asset)
    return _to_out(asset)


@router.delete("/{asset_id}")
def delete_fixed_asset(
    asset_id: int,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """删除固定资产"""
    with unit_of_work(db):
        ok = crud.delete_fixed_asset(db, account_id, asset_id, operator=operator)
        if not ok:
            raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND, data={"asset_id": asset_id})
    return {"message": "固定资产已删除"}


@router.post("/{asset_id}/depreciate")
def depreciate_fixed_asset(
    asset_id: int,
    period: str = Query(..., description="计提期间 YYYY-MM"),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """计提单个固定资产月折旧"""
    with unit_of_work(db):
        eng = FixedAssetEngine(db, account_id)
        dep = eng.record_depreciation(asset_id, period)
    if dep is None:
        return {"message": "无需计提（已提足或不在计提期）", "depreciation_id": None}
    return {"message": f"折旧计提成功: {dep.amount}", "depreciation_id": dep.id, "amount": str(dep.amount)}


@router.post("/batch-depreciate")
def batch_depreciate_fixed_assets(
    period: str = Query(..., description="计提期间 YYYY-MM"),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """批量计提所有在用固定资产折旧"""
    with unit_of_work(db):
        eng = FixedAssetEngine(db, account_id)
        results = eng.batch_depreciate(period)
    return {
        "message": f"批量折旧完成: {len(results)}项资产已计提",
        "count": len(results),
        "details": [{"asset_id": d.asset_id, "period": d.period, "amount": str(d.amount)} for d in results],
    }


@router.post("/{asset_id}/dispose")
def dispose_fixed_asset(
    asset_id: int,
    disposal_price: Decimal = Query(Decimal("0"), description="处置价格"),
    disposal_date: str = Query(..., description="处置业务日期 YYYY-MM-DD（必填）"),
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """处置（报废/出售）固定资产"""
    from datetime import datetime as _dt
    parsed_date = None
    if disposal_date:
        try:
            # date 类没有 strptime，必须用 datetime.strptime 再 .date()
            parsed_date = _dt.strptime(disposal_date, "%Y-%m-%d").date()
        except ValueError:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                                message=f"disposal_date 格式错误: {disposal_date}，应为 YYYY-MM-DD")
    with unit_of_work(db):
        eng = FixedAssetEngine(db, account_id)
        eng.record_disposal(asset_id, disposal_price, disposal_date=parsed_date)
    return {"message": "固定资产已处置"}


@router.put("/{asset_id}/with-invoice")
def update_asset_with_invoice(
    asset_id: int,
    data: FixedAssetWithInvoiceUpdate,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """更新固定资产（联动发票）"""
    from commands.invoice_commands import UpdateAssetWithInvoice

    try:
        with unit_of_work(db):
            cmd = UpdateAssetWithInvoice(
                account_id=account_id,
                operator=operator,
                asset_id=asset_id,
                original_value=data.original_value,
                name=data.name,
                category=data.category,
                salvage_rate=data.salvage_rate,
                useful_life=data.useful_life,
                depreciation_method=data.depreciation_method,
                start_date=data.start_date,
                status=data.status,
            )
            result = dispatch(cmd, db)
    except ValueError:
        raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "更新固定资产失败，请检查输入数据"})

    asset = result["asset"]
    invoice = result["invoice"]
    db.refresh(asset)
    if invoice:
        db.refresh(invoice)

    return {
        "message": "固定资产更新成功",
        "asset": _to_out(asset).model_dump(),
        "invoice": {
            "id": invoice.id,
            "invoice_no": invoice.invoice_no,
            "amount_without_tax": float(invoice.amount_without_tax),
            "tax_amount": float(invoice.tax_amount),
            "amount_with_tax": float(invoice.amount_with_tax),
        } if invoice else None
    }
