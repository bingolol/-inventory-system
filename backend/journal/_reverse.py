"""Journal builder"""
from decimal import Decimal
from datetime import datetime, date
from accounting_engine import AccountingError, AccountingErrorCode
from models import Product, StockMove
from models_finance import LedgerAccount, AccountMove, AccountMoveLine

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


