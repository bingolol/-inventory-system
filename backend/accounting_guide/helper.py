from datetime import datetime


def get_quarter_dates(year: int, quarter: int):
    start_month = (quarter - 1) * 3 + 1
    start_date = datetime(year, start_month, 1)
    if quarter == 4:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, start_month + 3, 1)
    return start_date, end_date
