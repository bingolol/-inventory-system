"""无形资产 CRUD"""

from datetime import datetime
from sqlalchemy.orm import Session

import models, schemas
from ..base import _log
from lineage import writes, TIER_L3

@writes("IntangibleAsset.useful_life_l3", tier=TIER_L3, source="policy")
def create_intangible_asset(db: Session, account_id: int, data: schemas.IntangibleAssetCreate, operator: str = "user"):
    """创建无形资产"""
    asset = models.IntangibleAsset(
        account_id=account_id,
        asset_code=data.asset_code,
        name=data.name,
        category=data.category,
        original_value_l1=data.original_value,
        useful_life_l3=data.useful_life,
        start_date_l1=datetime.strptime(data.start_date, "%Y-%m-%d").date(),
        accumulated_amortization_l4=data.accumulated_amortization,
        status=data.status
    )
    db.add(asset)
    db.flush()
    # 生成会计凭证：借:1701（无形资产）贷:2202（应付账款）
    from finance_integration import post_journal
    post_journal(db, account_id, "intangible_asset_purchase", {
        "asset_id": asset.id,
        "original_value": data.original_value,
        "date": data.start_date,
        "source_model": "intangible_asset",
        "source_id": asset.id,
    })
    _log(db, account_id, "create", "intangible_asset", asset.id, f"创建无形资产: {data.name}", operator=operator)
    return asset


def get_intangible_asset(db: Session, account_id: int, asset_id: int):
    return db.query(models.IntangibleAsset).filter(
        models.IntangibleAsset.account_id == account_id,
        models.IntangibleAsset.id == asset_id
    ).first()


def list_intangible_assets(db: Session, account_id: int, status: str = None):
    query = db.query(models.IntangibleAsset).filter(models.IntangibleAsset.account_id == account_id)
    if status:
        query = query.filter(models.IntangibleAsset.status == status)
    return query.order_by(models.IntangibleAsset.created_at.desc()).all()


def update_intangible_asset(db: Session, account_id: int, asset_id: int, data: schemas.IntangibleAssetUpdate, operator: str = "user"):
    asset = get_intangible_asset(db, account_id, asset_id)
    if not asset:
        return None
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if key == "start_date" and value:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        setattr(asset, key, value)
    db.flush()
    _log(db, account_id, "update", "intangible_asset", asset_id, f"更新无形资产: {asset.name}", operator=operator)
    return asset


def delete_intangible_asset(db: Session, account_id: int, asset_id: int, operator: str = "user"):
    asset = get_intangible_asset(db, account_id, asset_id)
    if not asset:
        return False
    _log(db, account_id, "delete", "intangible_asset", asset_id, f"删除无形资产: {asset.name}", operator=operator)
    db.delete(asset)
    db.flush()
    return True
