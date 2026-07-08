from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from account_dep import get_account_id
from dependencies import Pagination, DateRange
from schemas import PaginatedResponse, OperationLogOut
import schemas, crud

router = APIRouter()


@router.get("")
def list_logs(pag: Pagination = Depends(), entity_type: str = None, operation: str = None, date_range: DateRange = Depends(), account_id: int = Depends(get_account_id), db: Session = Depends(get_db)):
    total, items = crud.list_operation_logs(db, account_id, skip=pag.skip, limit=pag.limit, entity_type=entity_type, operation=operation, start_date=date_range.start, end_date=date_range.end)
    result = []
    for log in items:
        result.append(OperationLogOut(
            id=log.id, operation=log.operation, entity_type=log.entity_type,
            entity_id=log.entity_id, detail=log.detail, operator=getattr(log, 'operator', 'user'), created_at=log.created_at
        ))
    return PaginatedResponse(total=total, items=result)