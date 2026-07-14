"""Journal builder"""
from decimal import Decimal
from datetime import datetime, date
from accounting_engine import AccountingError, AccountingErrorCode
from models import Product, StockMove
from models_finance import LedgerAccount, AccountMove, AccountMoveLine

def _build_purchase_order(self, source):
    self._check_required(source, ["partner_id", "total_with_tax",
                                   "total_without_tax", "tax_amount"])

    total_with_tax = Decimal(str(source["total_with_tax"]))
    total_without_tax = Decimal(str(source["total_without_tax"]))
    tax_amount = Decimal(str(source["tax_amount"]))

    if total_without_tax + tax_amount != total_with_tax:
        raise AccountingError(AccountingErrorCode.AMOUNT_MISMATCH, "不含税 + 税额 != 价税合计")

    acct_conf = source.get("account_config", {})
    enable_vat_deduction = acct_conf.get("enable_vat_deduction") if "account_config" in source else True

    items = source.get("items", [])
    inventory_cost = Decimal("0")
    service_cost = Decimal("0")

    for item in items:
        track_inv = item.get("track_inventory", True)
        if enable_vat_deduction:
            line_cost = Decimal(str(item.get("total_price", "0")))
        else:
            line_cost = Decimal(str(item.get("total_with_tax", "0")))
        if track_inv:
            inventory_cost += line_cost
        else:
            service_cost += line_cost

    if not items:
        raise AccountingError(AccountingErrorCode.INVALID_SOURCE, "采购凭证缺少 items，无法确定科目归属")
    if inventory_cost == 0 and service_cost == 0:
        raise AccountingError(AccountingErrorCode.AMOUNT_MISMATCH, "采购凭证 items 金额拆分结果均为 0")

    lines = []
    if inventory_cost > 0:
        lines.append({"account_code": "1405", "debit": inventory_cost, "credit": Decimal("0")})
    if service_cost > 0:
        lines.append({"account_code": "6601", "debit": service_cost, "credit": Decimal("0")})
    if enable_vat_deduction and tax_amount > 0:
        lines.append({"account_code": "222102", "debit": tax_amount, "credit": Decimal("0")})
    lines.append({"account_code": "2202", "debit": Decimal("0"), "credit": total_with_tax,
                  "partner_id": source["partner_id"], "partner_type": "supplier"})

    return lines, "PURCHASE", {"balance_check": True}

def _build_purchase_return(self, source):
    """采购退货部分冲红（与原 purchase_order 借贷互换，按退货比例生成红字凭证）

    原采购凭证（一般纳税人）：
      借 1405 库存商品 (total_without_tax)
      借 222102 进项税额 (tax_amount)
      贷 2202 应付账款 (total_with_tax)

    原采购凭证（小规模）：
      借 1405 库存商品 (total_with_tax)  ← 价税合计进成本
      贷 2202 应付账款 (total_with_tax)

    退货冲红：
      借 2202 (total_with_tax_return)   ← 冲减应付
      贷 1405 (inventory_cost_return)    ← 库存退回
      贷 222102 (tax_return)              ← 进项税额转出（仅一般纳税人）
    """
    self._check_required(source, ["partner_id", "total_with_tax",
                                   "inventory_cost_return",
                                   "enable_vat_deduction"])

    total_with_tax = Decimal(str(source["total_with_tax"]))
    inventory_cost_return = Decimal(str(source["inventory_cost_return"]))
    enable_vat_deduction = source.get("enable_vat_deduction", True)
    tax_return = Decimal(str(source.get("tax_return", "0")))

    lines = [
        # 冲减应付：借 2202
        {"account_code": "2202", "debit": total_with_tax, "credit": Decimal("0"),
         "partner_id": source["partner_id"], "partner_type": "supplier"},
        # 库存退回：贷 1405
        {"account_code": "1405", "debit": Decimal("0"), "credit": inventory_cost_return},
    ]
    # 进项税额转出（仅一般纳税人）
    if enable_vat_deduction and tax_return > 0:
        lines.append({"account_code": "222102", "debit": Decimal("0"), "credit": tax_return})

    return lines, "PRET", {"balance_check": True}


