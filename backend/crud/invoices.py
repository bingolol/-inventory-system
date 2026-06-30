"""发票 CRUD（只读查询）

写操作已迁移至 commands 层（CreateInvoice/UpdateInvoice/DeleteInvoice）。
本模块仅保留 list/get 查询函数，供 routers 直接调用。
税务报表逻辑由 crud/finance/tax_declarations.py（aggregate_vat_invoices）
和 routers/tax.py（_calculate_tax_data）实现，单一真相源。
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
import models

logger = logging.getLogger("inventory")


def list_invoices(db: Session, account_id: int, skip: int = 0, limit: int = 100, direction: str = None, invoice_type: str = None, year: int = None, quarter: int = None):
    q = db.query(models.Invoice).filter(models.Invoice.account_id == account_id)
    if direction:
        q = q.filter(models.Invoice.direction == direction)
    if invoice_type:
        q = q.filter(models.Invoice.invoice_type == invoice_type)
    if year and quarter:
        quarter_start = datetime(year, (quarter - 1) * 3 + 1, 1)
        if quarter == 4:
            quarter_end = datetime(year + 1, 1, 1)
        else:
            quarter_end = datetime(year, quarter * 3 + 1, 1)
        q = q.filter(models.Invoice.issue_date >= quarter_start, models.Invoice.issue_date < quarter_end)
    total = q.count()
    items = q.order_by(models.Invoice.issue_date.desc()).offset(skip).limit(limit).all()
    return total, items


def get_invoice(db: Session, account_id: int, invoice_id: int):
    return db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.id == invoice_id
    ).first()
