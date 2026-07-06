"""资产负债表定义 — 会小企01表"""
from reports.dsl import (
    Field, Part, Bucket, Check,
    LEDGER_BALANCE, LEDGER_CREDIT, LEDGER_PERIOD, LEDGER_COMPOSITE,
    SUM_FIELDS, DualSource, STOCK_MOVES, OPENING, ESCAPE_HATCH,
    INVOICE_TAX_NET,
    PositivePart, NegativePart, OpeningFallback, SubaccountFallback, Negate,
)


# ── ESCAPE_HATCH: ending_cash 三级回退 ──
def _resolve_ending_cash(snapshot):
    from decimal import Decimal
    from utils import _d
    import models as m

    cash_bal, ids = snapshot.trace_bal("1001")
    if cash_bal != 0 or (snapshot._ledger and any(snapshot._trace_rows_by_code.values())):
        return cash_bal, ids

    db = snapshot._db
    aid = snapshot._account_id
    has_bank = db.query(m.BankAccount).filter(m.BankAccount.account_id == aid).first() is not None
    if has_bank:
        return Decimal("0"), []

    import models as models_mod
    from sqlalchemy import func as sqlfunc
    opening = snapshot.opening_balance
    ob_cash = _d(opening.cash_balance_l1) if opening else Decimal("0")
    total_payments = _d(db.query(sqlfunc.sum(models_mod.Payment.amount_l1)).filter(
        models_mod.Payment.account_id == aid,
    ).scalar())
    total_receipts = _d(db.query(sqlfunc.sum(models_mod.Receipt.amount_l1)).filter(
        models_mod.Receipt.account_id == aid,
    ).scalar())
    return ob_cash - total_payments + total_receipts, []


def _resolve_ending_bank(snapshot):
    from decimal import Decimal
    from utils import _d
    import models as m

    bank_bal, ids = snapshot.trace_bal("1002")
    if bank_bal != 0 or (snapshot._ledger and any(snapshot._trace_rows_by_code.values())):
        return bank_bal, ids

    db = snapshot._db
    aid = snapshot._account_id
    has_bank = db.query(m.BankAccount).filter(m.BankAccount.account_id == aid).first()
    if has_bank:
        from sqlalchemy import func as sqlfunc, case as sqlcase
        opening = snapshot.opening_balance
        ob_bank = _d(opening.bank_balance_l1) if opening else Decimal("0")
        tx_net = db.query(
            sqlfunc.sum(
                sqlcase(
                    (m.BankTransaction.transaction_type == 'inflow', m.BankTransaction.amount_l2),
                    else_=-m.BankTransaction.amount_l2
                )
            )
        ).filter(m.BankTransaction.account_id == aid).scalar()
        bank_balance = ob_bank + _d(tx_net) if tx_net else ob_bank
        return bank_balance, []

    return Decimal("0"), []


