from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id, get_operator
import schemas, crud
from commands import dispatch, AdjustInventory
from uow import unit_of_work
from errors import BusinessError, ErrorCode

router = APIRouter()


@router.get("")
def list_inventory(page: int = 1, page_size: int = 20, alert_only: bool = False, search: str = None, category: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, items = crud.list_inventory(db, account_id, skip=skip, limit=page_size, alert_only=alert_only, search=search, category=category)
    result = []
    for p, current_qty in items:
        result.append(schemas.InventoryOut(
            id=0, product_id=p.id, quantity=current_qty,
            average_cost=None, total_value=None,
            product_name=p.name if p else "",
            product_sku=p.sku if p else "",
            product_category=p.category if p else "",
            product_unit=p.unit if p else "",
            min_stock=p.min_stock_l3 if p else 0,
            purchase_price=p.purchase_price_l3 if p else 0,
            sale_price=p.sale_price_l3 if p else 0,
            last_updated=None,
            is_alert=current_qty < (p.min_stock_l3 if p else 0)
        ))
    return {"total": total, "items": result}


@router.get("/alerts", response_model=list[schemas.InventoryOut])
def get_alerts(account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    items = crud.get_stock_alerts(db, account_id)
    result = []
    for p, current_qty in items:
        result.append(schemas.InventoryOut(
            id=0, product_id=p.id, quantity=current_qty,
            average_cost=None, total_value=None,
            product_name=p.name if p else "",
            product_sku=p.sku if p else "",
            product_category=p.category if p else "",
            product_unit=p.unit if p else "",
            min_stock=p.min_stock_l3 if p else 0,
            purchase_price=p.purchase_price_l3 if p else 0,
            sale_price=p.sale_price_l3 if p else 0,
            last_updated=None,
            is_alert=True
        ))
    return result


@router.put("/{product_id}", response_model=schemas.InventoryOut)
def adjust_inventory(product_id: int, data: schemas.InventoryAdjust, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        inv = dispatch(AdjustInventory(
            account_id=account_id,
            operator=operator,
            product_id=product_id,
            quantity=data.quantity,
            adjust_date=data.adjust_date,
            reason=data.reason,
            unit_cost=data.unit_cost,
        ), db)
    if not inv:
        raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
    db.refresh(inv)
    p = inv.product
    return schemas.InventoryOut(
        id=inv.id, product_id=inv.product_id, quantity=inv.quantity_l4,
        average_cost=inv.average_cost_l4,
        total_value=(inv.average_cost_l4 * inv.quantity_l4) if inv.average_cost_l4 else None,
        product_name=p.name if p else "",
        product_sku=p.sku if p else "",
        product_category=p.category if p else "",
        product_unit=p.unit if p else "",
        min_stock=p.min_stock_l3 if p else 0,
        purchase_price=p.purchase_price_l3 if p else 0,
        sale_price=p.sale_price_l3 if p else 0,
        last_updated=inv.last_updated,
        is_alert=inv.quantity_l4 < (p.min_stock_l3 if p else 0)
    )