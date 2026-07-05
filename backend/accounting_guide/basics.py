from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from crud.finance.income_statement import generate_income_statement
from utils import _d, Q2


def build_module_basics(db: Session, account_id: int, start_date: datetime, end_date: datetime):
    is_data = generate_income_statement(
        db, account_id,
        start_date.strftime("%Y-%m-%d"),
        (end_date - timedelta(days=1)).strftime("%Y-%m-%d")
    )
    revenue = _d(is_data.get("revenue", 0)).quantize(Q2)
    cost = _d(is_data.get("cost_of_goods_sold", 0)).quantize(Q2)
    admin_expense = _d(is_data.get("administrative_expenses", 0)).quantize(Q2)
    selling_expense = _d(is_data.get("selling_expenses", 0)).quantize(Q2)
    fin_expense = _d(is_data.get("financial_expenses", 0)).quantize(Q2)
    total_expenses = (admin_expense + selling_expense + fin_expense).quantize(Q2)
    profit = (revenue - cost - total_expenses).quantize(Q2)

    expense_items = []
    if admin_expense > 0:
        expense_items.append({"category": "管理费用", "amount": float(admin_expense),
                              "explain": "房租、水电、办公用品、工资等日常运营开销，科目代码 6601"})
    if selling_expense > 0:
        expense_items.append({"category": "销售费用", "amount": float(selling_expense),
                              "explain": "广告宣传、运输费、包装费等与销售直接相关的支出，科目代码 6602"})
    if fin_expense > 0:
        expense_items.append({"category": "财务费用", "amount": float(fin_expense),
                              "explain": "银行手续费、贷款利息等与资金相关的支出，科目代码 6603"})

    return {
        "revenue": float(revenue), "cost": float(cost),
        "expenses": expense_items, "total_expenses": float(total_expenses),
        "profit": float(profit),
        "period_label": f"{start_date.year}年第{((start_date.month - 1) // 3) + 1}季度",
    }


