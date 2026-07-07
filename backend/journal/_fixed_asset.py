"""Journal builder"""
from decimal import Decimal
from datetime import datetime, date
from accounting_engine import AccountingError, AccountingErrorCode
from models import Product, StockMove
from models_finance import LedgerAccount, AccountMove, AccountMoveLine

def _build_fixed_asset_purchase(self, source):
    """固定资产入账：借:1601（固定资产，不含税）借:222102（进项税额）贷:2202（应付账款，价税合计）

    小规模纳税人：全额进资产（价税合计），不抵扣进项税。
    一般纳税人：不含税金额进资产，税额单列 222102 抵扣。
    """
    self._check_required(source, ["original_value", "asset_id"])
    original = Decimal(str(source["original_value"]))
    tax_amount = Decimal(str(source.get("tax_amount", 0)))
    total_with_tax = Decimal(str(source.get("amount_with_tax", original + tax_amount)))
    partner_id = source.get("partner_id")

    acct_conf = source.get("account_config", {})
    enable_vat_deduction = acct_conf.get("enable_vat_deduction", True) if "account_config" in source else True

    # 小规模：全额进资产；一般纳税人：不含税进资产
    asset_cost = total_with_tax if not enable_vat_deduction else original

    lines = [
        {"account_code": "1601", "debit": asset_cost, "credit": Decimal("0")},
        {"account_code": "2202", "debit": Decimal("0"), "credit": total_with_tax,
         "partner_id": partner_id, "partner_type": "supplier"},
    ]
    if enable_vat_deduction and tax_amount > 0:
        lines.insert(1, {"account_code": "222102", "debit": tax_amount, "credit": Decimal("0")})

    return lines, "GEN", {"balance_check": True}

def _build_intangible_asset_purchase(self, source):
    """无形资产入账：借:1701（无形资产，不含税）借:222102（进项税额）贷:2202（应付账款，价税合计）

    小规模纳税人：全额进资产（价税合计），不抵扣进项税。
    一般纳税人：不含税金额进资产，税额单列 222102 抵扣。
    """
    self._check_required(source, ["original_value", "asset_id"])
    original = Decimal(str(source["original_value"]))
    tax_amount = Decimal(str(source.get("tax_amount", 0)))
    total_with_tax = Decimal(str(source.get("amount_with_tax", original + tax_amount)))
    partner_id = source.get("partner_id")

    acct_conf = source.get("account_config", {})
    enable_vat_deduction = acct_conf.get("enable_vat_deduction", True) if "account_config" in source else True

    # 小规模：全额进资产；一般纳税人：不含税进资产
    asset_cost = total_with_tax if not enable_vat_deduction else original

    lines = [
        {"account_code": "1701", "debit": asset_cost, "credit": Decimal("0")},
        {"account_code": "2202", "debit": Decimal("0"), "credit": total_with_tax,
         "partner_id": partner_id, "partner_type": "supplier"},
    ]
    if enable_vat_deduction and tax_amount > 0:
        lines.insert(1, {"account_code": "222102", "debit": tax_amount, "credit": Decimal("0")})

    return lines, "GEN", {"balance_check": True}

def _build_depreciation(self, source):
    """折旧/摊销凭证：借:6601（管理费用）贷:累计折旧/累计摊销

    source 中可指定 contra_account_code（固定资产 1602 / 无形资产 1702），
    未指定时默认使用 1602。
    """
    self._check_required(source, ["amount"])
    amount = Decimal(str(source["amount"]))
    contra_account_code = source.get("contra_account_code", "1602")
    return [
        {"account_code": "6601", "debit": amount, "credit": Decimal("0")},
        {"account_code": contra_account_code, "debit": Decimal("0"), "credit": amount},
    ], "FA", {"balance_check": True}

def _build_asset_disposal(self, source):
    """处置凭证：借:累计折旧/摊销 借:1002(收款) 贷:资产原值科目 + 损益科目

    小企业会计准则：资产处置损益一律计入营业外收支，不使用"资产处置损益"科目。
    处置价格 > 账面净值 → 营业外收入（6301）
    处置价格 < 账面净值 → 营业外支出（6701）

    source 中可指定 asset_account_code / contra_account_code，
    未指定时默认固定资产 1601/1602。
    """
    self._check_required(source, ["original_value", "accumulated_depreciation", "net_value"])
    original = Decimal(str(source["original_value"]))
    accumulated = Decimal(str(source["accumulated_depreciation"]))
    net_value = Decimal(str(source["net_value"]))
    disposal_price = Decimal(str(source.get("disposal_price", 0)))
    diff = Decimal(str(source.get("diff", disposal_price - net_value)))
    asset_account_code = source.get("asset_account_code", "1601")
    contra_account_code = source.get("contra_account_code", "1602")

    lines = [
        {"account_code": contra_account_code, "debit": accumulated, "credit": Decimal("0")},
        {"account_code": asset_account_code, "debit": Decimal("0"), "credit": original},
    ]

    # 收到的处置款 → 借:银行存款
    if disposal_price > 0:
        lines.append({"account_code": "1002", "debit": disposal_price, "credit": Decimal("0")})

    if diff > 0:
        # 赚了：贷:6301（营业外收入）— 小企业准则不计入资产处置损益
        lines.append({"account_code": "6301", "debit": Decimal("0"), "credit": diff})
    elif diff < 0:
        # 亏了：借:6701（营业外支出）
        lines.append({"account_code": "6701", "debit": abs(diff), "credit": Decimal("0")})

    return lines, "FA", {"balance_check": True}


