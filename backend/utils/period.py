"""期间工具：解析 period 字符串 和 生成幂等哈希"""

from calendar import monthrange
from datetime import datetime
from typing import Tuple


def parse_period(period: str) -> Tuple[datetime, datetime]:
    """解析 "YYYY-MM" → (月初 00:00:00, 月末 23:59:59)"""
    year, month = int(period[:4]), int(period[5:7])
    _, last_day = monthrange(year, month)
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59)
    return start_dt, end_dt


def period_hash(period: str, tag: str) -> int:
    """确定性 63 位哈希，用于 source_id 幂等防御"""
    h = 0
    for c in f"{period}_{tag}":
        h = ((h << 5) - h) + ord(c)
        h &= 0x7FFFFFFFFFFFFFFF
    return h
