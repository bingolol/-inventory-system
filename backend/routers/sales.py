from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import SaleOrder
from account_dep import get_account_id, get_operator
from image_utils import delete_old_image
import schemas, crud
from uow import unit_of_work

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
            total_price=item.total_price
        ))
    return schemas.SaleOrderOut(
        id=order.id,
        order_no=order.order_no,
        customer_id=order.customer_id,
        customer_name=order.customer.name if order.customer else "散客",
        project_name=order.project_name,
        project_id=order.project_id,
        deduct_inventory=bool(order.deduct_inventory) if order.deduct_inventory is not None else False,
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


@router.get("/")
def list_sales(page: int = 1, page_size: int = 20, start_date: str = None, end_date: str = None, status: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, orders = crud.list_sale_orders(db, account_id, skip=skip, limit=page_size, start_date=start_date, end_date=end_date, status=status)
    result = []
    for order in orders:
        result.append(_build_sale_out(order))
    return {"total": total, "items": result}


@router.post("/", response_model=schemas.SaleOrderOut)
def create_sale(data: schemas.SaleOrderCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            order = crud.create_sale_order(db, account_id, data, operator)
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
        order = crud.update_sale_order(db, account_id, sale_id, data, operator)
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")
    db.refresh(order)
    return _build_sale_out(order)


@router.delete("/{sale_id}")
def delete_sale(sale_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    # 先查记录获取image_url
    order = db.query(SaleOrder).filter(
        SaleOrder.id == sale_id,
        SaleOrder.account_id == account_id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="销售单不存在")
    # 删除关联图片文件
    if order.image_url:
        delete_old_image(order.image_url)
    with unit_of_work(db):
        success = crud.delete_sale_order(db, account_id, sale_id, operator)
    if not success:
        raise HTTPException(status_code=404, detail="销售单不存在")
    return {"result": "销售单已删除"}