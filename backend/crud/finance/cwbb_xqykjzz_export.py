"""小企业会计准则财务报表 .xls 导出（xlrd + xlwt + xlutils）

使用税务申报模板文件作底稿，保留原格式，仅填充表头和数据。
"""

import io
import os
from decimal import Decimal

import xlrd
import xlwt
from xlutils.copy import copy

from utils import _d, Q2
from .cwbb_xqykjzz import generate_cwbb_xqykjzz


TEMPLATE_DIR = r"C:\Users\Administrator\Desktop\CWBB_XQYKJZZ"


def _template_path(report_type: str) -> str:
    if report_type == "annual":
        return os.path.join(TEMPLATE_DIR, "财务报表报送与信息采集（小企业会计准则）年报.xls")
    return os.path.join(TEMPLATE_DIR, "财务报表报送与信息采集（小企业会计准则）月季报.xls")


def _build_line_map(sh):
    """扫描模板，建立行次 -> (row, line_col) 映射"""
    mapping = {}
    for r in range(sh.nrows):
        for c in range(sh.ncols):
            v = sh.cell_value(r, c)
            if isinstance(v, (int, float)) and 1 <= int(v) <= 60:
                mapping[int(v)] = (r, c)
    return mapping


def _write_amount(ws, row, col, value):
    """写入金额，保留两位小数"""
    if value is None:
        return
    val = _d(value)
    ws.write(row, col, float(val.quantize(Q2)))


def _fill_balance_sheet(ws, items, line_map):
    for item in items:
        line_no = item["line_no"]
        if line_no not in line_map:
            continue
        row, line_col = line_map[line_no]
        _write_amount(ws, row, line_col + 1, item.get("end_amount"))
        _write_amount(ws, row, line_col + 2, item.get("start_amount"))


def _fill_income_or_cash(ws, items, line_map, is_annual: bool):
    for item in items:
        line_no = item["line_no"]
        if line_no not in line_map:
            continue
        row, line_col = line_map[line_no]
        if is_annual:
            # 本年累计金额 / 上年金额
            _write_amount(ws, row, line_col + 1, item.get("cumulative_amount"))
            _write_amount(ws, row, line_col + 2, item.get("prior_amount"))
        else:
            # 本期金额 / 本年累计金额
            _write_amount(ws, row, line_col + 1, item.get("period_amount"))
            _write_amount(ws, row, line_col + 2, item.get("cumulative_amount"))


def export_cwbb_xqykjzz(db, account_id: int, report_type: str, date: str, account):
    """生成并返回填充好的 .xls 文件二进制内容"""
    data = generate_cwbb_xqykjzz(db, account_id, report_type, date, account)

    template_path = _template_path(report_type)
    rb = xlrd.open_workbook(template_path, formatting_info=False)
    wb = copy(rb)

    is_annual = report_type == "annual"

    # 资产负债表
    bs_sheet_index = rb.sheet_names().index("资产负债表")
    ws_bs = wb.get_sheet(bs_sheet_index)
    bs_map = _build_line_map(rb.sheet_by_index(bs_sheet_index))
    ws_bs.write(2, 2, data.get("taxpayer_id", ""))
    ws_bs.write(2, 6, data.get("taxpayer_name", ""))
    ws_bs.write(3, 2, data.get("period_start", ""))
    ws_bs.write(3, 6, data.get("period_end", ""))
    _fill_balance_sheet(ws_bs, data["balance_sheet"], bs_map)

    # 利润表
    is_sheet_name = "利润表_年" if is_annual else "利润表_月季报"
    is_sheet_index = rb.sheet_names().index(is_sheet_name)
    ws_is = wb.get_sheet(is_sheet_index)
    is_map = _build_line_map(rb.sheet_by_index(is_sheet_index))
    ws_is.write(2, 2, data.get("taxpayer_id", ""))
    ws_is.write(2, 4, data.get("taxpayer_name", ""))
    ws_is.write(3, 2, data.get("period_start", ""))
    ws_is.write(3, 4, data.get("period_end", ""))
    _fill_income_or_cash(ws_is, data["income_statement"], is_map, is_annual)

    # 现金流量表
    cf_sheet_name = "现金流量表_年" if is_annual else "现金流量表_月季报"
    cf_sheet_index = rb.sheet_names().index(cf_sheet_name)
    ws_cf = wb.get_sheet(cf_sheet_index)
    cf_map = _build_line_map(rb.sheet_by_index(cf_sheet_index))
    ws_cf.write(2, 2, data.get("taxpayer_id", ""))
    ws_cf.write(2, 4, data.get("taxpayer_name", ""))
    ws_cf.write(3, 2, data.get("period_start", ""))
    ws_cf.write(3, 4, data.get("period_end", ""))
    _fill_income_or_cash(ws_cf, data["cash_flow_statement"], cf_map, is_annual)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
