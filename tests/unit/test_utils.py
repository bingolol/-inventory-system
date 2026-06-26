"""Utils 工具函数单元测试"""
from datetime import datetime
from utils import get_quarter_date_range


class TestGetQuarterDateRange:

    def test_q1(self):
        """Q1: 2025-01-01 ~ 2025-04-01"""
        start, end = get_quarter_date_range(2025, 1)
        assert start == datetime(2025, 1, 1)
        assert end == datetime(2025, 4, 1)

    def test_q2(self):
        """Q2: 2025-04-01 ~ 2025-07-01"""
        start, end = get_quarter_date_range(2025, 2)
        assert start == datetime(2025, 4, 1)
        assert end == datetime(2025, 7, 1)

    def test_q3(self):
        """Q3: 2025-07-01 ~ 2025-10-01"""
        start, end = get_quarter_date_range(2025, 3)
        assert start == datetime(2025, 7, 1)
        assert end == datetime(2025, 10, 1)

    def test_q4_cross_year(self):
        """Q4 跨年: 2025-10-01 ~ 2026-01-01"""
        start, end = get_quarter_date_range(2025, 4)
        assert start == datetime(2025, 10, 1)
        assert end == datetime(2026, 1, 1)
