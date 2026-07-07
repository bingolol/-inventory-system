"""Journal builder"""
from decimal import Decimal
from datetime import datetime, date
from accounting_engine import AccountingError, AccountingErrorCode
from models import Product, StockMove
from models_finance import LedgerAccount, AccountMove, AccountMoveLine
from operation_result import EntityType

def _build_sale_order(self, source):
    self._check_required(source, ["partner_id", "total_with_tax",
                                   "total_without_tax", "tax_amount", "items"])

    total_with_tax = Decimal(str(source["total_with_tax"]))
    total_without_tax = Decimal(str(source["total_without_tax"]))
    tax_amount = Decimal(str(source["tax_amount"]))

    if total_without_tax + tax_amount != total_with_tax:
        raise AccountingError(AccountingErrorCode.AMOUNT_MISMATCH, "不含税 + 税额 != 价税合计")

    acct_conf = source.get("account_config", {})
    taxpayer_type = acct_conf.get("taxpayer_type") if "account_config" in source else "general"
    tax_code = "222103" if taxpayer_type == "small_scale" else "222101"

    lines = [
        {"account_code": "1122", "debit": total_with_tax, "credit": Decimal("0"),
         "partner_id": source["partner_id"], "partner_type": "customer"},
        {"account_code": "6001", "debit": Decimal("0"), "credit": total_without_tax},
        {"account_code": tax_code, "debit": Decimal("0"), "credit": tax_amount},
    ]

    total_cost = Decimal("0")
    for item in source["items"]:
        quantity = Decimal(str(item.get("quantity", 0)))
        unit_cost = item.get("unit_cost")
        # 单一真相源：unit_cost 为空时从 StockMove 获取实际出库成本，
        # 禁止用 Product.purchase_price 兜底（主数据静态字段，不反映实际采购成本）
        if unit_cost is None or Decimal(str(unit_cost)) == 0:
            move = self.db.query(StockMove).filter(
                StockMove.source_type == EntityType.SALE_ORDER,
                StockMove.source_id == source.get("source_id", 0),
                StockMove.product_id == item["product_id"],
            ).order_by(StockMove.id.desc()).first()
            if move and move.unit_cost_l2:
                unit_cost = move.unit_cost_l2
            else:
                # 非追踪库存商品（track_inventory=False）无 StockMove，成本为 0
                unit_cost = Decimal("0")
        total_cost += quantity * Decimal(str(unit_cost))

    if total_cost > 0:
        lines.append({"account_code": "6401", "debit": total_cost, "credit": Decimal("0")})
        lines.append({"account_code": "1405", "debit": Decimal("0"), "credit": total_cost})

    return lines, "SALE", {"balance_check": True}

def _build_sale_return(self, source):
    """销售退货部分冲红（与原 sale_order 借贷互换，按退货比例生成红字凭证）

    原销售凭证：
      借 1122 应收账款 (total_with_tax)
      贷 6001 主营业务收入 (total_without_tax)
      贷 222101/222103 销项税额 (tax_amount)
      借 6401 主营业务成本 (cost)
      贷 1405 库存商品 (cost)

    退货冲红（借贷互换）：
      借 6001 (revenue_return)        ← 冲减收入
      借 222101/222103 (tax_return)   ← 冲减销项税
      贷 1122 (total_with_tax_return) ← 冲减应收
      借 1405 (cost_return)           ← 库存回补
      贷 6401 (cost_return)           ← 冲减成本
    """
    self._check_required(source, ["partner_id", "total_with_tax",
                                   "total_without_tax", "tax_amount",
                                   "cost_return", "taxpayer_type"])

    total_with_tax = Decimal(str(source["total_with_tax"]))
    total_without_tax = Decimal(str(source["total_without_tax"]))
    tax_amount = Decimal(str(source["tax_amount"]))
    cost_return = Decimal(str(source["cost_return"]))
    taxpayer_type = source.get("taxpayer_type", "general")
    tax_code = "222103" if taxpayer_type == "small_scale" else "222101"

    lines = [
        # 冲减收入：借 6001
        {"account_code": "6001", "debit": total_without_tax, "credit": Decimal("0")},
        # 冲减销项税：借 222101/222103
        {"account_code": tax_code, "debit": tax_amount, "credit": Decimal("0")},
        # 冲减应收：贷 1122
        {"account_code": "1122", "debit": Decimal("0"), "credit": total_with_tax,
         "partner_id": source["partner_id"], "partner_type": "customer"},
    ]
    # 库存回补 + 冲减成本
    if cost_return > 0:
        lines.append({"account_code": "1405", "debit": cost_return, "credit": Decimal("0")})
        lines.append({"account_code": "6401", "debit": Decimal("0"), "credit": cost_return})

    return lines, "SRET", {"balance_check": True}


