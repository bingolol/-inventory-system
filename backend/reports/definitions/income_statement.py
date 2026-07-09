"""利润表定义 — 会小企02表

设计原则（方案 C）：
- 汇总字段（gross_profit / total_operating_expenses / operating_profit /
  gross_profit_total / net_profit）禁止用 LEDGER_COMPOSITE 重新写公式，
  必须用 SUM_FIELDS 引用已定义的子字段。
- 子字段（revenue / cogs / expenses / tax_surcharges）各自挂 transform，
  汇总字段自动继承子字段的计算结果（含 SubaccountFallback）。
- 这样消灭了"同一逻辑两处定义漂移"的 bug（如 gross_profit_total 漏 6403 子科目）。
"""
from reports.dsl import (
    Field, Part, Bucket,
    LEDGER_COMPOSITE, LEDGER_PERIOD, SUM_FIELDS, ESCAPE_HATCH,
    SubaccountFallback,
)


def _resolve_cumulative_profit(snapshot):
    """利润总额：与月结所得税基数保持一致"""
    from crud.finance._profit import compute_cumulative_profit
    start = snapshot._period_start
    end = snapshot._period_end
    return compute_cumulative_profit(snapshot, start, end), []


INCOME_STATEMENT = [
    # ── 叶子字段：直接从总账取数 ──
    Field("revenue", "营业收入",
        source=LEDGER_COMPOSITE(parts=[
            Part(codes=["6001", "6051"], side="credit", sign=+1),
            Part(codes=["6001", "6051"], side="debit", sign=-1),
        ], bucket=Bucket.PNL_EXCLUDED),
    ),

    Field("cost_of_goods_sold", "营业成本",
        source=LEDGER_PERIOD(["6401"], bucket=Bucket.PNL_EXCLUDED),
    ),

    Field("selling_expenses", "销售费用",
        source=LEDGER_PERIOD(["6602"], bucket=Bucket.PNL_EXCLUDED),
    ),

    Field("administrative_expenses", "管理费用",
        source=LEDGER_PERIOD(["6601"], bucket=Bucket.PNL_EXCLUDED),
    ),

    Field("financial_expenses", "财务费用",
        source=LEDGER_PERIOD(["6603"], bucket=Bucket.PNL_EXCLUDED),
    ),

    # 6403 主科目余额为 0 时回退到子科目（640302/303/304）
    Field("tax_surcharges", "税金及附加",
        source=LEDGER_PERIOD(["6403"], bucket=Bucket.PNL_EXCLUDED),
        transform=SubaccountFallback(["640302", "640303", "640304"]),
    ),

    # ── 附加税明细 ──
    Field("consumption_tax", "消费税",
        source=LEDGER_PERIOD(["640301"], bucket=Bucket.PNL_EXCLUDED),
    ),
    Field("urban_construction_tax", "城建税",
        source=LEDGER_PERIOD(["640302"], bucket=Bucket.PNL_EXCLUDED),
    ),
    Field("education_surcharge", "教育费附加",
        source=LEDGER_PERIOD(["640303"], bucket=Bucket.PNL_EXCLUDED),
    ),
    Field("local_education_surcharge", "地方教育附加",
        source=LEDGER_PERIOD(["640304"], bucket=Bucket.PNL_EXCLUDED),
    ),
    Field("depreciation_expense", "折旧费用",
        source=LEDGER_PERIOD(["1602"], bucket=Bucket.PNL_EXCLUDED),
    ),

    Field("non_operating_income", "营业外收入",
        source=LEDGER_COMPOSITE(parts=[
            Part(codes=["6301", "6111"], side="credit", sign=+1),
            Part(codes=["6301", "6111"], side="debit", sign=-1),
        ], bucket=Bucket.PNL_EXCLUDED),
    ),

    Field("non_operating_expense", "营业外支出",
        source=LEDGER_COMPOSITE(parts=[
            Part(codes=["6701", "6711"], side="debit", sign=+1),
        ], bucket=Bucket.PNL_EXCLUDED),
    ),

    Field("income_tax_expense", "所得税费用",
        source=LEDGER_PERIOD(["6801"], bucket=Bucket.PNL_EXCLUDED),
    ),

    # ── 汇总字段：只引用子字段，禁止重新写科目公式 ──
    # 费用/成本用 sign=-1，收入用 sign=+1
    Field("gross_profit", "营业毛利",
        source=SUM_FIELDS([
            ("revenue", +1),
            ("cost_of_goods_sold", -1),
        ]),
    ),

    Field("total_operating_expenses", "营业费用合计",
        source=SUM_FIELDS([
            ("selling_expenses", +1),
            ("administrative_expenses", +1),
            ("financial_expenses", +1),
            ("tax_surcharges", +1),
        ]),
    ),

    Field("operating_profit", "营业利润",
        source=SUM_FIELDS([
            ("gross_profit", +1),
            ("total_operating_expenses", -1),
        ]),
    ),

    # 利润总额 = 统一税基口径
    Field("gross_profit_total", "利润总额",
        source=ESCAPE_HATCH(_resolve_cumulative_profit),
    ),

    Field("net_profit", "净利润",
        source=SUM_FIELDS([
            ("gross_profit_total", +1),
            ("income_tax_expense", -1),
        ]),
    ),
]
