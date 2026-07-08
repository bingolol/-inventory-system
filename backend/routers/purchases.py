from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import PurchaseOrder
from errors import BusinessError, ErrorCode
from account_dep import get_account_id, get_operator
from dependencies import Pagination, DateRange
from utils import get_or_404
from image_utils import delete_old_image
import schemas, crud
from schemas import PaginatedResponse
from uow import unit_of_work
from commands.base import dispatch
from commands.orders import (
    CreateOrder, CancelOrder,
    DeleteOrder, UpdateOrderItems,
    UpdateOrderFields, ReturnOrder,
)
from enums import OrderStatus, OrderType
from operation_result import OperationResult, EntityType, OperationType
from crud.invoice_linkage import has_invoice as linkage_has_invoice, bulk_has_invoice

router = APIRouter()


def _build_purchase_out(order, invoiced: bool = False):
    items = []
    for item in order.items:
        items.append(schemas.PurchaseItemOut(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product.name if item.product else None,
            quantity=item.quantity_l1,
            unit_price=item.unit_price_l1,
            tax_rate=item.tax_rate_l1,
            total_price=item.total_price_l1,
            notes=item.notes or "",
        ))
    return schemas.PurchaseOrderOut(
        id=order.id,
        order_no=order.order_no,
        supplier_id=order.supplier_id,
        supplier_name=order.supplier.name if order.supplier else None,
        order_type=order.order_type if order.order_type is not None else OrderType.RETAIL,
        total_price=order.total_price_l1,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        status=order.status,
        notes=order.notes,
        image_url=order.image_url or "",
        purchase_date=order.purchase_date_l1,
        created_at=order.created_at,
        items=items
    )


@router.get("")
def list_purchases(pag: Pagination = Depends(), date_range: DateRange = Depends(), status: str = None, keyword: str = None, order_type: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    total, orders = crud.list_purchase_orders(db, account_id, skip=pag.skip, limit=pag.limit, start_date=date_range.start, end_date=date_range.end, status=status, keyword=keyword, order_type=order_type)
    # 批量派生查询:哪些采购单有发票关联(单一真相源)
    invoiced_ids = bulk_has_invoice(db, account_id, "purchase_order", [o.id for o in orders])
    result = []
    for order in orders:
        result.append(_build_purchase_out(order, invoiced=(order.id in invoiced_ids)))
    return PaginatedResponse(total=total, items=result)


@router.post("")
def create_purchase(data: schemas.PurchaseOrderCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            cmd = CreateOrder(
                order_type="purchase",
                account_id=account_id,
                operator=operator,
                supplier_id=data.supplier_id,
                purchase_date=data.purchase_date,
                payment_method=data.payment_method,
                notes=data.notes,
                image_url=data.image_url or "",
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
            "quantity": f"+{item.quantity_l1}"
        })
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.PURCHASE_ORDER,
        entity_id=order.id,
        summary=f"采购单 {order.order_no} 创建成功，金额 {order.total_price_l1}，商品数量 {len(order.items)}",
        ai_hint="采购单已创建，库存已增加。如需付款，请调用 POST /api/payments。",
        data=_build_purchase_out(order, invoiced=linkage_has_invoice(db, account_id, "purchase_order", order.id)).model_dump(),
        changes={
            "inventory": inventory_changes,
            "payable": {"amount": f"+{order.total_price_l1}"}
        }
    )
    return result.to_dict()


