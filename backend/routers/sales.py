from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import SaleOrder
from account_dep import get_account_id, get_operator
from image_utils import delete_old_image
import schemas, crud
from uow import unit_of_work
from commands.base import dispatch
from commands.sale_commands import (
    CreateSaleOrder, CancelSaleOrder, RestoreSaleOrder,
    DeleteSaleOrder, UpdateSaleOrderItems,
    UpdateSaleOrderFields,
)
from enums import OrderStatus, OrderType

router = APIRouter()


def _build_sale_out(order):
    items = []
    for item in order.items:
        items.append(schemas.SaleItemOut(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name if item.product else None,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate,
            total_price=item.total_price,
            notes=item.notes or "",
        ))
    return schemas.SaleOrderOut(
        id=order.id,
        order_no=order.order_no,
        customer_id=order.customer_id,
        customer_name=order.customer.name if order.customer else "散客",
        order_type=order.order_type if order.order_type is not None else OrderType.RETAIL,
        total_price=order.total_price,
        has_invoice=order.has_invoice,
        payment_status=order.payment_status,
        status=order.status,
        notes=order.notes,
        image_url=order.image_url or "",
        sale_date=order.sale_date,
        created_at=order.created_at,
        items=items
    )


@router.get("")
def list_sales(page: int = 1, page_size: int = 20, start_date: str = None, end_date: str = None, status: str = None, order_type: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, orders = crud.list_sale_orders(db, account_id, skip=skip, limit=page_size, start_date=start_date, end_date=end_date, status=status, order_type=order_type)
    result = []
    for order in orders:
        result.append(_build_sale_out(order))
    return {"total": total, "items": result}


@router.post("", response_model=schemas.SaleOrderOut)
def create_sale(data: schemas.SaleOrderCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            cmd = CreateSaleOrder(
                account_id=account_id,
                operator=operator,
                customer_id=data.customer_id,
                has_invoice=data.has_invoice,
                payment_status=data.payment_status,
                notes=data.notes,
                image_url=data.image_url or "",
                total_price=data.total_price,
                sale_date=data.sale_date,
                items=[item.model_dump() for item in data.items],
            )
            order = dispatch(cmd, db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    db.refresh(order)
    return _build_sale_out(order)


@router.get("/{sale_id}", response_model=schemas.SaleOrderOut)
def get_sale(sale_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    order = crud.get_sale_order(db, account_id, sale_id)
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")
    return _build_sale_out(order)


@router.put("/{sale_id}", response_model=schemas.SaleOrderOut)
def update_sale(sale_id: int, data: schemas.SaleOrderUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            order = None
            has_items = data.items is not None

            # 1) items 全量替换 → UpdateSaleOrderItems
            if has_items:
                items_dicts = [item.model_dump() for item in data.items]
                cmd = UpdateSaleOrderItems(
                    account_id=account_id,
                    operator=operator,
                    order_id=sale_id,
                    items=items_dicts,
                    total_price=data.total_price,
                )
                order = dispatch(cmd, db)
                if order is None:
                    # items 为空 → 自动删除，与原逻辑一致返回 404
                    raise ValueError("销售单不存在")

            # 2) 无 items 时的状态切换 → Cancel / Restore
            if not has_items and data.status is not None:
                current = crud.get_sale_order(db, account_id, sale_id)
                if not current:
                    raise ValueError("销售单不存在")
                if data.status == OrderStatus.CANCELLED and current.status != OrderStatus.CANCELLED:
                    dispatch(CancelSaleOrder(account_id=account_id, operator=operator, order_id=sale_id), db)
                elif data.status == OrderStatus.COMPLETED and current.status == OrderStatus.CANCELLED:
                    dispatch(RestoreSaleOrder(account_id=account_id, operator=operator, order_id=sale_id), db)

                        # 4) 普通字段 → UpdateSaleOrderFields
            #    有 items 时 status 也作为普通字段设置（只 setattr，不做库存联动）
            field_kwargs = {}
            for k in ('customer_id', 'has_invoice', 'payment_status', 'notes', 'image_url'):
                v = getattr(data, k, None)
                if v is not None:
                    field_kwargs[k] = v
            if has_items and data.status is not None:
                field_kwargs['status'] = data.status
            if field_kwargs:
                dispatch(UpdateSaleOrderFields(
                    account_id=account_id,
                    operator=operator,
                    order_id=sale_id,
                    **field_kwargs
                ), db)

            # 获取最新 order 对象
            if order is None:
                order = crud.get_sale_order(db, account_id, sale_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")
    db.refresh(order)
    return _build_sale_out(order)


@router.delete("/{sale_id}")
def delete_sale(sale_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    # 先查记录获取 image_url
    order = db.query(SaleOrder).filter(
        SaleOrder.id == sale_id,
        SaleOrder.account_id == account_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")
    # 删除关联图片文件
    image_url = order.image_url
    if image_url:
        delete_old_image(image_url)
    with unit_of_work(db):
        try:
            dispatch(DeleteSaleOrder(account_id=account_id, operator=operator, order_id=sale_id), db)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"result": "销售单已删除"}