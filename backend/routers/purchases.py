from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import PurchaseOrder
from account_dep import get_account_id, get_operator
from image_utils import delete_old_image
import schemas, crud
from uow import unit_of_work
from commands.base import dispatch
from commands.purchase_commands import (
    CreatePurchaseOrder, CancelPurchaseOrder,
    DeletePurchaseOrder, UpdatePurchaseOrderItems,
    UpdatePurchaseOrderFields,
)
from enums import OrderStatus, OrderType

router = APIRouter()


def _build_purchase_out(order):
    items = []
    for item in order.items:
        items.append(schemas.PurchaseItemOut(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name if item.product else None,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate,
            total_price=item.total_price,
            notes=item.notes or "",
        ))
    return schemas.PurchaseOrderOut(
        id=order.id,
        order_no=order.order_no,
        supplier_id=order.supplier_id,
        supplier_name=order.supplier.name if order.supplier else None,
        order_type=order.order_type if order.order_type is not None else OrderType.RETAIL,
        total_price=order.total_price,
        has_invoice=order.has_invoice,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        status=order.status,
        notes=order.notes,
        image_url=order.image_url or "",
        purchase_date=order.purchase_date,
        created_at=order.created_at,
        items=items
    )


@router.get("")
def list_purchases(page: int = 1, page_size: int = 20, start_date: str = None, end_date: str = None, status: str = None, keyword: str = None, order_type: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, orders = crud.list_purchase_orders(db, account_id, skip=skip, limit=page_size, start_date=start_date, end_date=end_date, status=status, keyword=keyword, order_type=order_type)
    result = []
    for order in orders:
        result.append(_build_purchase_out(order))
    return {"total": total, "items": result}


@router.post("", response_model=schemas.PurchaseOrderOut)
def create_purchase(data: schemas.PurchaseOrderCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            cmd = CreatePurchaseOrder(
                account_id=account_id,
                operator=operator,
                supplier_id=data.supplier_id,
                has_invoice=data.has_invoice,
                payment_method=data.payment_method,
                notes=data.notes,
                image_url=data.image_url or "",
                items=[item.model_dump() for item in data.items],
            )
            order = dispatch(cmd, db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    db.refresh(order)
    return _build_purchase_out(order)


@router.get("/{purchase_id}", response_model=schemas.PurchaseOrderOut)
def get_purchase(purchase_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    order = crud.get_purchase_order(db, account_id, purchase_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    return _build_purchase_out(order)


@router.put("/{purchase_id}", response_model=schemas.PurchaseOrderOut)
def update_purchase(purchase_id: int, data: schemas.PurchaseOrderUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            order = None
            has_items = data.items is not None

            # 1) items 全量替换 → UpdatePurchaseOrderItems
            if has_items:
                items_dicts = [item.model_dump() for item in data.items]
                cmd = UpdatePurchaseOrderItems(
                    account_id=account_id,
                    operator=operator,
                    order_id=purchase_id,
                    items=items_dicts,
                    supplier_id=data.supplier_id,
                    has_invoice=data.has_invoice,
                    payment_method=data.payment_method,
                    notes=data.notes,
                    status=data.status,
                )
                order = dispatch(cmd, db)
                if order is None:
                    # items 为空 → 自动删除
                    raise ValueError("采购单不存在")

            # 2) 无 items 时的状态切换 → Cancel
            if not has_items and data.status is not None:
                current = crud.get_purchase_order(db, account_id, purchase_id)
                if not current:
                    raise ValueError("采购单不存在")
                if data.status == OrderStatus.CANCELLED and current.status != OrderStatus.CANCELLED:
                    dispatch(CancelPurchaseOrder(account_id=account_id, operator=operator, order_id=purchase_id), db)

            # 3) 普通字段 → UpdatePurchaseOrderFields
            field_kwargs = {}
            for k in ('supplier_id', 'has_invoice', 'payment_method', 'payment_status', 'notes', 'image_url'):
                v = getattr(data, k, None)
                if v is not None:
                    field_kwargs[k] = v
            if has_items and data.status is not None:
                field_kwargs['status'] = data.status
            if not has_items and data.status is not None and data.status != OrderStatus.CANCELLED:
                field_kwargs['status'] = data.status
            if field_kwargs:
                dispatch(UpdatePurchaseOrderFields(
                    account_id=account_id,
                    operator=operator,
                    order_id=purchase_id,
                    **field_kwargs
                ), db)

            # 获取最新 order 对象
            if order is None:
                order = crud.get_purchase_order(db, account_id, purchase_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    db.refresh(order)
    return _build_purchase_out(order)


@router.delete("/{purchase_id}")
def delete_purchase(purchase_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    # 先查记录获取image_url
    order = db.query(PurchaseOrder).filter(
        PurchaseOrder.id == purchase_id,
        PurchaseOrder.account_id == account_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    # 删除关联图片文件
    if order.image_url:
        delete_old_image(order.image_url)
    with unit_of_work(db):
        try:
            dispatch(DeletePurchaseOrder(account_id=account_id, operator=operator, order_id=purchase_id), db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"result": "采购单已删除"}