@router.get("/{purchase_id}", response_model=schemas.PurchaseOrderOut)
def get_purchase(purchase_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    order = crud.get_purchase_order(db, account_id, purchase_id)
    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": purchase_id})
    return _build_purchase_out(order, invoiced=linkage_has_invoice(db, account_id, "purchase_order", order.id))


@router.put("/{purchase_id}")
def update_purchase(purchase_id: int, data: schemas.PurchaseOrderUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            order = None
            has_items = data.items is not None

            # 1) items 全量替换 → UpdatePurchaseOrderItems
            if has_items:
                items_dicts = [item.model_dump() for item in data.items]
                cmd = UpdateOrderItems(
                    order_type="purchase",
                    account_id=account_id,
                    operator=operator,
                    order_id=purchase_id,
                    items=items_dicts,
                    supplier_id=data.supplier_id,
                    payment_method=data.payment_method,
                    notes=data.notes,
                    status=data.status,
                )
                order = dispatch(cmd, db)
                if order is None:
                    # items 为空 → 自动删除
                    raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单"})

            # 2) 无 items 时的状态切换 → Cancel
            if not has_items and data.status is not None:
                current = crud.get_purchase_order(db, account_id, purchase_id)
                if not current:
                    raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单"})
                if data.status == OrderStatus.CANCELLED and current.status != OrderStatus.CANCELLED:
                    dispatch(CancelOrder(order_type="purchase", account_id=account_id, operator=operator, order_id=purchase_id), db)

            # 3) 普通字段 → UpdatePurchaseOrderFields
            field_kwargs = {}
            for k in ('supplier_id', 'payment_method', 'payment_status', 'notes', 'image_url'):
                v = getattr(data, k, None)
                if v is not None:
                    field_kwargs[k] = v
            if has_items and data.status is not None:
                field_kwargs['status'] = data.status
            if not has_items and data.status is not None and data.status != OrderStatus.CANCELLED:
                field_kwargs['status'] = data.status
            if field_kwargs:
                dispatch(UpdateOrderFields(
                    order_type="purchase",
                    account_id=account_id,
                    operator=operator,
                    order_id=purchase_id,
                    **field_kwargs
                ), db)

            # 获取最新 order 对象
            if order is None:
                order = crud.get_purchase_order(db, account_id, purchase_id)
        except ValueError as e:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message=str(e))

    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": purchase_id})
    db.refresh(order)
    
    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.PURCHASE_ORDER,
        entity_id=order.id,
        summary=f"采购单 {order.order_no} 更新成功",
        ai_hint="采购单已更新。",
        data=_build_purchase_out(order, invoiced=linkage_has_invoice(db, account_id, "purchase_order", order.id)).model_dump()
    )
    return result.to_dict()


@router.post("/{purchase_id}/cancel")
def cancel_purchase(
    purchase_id: int,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """取消采购单（BR-19：保留审计轨迹+冲红凭证+回退库存，不物理删除）

    取代 DELETE /api/purchases/{id}，避免直接删除已完成订单导致总账/库存不一致。
    内部调用 CancelPurchaseOrder 命令。
    """
    with unit_of_work(db):
        try:
            order = dispatch(CancelOrder(
                order_type="purchase",
                account_id=account_id,
                operator=operator,
                order_id=purchase_id,
            ), db)
        except ValueError as e:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "取消采购单失败，请检查状态"})

    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": purchase_id})
    db.refresh(order)

    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.PURCHASE_ORDER,
        entity_id=order.id,
        summary=f"采购单 {order.order_no} 已取消（冲红凭证+回退库存）",
        ai_hint="采购单已取消，关联凭证和库存已冲红/回退，记录保留以备审计。",
        data=_build_purchase_out(order, invoiced=linkage_has_invoice(db, account_id, "purchase_order", order.id)).model_dump(),
    )
    return result.to_dict()


@router.post("/{purchase_id}/return")
def return_purchase(
    purchase_id: int,
    data: schemas.PurchaseReturnCreate,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """采购退货（部分冲红，保留原单状态）

    支持多次部分退货：每次退货生成独立的冲红凭证 + 反向 StockMove。

    - 库存：InventoryEngine.reverse 退回指定数量（自动取原采购 unit_cost）
    - 凭证：按退货比例计算应付/库存/进项税额转出（move_type=purchase_return）
    - 付款：不自动冲销（如需退款，调用 /api/payments/{id}/reverse）
    """
    items = [{"product_id": it.product_id, "quantity": it.quantity} for it in data.items]
    with unit_of_work(db):
        order = dispatch(ReturnOrder(
            order_type="purchase",
            account_id=account_id,
            operator=operator,
            order_id=purchase_id,
            return_date=data.return_date,
            reason=data.reason,
            items=items,
        ), db)

    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "采购单", "order_id": purchase_id})
    db.refresh(order)

    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.PURCHASE_ORDER,
        entity_id=order.id,
        summary=f"采购单 {order.order_no} 部分退货 {len(items)} 项",
        ai_hint="采购退货已记账，原单状态保留。库存退回 + 应付冲减 + 进项税额转出已生成。",
        data=_build_purchase_out(order, invoiced=linkage_has_invoice(db, account_id, "purchase_order", order.id)).model_dump(),
    )
    return result.to_dict()


@router.delete("/{purchase_id}")
def delete_purchase(purchase_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    order = get_or_404(db, PurchaseOrder, purchase_id, account_id)
    if order.image_url:
        delete_old_image(order.image_url)
    with unit_of_work(db):
        dispatch(DeleteOrder(order_type="purchase", account_id=account_id, operator=operator, order_id=purchase_id), db)
    
    result = OperationResult(
        operation=OperationType.DELETE,
        entity_type=EntityType.PURCHASE_ORDER,
        entity_id=purchase_id,
        summary=f"采购单 {order.order_no} 删除成功",
        ai_hint="采购单已删除。",
        data={"purchase_id": purchase_id, "order_no": order.order_no}
    )
    return result.to_dict()