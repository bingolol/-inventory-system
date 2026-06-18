from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from schemas import FixedAssetCreate, FixedAssetUpdate, FixedAssetOut, PaginatedResponse
from account_dep import get_account_id, get_operator
import crud
from uow import unit_of_work

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
            raise HTTPException(status_code=404, detail="固定资产不存在")
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
            raise HTTPException(status_code=404, detail="固定资产不存在")
    return {"message": "固定资产已删除"}