def build_module_statements(db: Session, account_id: int, start_date: datetime, end_date: datetime):
    is_data = generate_income_statement(
        db, account_id,
        start_date.strftime("%Y-%m-%d"),
        (end_date - timedelta(days=1)).strftime("%Y-%m-%d")
    )
    net_profit = float(_d(is_data.get("net_profit", 0)).quantize(Q2))
    revenue = float(_d(is_data.get("revenue", 0)).quantize(Q2))
    total_opex = float(_d(is_data.get("total_operating_expenses", 0)).quantize(Q2))
    gross_profit = float(_d(is_data.get("gross_profit", 0)).quantize(Q2))

    return {
        "net_profit": net_profit, "revenue": revenue,
        "period_label": f"{start_date.year}年第{((start_date.month - 1) // 3) + 1}季度",
        "reports": [
            {"name": "资产负债表", "alt_name": "Balance Sheet", "code": "会小企01表",
             "purpose": "公司的「体检表」— 在某一个时间点（比如 12 月 31 日），拍一张快照，看公司有多少资产、欠多少债、股东有多少钱在里面。",
             "formula": "资产 = 负债 + 所有者权益",
             "formula_explain": "左边（钱到哪去了）= 右边（钱从哪来的）。这个等式永远相等，不等就是账做错了。",
             "structure": [
                 {"side": "左边：资产", "items": "你公司拥有的东西", "examples": "现金、银行存款、应收款（客户欠你的）、库存商品、固定资产（机器/电脑/车）"},
                 {"side": "右边上半：负债", "items": "你欠别人的钱", "examples": "应付账款（你欠供应商的）、应交税费（你欠税务局的）、短期借款（你欠银行的）"},
                 {"side": "右边下半：所有者权益", "items": "真正属于股东的钱", "examples": "实收资本（股东投的）+ 未分配利润（这些年攒下来的净利润）"},
             ],
             "how_to_read": "看资产总额知道公司规模；看资产负债率（负债/资产）知道风险有多大；看未分配利润知道这些年攒了多少钱。",
             "link": "利润表的「净利润」最终进入资产负债表的「未分配利润」。两表勾稽：本期净利润 = 期末未分配利润 − 期初未分配利润。",
             "system_page": "财务报表 → 资产负债表/利润表"},
            {"name": "利润表", "alt_name": "Income Statement / P&L", "code": "会小企02表",
             "purpose": f"公司的「成绩单」— 看一段时期（比如 {start_date.year}年第{((start_date.month - 1) // 3) + 1}季度）赚了还是亏了。资产负债表是快照，利润表是录像。",
             "formula": "收入 − 成本 − 费用 = 净利润",
             "formula_explain": "从上到下逐层递减，每一层都代表不同类型的扣除。",
             "structure": [
                 {"line": "① 营业收入", "explain": "卖货/服务收到的钱", "value": revenue},
                 {"line": "② 减：营业成本", "explain": "对应卖出货物的进货成本", "value": None},
                 {"line": "③ = 毛利润", "explain": "卖货本身赚的差价", "value": gross_profit},
                 {"line": "④ 减：期间费用", "explain": "管理+销售+财务+税金及附加", "value": total_opex},
                 {"line": "⑤ ± 营业外收支", "explain": "非日常经营的收入/支出", "value": None},
                 {"line": "⑥ = 利润总额", "explain": "税前利润", "value": None},
                 {"line": "⑦ 减：所得税费用", "explain": "企业所得税", "value": None},
                 {"line": "⑧ = 净利润", "explain": "最终真正赚到的钱", "value": net_profit},
             ],
             "how_to_read": "看净利润知道赚了还是亏了；看毛利率（毛利/收入）知道产品有没有竞争力；看费用率（费用/收入）知道管理效率。",
             "link": "净利润进入资产负债表的所有者权益。利润表是连接期初和期末资产负债表的桥梁。",
             "system_page": "财务报表 → 资产负债表/利润表"},
            {"name": "现金流量表", "alt_name": "Cash Flow Statement", "code": "会小企03表",
             "purpose": "公司的「流水账」— 真金白银的进出记录。利润表说赚了 100 万，但银行账户可能只多了 30 万（剩下的全赊出去了）。现金流量表告诉你手里到底有多少钱。",
             "formula": "期初现金 + 经营现金流 + 投资现金流 + 筹资现金流 = 期末现金",
             "formula_explain": "把现金变动分成三大类，看钱是从哪来的。",
             "structure": [
                 {"side": "经营活动现金流", "items": "日常买卖产生的现金进出", "examples": "卖货收现 − 进货付现 − 工资付现 − 交税付现 = 经营现金流净额。正数说明主业能造血，负数说明入不敷出。"},
                 {"side": "投资活动现金流", "items": "买卖固定资产/投资的现金进出", "examples": "买设备/买车/装修花的钱（通常是负数，说明在扩张）；变卖资产收回的钱。"},
                 {"side": "筹资活动现金流", "items": "和股东/银行之间的现金进出", "examples": "股东投资（正）、银行贷款（正）、还贷款（负）、分红（负）。"},
             ],
             "how_to_read": "经营现金流是命根子——必须为正，否则公司活不下去。利润表可能因为折旧等因素不真实，现金流量表最难造假。三表互验：净利润 > 经营现金流净额 → 很多钱没收回来，警惕坏账。",
             "link": "期末现金余额等于资产负债表的「货币资金」（现金+银行存款）。利润表决定经营现金流的上限，资产负债表解释现金去哪了。",
             "system_page": "财务报表 → 现金流量表"},
        ],
        "linkage": {
            "title": "三张表怎么串起来？",
            "text": f"利润表的净利润（{net_profit} 元）→ 进入资产负债表的所有者权益（未分配利润）→ 资产负债表左右平衡 → 资产负债表的现金变动 → 由现金流量表解释去向。三张表从来不是孤立的，一张出错，另两张必然不平。",
        },
    }
