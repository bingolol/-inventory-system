"""Journal builder"""
from decimal import Decimal
from datetime import datetime, date
from accounting_engine import AccountingError, AccountingErrorCode
from models import Product, StockMove
from models_finance import LedgerAccount, AccountMove, AccountMoveLine

def _build_receipt(self, source):
    self._check_required(source, ["amount"])

    amount = Decimal(str(source["amount"]))
    partner_id = source.get("partner_id")
    cr_line = {"account_code": "1122", "debit": Decimal("0"), "credit": amount}
    if partner_id is not None:
        cr_line["partner_id"] = partner_id
        cr_line["partner_type"] = "customer"

    bank_account_id = source.get("bank_account_id")
    if bank_account_id is not None:
        dr_line = {"account_code": "1002", "debit": amount, "credit": Decimal("0")}
    else:
        dr_line = {"account_code": "1001", "debit": amount, "credit": Decimal("0")}

    return [
        dr_line,
        cr_line,
    ], "BNK", {"balance_check": True}

def _build_payment(self, source):
    self._check_required(source, ["amount"])

    amount = Decimal(str(source["amount"]))
    withholding_tax = Decimal(str(source.get("withholding_tax_amount", 0) or 0))
    partner_id = source.get("partner_id")
    debit_account = source.get("debit_account_code", "2202")

    # 借方:应付科目(应发金额 = 实发 + 代扣个税)
    gross = amount + withholding_tax
    dr_line = {"account_code": debit_account, "debit": gross, "credit": Decimal("0")}
    if partner_id is not None:
        dr_line["partner_id"] = partner_id
        dr_line["partner_type"] = "supplier"

    # 贷方1:银行存款/库存现金(实发金额)
    bank_account_id = source.get("bank_account_id")
    cash_code = "1002" if bank_account_id is not None else "1001"
    cr_cash = {"account_code": cash_code, "debit": Decimal("0"), "credit": amount}

    lines = [dr_line, cr_cash]

    # 贷方2:应交个人所得税(代扣金额) — 仅工资场景有值
    # 业务因果链 E:发放工资时借2211(应发)、贷1002(实发)、贷222108(代扣个税)
    if withholding_tax > 0:
        withholding_account = source.get("withholding_tax_account_code", "222108")
        lines.append({"account_code": withholding_account, "debit": Decimal("0"), "credit": withholding_tax})

    return lines, "BNK", {"balance_check": True}

def _build_expense(self, source):
    self._check_required(source, ["amount", "expense_account_code"])

    amount = Decimal(str(source["amount"]))
    bank_account_id = source.get("bank_account_id")
    credit_account = source.get("credit_account_code", "2202")

    if bank_account_id is not None:
        lines = [
            {"account_code": source["expense_account_code"], "debit": amount, "credit": Decimal("0")},
            {"account_code": "1002", "debit": Decimal("0"), "credit": amount},
        ]
    else:
        lines = [
            {"account_code": source["expense_account_code"], "debit": amount, "credit": Decimal("0")},
            {"account_code": credit_account, "debit": Decimal("0"), "credit": amount,
             "partner_id": source.get("partner_id"), "partner_type": source.get("partner_type", "supplier")},
        ]

    return lines, "GEN", {"balance_check": True}


