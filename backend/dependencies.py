from datetime import datetime
from typing import Optional
from fastapi import Query as _Query
from fastapi.params import Query as _QueryParam


class Pagination:
    def __init__(
        self,
        page: int = _Query(1, ge=1, description="页码"),
        page_size: int = _Query(20, ge=1, le=1000, description="每页数量"),
    ):
        self.page = _resolve_query(page, 1)
        self.page_size = _resolve_query(page_size, 20)
        self.skip = (self.page - 1) * self.page_size
        self.limit = self.page_size


class DateRange:
    def __init__(
        self,
        start_date: Optional[str] = _Query(None, description="开始日期 (YYYY-MM-DD)"),
        end_date: Optional[str] = _Query(None, description="结束日期 (YYYY-MM-DD)"),
    ):
        from utils import parse_date, end_of_day

        start = _resolve_query(start_date)
        end = _resolve_query(end_date)
        self.start = parse_date(start) if start else None
        self.end = end_of_day(parse_date(end)) if end else None


def _resolve_query(value, fallback=None):
    """非FastAPI调用时将Query对象还原为其默认值"""
    if isinstance(value, _QueryParam):
        return value.default
    if value is not None:
        return value
    return fallback


