"""操作日志查询"""

from sqlalchemy.orm import Session
import models


def list_operation_logs(db: Session, account_id: int, skip: int = 0, limit: int = 100, entity_type: str = None, operation: str = None, start_date: str = None, end_date: str = None):
    q = db.query(models.OperationLog).filter(models.OperationLog.account_id == account_id)
    if entity_type:
        q = q.filter(models.OperationLog.entity_type == entity_type)
    if operation:
        q = q.filter(models.OperationLog.operation == operation)
    if start_date:
        q = q.filter(models.OperationLog.created_at >= start_date)
    if end_date:
        q = q.filter(models.OperationLog.created_at <= end_date)
    total = q.count()
    items = q.order_by(models.OperationLog.created_at.desc()).offset(skip).limit(limit).all()
    return total, items