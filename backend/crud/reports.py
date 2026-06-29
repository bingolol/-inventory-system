"""统计报表"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
import models, schemas

from enums import OrderStatus
from utils import _d
from .products import get_stock_alerts


def get_overview(db: Session, account_id: int):
    total_products = db.query(models.Product).filter(models.Product.account_id == account_id).count()

    inv_data = db.query(models.Inventory).filter(models.Inventory.account_id == account_id).all()
    # 单一真相源：库存价值读 Inventory.total_value（引擎维护的移动加权平均缓存），
    # 禁止用 quantity × Product.purchase_price（主数据静态字段，不反映实际采购成本）
    total_stock_value = _d(sum(
        Decimal(str(inv.total_value)) if inv.total_value is not None else Decimal('0')
        for inv in inv_data
    ))
    positive_stock_count = sum(inv.quantity for inv in inv_data if (inv.quantity if inv.quantity is not None else 0) > 0)
    negative_stock_count = sum(abs(inv.quantity) for inv in inv_data if (inv.quantity if inv.quantity is not None else 0) < 0)
    total_inventory_quantity = positive_stock_count - negative_stock_count

    today = datetime.now().strftime("%Y-%m-%d")
    today_purchase_orders = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.purchase_date >= today,
        models.PurchaseOrder.status == OrderStatus.COMPLETED,
    ).all()
    today_sale_orders = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.sale_date >= today,
        models.SaleOrder.status == OrderStatus.COMPLETED,
    ).all()

    low_stock_count = len(get_stock_alerts(db, account_id))

    return schemas.ReportOverview(
        total_products=total_products,
        total_stock_value=round(total_stock_value, 2),
        total_inventory_quantity=total_inventory_quantity,
        positive_stock_count=positive_stock_count,
        negative_stock_count=negative_stock_count,
        today_purchase_count=len(today_purchase_orders),
        today_purchase_amount=round(_d(sum(o.total_price for o in today_purchase_orders)), 2),
        today_sale_count=len(today_sale_orders),
        today_sale_amount=round(_d(sum(o.total_price for o in today_sale_orders)), 2),
        low_stock_count=low_stock_count
    )


def get_purchase_report(db: Session, account_id: int, start_date: str = None, end_date: str = None):
    q = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.account_id == account_id,
        models.PurchaseOrder.status == OrderStatus.COMPLETED,
    )
    if start_date:
        q = q.filter(models.PurchaseOrder.purchase_date >= start_date)
    if end_date:
        q = q.filter(models.PurchaseOrder.purchase_date <= end_date + " 23:59:59")
    return q.order_by(models.PurchaseOrder.purchase_date.desc()).all()


def get_sale_report(db: Session, account_id: int, start_date: str = None, end_date: str = None):
    q = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.status == OrderStatus.COMPLETED,
    )
    if start_date:
        q = q.filter(models.SaleOrder.sale_date >= start_date)
    if end_date:
        q = q.filter(models.SaleOrder.sale_date <= end_date + " 23:59:59")
    return q.order_by(models.SaleOrder.sale_date.desc()).all()


def get_profit_report(db: Session, account_id: int, start_date: str = None, end_date: str = None):
    """利润报表：收入=所有销售单金额，成本=销售行项的出库成本合计

    成本 = Σ(SaleItem.quantity × SaleItem.unit_cost)，即移动加权平均出库成本（单一真相源）。
    禁止用 Product.purchase_price（主数据静态字段，不反映实际采购成本）。
    """
    from decimal import Decimal

    q_sale = db.query(models.SaleOrder).filter(
        models.SaleOrder.account_id == account_id,
        models.SaleOrder.status == OrderStatus.COMPLETED,
    )
    if start_date:
        q_sale = q_sale.filter(models.SaleOrder.sale_date >= start_date)
    if end_date:
        q_sale = q_sale.filter(models.SaleOrder.sale_date <= end_date + " 23:59:59")

    sale_orders = q_sale.all()

    # 收入 = 所有已完成销售单的 total_price
    total_revenue = _d(sum(Decimal(str(o.total_price or 0)) for o in sale_orders))

    # 成本 = 销售行项的 quantity × SaleItem.unit_cost（移动加权平均出库成本）
    total_cost = Decimal('0')
    for order in sale_orders:
        for item in order.items:
            # 单一真相源：读 SaleItem.unit_cost（出库时锁定的加权平均成本）
            unit_cost = Decimal(str(item.unit_cost)) if item.unit_cost else Decimal('0')
            total_cost += Decimal(str(item.quantity)) * unit_cost

    total_profit = total_revenue - total_cost

    return {
        "total_sale_amount": round(float(total_revenue), 2),
        "total_profit": round(float(total_profit), 2),
        "sale_count": len(sale_orders),
        "sale_orders": sale_orders,
        "total_revenue": round(float(total_revenue), 2),
        "total_cost": round(float(total_cost), 2),
    }


def get_trend(db: Session, account_id: int, days: int = 7):
    today = datetime.now().date()
    result = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        next_d = (d + timedelta(days=1)).strftime("%Y-%m-%d")
        purchase_amount = _d(sum(
            o.total_price for o in db.query(models.PurchaseOrder).filter(
                models.PurchaseOrder.account_id == account_id,
                models.PurchaseOrder.purchase_date >= d_str,
                models.PurchaseOrder.purchase_date < next_d,
                models.PurchaseOrder.status == OrderStatus.COMPLETED,
            ).all()
        ))
        sale_amount = _d(sum(
            o.total_price for o in db.query(models.SaleOrder).filter(
                models.SaleOrder.account_id == account_id,
                models.SaleOrder.sale_date >= d_str,
                models.SaleOrder.sale_date < next_d,
                models.SaleOrder.status == OrderStatus.COMPLETED,
            ).all()
        ))
        result.append({
            "date": d_str,
            "purchase_amount": round(purchase_amount, 2),
            "sale_amount": round(sale_amount, 2),
        })
    return result