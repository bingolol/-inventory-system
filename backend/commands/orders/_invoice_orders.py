"""发票自动生单 — 从 _invoice.py 拆分出来的独立模块

职责：根据进项/销项发票自动生成采购单/销售单。
避免 _invoice.py 同时承载"发票命令"与"订单生成"两种职责。
"""

from typing import Any, List

import models
from schemas.order import PurchaseItemCreate, SaleItemCreate

from ._lifecycle import OrderLifecycle


def _auto_generate_sale_order(db: Any, account_id: int, operator: str,
                              invoice: models.Invoice, items: List[dict]) -> models.SaleOrder:
    """根据销项发票自动生成销售单。"""
    customer = db.query(models.Customer).filter(
        models.Customer.account_id == account_id,
        models.Customer.name == invoice.counterparty_name,
    ).first()
    if not customer and invoice.counterparty_name:
        customer = models.Customer(
            account_id=account_id, name=invoice.counterparty_name,
            contact="", phone="",
        )
        db.add(customer)
        db.flush()
    customer_id = customer.id if customer else None
    order_items = [SaleItemCreate(**it).to_orm_kwargs() for it in items]
    return OrderLifecycle.create_sale_order(
        db=db, account_id=account_id, operator=operator,
        items=order_items, sale_date=invoice.issue_date_l1,
        customer_id=customer_id,
        total_price=invoice.amount_with_tax_l1,
        tax_amount=invoice.tax_amount_l1,
        has_invoice=True,
        notes=f"由发票 {invoice.invoice_no} 自动生成",
        auto_generated_from=invoice.invoice_no,
    )


def _auto_generate_purchase_order(db: Any, account_id: int, operator: str,
                                  invoice: models.Invoice, items: List[dict]) -> models.PurchaseOrder:
    """根据进项发票自动生成采购单。"""
    supplier_id = None
    supplier = db.query(models.Supplier).filter(
        models.Supplier.account_id == account_id,
        models.Supplier.name == invoice.counterparty_name,
    ).first()
    if supplier:
        supplier_id = supplier.id
    order_items = [PurchaseItemCreate(**it).to_orm_kwargs() for it in items]
    return OrderLifecycle.create_purchase_order(
        db=db, account_id=account_id, operator=operator,
        items=order_items, purchase_date=invoice.issue_date_l1,
        supplier_id=supplier_id,
        total_price=invoice.amount_with_tax_l1,
        tax_amount=invoice.tax_amount_l1,
        notes=f"由发票 {invoice.invoice_no} 自动生成",
        auto_generated_from=invoice.invoice_no,
    )
