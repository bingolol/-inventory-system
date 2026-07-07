from datetime import datetime
from utils.period import quarter_bounds


def get_quarter_dates(year: int, quarter: int):
    return quarter_bounds(year, quarter)
