"""统一单号生成器

所有单据编号的单一真相源。消除 crud/base.py 和 crud/personal_advances.py 中
重复实现的模式，未来新增单据类型只需注册前缀即可。
"""

from datetime import datetime
from sqlalchemy.orm import Session


def next_order_no(db: Session, prefix: str, business_date: datetime) -> str:
    """生成采购/销售订单号

    格式: {中文前缀}{年}—{月}-{日}-{时}:{分}-{序号}
    例: CG2026—2-17-20:01-01
    """
    import models

    prefix_map = {"PO": "CG", "PL": "RG", "SO": "XS", "PS": "XS"}
    cn_prefix = prefix_map.get(prefix, prefix)

    dt = business_date
    date_part = f"{dt.year}—{dt.month}-{dt.day}"
    time_part = f"{dt.hour:02d}:{dt.minute:02d}"
    pattern = f"{cn_prefix}{dt.year}—{dt.month}-{dt.day}-{dt.hour:02d}:{dt.minute:02d}-%"
    model = models.PurchaseOrder if prefix in ("PO", "PL") else models.SaleOrder
    count = db.query(model).filter(model.order_no.like(pattern)).count()
    return f"{cn_prefix}{date_part}-{time_part}-{count + 1:02d}"


def next_advance_no(db: Session, account_id: int) -> str:
    """生成垫付单号: PA-YYYY-NNNN（账本内年度递增）"""
    import models

    year = datetime.now().year
    pattern = f"PA-{year}-%"
    count = db.query(models.PersonalAdvance).filter(
        models.PersonalAdvance.account_id == account_id,
        models.PersonalAdvance.advance_no.like(pattern)
    ).count()
    return f"PA-{year}-{count + 1:04d}"


def next_invoice_no(db: Session, account_id: int) -> str:
    """生成发票号: INV-YYYY-NNNN（账本内年度递增）"""
    import models

    year = datetime.now().year
    pattern = f"INV-{year}-%"
    count = db.query(models.Invoice).filter(
        models.Invoice.account_id == account_id,
        models.Invoice.invoice_no.like(pattern)
    ).count()
    return f"INV-{year}-{count + 1:04d}"
