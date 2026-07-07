"""损益科目汇总 — BR-23 统一科目清单的累计利润计算

engine_tax.py 和 income_statement.py 共用此模块，确保损益科目变更时两处同步。
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from utils import Q2

if TYPE_CHECKING:
    from ._snapshot import LedgerSnapshot

# ── 损益科目清单（BR-23 全覆盖，单一真相源）──

REVENUE_CODES = ["6001", "6051"]
COST_CODES = ["6401"]
EXPENSE_CODES = ["6601", "6602", "6603", "6403"]
# 6403 税金及附加子科目：主科目为 0 时回退到明细合计
SURCHARGE_SUB_CODES = [
    "640301", "640302", "640303", "640304", "640305",
    "640306", "640307", "640308", "640309", "640310", "640311",
]
NON_OP_INCOME_CODES = ["6301", "6111"]
NON_OP_EXPENSE_CODES = ["6701", "6711"]


def compute_cumulative_profit(
    snapshot: "LedgerSnapshot",
    start_dt: datetime,
    end_dt: datetime,
) -> Decimal:
    """计算累计利润（利润总额 = 收入 - 成本 - 费用 + 营业外收入 - 营业外支出）

    engine_tax 的月结所得税计提 和 income_statement 的利润表 共用此函数。
    """

    # 收入 = 主营业务收入(6001) + 其他业务收入(6051)，贷方 - 借方
    revenue = Decimal("0")
    for code in REVENUE_CODES:
        d, c = snapshot.pnl_dc(code, start_dt, end_dt)
        revenue += c - d

    # 成本 = 主营业务成本(6401)，借方 - 贷方
    cogs = Decimal("0")
    for code in COST_CODES:
        d, c = snapshot.pnl_dc(code, start_dt, end_dt)
        cogs += d - c

    # 费用 = 管理费用(6601) + 销售费用(6602) + 财务费用(6603) + 税金及附加(6403)
    # 6403 子科目回退：主科目余额为 0 时汇总明细科目（附加税计提写到 640302/303/304）
    expenses = Decimal("0")
    for code in EXPENSE_CODES:
        d, c = snapshot.pnl_dc(code, start_dt, end_dt)
        net = d - c
        if code == "6403" and net == Decimal("0"):
            for sub_code in SURCHARGE_SUB_CODES:
                sd, sc = snapshot.pnl_dc(sub_code, start_dt, end_dt)
                net += sd - sc
        expenses += net

    # 营业外收入 = 税收减免(6301) + 资产处置收益(6111)，贷方 - 借方
    non_op_income = Decimal("0")
    for code in NON_OP_INCOME_CODES:
        d, c = snapshot.pnl_dc(code, start_dt, end_dt)
        non_op_income += c - d

    # 营业外支出 = 营业外支出(6701) + 资产处置损失(6711)，借方 - 贷方
    non_op_expense = Decimal("0")
    for code in NON_OP_EXPENSE_CODES:
        d, c = snapshot.pnl_dc(code, start_dt, end_dt)
        non_op_expense += d - c

    profit = (revenue - cogs - expenses + non_op_income - non_op_expense).quantize(Q2)
    return profit
