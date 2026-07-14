"""小企业会计准则财务报表（会小企01/02/03表）模板对接

将现有 generate_balance_sheet / generate_income_statement / generate_cash_flow_statement
的输出映射到税务申报模板行次，供前端展示和 .xls 导出使用。
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal
from sqlalchemy.orm import Session

from utils import _d, Q2, end_of_day
from reports.engine import ReportEngine
from reports.definitions.balance_sheet import BALANCE_SHEET
from ._snapshot import LedgerSnapshot
from .income_statement import generate_income_statement
from .cash_flow import generate_cash_flow_statement


ReportType = Literal["monthly", "quarterly", "annual"]


def _last_day_of_month(d: datetime) -> datetime:
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1, day=1) - timedelta(days=1)
    return d.replace(month=d.month + 1, day=1) - timedelta(days=1)


def _quarter_start_end(d: datetime):
    quarter = (d.month - 1) // 3 + 1
    start = d.replace(month=(quarter - 1) * 3 + 1, day=1)
    end = _last_day_of_month(start.replace(month=start.month + 2))
    return start, end


def _derive_periods(report_type: ReportType, date_str: str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    year_start = d.replace(month=1, day=1)
    year_end = d.replace(month=12, day=31)
    prior_year_start = year_start.replace(year=d.year - 1)
    prior_year_end = year_end.replace(year=d.year - 1)

    if report_type == "monthly":
        period_start = d.replace(day=1)
        period_end = _last_day_of_month(d)
    elif report_type == "quarterly":
        period_start, period_end = _quarter_start_end(d)
    else:  # annual
        period_start = year_start
        period_end = year_end

    return {
        "period_start": period_start.strftime("%Y-%m-%d"),
        "period_end": period_end.strftime("%Y-%m-%d"),
        "year_start": year_start.strftime("%Y-%m-%d"),
        "year_end": year_end.strftime("%Y-%m-%d"),
        "prior_year_start": prior_year_start.strftime("%Y-%m-%d"),
        "prior_year_end": prior_year_end.strftime("%Y-%m-%d"),
    }


def _fmt(v) -> float:
    return float(_d(v).quantize(Q2))


def generate_cwbb_xqykjzz(
    db: Session,
    account_id: int,
    report_type: ReportType,
    date: str,
    account,
):
    """生成小企业会计准则财务报表（月季报/年报）模板数据

    Args:
        db: 数据库会话
        account_id: 账本ID
        report_type: monthly / quarterly / annual
        date: 报表日期（资产负债表期末日期，同时也是利润表/现金流量表期间终点）
        account: Account ORM 对象，用于读取纳税人信息
    """
    periods = _derive_periods(report_type, date)
    end_date = periods["period_end"]
    start_date = periods["period_start"]
    year_start = periods["year_start"]
    prior_start = periods["prior_year_start"]
    prior_end = periods["prior_year_end"]

    # 期末资产负债表（DSL 报表引擎）
    end_dt = end_of_day(datetime.strptime(end_date, "%Y-%m-%d"))
    prior_dt = end_of_day(datetime.strptime(prior_end, "%Y-%m-%d"))
    engine = ReportEngine()
    bs_end = engine.execute(BALANCE_SHEET, LedgerSnapshot(db, account_id, bs_cutoff=end_dt))
    bs_start = engine.execute(BALANCE_SHEET, LedgerSnapshot(db, account_id, bs_cutoff=prior_dt))

    # 利润表
    is_period = generate_income_statement(db, account_id, start_date, end_date)
    is_cumulative = generate_income_statement(db, account_id, year_start, end_date)
    is_prior = generate_income_statement(db, account_id, prior_start, prior_end)

    # 现金流量表
    cf_period = generate_cash_flow_statement(db, account_id, start_date, end_date)
    cf_cumulative = generate_cash_flow_statement(db, account_id, year_start, end_date)
    cf_prior = generate_cash_flow_statement(db, account_id, prior_start, prior_end)

    def bs_item(line_no: int, name: str, end_key: str, start_key: str):
        return {
            "line_no": line_no,
            "name": name,
            "end_amount": _fmt(bs_end.get(end_key, 0)),
            "start_amount": _fmt(bs_start.get(start_key, 0)),
        }

    def is_item(line_no: int, name: str, period_key, cumulative_key, prior_key):
        """period_key/cumulative_key/prior_key 可为单 key 或 key 列表（多列求和）"""
        def _get(data, key):
            if isinstance(key, (list, tuple)):
                return sum(_d(data.get(k, 0)) for k in key)
            return _d(data.get(key, 0))
        return {
            "line_no": line_no,
            "name": name,
            "period_amount": _fmt(_get(is_period, period_key)),
            "cumulative_amount": _fmt(_get(is_cumulative, cumulative_key)),
            "prior_amount": _fmt(_get(is_prior, prior_key)),
        }

    def cf_item(line_no: int, name: str, period_key, cumulative_key, prior_key):
        """period_key/cumulative_key/prior_key 可为单 key 或 key 列表；
        tuple 表示嵌套访问如 ("operating_activities", "net")；
        key 以 'CF' 开头时从 cf_details 取数（流出项目以正数展示），
        否则从现金流表顶层取数（带符号）。"""
        def _get(data, key):
            if isinstance(key, list):
                # 列表表示多个独立 key 求和
                return sum(_get(data, k) for k in key)
            if isinstance(key, tuple):
                # 元组表示嵌套字典访问
                first, rest = key[0], key[1:]
                return _get(data.get(first, {}), rest[0] if len(rest) == 1 else rest)
            if isinstance(key, str) and key.startswith("CF"):
                return abs(_d(data.get("cf_details", {}).get(key, 0)))
            return _d(data.get(key, 0))
        return {
            "line_no": line_no,
            "name": name,
            "period_amount": _fmt(_get(cf_period, period_key)),
            "cumulative_amount": _fmt(_get(cf_cumulative, cumulative_key)),
            "prior_amount": _fmt(_get(cf_prior, prior_key)),
        }

    # 资产负债表（会小企01表）
    balance_sheet = [
        bs_item(1, "货币资金", "monetary_funds", "monetary_funds"),
        bs_item(2, "短期投资", None, None),
        bs_item(3, "应收票据", None, None),
        bs_item(4, "应收账款", "accounts_receivable", "accounts_receivable"),
        bs_item(5, "预付账款", "prepayments", "prepayments"),
        bs_item(6, "应收股利", None, None),
        bs_item(7, "应收利息", None, None),
        bs_item(8, "其他应收款", "other_receivable", "other_receivable"),
        bs_item(9, "存货", "inventory", "inventory"),
        bs_item(10, "其中：原材料", None, None),
        bs_item(11, "在产品", None, None),
        bs_item(12, "库存商品", None, None),
        bs_item(13, "周转材料", None, None),
        bs_item(14, "其他流动资产", None, None),
        bs_item(15, "流动资产合计", "total_current_assets", "total_current_assets"),
        bs_item(16, "长期债券投资", None, None),
        bs_item(17, "长期股权投资", None, None),
        bs_item(18, "固定资产原价", "fixed_assets_original", "fixed_assets_original"),
        bs_item(19, "减：累计折旧", "accumulated_depreciation", "accumulated_depreciation"),
        bs_item(20, "固定资产账面价值", "fixed_assets_net", "fixed_assets_net"),
        bs_item(21, "在建工程", None, None),
        bs_item(22, "工程物资", None, None),
        bs_item(23, "固定资产清理", None, None),
        bs_item(24, "生产性生物资产", None, None),
        bs_item(25, "无形资产", "intangible_assets_net", "intangible_assets_net"),
        bs_item(26, "开发支出", None, None),
        bs_item(27, "长期待摊费用", None, None),
        bs_item(28, "其他非流动资产", None, None),
        bs_item(29, "非流动资产合计", "total_non_current_assets", "total_non_current_assets"),
        bs_item(30, "资产合计", "total_assets", "total_assets"),
        bs_item(31, "短期借款", None, None),
        bs_item(32, "应付票据", None, None),
        bs_item(33, "应付账款", "accounts_payable", "accounts_payable"),
        bs_item(34, "预收账款", None, None),
        bs_item(35, "应付职工薪酬", "salaries_payable", "salaries_payable"),
        bs_item(36, "应交税费", "tax_payable", "tax_payable"),
        bs_item(37, "应付利息", None, None),
        bs_item(38, "应付利润", None, None),
        bs_item(39, "其他应付款", "other_payable", "other_payable"),
        bs_item(40, "其他流动负债", None, None),
        bs_item(41, "流动负债合计", "total_current_liabilities", "total_current_liabilities"),
        bs_item(42, "长期借款", "long_term_borrowings", "long_term_borrowings"),
        bs_item(43, "长期应付款", None, None),
        bs_item(44, "递延收益", None, None),
        bs_item(45, "其他非流动负债", None, None),
        bs_item(46, "非流动负债合计", "total_non_current_liabilities", "total_non_current_liabilities"),
        bs_item(47, "负债合计", "total_liabilities", "total_liabilities"),
        bs_item(48, "实收资本（或股本）", "paid_in_capital", "paid_in_capital"),
        bs_item(49, "资本公积", None, None),
        bs_item(50, "盈余公积", None, None),
        bs_item(51, "未分配利润", "retained_earnings", "retained_earnings"),
        bs_item(52, "所有者权益（或股东权益）合计", "total_equity", "total_equity"),
        bs_item(53, "负债和所有者权益（或股东权益）总计", "total_liabilities_and_equity", "total_liabilities_and_equity"),
    ]

    # 利润表（会小企02表）
    income_statement = [
        is_item(1, "一、营业收入", "revenue", "revenue", "revenue"),
        is_item(2, "减：营业成本", "cost_of_goods_sold", "cost_of_goods_sold", "cost_of_goods_sold"),
        is_item(3, "税金及附加", "tax_surcharges", "tax_surcharges", "tax_surcharges"),
        is_item(4, "其中：消费税", "consumption_tax", "consumption_tax", "consumption_tax"),
        is_item(5, "营业税", None, None, None),
        is_item(6, "城市维护建设税", "urban_construction_tax_l1", "urban_construction_tax_l1", "urban_construction_tax_l1"),
        is_item(7, "资源税", "resource_tax", "resource_tax", "resource_tax"),
        is_item(8, "土地增值税", "land_appreciation_tax", "land_appreciation_tax", "land_appreciation_tax"),
        is_item(9, "城镇土地使用税、房产税、车船税、印花税", ["property_tax", "land_use_tax", "vehicle_vessel_tax", "stamp_tax"], ["property_tax", "land_use_tax", "vehicle_vessel_tax", "stamp_tax"], ["property_tax", "land_use_tax", "vehicle_vessel_tax", "stamp_tax"]),
        is_item(10, "教育费附加、矿产资源补偿费、排污费", ["education_surcharge_l1", "local_education_surcharge_l1", "environmental_tax"], ["education_surcharge_l1", "local_education_surcharge_l1", "environmental_tax"], ["education_surcharge_l1", "local_education_surcharge_l1", "environmental_tax"]),
        is_item(11, "销售费用", "selling_expenses", "selling_expenses", "selling_expenses"),
        is_item(12, "其中：商品维修费", None, None, None),
        is_item(13, "广告费和业务宣传费", None, None, None),
        is_item(14, "管理费用", "administrative_expenses", "administrative_expenses", "administrative_expenses"),
        is_item(15, "其中：开办费", None, None, None),
        is_item(16, "业务招待费", None, None, None),
        is_item(17, "研究费用", None, None, None),
        is_item(18, "财务费用", "financial_expenses", "financial_expenses", "financial_expenses"),
        is_item(19, "其中：利息费用（收入以“-”号填列）", None, None, None),
        is_item(20, "加：投资收益（损失以“-”号填列）", None, None, None),
        is_item(21, "二、营业利润（亏损以“-”号填列）", "operating_profit", "operating_profit", "operating_profit"),
        is_item(22, "加：营业外收入", "non_operating_income", "non_operating_income", "non_operating_income"),
        is_item(23, "其中：政府补助", None, None, None),
        is_item(24, "减：营业外支出", "non_operating_expense", "non_operating_expense", "non_operating_expense"),
        is_item(25, "其中：坏账损失", None, None, None),
        is_item(26, "无法收回的长期债券投资损失", None, None, None),
        is_item(27, "无法收回的长期股权投资损失", None, None, None),
        is_item(28, "自然灾害等不可抗力因素造成的损失", None, None, None),
        is_item(29, "税收滞纳金", None, None, None),
        is_item(30, "三、利润总额（亏损总额以“-”号填列）", "gross_profit_total", "gross_profit_total", "gross_profit_total"),
        is_item(31, "减：所得税费用", "income_tax_expense", "income_tax_expense", "income_tax_expense"),
        is_item(32, "四、净利润（净亏损以“-”号填列）", "net_profit", "net_profit", "net_profit"),
    ]

    # 现金流量表（会小企03表）
    # 按 CF01~CF19 明细项目取数，其余为计算项
    cash_flow_statement = [
        cf_item(1, "销售产成品、商品、提供劳务收到的现金", "CF01", "CF01", "CF01"),
        cf_item(2, "收到其他与经营活动有关的现金", "CF02", "CF02", "CF02"),
        cf_item(3, "购买原材料、商品、接受劳务支付的现金", "CF03", "CF03", "CF03"),
        cf_item(4, "支付的职工薪酬", "CF04", "CF04", "CF04"),
        cf_item(5, "支付的税费", "CF05", "CF05", "CF05"),
        cf_item(6, "支付其他与经营活动有关的现金", "CF06", "CF06", "CF06"),
        cf_item(7, "经营活动产生的现金流量净额", ("operating_activities", "net"), ("operating_activities", "net"), ("operating_activities", "net")),
        cf_item(8, "收回短期投资、长期债券投资和长期股权投资收到的现金", "CF08", "CF08", "CF08"),
        cf_item(9, "取得投资收益收到的现金", "CF09", "CF09", "CF09"),
        cf_item(10, "处置固定资产、无形资产和其他非流动资产收回的现金净额", "CF10", "CF10", "CF10"),
        cf_item(11, "短期投资、长期债券投资和长期股权投资支付的现金", "CF11", "CF11", "CF11"),
        cf_item(12, "购建固定资产、无形资产和其他非流动资产支付的现金", "CF12", "CF12", "CF12"),
        cf_item(13, "投资活动产生的现金流量净额", ("investing_activities", "net"), ("investing_activities", "net"), ("investing_activities", "net")),
        cf_item(14, "取得借款收到的现金", "CF14", "CF14", "CF14"),
        cf_item(15, "吸收投资者投资收到的现金", "CF15", "CF15", "CF15"),
        cf_item(16, "偿还借款本金支付的现金", "CF16", "CF16", "CF16"),
        cf_item(17, "偿还借款利息支付的现金", "CF17", "CF17", "CF17"),
        cf_item(18, "分配利润支付的现金", "CF18", "CF18", "CF18"),
        cf_item(19, "筹资活动产生的现金流量净额", ("financing_activities", "net"), ("financing_activities", "net"), ("financing_activities", "net")),
        cf_item(20, "四、现金净增加额", "net_cash_flow", "net_cash_flow", "net_cash_flow"),
        cf_item(21, "加：期初现金余额", "beginning_cash_balance", "beginning_cash_balance", "beginning_cash_balance"),
        cf_item(22, "五、期末现金余额", "ending_cash_balance", "ending_cash_balance", "ending_cash_balance"),
    ]

    return {
        "report_type": report_type,
        "taxpayer_id": (account.taxpayer_id_l1 or "") if account else "",
        "taxpayer_name": (account.taxpayer_name_l1 or account.name or "") if account else "",
        "period_start": start_date,
        "period_end": end_date,
        "balance_sheet": balance_sheet,
        "income_statement": income_statement,
        "cash_flow_statement": cash_flow_statement,
    }
