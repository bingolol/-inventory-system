"""固定资产 CRUD（含会计凭证）"""

from datetime import datetime
from sqlalchemy.orm import Session

import models, schemas
from ..base import log_op
from utils import get_or_404
from lineage import writes, TIER_L3

@writes("FixedAsset.salvage_rate_l3", tier=TIER_L3, source="policy")
@writes("FixedAsset.useful_life_l3", tier=TIER_L3, source="policy")
@writes("FixedAsset.depreciation_method_l3", tier=TIER_L3, source="policy")
def create_fixed_asset(db: Session, account_id: int, data: schemas.FixedAssetCreate, operator: str = "user"):
    """创建固定资产"""
    asset = models.FixedAsset(
        account_id=account_id,
        asset_code=data.asset_code,
        name=data.name,
        category=data.category,
        original_value_l1=data.original_value,
        salvage_rate_l3=data.salvage_rate,
        useful_life_l3=data.useful_life,
        depreciation_method_l3=data.depreciation_method,
        start_date_l1=datetime.strptime(data.start_date, "%Y-%m-%d").date(),
        accumulated_depreciation_l4=data.accumulated_depreciation,
        status=data.status
    )
    db.add(asset)
    db.flush()
    log_op(db, account_id, "create", "fixed_asset", asset.id, f"创建固定资产: {data.name}", operator=operator)
    return asset


def get_fixed_asset(db: Session, account_id: int, asset_id: int):
    return get_or_404(db, models.FixedAsset, asset_id, account_id)


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
    log_op(db, account_id, "update", "fixed_asset", asset_id, f"更新固定资产: {asset.name}", operator=operator)
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

    log_op(db, account_id, "delete", "fixed_asset", asset_id, f"删除固定资产: {asset.name}", operator=operator)
    db.delete(asset)
    db.flush()
    return True