BALANCE_SHEET = [
    # ── 流动资产 ──
    Field("ending_cash", "库存现金",
        source=ESCAPE_HATCH(_resolve_ending_cash),
    ),
    Field("ending_bank", "银行存款",
        source=ESCAPE_HATCH(_resolve_ending_bank),
    ),

    Field("monetary_funds", "货币资金",
        source=SUM_FIELDS(["ending_cash", "ending_bank"]),
    ),

    Field("accounts_receivable", "应收账款",
        source=LEDGER_BALANCE(["1122"]),
        transform=OpeningFallback("accounts_receivable"),
    ),

    Field("prepayments", "预付账款",
        source=LEDGER_BALANCE(["1123"]),
    ),

    Field("inventory", "存货",
        source=STOCK_MOVES(),
        transform=OpeningFallback("inventory_value"),
    ),

    Field("prepaid_tax", "预付税款",
        source=SUM_FIELDS(["_vat_net"]),
        transform=NegativePart(abs=True),
    ),

    Field("deferred_assets", "其他流动资产",
        source=LEDGER_BALANCE(["1901"]),
    ),

    Field("total_current_assets", "流动资产合计",
        source=SUM_FIELDS(["monetary_funds", "accounts_receivable",
                           "prepayments", "inventory", "prepaid_tax",
                           "deferred_assets"]),
    ),

    # ── 非流动资产 ──
    Field("fixed_assets_original", "固定资产原值",
        source=LEDGER_BALANCE(["1601"]),
    ),
    Field("accumulated_depreciation", "累计折旧",
        source=LEDGER_CREDIT(["1602"]),
        transform=Negate(),
    ),
    Field("fixed_assets_net", "固定资产净值",
        source=SUM_FIELDS(["fixed_assets_original", "accumulated_depreciation"]),
    ),

    Field("intangible_assets_original", "无形资产原值",
        source=LEDGER_BALANCE(["1701"]),
    ),
    Field("accumulated_amortization", "累计摊销",
        source=LEDGER_CREDIT(["1702"]),
        transform=Negate(),
    ),
    Field("intangible_assets_net", "无形资产净值",
        source=SUM_FIELDS(["intangible_assets_original", "accumulated_amortization"]),
    ),

    Field("total_non_current_assets", "非流动资产合计",
        source=SUM_FIELDS(["fixed_assets_net", "intangible_assets_net"]),
    ),

    Field("total_assets", "资产总计",
        source=SUM_FIELDS(["total_current_assets", "total_non_current_assets"]),
    ),

    # ── 流动负债 ──
    Field("accounts_payable", "应付账款",
        source=LEDGER_CREDIT(["2202"]),
        transform=OpeningFallback("accounts_payable"),
    ),

    Field("salaries_payable", "应付职工薪酬",
        source=LEDGER_CREDIT(["2211"]),
    ),

    Field("other_payable", "其他应付款",
        source=LEDGER_CREDIT(["2241"]),
    ),

    # ── 应交税费 ──
    Field("_vat_net", None,
        source=DualSource(
            primary=INVOICE_TAX_NET(),
            secondary=LEDGER_COMPOSITE(parts=[
                Part(codes=["222101", "222103", "222107"], side="credit", sign=+1),
                Part(codes=["222102", "222106"], side="debit", sign=-1),
            ]),
        ),
    ),
    Field("vat_payable", "应交增值税",
        source=SUM_FIELDS(["_vat_net"]),
        transform=PositivePart(),
    ),

    Field("surcharge_liability", "附加税负债",
        source=LEDGER_CREDIT(["222104", "222110", "222111", "222112",
                              "222113", "222114", "222115", "222116",
                              "222117", "222118", "222119", "222120"]),
    ),
    Field("income_tax_liability", "应交所得税",
        source=LEDGER_CREDIT(["222105"]),
    ),
    Field("personal_income_tax_liability", "应交个人所得税",
        source=LEDGER_CREDIT(["222108"]),
    ),

    Field("tax_payable", "应交税费合计",
        source=SUM_FIELDS(["vat_payable", "surcharge_liability",
                           "income_tax_liability", "personal_income_tax_liability"]),
    ),

    Field("total_current_liabilities", "流动负债合计",
        source=SUM_FIELDS(["accounts_payable", "salaries_payable",
                           "tax_payable", "other_payable"]),
    ),

    # ── 非流动负债 ──
    Field("long_term_borrowings", "长期借款",
        source=LEDGER_CREDIT(["2501"]),
    ),

    Field("total_non_current_liabilities", "非流动负债合计",
        source=SUM_FIELDS(["long_term_borrowings"]),
    ),

    Field("total_liabilities", "负债合计",
        source=SUM_FIELDS(["total_current_liabilities", "total_non_current_liabilities"]),
    ),

    # ── 所有者权益 ──
    Field("paid_in_capital", "实收资本",
        source=LEDGER_CREDIT(["3001"]),
    ),
    Field("current_year_profit", "本年利润",
        source=LEDGER_CREDIT(["4103"]),
    ),
    Field("retained_earnings_prev", "利润分配",
        source=LEDGER_CREDIT(["4104"]),
    ),

    # 当期净利润（月结前来自损益科目，月结后 = 0 避免重复）
    # side=None 取净额(d-c)，sign=-1 转为 c-d：
    #   收入类 c > d → (c-d) 正值；费用类 d > c → (c-d) 负值
    Field("period_profit", "当期净利润",
        source=LEDGER_COMPOSITE(parts=[
            Part(codes=["6001", "6051", "6301", "6111", "6401", "6403",
                        "6601", "6602", "6603", "6801", "6701", "6711"],
                 side=None, sign=-1),
        ]),
    ),

    # 留存收益 = 期初留存 + 本年利润 + 利润分配
    Field("_opening_retained", None,
        source=OPENING("retained_earnings"),
    ),
    Field("retained_earnings", "留存收益",
        source=SUM_FIELDS(["_opening_retained", "current_year_profit",
                           "retained_earnings_prev"]),
    ),

    Field("total_equity", "所有者权益合计",
        source=SUM_FIELDS(["paid_in_capital", "retained_earnings",
                           "period_profit"]),
    ),

    Field("total_liabilities_and_equity", "负债和所有者权益总计",
        source=SUM_FIELDS(["total_liabilities", "total_equity"]),
    ),
]

BALANCE_CHECKS = [
    Check(left=["total_assets"], op="==",
          right=["total_liabilities", "total_equity"],
          desc="资产 = 负债 + 权益"),
]
