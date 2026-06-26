"""凭证模板引擎 - 所有余额变更的唯一入口"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from models import Product
from models_finance import (
    LedgerAccount, AccountMove, AccountMoveLine, AccountJournal,
    generate_voucher_number, AccountingError,
)
from engine_ledger import LedgerEngine


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

        name = generate_voucher_number(self.db, ledger_id, journal_code, date_str)
        move_date = date_val if isinstance(date_val, date) else datetime.strptime(date_str, "%Y-%m-%d").date()

        move = AccountMove(
            ledger_id=ledger_id,
            name=name,
            move_type=move_type,
            date=move_date,
            state="posted",
            source_model=source.get("source_model"),
            source_id=source.get("source_id"),
            amount_total=sum(Decimal(str(l["debit"])) for l in lines),
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
                debit=debit_val,
                credit=credit_val,
                partner_id=line_data.get("partner_id"),
                partner_type=line_data.get("partner_type"),
                amount_residual=residual,
            )
            self.db.add(line)
            self.db.flush()

            self.ledger_engine.update_balance(line)

        return move

    def _build(self, move_type: str, source: dict):
        builders = {
            "sale_order":       self._build_sale_order,
            "purchase_order":   self._build_purchase_order,
            "receipt":          self._build_receipt,
            "payment":          self._build_payment,
            "expense":          self._build_expense,
            "depreciation":     self._build_depreciation,
            "asset_disposal":   self._build_asset_disposal,
        }
        builder = builders.get(move_type)
        if not builder:
            raise AccountingError("UNKNOWN_MOVE_TYPE",
                f"未知凭证类型: {move_type}。支持 "
                f"sale_order/purchase_order/receipt/payment/expense/depreciation/asset_disposal")
        return builder(source)

    def _build_sale_order(self, source):
        self._check_required(source, ["partner_id", "total_with_tax",
                                       "total_without_tax", "tax_amount", "items"])

        total_with_tax = Decimal(str(source["total_with_tax"]))
        total_without_tax = Decimal(str(source["total_without_tax"]))
        tax_amount = Decimal(str(source["tax_amount"]))

        if total_without_tax + tax_amount != total_with_tax:
            raise AccountingError("AMOUNT_MISMATCH", "不含税 + 税额 != 价税合计")

        acct_conf = source.get("account_config", {})
        taxpayer_type = acct_conf.get("taxpayer_type") if "account_config" in source else "general"
        tax_code = "222103" if taxpayer_type == "small_scale" else "222101"

        lines = [
            {"account_code": "1122", "debit": total_with_tax, "credit": Decimal("0"),
             "partner_id": source["partner_id"], "partner_type": "customer"},
            {"account_code": "5001", "debit": Decimal("0"), "credit": total_without_tax},
            {"account_code": tax_code, "debit": Decimal("0"), "credit": tax_amount},
        ]

        total_cost = Decimal("0")
        for item in source["items"]:
            quantity = Decimal(str(item.get("quantity", 0)))
            unit_cost = item.get("unit_cost")
            if unit_cost is None:
                product = self.db.query(Product).filter(
                    Product.id == item["product_id"]
                ).first()
                unit_cost = product.purchase_price if product else Decimal("0")
            total_cost += quantity * Decimal(str(unit_cost))

        if total_cost > 0:
            lines.append({"account_code": "5401", "debit": total_cost, "credit": Decimal("0")})
            lines.append({"account_code": "1405", "debit": Decimal("0"), "credit": total_cost})

        return lines, "SALE", {"balance_check": True}

    def _build_purchase_order(self, source):
        self._check_required(source, ["partner_id", "total_with_tax",
                                       "total_without_tax", "tax_amount"])

        total_with_tax = Decimal(str(source["total_with_tax"]))
        total_without_tax = Decimal(str(source["total_without_tax"]))
        tax_amount = Decimal(str(source["tax_amount"]))

        if total_without_tax + tax_amount != total_with_tax:
            raise AccountingError("AMOUNT_MISMATCH", "不含税 + 税额 != 价税合计")

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
        partner_id = source.get("partner_id")
        dr_line = {"account_code": "2202", "debit": amount, "credit": Decimal("0")}
        if partner_id is not None:
            dr_line["partner_id"] = partner_id
            dr_line["partner_type"] = "supplier"

        bank_account_id = source.get("bank_account_id")
        if bank_account_id is not None:
            cr_line = {"account_code": "1002", "debit": Decimal("0"), "credit": amount}
        else:
            cr_line = {"account_code": "1001", "debit": Decimal("0"), "credit": amount}

        return [
            dr_line,
            cr_line,
        ], "BNK", {"balance_check": True}

    def _build_expense(self, source):
        self._check_required(source, ["amount", "expense_account_code"])

        amount = Decimal(str(source["amount"]))
        bank_account_id = source.get("bank_account_id")

        if bank_account_id is not None:
            lines = [
                {"account_code": source["expense_account_code"], "debit": amount, "credit": Decimal("0")},
                {"account_code": "1002", "debit": Decimal("0"), "credit": amount},
            ]
        else:
            lines = [
                {"account_code": source["expense_account_code"], "debit": amount, "credit": Decimal("0")},
                {"account_code": "2202", "debit": Decimal("0"), "credit": amount,
                 "partner_id": source.get("partner_id"), "partner_type": source.get("partner_type", "supplier")},
            ]

        return lines, "GEN", {"balance_check": True}

    def _build_depreciation(self, source):
        """折旧凭证：借:6602（管理费用—折旧费）贷:1602（累计折旧）"""
        self._check_required(source, ["amount"])
        amount = Decimal(str(source["amount"]))
        return [
            {"account_code": "5602", "debit": amount, "credit": Decimal("0")},
            {"account_code": "1602", "debit": Decimal("0"), "credit": amount},
        ], "FA", {"balance_check": True}

    def _build_asset_disposal(self, source):
        """处置凭证：借:1602 借:1002(收款) 贷:1601 + 损益科目"""
        self._check_required(source, ["original_value", "accumulated_depreciation", "net_value"])
        original = Decimal(str(source["original_value"]))
        accumulated = Decimal(str(source["accumulated_depreciation"]))
        net_value = Decimal(str(source["net_value"]))
        disposal_price = Decimal(str(source.get("disposal_price", 0)))
        diff = Decimal(str(source.get("diff", disposal_price - net_value)))

        lines = [
            {"account_code": "1602", "debit": accumulated, "credit": Decimal("0")},
            {"account_code": "1601", "debit": Decimal("0"), "credit": original},
        ]

        # 收到的处置款 → 借:银行存款
        if disposal_price > 0:
            lines.append({"account_code": "1002", "debit": disposal_price, "credit": Decimal("0")})

        if diff > 0:
            # 赚了：贷:6111（资产处置收益）
            lines.append({"account_code": "6111", "debit": Decimal("0"), "credit": diff})
        elif diff < 0:
            # 亏了：借:6711（营业外支出）
            lines.append({"account_code": "6711", "debit": abs(diff), "credit": Decimal("0")})

        return lines, "FA", {"balance_check": True}

    def _validate(self, lines: list, validation: dict):
        if validation.get("balance_check"):
            total_debit = sum(l["debit"] for l in lines)
            total_credit = sum(l["credit"] for l in lines)
            if abs(total_debit - total_credit) > Decimal("0.01"):
                raise AccountingError("BALANCE_NOT_EQUAL",
                    f"借贷不平衡: 借={total_debit}, 贷={total_credit}")

    def _check_required(self, source: dict, fields: list):
        for field in fields:
            if field not in source or source[field] is None:
                raise AccountingError("FIELD_REQUIRED", f"{field} 为必填")

    def _get_leaf_account_id(self, ledger_id: int, account_code: str) -> int:
        if account_code.startswith("DYNAMIC_"):
            acct_type = account_code.replace("DYNAMIC_", "").lower()
            account = self.db.query(LedgerAccount).filter(
                LedgerAccount.ledger_id == ledger_id,
                LedgerAccount.account_type == acct_type,
                LedgerAccount.is_leaf == True,
            ).first()
            if not account:
                raise AccountingError("ACCOUNT_NOT_FOUND",
                    f"找不到 {acct_type} 类型叶子科目，请检查科目表")
            return account.id

        account = self.db.query(LedgerAccount).filter(
            LedgerAccount.ledger_id == ledger_id,
            LedgerAccount.code == account_code,
        ).first()
        if not account:
            raise AccountingError("ACCOUNT_NOT_FOUND",
                f"科目编码不存在: {account_code}")
        return account.id
