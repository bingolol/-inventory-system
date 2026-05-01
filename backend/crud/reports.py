"""统计报表"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
import models, schemas

from .products import get_stock_alerts


def get_overview(db: Session, account_id: int):
    total_products = db.query(models.Product).filter(models.Product.account_id == account_id).count()

    inv_data = db.query(models.Inventory).filter(models.Inventory.account_id == account_id).all()
    total_stock_value = sum(
        max(inv.quantity or 0, 0) * (inv.product.purchase_price or 0)
        for inv in inv_data
    )
    positive_stock_count = sum(inv.quantity for inv in inv_data if (inv.quantity or 0) > 0)
    negative_stock_count = sum(abs(inv.quantity) for inv in inv_data if (inv.quantity or 0) < 0)
    total_inventory_quantity = positive_stock_count - negative_stock_count

    today = datetime.now().strftime("%Y-%m-%d")
    today_purchase_orders = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.purchase_date >= today,
        models.PurchaseOrder.status == "completed"
    ).all()
    today_sale_orders = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= today,
        models.SaleOrder.status == "completed"
    ).all()

    low_stock_count = len(get_stock_alerts(db, account_id))

    return schemas.ReportOverview(
        total_products=total_products,
        total_stock_value=round(total_stock_value, 2),
        total_inventory_quantity=total_inventory_quantity,
        positive_stock_count=positive_stock_count,
        negative_stock_count=negative_stock_count,
        today_purchase_count=len(today_purchase_orders),
        today_purchase_amount=round(sum(o.total_price for o in today_purchase_orders), 2),
        today_sale_count=len(today_sale_orders),
        today_sale_amount=round(sum(o.total_price for o in today_sale_orders), 2),
        low_stock_count=low_stock_count
    )


def get_purchase_report(db: Session, account_id: int, start_date: str = None, end_date: str = None):
    q = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.status == "completed"
    )
    if start_date:
        q = q.filter(models.PurchaseOrder.purchase_date >= start_date)
    if end_date:
        q = q.filter(models.PurchaseOrder.purchase_date <= end_date + " 23:59:59")
    return q.order_by(models.PurchaseOrder.purchase_date.desc()).all()


def get_sale_report(db: Session, account_id: int, start_date: str = None, end_date: str = None):
    q = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.status == "completed"
    )
    if start_date:
        q = q.filter(models.SaleOrder.sale_date >= start_date)
    if end_date:
        q = q.filter(models.SaleOrder.sale_date <= end_date + " 23:59:59")
    return q.order_by(models.SaleOrder.sale_date.desc()).all()


def get_profit_report(db: Session, account_id: int, start_date: str = None, end_date: str = None):
    q_purchase = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.status == "completed"
    )
    q_sale = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.status == "completed"
    )
    if start_date:
        q_purchase = q_purchase.filter(models.PurchaseOrder.purchase_date >= start_date)
        q_sale = q_sale.filter(models.SaleOrder.sale_date >= start_date)
    if end_date:
        q_purchase = q_purchase.filter(models.PurchaseOrder.purchase_date <= end_date + " 23:59:59")
        q_sale = q_sale.filter(models.SaleOrder.sale_date <= end_date + " 23:59:59")

    purchase_orders = q_purchase.all()
    sale_orders = q_sale.all()

    total_purchase = sum(o.total_price for o in purchase_orders)
    total_sale = sum(o.total_price for o in sale_orders)

    return {
        "total_purchase_amount": round(total_purchase, 2),
        "total_sale_amount": round(total_sale, 2),
        "total_profit": round(total_sale - total_purchase, 2),
        "purchase_count": len(purchase_orders),
        "sale_count": len(sale_orders),
        "purchase_orders": purchase_orders,
        "sale_orders": sale_orders,
    }


def get_trend(db: Session, account_id: int, days: int = 7):
    today = datetime.now().date()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        next_d = (d + timedelta(days=1)).strftime("%Y-%m-%d")
        purchase_amount = sum(
            o.total_price for o in db.query(models.PurchaseOrder).filter(
                models.PurchaseOrder.account_id == account_id,
                models.PurchaseOrder.purchase_date >= d_str,
                models.PurchaseOrder.purchase_date < next_d,
                models.PurchaseOrder.status == "completed"
            ).all()
        )
        sale_amount = sum(
            o.total_price for o in db.query(models.SaleOrder).filter(
                models.SaleOrder.account_id == account_id,
                models.SaleOrder.sale_date >= d_str,
                models.SaleOrder.sale_date < next_d,
                models.SaleOrder.status == "completed"
            ).all()
        )
        result.append({
            "date": d_str,
            "purchase_amount": round(purchase_amount, 2),
            "sale_amount": round(sale_amount, 2),
        })
    return result