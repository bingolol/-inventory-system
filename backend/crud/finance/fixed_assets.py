"""固定资产 CRUD（含会计凭证）"""

from datetime import datetime
from sqlalchemy.orm import Session

import models, schemas
from ..base import _log

def create_fixed_asset(db: Session, account_id: int, data: schemas.FixedAssetCreate, operator: str = "user"):
    """创建固定资产（含会计凭证：借:1601 贷:2202）"""
    asset = models.FixedAsset(
        account_id=account_id,
        asset_code=data.asset_code,
        name=data.name,
        category=data.category,
        original_value=data.original_value,
        salvage_rate=data.salvage_rate,
        useful_life=data.useful_life,
        depreciation_method=data.depreciation_method,
        start_date=datetime.strptime(data.start_date, "%Y-%m-%d").date(),
        accumulated_depreciation=data.accumulated_depreciation,
        status=data.status
    )
    db.add(asset)
    db.flush()
    from finance_integration import post_journal
    post_journal(db, account_id, "fixed_asset_purchase", {
        "asset_id": asset.id,
        "original_value": data.original_value,
        "date": data.start_date,
        "source_model": "fixed_asset",
        "source_id": asset.id,
    })
    _log(db, account_id, "create", "fixed_asset", asset.id, f"创建固定资产: {data.name}", operator=operator)
    return asset


def get_fixed_asset(db: Session, account_id: int, asset_id: int):
    return db.query(models.FixedAsset).filter(
        models.FixedAsset.account_id == account_id,
        models.FixedAsset.id == asset_id
    ).first()


def list_fixed_assets(db: Session, account_id: int, status: str = None):
    query = db.query(models.FixedAsset).filter(models.FixedAsset.account_id == account_id)
    if status:
        query = query.filter(models.FixedAsset.status == status)
    return query.order_by(models.FixedAsset.created_at.desc()).all()


def update_fixed_asset(db: Session, account_id: int, asset_id: int, data: schemas.FixedAssetUpdate, operator: str = "user"):
    asset = get_fixed_asset(db, account_id, asset_id)
    if not asset:
        return None
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key == "start_date" and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        setattr(asset, key, value)
    db.flush()
    _log(db, account_id, "update", "fixed_asset", asset_id, f"更新固定资产: {asset.name}", operator=operator)
    return asset


def delete_fixed_asset(db: Session, account_id: int, asset_id: int, operator: str = "user"):
    asset = get_fixed_asset(db, account_id, asset_id)
    if not asset:
        return False

    # 清空关联发票的引用
    invoices = db.query(models.Invoice).filter(
        models.Invoice.related_order_id == asset_id,
        models.Invoice.related_order_type == "fixed_asset",
        models.Invoice.account_id == account_id,
    ).all()
    for inv in invoices:
        inv.related_order_id = None
        inv.related_order_type = None

    _log(db, account_id, "delete", "fixed_asset", asset_id, f"删除固定资产: {asset.name}", operator=operator)
    db.delete(asset)
    db.flush()
    return True
