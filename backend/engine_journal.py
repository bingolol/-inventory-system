"""凭证模板引擎 - 所有余额变更的唯一入口"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from models import Product, StockMove
from models_finance import (
    LedgerAccount, AccountMove, AccountMoveLine, AccountJournal,
    generate_voucher_number,
)
from accounting_engine import AccountingError, AccountingErrorCode
from engine_ledger import LedgerEngine
from lineage import writes, reads, derives, TIER_L1, TIER_L2
from operation_result import EntityType
from rules import enforce_rules


# 税金及附加明细科目 -> 应交税费对应科目
TAX_SURCHARGE_EXPENSE_TO_PAYABLE = {
    "640301": "222113",  # 消费税
    "640302": "222110",  # 城市维护建设税
    "640303": "222111",  # 教育费附加
    "640304": "222112",  # 地方教育附加
    "640305": "222114",  # 资源税
    "640306": "222115",  # 土地增值税
    "640307": "222116",  # 房产税
    "640308": "222117",  # 城镇土地使用税
    "640309": "222118",  # 车船税
    "640310": "222119",  # 印花税
    "640311": "222120",  # 环境保护税
}


class JournalEngine:
    """凭证模板引擎 - 每种凭证类型对应一个硬编码方法"""

    def __init__(self, db: Session):
        self.db = db
        self.ledger_engine = LedgerEngine(db)

    def post(self, ledger_id: int, move_type: str, source: dict) -> AccountMove:
        lines, journal_code, validation = self._build(move_type, source)

        self._validate(lines, validation)

        date_val = source.get("date")
        if isinstance(date_val, date) and not isinstance(date_val, str):
            date_str = date_val.isoformat()
        else:
            date_str = str(date_val or "")

        move_name = source.get("move_name")
        name = move_name if move_name else generate_voucher_number(self.db, ledger_id, journal_code, date_str)
        move_date = date_val if isinstance(date_val, date) else datetime.strptime(date_str, "%Y-%m-%d").date()

        move = AccountMove(
            ledger_id=ledger_id,
            name=name,
            move_type=move_type,
            date_l1=move_date,
            state="posted",
            source_model=source.get("source_model"),
            source_id=source.get("source_id"),
            amount_total_l2=sum(Decimal(str(l["debit"])) for l in lines),
            is_reversal=source.get("is_reversal", False),
            reversed_entry_id=source.get("reversed_entry_id"),
        )
        self.db.add(move)
        self.db.flush()

        for line_data in lines:
            debit_val = Decimal(str(line_data.get("debit", 0)))
            credit_val = Decimal(str(line_data.get("credit", 0)))
            residual = debit_val or credit_val

            line = AccountMoveLine(
                move_id=move.id,
                ledger_account_id=self._get_leaf_account_id(ledger_id, line_data["account_code"]),
                debit_l2=debit_val,
                credit_l2=credit_val,
                partner_id=line_data.get("partner_id"),
                partner_type=line_data.get("partner_type"),
                amount_residual_l2=residual,
            )
            self.db.add(line)
            self.db.flush()

            self.ledger_engine.update_balance(line)

        # AS-01 借贷平衡后写校验(纵深防御:即使 _validate 漏检,DB 层兜底)
        enforce_rules(self.db, ["AS-01"], {"move_id": move.id})

        return move

    def _build(self, move_type: str, source: dict):
        builders = {
            EntityType.SALE_ORDER:              self._build_sale_order,
            EntityType.PURCHASE_ORDER:          self._build_purchase_order,
            EntityType.RECEIPT:                 self._build_receipt,
            EntityType.PAYMENT:                 self._build_payment,
            EntityType.EXPENSE:                 self._build_expense,
            EntityType.DEPRECIATION:            self._build_depreciation,
            EntityType.ASSET_DISPOSAL:          self._build_asset_disposal,
            EntityType.FIXED_ASSET_PURCHASE:    self._build_fixed_asset_purchase,
            EntityType.INTANGIBLE_ASSET_PURCHASE: self._build_intangible_asset_purchase,
            EntityType.OPENING_BALANCE:         self._build_opening_balance,
            EntityType.CASH_FLOW:               self._build_cash_flow,
            EntityType.SALE_RETURN:             self._build_sale_return,
            EntityType.PURCHASE_RETURN:         self._build_purchase_return,
            EntityType.TAX_SURCHARGE:           self._build_tax_surcharge,
            EntityType.TAX_INCOME:              self._build_tax_income,
            EntityType.TAX_INCOME_REVERSAL:     self._build_tax_income_reversal,
            EntityType.VAT_TRANSFER_OUT:        self._build_vat_transfer_out,
            EntityType.VAT_EXEMPTION:           self._build_vat_exemption,
            EntityType.BANK_FEE_ENTRY:          self._build_bank_fee_entry,
            EntityType.PERSONAL_ADVANCE:        self._build_personal_advance,
            EntityType.PERSONAL_ADVANCE_REPAYMENT: self._build_personal_advance_repay,
            EntityType.PERIOD_CLOSE:            self._build_period_close,
            EntityType.YEAR_CLOSE:              self._build_year_close,
            EntityType.REVERSE_ENTRY:           self._build_reverse_entry,
        }
        builder = builders.get(move_type)
        if not builder:
            raise AccountingError(AccountingErrorCode.UNKNOWN_MOVE_TYPE,
                f"未知凭证类型: {move_type}。支持 "
                f"sale_order/purchase_order/receipt/payment/expense/depreciation/asset_disposal/fixed_asset_purchase/opening_balance/cash_flow")
        return builder(source)

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
                    StockMove.source_type == "sale_order",
                    StockMove.source_id == source.get("source_id", 0),
                    StockMove.product_id == item["product_id"],
                ).first()
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

        # 小规模纳税人：全额进成本（价税合计）；一般纳税人：不含税金额进成本
        inventory_cost = total_with_tax if not enable_vat_deduction else total_without_tax
        lines = [
            {"account_code": "1405", "debit": inventory_cost, "credit": Decimal("0")},
            {"account_code": "2202", "debit": Decimal("0"), "credit": total_with_tax,
             "partner_id": source["partner_id"], "partner_type": "supplier"},
        ]

        if enable_vat_deduction and tax_amount > 0:
            lines.insert(1, {"account_code": "222102", "debit": tax_amount, "credit": Decimal("0")})

        return lines, "PURCHASE", {"balance_check": True}

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

    def _build_period_close(self, source):
        """损益结转：按传入的 lines 生成"""
        return self._build_from_lines(source), "GEN", {"balance_check": True}

    def _build_year_close(self, source):
        """年结：按传入的 lines 生成"""
        return self._build_from_lines(source), "GEN", {"balance_check": True}

    def _build_from_lines(self, source):
        self._check_required(source, ["lines"])
        result = []
        for line in source["lines"]:
            result.append({
                "account_code": line["account_code"],
                "debit": Decimal(str(line.get("debit", 0))),
                "credit": Decimal(str(line.get("credit", 0))),
            })
        return result

    def _build_opening_balance(self, source):
        """期初余额过账：按传入的 lines 生成"""
        return self._build_from_lines(source), "GEN", {"balance_check": True}

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
        """转出未交增值税（一般纳税人月结）

        标准三步式结转：
          1. Dr 222101(销项税额) / Cr 222106(转出未交增值税) — 结转销项
          2. Dr 222106(转出未交增值税) / Cr 222107(未交增值税) — 转出未交

        合并后：Dr 222101 / Cr 222107（222106 借贷相抵为 0，可省略）
        不能只 Dr 222106 / Cr 222107 而漏掉 222101，否则 222101 余额永远不会被清零，
        导致 BS 应交税费项目重复计算（销项税 + 未交增值税双计）。
        """
        self._check_required(source, ["amount"])
        amount = Decimal(str(source["amount"]))
        return [
            {"account_code": "222101", "debit": amount, "credit": Decimal("0")},
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

    @reads("AccountMove.amount_total_l2", tier=TIER_L2, source="engine")
    @reads("AccountMoveLine.debit_l2", tier=TIER_L2, source="engine")
    @reads("AccountMoveLine.credit_l2", tier=TIER_L2, source="engine")
    @reads("AccountMoveLine.amount_residual_l2", tier=TIER_L2, source="engine")
    def _build_reverse_entry(self, source):
        """通用冲红凭证：读取原凭证，按行借贷互换生成红字分录

        source 必填字段:
        - original_move_id: 被冲红的原凭证 ID
        """
        self._check_required(source, ["original_move_id"])
        original_id = source["original_move_id"]
        original = self.db.query(AccountMove).filter(
            AccountMove.id == original_id,
            AccountMove.is_reversal == False,
        ).first()
        if not original:
            raise AccountingError(
                AccountingErrorCode.LINE_NOT_FOUND,
                f"找不到可冲红的原凭证: move_id={original_id}",
            )

        lines = []
        for ol in original.line_ids:
            lines.append({
                "account_code": self._get_account_code(ol.ledger_account_id),
                "debit": ol.credit_l2 or Decimal("0"),
                "credit": ol.debit_l2 or Decimal("0"),
                "partner_id": ol.partner_id,
                "partner_type": ol.partner_type,
            })

        # 沿用原凭证 journal prefix，使凭证号序列与原业务类型一致
        journal_code = original.name.split("-")[0] if "-" in original.name else "REV"
        return lines, journal_code, {"balance_check": True}

    def _validate(self, lines: list, validation: dict):
        if validation.get("balance_check"):
            total_debit = sum(l["debit"] for l in lines)
            total_credit = sum(l["credit"] for l in lines)
            if abs(total_debit - total_credit) > Decimal("0.01"):
                raise AccountingError(AccountingErrorCode.BALANCE_NOT_EQUAL,
                    f"借贷不平衡: 借={total_debit}, 贷={total_credit}")

    def _check_required(self, source: dict, fields: list):
        for field in fields:
            if field not in source or source[field] is None:
                raise AccountingError(AccountingErrorCode.FIELD_REQUIRED, f"{field} 为必填")

    def _get_leaf_account_id(self, ledger_id: int, account_code: str) -> int:
        if account_code.startswith("DYNAMIC_"):
            acct_type = account_code.replace("DYNAMIC_", "").lower()
            account = self.db.query(LedgerAccount).filter(
                LedgerAccount.ledger_id == ledger_id,
                LedgerAccount.account_type == acct_type,
                LedgerAccount.is_leaf == True,
            ).first()
            if not account:
                raise AccountingError(AccountingErrorCode.ACCOUNT_NOT_FOUND,
                    f"找不到 {acct_type} 类型叶子科目，请检查科目表")
            return account.id

        account = self.db.query(LedgerAccount).filter(
            LedgerAccount.ledger_id == ledger_id,
            LedgerAccount.code == account_code,
        ).first()
        if not account:
            raise AccountingError(AccountingErrorCode.ACCOUNT_NOT_FOUND,
                f"科目编码不存在: {account_code}")
        return account.id

    def _get_account_code(self, ledger_account_id: int) -> str:
        """由 ledger_account_id 反查科目编码（冲红时复用原分录科目）"""
        account = self.db.query(LedgerAccount).filter(
            LedgerAccount.id == ledger_account_id,
        ).first()
        if not account:
            raise AccountingError(AccountingErrorCode.ACCOUNT_NOT_FOUND,
                f"科目不存在: id={ledger_account_id}")
        return account.code
