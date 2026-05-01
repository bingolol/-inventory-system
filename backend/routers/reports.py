from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from database import get_db
from account_dep import get_account_id
import schemas, crud

Q2 = Decimal('0.01')

def _d(val):
    """安全转换为 Decimal"""
    if val is None:
        return Decimal('0')
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))

router = APIRouter()


@router.get("/overview", response_model=schemas.ReportOverview)
def get_overview(account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    return crud.get_overview(db, account_id)


@router.get("/purchase")
def get_purchase_report(start_date: str = None, end_date: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    orders = crud.get_purchase_report(db, account_id, start_date, end_date)
    result = []
    for o in orders:
        items = []
        for item in o.items:
            items.append({
                "id": item.id, "product_id": item.product_id,
                "product_name": item.product.name if item.product else None,
                "quantity": item.quantity, "unit_price": item.unit_price,
                "total_price": item.total_price
            })
        result.append({
            "id": o.id, "order_no": o.order_no,
            "supplier_name": o.supplier.name if o.supplier else None,
            "total_price": o.total_price, "status": o.status,
            "purchase_date": o.purchase_date.isoformat() if o.purchase_date else None,
            "notes": o.notes, "items": items
        })
    total = sum((_d(o.total_price) for o in orders), Decimal('0'))
    return {"total_amount": total.quantize(Q2), "count": len(orders), "items": result}


@router.get("/sale")
def get_sale_report(start_date: str = None, end_date: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    orders = crud.get_sale_report(db, account_id, start_date, end_date)
    result = []
    for o in orders:
        items = []
        for item in o.items:
            items.append({
                "id": item.id, "product_id": item.product_id,
                "product_name": item.product.name if item.product else None,
                "quantity": item.quantity, "unit_price": item.unit_price,
                "total_price": item.total_price
            })
        result.append({
            "id": o.id, "order_no": o.order_no,
            "customer_name": o.customer.name if o.customer else "散客",
            "total_price": o.total_price, "status": o.status,
            "sale_date": o.sale_date.isoformat() if o.sale_date else None,
            "notes": o.notes, "items": items
        })
    total = sum((_d(o.total_price) for o in orders), Decimal('0'))
    return {"total_amount": total.quantize(Q2), "count": len(orders), "items": result}


@router.get("/profit")
def get_profit_report(start_date: str = None, end_date: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    return crud.get_profit_report(db, account_id, start_date, end_date)


@router.get("/trend")
def get_trend(days: int = 7, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    return crud.get_trend(db, account_id, days)


@router.get("/tax-report", response_model=schemas.TaxReport)
def get_tax_report(year: int, quarter: int, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    if quarter < 1 or quarter > 4:
        raise HTTPException(status_code=400, detail="季度必须在 1-4 之间")
    return crud.get_tax_report(db, account_id, year, quarter)


@router.get("/project")
def get_project_report(project_id: int = None, start_date: str = None, end_date: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    """获取项目报表"""
    return crud.get_project_report(db, account_id, project_id, start_date, end_date)