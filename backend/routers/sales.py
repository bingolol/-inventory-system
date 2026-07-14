from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import SaleOrder
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
    CancelOrder, RestoreOrder,
    DeleteOrder, UpdateOrderItems,
    UpdateOrderFields, ReturnOrder,
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
            quantity=item.quantity_l1,
            unit_price=item.unit_price_l1,
            tax_rate=item.tax_rate_l1,
            total_price=item.total_price_l1,
            notes=item.notes or "",
        ))
    return schemas.SaleOrderOut(
        id=order.id,
        order_no=order.order_no,
        customer_id=order.customer_id,
        customer_name=order.customer.name if order.customer else "散客",
        order_type=order.order_type if order.order_type is not None else OrderType.RETAIL,
        total_price=order.total_price_l1,
        has_invoice=invoiced,
        payment_status=order.payment_status,
        status=order.status,
        notes=order.notes,
        image_url=order.image_url or "",
        business_date=order.sale_date_l1,
        created_at=order.created_at,
        items=items
    )


@router.get("")
def list_sales(pag: Pagination = Depends(), date_range: DateRange = Depends(), status: str = None, order_type: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    total, orders = crud.list_sale_orders(db, account_id, skip=pag.skip, limit=pag.limit, start_date=date_range.start, end_date=date_range.end, status=status, order_type=order_type)
    # 批量派生查询:哪些销售单有发票关联(单一真相源)
    invoiced_ids = bulk_has_invoice(db, account_id, "sale_order", [o.id for o in orders])
    result = []
    for order in orders:
        result.append(_build_sale_out(order, invoiced=(order.id in invoiced_ids)))
    return PaginatedResponse(total=total, items=result)


@router.post("")
def create_sale(data: schemas.SaleOrderCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    """POST /api/sales 已停用：系统只允许开票订单录入。

    架构改造后，销售业务必须通过 POST /api/invoices（direction='out',
    sale_order_action='auto_create'）创建发票，由发票驱动自动生成销售单。
    这确保发票是唯一真相源，增值税口径与会计口径统一，不存在无票收入兜底。
    """
    raise BusinessError(
        code=ErrorCode.VALIDATION_ERROR,
        message=(
            "POST /api/sales 已停用：系统只允许开票订单录入。"
            "请通过 POST /api/invoices 创建销项发票（direction='out', sale_order_action='auto_create'），"
            "由发票驱动自动生成销售单。"
        ),
        ai_instruction=(
            "STOP_RETRYING. POST /api/sales 已被禁用。"
            "请改用 POST /api/invoices，body 中设置 direction='out', sale_order_action='auto_create'。"
        ),
    )


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
                items_dicts = [item.to_orm_kwargs() for item in data.items]
                cmd = UpdateOrderItems(
                    order_type="sale",
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
                    dispatch(CancelOrder(order_type="sale", account_id=account_id, operator=operator, order_id=sale_id), db)
                elif data.status == OrderStatus.COMPLETED and current.status == OrderStatus.CANCELLED:
                    dispatch(RestoreOrder(order_type="sale", account_id=account_id, operator=operator, order_id=sale_id), db)

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
                dispatch(UpdateOrderFields(
                    order_type="sale",
                    account_id=account_id,
                    operator=operator,
                    order_id=sale_id,
                    **field_kwargs
                ), db)

            # 获取最新 order 对象
            if order is None:
                order = crud.get_sale_order(db, account_id, sale_id)
        except ValueError as e:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "更新销售单失败，请检查输入数据"})

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


@router.post("/{sale_id}/cancel")
def cancel_sale(
    sale_id: int,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """取消销售单（BR-19：保留审计轨迹+冲红凭证+回退库存，不物理删除）

    取代 DELETE /api/sales/{id}，避免直接删除已完成订单导致总账/库存不一致。
    内部调用 CancelSaleOrder 命令，与 PUT /{id} (status=cancelled) 走同一逻辑。
    """
    with unit_of_work(db):
        try:
            order = dispatch(CancelOrder(
                order_type="sale",
                account_id=account_id,
                operator=operator,
                order_id=sale_id,
            ), db)
        except ValueError as e:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, data={"details": "取消销售单失败，请检查状态"})

    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": sale_id})
    db.refresh(order)

    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.SALE_ORDER,
        entity_id=order.id,
        summary=f"销售单 {order.order_no} 已取消（冲红凭证+回退库存）",
        ai_hint="销售单已取消，关联凭证和库存已冲红/回退，记录保留以备审计。",
        data=_build_sale_out(order, invoiced=linkage_has_invoice(db, account_id, "sale_order", order.id)).model_dump(),
    )
    return result.to_dict()


@router.post("/{sale_id}/return")
def return_sale(
    sale_id: int,
    data: schemas.SaleReturnCreate,
    account_id: int = Depends(get_account_id),
    operator: str = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """销售退货（部分冲红，保留原单状态）

    支持多次部分退货：每次退货生成独立的冲红凭证 + 反向 StockMove，
    使用纳秒时间戳作 source_id 避免幂等冲突。

    - 库存：InventoryEngine.reverse 回补指定数量（自动取原销售 unit_cost）
    - 凭证：按退货比例计算收入/税额/成本冲红（move_type=sale_return）
    - 收款：不自动冲销（如需退款，调用 /api/receipts/{id}/reverse）
    """
    items = [{"product_id": it.product_id, "quantity": it.quantity} for it in data.items]
    with unit_of_work(db):
        order = dispatch(ReturnOrder(
            order_type="sale",
            account_id=account_id,
            operator=operator,
            order_id=sale_id,
            return_date=data.return_date,
            reason=data.reason,
            items=items,
        ), db)

    if not order:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "销售单", "order_id": sale_id})
    db.refresh(order)

    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.SALE_ORDER,
        entity_id=order.id,
        summary=f"销售单 {order.order_no} 部分退货 {len(items)} 项",
        ai_hint="销售退货已记账，原单状态保留。库存回补 + 收入/成本冲红已生成。",
        data=_build_sale_out(order, invoiced=linkage_has_invoice(db, account_id, "sale_order", order.id)).model_dump(),
    )
    return result.to_dict()


@router.delete("/{sale_id}")
def delete_sale(sale_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    order = get_or_404(db, SaleOrder, sale_id, account_id)
    if order.image_url:
        delete_old_image(order.image_url)
    with unit_of_work(db):
        dispatch(DeleteOrder(order_type="sale", account_id=account_id, operator=operator, order_id=sale_id), db)
    
    result = OperationResult(
        operation=OperationType.DELETE,
        entity_type=EntityType.SALE_ORDER,
        entity_id=sale_id,
        summary=f"销售单 {order.order_no} 删除成功",
        ai_hint="销售单已删除。",
        data={"sale_id": sale_id, "order_no": order.order_no}
    )
    return result.to_dict()