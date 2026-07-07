"""Journal builder"""
from decimal import Decimal
from datetime import datetime, date
from accounting_engine import AccountingError, AccountingErrorCode
from models import Product, StockMove
from models_finance import LedgerAccount, AccountMove, AccountMoveLine

def _build_opening_balance(self, source):
    """期初余额过账：动态科目，按传入的 lines 生成"""
    self._check_required(source, ["lines"])
    result = []
    for line in source["lines"]:
        result.append({
            "account_code": line["account_code"],
            "debit": Decimal(str(line.get("debit", 0))),
            "credit": Decimal(str(line.get("credit", 0))),
        })
    return result, "GEN", {"balance_check": True}

def _build_cash_flow(self, source):
    """现金流水：inflow → 借:1002 贷:对应科目，outflow → 借:对应科目 贷:1002"""
    self._check_required(source, ["amount", "flow_category", "direction"])
    amount = Decimal(str(source["amount"]))
    direction = source["direction"]
    if direction == "inflow":
        return [
            {"account_code": "1002", "debit": amount, "credit": Decimal("0")},
            {"account_code": source["counter_account"], "debit": Decimal("0"), "credit": amount},
        ], "GEN", {"balance_check": True}
    else:
        return [
            {"account_code": source["counter_account"], "debit": amount, "credit": Decimal("0")},
            {"account_code": "1002", "debit": Decimal("0"), "credit": amount},
        ], "GEN", {"balance_check": True}

def _build_bank_fee_entry(self, source):
    """银行手续费/利息: dr 6603 cr 1002 或 dr 1002 cr 6603"""
    self._check_required(source, ["amount", "direction"])
    if source["direction"] not in ("in", "out"):
        raise AccountingError(AccountingErrorCode.VALIDATION_ERROR,
            f"direction 必须是 'in' 或 'out', 收到 '{source['direction']}'")
    amt = Decimal(str(source["amount"]))
    if source["direction"] == "out":
        return [
            {"account_code": "6603", "debit": amt, "credit": Decimal("0")},
            {"account_code": "1002", "debit": Decimal("0"), "credit": amt},
        ], "BNK", {"balance_check": True}
    else:
        return [
            {"account_code": "1002", "debit": amt, "credit": Decimal("0")},
            {"account_code": "6603", "debit": Decimal("0"), "credit": amt},
        ], "BNK", {"balance_check": True}

def _build_personal_advance(self, source):
    """个人垫付（其他应付款）：dr 借方科目(默认6601) cr 2241 其他应付款

    业务场景：老板/员工用个人资金替公司垫付费用，公司形成一笔对个人的负债。
    借方科目由 debit_account_code 决定用途（费用/存货/资产）。
    """
    self._check_required(source, ["amount", "debit_account_code"])
    amt = Decimal(str(source["amount"]))
    debit_code = source["debit_account_code"]
    return [
        {"account_code": debit_code, "debit": amt, "credit": Decimal("0")},
        {"account_code": "2241", "debit": Decimal("0"), "credit": amt,
         "partner_id": source.get("partner_id"), "partner_type": source.get("partner_type", "advancer")},
    ], "GEN", {"balance_check": True}

def _build_period_close(self, source):
    """期间损益结转：直接使用 source["lines"]，由 PeriodCloseEngine 预构建分录"""
    self._check_required(source, ["lines"])
    result = []
    for line in source["lines"]:
        result.append({
            "account_code": line["account_code"],
            "debit": Decimal(str(line.get("debit", 0))),
            "credit": Decimal(str(line.get("credit", 0))),
        })
    return result, "PNL", {"balance_check": True}


def _build_year_close(self, source):
    """年末结转：4103→4104，由 PeriodCloseEngine 预构建分录"""
    self._check_required(source, ["lines"])
    result = []
    for line in source["lines"]:
        result.append({
            "account_code": line["account_code"],
            "debit": Decimal(str(line.get("debit", 0))),
            "credit": Decimal(str(line.get("credit", 0))),
        })
    return result, "GEN", {"balance_check": True}


def _build_personal_advance_repay(self, source):
    """偿还个人垫付：dr 2241 其他应付款 cr 1002 银行存款 / 1001 库存现金

    带银行账户 → 贷 1002（同时由调用方生成 BankTransaction）
    不带银行账户 → 贷 1001 库存现金
    """
    self._check_required(source, ["amount"])
    amt = Decimal(str(source["amount"]))
    bank_account_id = source.get("bank_account_id")
    credit_code = "1002" if bank_account_id is not None else "1001"
    return [
        {"account_code": "2241", "debit": amt, "credit": Decimal("0"),
         "partner_id": source.get("partner_id"), "partner_type": source.get("partner_type", "advancer")},
        {"account_code": credit_code, "debit": Decimal("0"), "credit": amt},
    ], "BNK", {"balance_check": True}


