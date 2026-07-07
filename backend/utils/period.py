"""期间工具：解析 period 字符串 和 生成幂等哈希"""

from calendar import monthrange
from datetime import date, datetime
from typing import Tuple


def parse_period(period: str) -> Tuple[datetime, datetime]:
    """解析 "YYYY-MM" → (月初 00:00:00, 月末 23:59:59)"""
    year, month = int(period[:4]), int(period[5:7])
    _, last_day = monthrange(year, month)
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59)
    return start_dt, end_dt


def period_end_date(period: str) -> date:
    """YYYY-MM → 该月最后一天"""
    year, month = map(int, period.split("-"))
    last_day = monthrange(year, month)[1]
    return date(year, month, last_day)


def period_bounds(period: str) -> Tuple[date, date]:
    """YYYY-MM → (该月第一天, 该月最后一天)"""
    year, month = map(int, period.split("-"))
    last_day = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def quarter_end_month(month: int) -> int:
    """返回该月所在季度末月份（1→3, 6→6, 12→12）"""
    return ((month - 1) // 3 + 1) * 3


def quarter_bounds(year: int, quarter: int) -> Tuple[datetime, datetime]:
    """返回季度起止日期（左闭右开: [start, end_of_next_quarter)）"""
    start_month = (quarter - 1) * 3 + 1
    start = datetime(year, start_month, 1)
    if quarter == 4:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, start_month + 3, 1)
    return start, end


def period_hash(period: str, tag: str) -> int:
    """确定性 63 位哈希，用于 source_id 幂等防御"""
    h = 0
    for c in f"{period}_{tag}":
        h = ((h << 5) - h) + ord(c)
        h &= 0x7FFFFFFFFFFFFFFF
    return h
