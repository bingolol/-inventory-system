from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id, get_operator
import schemas, crud
from commands import dispatch, CreateSupplier, UpdateSupplier, DeleteSupplier
from uow import unit_of_work

router = APIRouter()


@router.get("")
def list_suppliers(page: int = 1, page_size: int = 20, search: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, items = crud.list_suppliers(db, account_id, skip=skip, limit=page_size, search=search)
    return {"total": total, "items": items}


@router.post("", response_model=schemas.SupplierOut)
def create_supplier(data: schemas.SupplierCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        s = dispatch(CreateSupplier(
            account_id=account_id,
            operator=operator,
            name=data.name,
            contact=data.contact,
            phone=data.phone,
            address=data.address,
            notes=data.notes,
        ), db)
    db.refresh(s)
    return s


@router.get("/{supplier_id}", response_model=schemas.SupplierOut)
def get_supplier(supplier_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    s = crud.get_supplier(db, account_id, supplier_id)
    if not s:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return s


@router.put("/{supplier_id}", response_model=schemas.SupplierOut)
def update_supplier(supplier_id: int, data: schemas.SupplierUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        s = dispatch(UpdateSupplier(
            account_id=account_id,
            operator=operator,
            supplier_id=supplier_id,
            name=data.name,
            contact=data.contact,
            phone=data.phone,
            address=data.address,
            notes=data.notes,
        ), db)
    if not s:
        raise HTTPException(status_code=404, detail="供应商不存在")
    db.refresh(s)
    return s


@router.delete("/{supplier_id}")
def delete_supplier(supplier_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            if not dispatch(DeleteSupplier(
                account_id=account_id,
                operator=operator,
                supplier_id=supplier_id,
            ), db):
                raise HTTPException(status_code=404, detail="供应商不存在")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
    return {"message": "已删除"}
