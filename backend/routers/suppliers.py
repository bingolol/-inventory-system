from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id, get_operator
from dependencies import Pagination
from schemas import PaginatedResponse
import schemas, crud
from commands import dispatch, CreatePartner, UpdatePartner, DeletePartner
from uow import unit_of_work
from errors import BusinessError, ErrorCode
from operation_result import OperationResult, EntityType, OperationType

router = APIRouter()


@router.get("")
def list_suppliers(pag: Pagination = Depends(), search: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    total, items = crud.list_suppliers(db, account_id, skip=pag.skip, limit=pag.limit, search=search)
    return PaginatedResponse(total=total, items=[schemas.SupplierOut.model_validate(s) for s in items])


@router.post("")
def create_supplier(data: schemas.SupplierCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        s = dispatch(CreatePartner(
            account_id=account_id,
            operator=operator,
            partner_type="supplier",
            name=data.name,
            contact=data.contact,
            phone=data.phone,
            address=data.address,
            notes=data.notes,
        ), db)
    db.refresh(s)
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.SUPPLIER,
        entity_id=s.id,
        summary=f"供应商 {s.name} 创建成功",
        ai_hint="供应商已创建。如需创建采购单，请调用 POST /api/purchases。",
        data={
            "id": s.id, "name": s.name, "contact": s.contact,
            "phone": s.phone, "address": s.address, "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
    )
    return result.to_dict()


@router.get("/{supplier_id}", response_model=schemas.SupplierOut)
def get_supplier(supplier_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    return crud.get_supplier(db, account_id, supplier_id)


@router.put("/{supplier_id}")
def update_supplier(supplier_id: int, data: schemas.SupplierUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        s = dispatch(UpdatePartner(
            account_id=account_id,
            operator=operator,
            partner_type="supplier",
            partner_id=supplier_id,
            name=data.name,
            contact=data.contact,
            phone=data.phone,
            address=data.address,
            notes=data.notes,
        ), db)
    if not s:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "供应商", "order_id": supplier_id})
    db.refresh(s)
    
    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.SUPPLIER,
        entity_id=s.id,
        summary=f"供应商 {s.name} 更新成功",
        ai_hint="供应商已更新。",
        data={"id": s.id, "name": s.name, "contact": s.contact, "phone": s.phone}
    )
    return result.to_dict()


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    # 先获取供应商信息用于返回
    supplier = crud.get_supplier(db, account_id, supplier_id)
    if not supplier:
        raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "供应商", "order_id": supplier_id})
    
    with unit_of_work(db):
        if not dispatch(DeletePartner(
            account_id=account_id,
            operator=operator,
            partner_type="supplier",
            partner_id=supplier_id,
        ), db):
            raise BusinessError(code=ErrorCode.ORDER_NOT_FOUND, data={"order_type": "供应商", "order_id": supplier_id})
    
    result = OperationResult(
        operation=OperationType.DELETE,
        entity_type=EntityType.SUPPLIER,
        entity_id=supplier_id,
        summary=f"供应商 {supplier.name} 删除成功",
        ai_hint="供应商已删除。",
        data={"supplier_id": supplier_id, "name": supplier.name}
    )
    return result.to_dict()
