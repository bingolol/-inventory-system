from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
import schemas, crud

router = APIRouter()


@router.get("/")
def list_logs(page: int = 1, page_size: int = 20, entity_type: str = None, operation: str = None, start_date: str = None, end_date: str = None, account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    skip = (page - 1) * page_size
    total, items = crud.list_operation_logs(db, account_id, skip=skip, limit=page_size, entity_type=entity_type, operation=operation, start_date=start_date, end_date=end_date)
    result = []
    for log in items:
        result.append(schemas.OperationLogOut(
            id=log.id, operation=log.operation, entity_type=log.entity_type,
            entity_id=log.entity_id, detail=log.detail, operator=getattr(log, 'operator', 'user'), created_at=log.created_at
        ))
    return {"total": total, "items": result}