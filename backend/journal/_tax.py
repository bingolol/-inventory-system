"""Journal builder"""
from decimal import Decimal
from datetime import datetime, date
from accounting_engine import AccountingError, AccountingErrorCode
from models import Product, StockMove
from models_finance import LedgerAccount, AccountMove, AccountMoveLine
from . import TAX_SURCHARGE_EXPENSE_TO_PAYABLE

def _build_tax_surcharge(self, source):
    """计提附加税

    兼容旧模式：source["amount"] 单金额 → 6403/222104。
    新模式：source["taxes"] = {expense_code: amount, ...}，分别计入明细科目。
    """
    if "taxes" in source:
        lines = []
        for expense_code, amount in source["taxes"].items():
            amount = Decimal(str(amount))
            if amount <= Decimal("0"):
                continue
            # expense_code 形如 "640302"，对应 payable_code "222110"
            payable_code = TAX_SURCHARGE_EXPENSE_TO_PAYABLE.get(expense_code)
            if not payable_code:
                raise ValueError(f"附加税明细科目 {expense_code} 未配置对应应交科目")
            lines.append({"account_code": expense_code, "debit": amount, "credit": Decimal("0")})
            lines.append({"account_code": payable_code, "debit": Decimal("0"), "credit": amount})
        if not lines:
            return [], "TAX", {"balance_check": False}
        return lines, "TAX", {"balance_check": True}

    self._check_required(source, ["amount"])
    amount = Decimal(str(source["amount"]))
    return [
        {"account_code": "6403", "debit": amount, "credit": Decimal("0")},
        {"account_code": "222104", "debit": Decimal("0"), "credit": amount},
    ], "TAX", {"balance_check": True}

def _build_tax_income(self, source):
    """计提所得税：借:6801（所得税费用）贷:222105（应交所得税）"""
    self._check_required(source, ["amount"])
    amount = Decimal(str(source["amount"]))
    return [
        {"account_code": "6801", "debit": amount, "credit": Decimal("0")},
        {"account_code": "222105", "debit": Decimal("0"), "credit": amount},
    ], "TAX", {"balance_check": True}

def _build_tax_income_reversal(self, source):
    """冲回所得税：借:222105（应交所得税）贷:6801（所得税费用）"""
    self._check_required(source, ["amount"])
    amount = Decimal(str(source["amount"]))
    return [
        {"account_code": "222105", "debit": amount, "credit": Decimal("0")},
        {"account_code": "6801", "debit": Decimal("0"), "credit": amount},
    ], "TAX", {"balance_check": True}

def _build_vat_transfer_out(self, source):
    """转出未交增值税：dr:222106(转出未交增值税) cr:222107(未交增值税)"""
    self._check_required(source, ["amount"])
    amount = Decimal(str(source["amount"]))
    return [
        {"account_code": "222106", "debit": amount, "credit": Decimal("0")},
        {"account_code": "222107", "debit": Decimal("0"), "credit": amount},
    ], "VAT", {"balance_check": True}

def _build_vat_exemption(self, source):
    """增值税减免结转：dr:222103(应交增值税-小规模) cr:6301(营业外收入-税收减免)

    依据：财税〔2008〕151号 — 直接减免的增值税属于财政性资金，
    需计入当年收入总额缴纳企业所得税。
    实务分录：借 应交税费-应交增值税 贷 营业外收入-增值税减免
    """
    self._check_required(source, ["amount"])
    amount = Decimal(str(source["amount"]))
    return [
        {"account_code": "222103", "debit": amount, "credit": Decimal("0")},
        {"account_code": "6301", "debit": Decimal("0"), "credit": amount},
    ], "VAT", {"balance_check": True}


