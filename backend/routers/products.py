from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id, get_operator
import schemas, crud
from commands import dispatch, CreateProduct, UpdateProduct, DeleteProduct, AdjustInventory
from uow import unit_of_work
from errors import BusinessError, ErrorCode
from operation_result import OperationResult, EntityType, OperationType

router = APIRouter()


@router.get("")
def list_products(page: int = 1, page_size: int = 20, search: str = None, sku: str = None, category: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, items = crud.list_products(db, account_id, skip=skip, limit=page_size, search=search, sku=sku, category=category)
    result = []
    for p in items:
        inv = p.inventory
        result.append(schemas.ProductOut(
            id=p.id, name=p.name, sku=p.sku, category=p.category,
            unit=p.unit, purchase_price=p.purchase_price, sale_price=p.sale_price,
            min_stock=p.min_stock, track_inventory=p.track_inventory, description=p.description,
            created_at=p.created_at, updated_at=p.updated_at,
            current_stock=inv.quantity if inv else 0
        ))
    return {"total": total, "items": result}


@router.post("")
def create_product(data: schemas.ProductCreate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        product = dispatch(CreateProduct(
            account_id=account_id,
            operator=operator,
            name=data.name,
            sku=data.sku,
            category=data.category,
            unit=data.unit,
            purchase_price=data.purchase_price,
            sale_price=data.sale_price,
            min_stock=data.min_stock,
            track_inventory=data.track_inventory,
            description=data.description,
            initial_stock=data.initial_stock,
        ), db)
    db.refresh(product)
    inv = product.inventory
    
    # 返回 OperationResult 格式
    result = OperationResult(
        operation=OperationType.CREATE,
        entity_type=EntityType.PRODUCT,
        entity_id=product.id,
        summary=f"商品 {product.name} 创建成功，采购价 {product.purchase_price}，销售价 {product.sale_price}",
        ai_hint="商品已创建。如需采购入库，请调用 POST /api/purchases。",
        data={
            "id": product.id, "name": product.name, "sku": product.sku, "category": product.category,
            "unit": product.unit, "purchase_price": float(product.purchase_price), "sale_price": float(product.sale_price),
            "min_stock": product.min_stock, "track_inventory": product.track_inventory,
            "description": product.description,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
            "current_stock": inv.quantity if inv else 0
        }
    )
    return result.to_dict()


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
        raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
    inv = p.inventory
    return schemas.ProductOut(
        id=p.id, name=p.name, sku=p.sku, category=p.category,
        unit=p.unit, purchase_price=p.purchase_price, sale_price=p.sale_price,
        min_stock=p.min_stock, track_inventory=p.track_inventory, description=p.description,
        created_at=p.created_at, updated_at=p.updated_at,
        current_stock=inv.quantity if inv else 0
    )


@router.put("/{product_id}")
def update_product(product_id: int, data: schemas.ProductUpdate, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    with unit_of_work(db):
        p = dispatch(UpdateProduct(
            account_id=account_id,
            operator=operator,
            product_id=product_id,
            name=data.name,
            sku=data.sku,
            category=data.category,
            unit=data.unit,
            purchase_price=data.purchase_price,
            sale_price=data.sale_price,
            min_stock=data.min_stock,
            track_inventory=data.track_inventory,
            description=data.description,
        ), db)
    if not p:
        raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
    db.refresh(p)
    inv = p.inventory
    
    result = OperationResult(
        operation=OperationType.UPDATE,
        entity_type=EntityType.PRODUCT,
        entity_id=p.id,
        summary=f"商品 {p.name} 更新成功",
        ai_hint="商品已更新。",
        data={"id": p.id, "name": p.name, "purchase_price": float(p.purchase_price), "sale_price": float(p.sale_price)}
    )
    return result.to_dict()


@router.delete("/{product_id}")
def delete_product(product_id: int, account_id: int = Depends(get_account_id), operator: str = Depends(get_operator), db: Session = Depends(get_db)):
    # 先获取商品信息用于返回
    product = crud.get_product(db, account_id, product_id)
    if not product:
        raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
    
    with unit_of_work(db):
        if not dispatch(DeleteProduct(
            account_id=account_id,
            operator=operator,
            product_id=product_id,
        ), db):
            raise BusinessError(code=ErrorCode.PRODUCT_NOT_FOUND, data={"product_id": product_id})
    
    result = OperationResult(
        operation=OperationType.DELETE,
        entity_type=EntityType.PRODUCT,
        entity_id=product_id,
        summary=f"商品 {product.name} 删除成功",
        ai_hint="商品已删除。",
        data={"product_id": product_id, "name": product.name}
    )
    return result.to_dict()
