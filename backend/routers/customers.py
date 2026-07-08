from fastapi import APIRouter, Depends
from errors import BusinessError, ErrorCode, ActionType
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id, get_operator
from dependencies import Pagination
from schemas import PaginatedResponse
import schemas, crud
from commands import dispatch, CreatePartner, UpdatePartner, DeletePartner
from uow import unit_of_work
from operation_result import OperationResult, EntityType, OperationType

router = APIRouter()


@router.get("")
def list_customers(pag: Pagination = Depends(), search: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    total, items = crud.list_customers(db, account_id, skip=pag.skip, limit=pag.limit, search=search)
    return PaginatedResponse(total=total, items=[schemas.CustomerOut.model_validate(c) for c in items])


@router.post("")
def create_customer(data: schemas.CustomerCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        c = dispatch(CreatePartner(
            account_id=account_id,
            operator=operator,
            partner_type="customer",
            name=data.name,
            contact=data.contact,
            phone=data.phone,
            address=data.address,
            notes=data.notes,
        ), db)
    db.refresh(c)
    
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.CUSTOMER,
        entity_id=c.id,
        summary=f"客户 {c.name} 创建成功",
        ai_hint="客户已创建。如需创建销售单，请调用 POST /api/sales。",
        data={"id": c.id, "name": c.name, "contact": c.contact, "phone": c.phone}
    )
    return result.to_dict()


@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    return crud.get_customer(db, account_id, customer_id)


@router.put("/{customer_id}")
def update_customer(customer_id: int, data: schemas.CustomerUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        c = dispatch(UpdatePartner(
            account_id=account_id,
            operator=operator,
            partner_type="customer",
            partner_id=customer_id,
            name=data.name,
            contact=data.contact,
            phone=data.phone,
            address=data.address,
            notes=data.notes,
        ), db)
    if not c:
        raise BusinessError(code=ErrorCode.CUSTOMER_NOT_FOUND, data={"customer_id": customer_id})
    db.refresh(c)
    
    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.CUSTOMER,
        entity_id=c.id,
        summary=f"客户 {c.name} 更新成功",
        ai_hint="客户已更新。",
        data={"id": c.id, "name": c.name, "contact": c.contact, "phone": c.phone}
    )
    return result.to_dict()


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    # 先获取客户信息用于返回
    customer = crud.get_customer(db, account_id, customer_id)
    if not customer:
        raise BusinessError(code=ErrorCode.CUSTOMER_NOT_FOUND, data={"customer_id": customer_id})
    
    with unit_of_work(db):
        if not dispatch(DeletePartner(
            account_id=account_id,
            operator=operator,
            partner_type="customer",
            partner_id=customer_id,
        ), db):
            raise BusinessError(code=ErrorCode.CUSTOMER_NOT_FOUND, data={"customer_id": customer_id})
    
    result = OperationResult(
        operation=OperationType.DELETE,
        entity_type=EntityType.CUSTOMER,
        entity_id=customer_id,
        summary=f"客户 {customer.name} 删除成功",
        ai_hint="客户已删除。",
        data={"customer_id": customer_id, "name": customer.name}
    )
    return result.to_dict()
