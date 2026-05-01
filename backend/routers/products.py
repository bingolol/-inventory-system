from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
import schemas, crud
from uow import unit_of_work

router = APIRouter()


@router.get("/")
def list_products(page: int = 1, page_size: int = 20, search: str = None, sku: str = None, category: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, items = crud.list_products(db, account_id, skip=skip, limit=page_size, search=search, sku=sku, category=category)
    result = []
    for p in items:
        inv = p.inventory
        result.append(schemas.ProductOut(
            id=p.id, name=p.name, sku=p.sku, category=p.category,
            unit=p.unit, purchase_price=p.purchase_price, sale_price=p.sale_price,
            min_stock=p.min_stock, description=p.description,
            created_at=p.created_at, updated_at=p.updated_at,
            current_stock=inv.quantity if inv else 0
        ))
    return {"total": total, "items": result}


@router.post("/", response_model=schemas.ProductOut)
def create_product(data: schemas.ProductCreate, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    with unit_of_work(db):
        product = crud.create_product(db, account_id, data)
    db.refresh(product)
    inv = product.inventory
    return schemas.ProductOut(
        id=product.id, name=product.name, sku=product.sku, category=product.category,
        unit=product.unit, purchase_price=product.purchase_price, sale_price=product.sale_price,
        min_stock=product.min_stock, description=product.description,
        created_at=product.created_at, updated_at=product.updated_at,
        current_stock=inv.quantity if inv else 0
    )


@router.get("/categories/list")
def list_categories(account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    import models
    from sqlalchemy import distinct
    categories = db.query(distinct(models.Product.category)).filter(
        models.Product.account_id == account_id,
        models.Product.category != ""
    ).all()
    return [c[0] for c in categories]


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    p = crud.get_product(db, account_id, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="商品不存在")
    inv = p.inventory
    return schemas.ProductOut(
        id=p.id, name=p.name, sku=p.sku, category=p.category,
        unit=p.unit, purchase_price=p.purchase_price, sale_price=p.sale_price,
        min_stock=p.min_stock, description=p.description,
        created_at=p.created_at, updated_at=p.updated_at,
        current_stock=inv.quantity if inv else 0
    )


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, data: schemas.ProductUpdate, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    with unit_of_work(db):
        p = crud.update_product(db, account_id, product_id, data)
    if not p:
        raise HTTPException(status_code=404, detail="商品不存在")
    db.refresh(p)
    inv = p.inventory
    return schemas.ProductOut(
        id=p.id, name=p.name, sku=p.sku, category=p.category,
        unit=p.unit, purchase_price=p.purchase_price, sale_price=p.sale_price,
        min_stock=p.min_stock, description=p.description,
        created_at=p.created_at, updated_at=p.updated_at,
        current_stock=inv.quantity if inv else 0
    )


@router.delete("/{product_id}")
def delete_product(product_id: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    with unit_of_work(db):
        try:
            if not crud.delete_product(db, account_id, product_id):
                raise HTTPException(status_code=404, detail="商品不存在")
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
    return {"message": "已删除"}