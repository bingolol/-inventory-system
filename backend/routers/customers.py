from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
import schemas, crud
from uow import unit_of_work

router = APIRouter()


@router.get("/")
def list_customers(page: int = 1, page_size: int = 20, search: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, items = crud.list_customers(db, account_id, skip=skip, limit=page_size, search=search)
    return {"total": total, "items": items}


@router.post("/", response_model=schemas.CustomerOut)
def create_customer(data: schemas.CustomerCreate, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    with unit_of_work(db):
        c = crud.create_customer(db, account_id, data)
    db.refresh(c)
    return c


@router.get("/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    c = crud.get_customer(db, account_id, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    return c


@router.put("/{customer_id}", response_model=schemas.CustomerOut)
def update_customer(customer_id: int, data: schemas.CustomerUpdate, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    with unit_of_work(db):
        c = crud.update_customer(db, account_id, customer_id, data)
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    db.refresh(c)
    return c


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            if not crud.delete_customer(db, account_id, customer_id):
                raise HTTPException(status_code=404, detail="客户不存在")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
    return {"message": "已删除"}