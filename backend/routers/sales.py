from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import SaleOrder
from errors import BusinessError, ErrorCode
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
from crud.invoice_linkage import has_invoice as linkage_has_invoice, bulk_has_invoice
from enums import OrderStatus, OrderType
from operation_result import OperationResult, EntityType, OperationType

router = APIRouter()


def _build_sale_out(order, invoiced: bool = False):
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
        has_invoice=invoiced,
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
    # 批量派生查询:哪些销售单有发票关联(单一真相源)
    invoiced_ids = bulk_has_invoice(db, account_id, "sale_order", [o.id for o in orders])
    result = []
    for order in orders:
        result.append(_build_sale_out(order, invoiced=(order.id in invoiced_ids)))
    return {"total": total, "items": result}


@router.post("")
def create_sale(data: schemas.SaleOrderCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            cmd = CreateSaleOrder(
                account_id=account_id,
                operator=operator,
                customer_id=data.customer_id,
                deduct_inventory=data.deduct_inventory,
                payment_status=data.payment_status,
                notes=data.notes,
                image_url=data.image_url or "",
                total_price=data.total_price,
                sale_date=data.sale_date,
                items=[item.model_dump() for item in data.items],
            )
            order = dispatch(cmd, db)
        except ValueError as e:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message=str(e))
    db.refresh(order)
    
    # 构建库存变化信息
    inventory_changes = []
    for item in order.items:
        product = crud.get_product(db, account_id, item.product_id)
        inventory_changes.append({
            "product_id": item.product_id,
            "product_name": product.name if product else f"商品{item.product_id}",
            "quantity": f"-{item.quantity}"
        })
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.SALE_ORDER,
        entity_id=order.id,
        summary=f"销售单 {order.order_no} 创建成功，金额 {order.total_price}，商品数量 {len(order.items)}",
        ai_hint="销售单已创建，库存已扣减。如需收款，请调用 POST /api/receipts。",
        data=_build_sale_out(order, invoiced=linkage_has_invoice(db, account_id, "sale_order", order.id)).model_dump(),
        changes={
            "inventory": inventory_changes,
            "receivable": {"amount": f"+{order.total_price}"}
        }
    )
    return result.to_dict()


@router.get("/{sale_id}", response_model=schemas.SaleOrderOut)
def get_sale(sale_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    order = crud.get_sale_order(db, account_id, sale_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": sale_id})
    return _build_sale_out(order, invoiced=linkage_has_invoice(db, account_id, "sale_order", order.id))


@router.put("/{sale_id}")
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
                    raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单"})

            # 2) 无 items 时的状态切换 → Cancel / Restore
            if not has_items and data.status is not None:
                current = crud.get_sale_order(db, account_id, sale_id)
                if not current:
                    raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单"})
                if data.status == OrderStatus.CANCELLED and current.status != OrderStatus.CANCELLED:
                    dispatch(CancelSaleOrder(account_id=account_id, operator=operator, order_id=sale_id), db)
                elif data.status == OrderStatus.COMPLETED and current.status == OrderStatus.CANCELLED:
                    dispatch(RestoreSaleOrder(account_id=account_id, operator=operator, order_id=sale_id), db)

                        # 4) 普通字段 → UpdateSaleOrderFields
            #    有 items 时 status 也作为普通字段设置（只 setattr，不做库存联动）
            field_kwargs = {}
            for k in ('customer_id', 'payment_status', 'notes', 'image_url'):
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
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message=str(e))

    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": sale_id})
    db.refresh(order)
    
    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.SALE_ORDER,
        entity_id=order.id,
        summary=f"销售单 {order.order_no} 更新成功",
        ai_hint="销售单已更新。",
        data=_build_sale_out(order, invoiced=linkage_has_invoice(db, account_id, "sale_order", order.id)).model_dump()
    )
    return result.to_dict()


@router.delete("/{sale_id}")
def delete_sale(sale_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    order = db.query(SaleOrder).filter(
        SaleOrder.id == sale_id,
        SaleOrder.account_id == account_id
    ).first()
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": sale_id})
    if order.image_url:
        delete_old_image(order.image_url)
    with unit_of_work(db):
        dispatch(DeleteSaleOrder(account_id=account_id, operator=operator, order_id=sale_id), db)
    
    result = OperationResult(
        operation=OperationType.DELETE,
        entity_type=EntityType.SALE_ORDER,
        entity_id=sale_id,
        summary=f"销售单 {order.order_no} 删除成功",
        ai_hint="销售单已删除。",
        data={"sale_id": sale_id, "order_no": order.order_no}
    )
    return result.to_dict()