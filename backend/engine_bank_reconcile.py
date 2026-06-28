"""银行对账引擎 — 匹配、调节、确认"""
import logging
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from utils import _d, Q2
from errors import BusinessError, ErrorCode

logger = logging.getLogger("inventory")

FEE_KEYWORDS = ["手续费", "管理费", "service charge", "fee", "利息", "interest", "结息"]


class BankReconcileEngine:

    def __init__(self, db: Session, account_id: int, bank_account_id: int, period: str):
        import models, models_bank
        bank_acct = db.query(models.BankAccount).filter(
            models.BankAccount.id == bank_account_id,
            models.BankAccount.account_id == account_id,
        ).first()
        if not bank_acct:
            raise BusinessError(code=ErrorCode.BANK_ACCOUNT_NOT_FOUND,
                                data={"bank_account_id": bank_account_id})
        self.db = db
        self.account_id = account_id
        self.bank_account_id = bank_account_id
        self.period = period
        self.period_start = datetime(int(period[:4]), int(period[5:7]), 1).date()
        y, m = int(period[:4]), int(period[5:7])
        if m == 12:
            cd = datetime(y + 1, 1, 1) - timedelta(days=1)
        else:
            cd = datetime(y, m + 1, 1) - timedelta(days=1)
        self.period_end = cd.date()
        self._models = models
        self._models_bank = models_bank
        self._match_group_counter = 0

    # ═══════════════════════════════════════════════════
    # create_reconciliation — 创建调节表 + seed
    # ═══════════════════════════════════════════════════

    def create_reconciliation(self, seed: List[Dict]):
        mb = self._models_bank
        cutoff = datetime.combine(self.period_end, datetime.max.time())
        book_balance = self._read_book_balance(cutoff)
        existing = self.db.query(mb.BankReconciliation).filter(
            mb.BankReconciliation.bank_account_id == self.bank_account_id,
            mb.BankReconciliation.account_id == self.account_id,
            mb.BankReconciliation.period == self.period,
        ).first()
        if existing:
            return existing
        rec = mb.BankReconciliation(
            bank_account_id=self.bank_account_id, account_id=self.account_id,
            period=self.period, book_balance=book_balance, statement_balance=Decimal("0"),
            adjusted_book=book_balance, adjusted_statement=Decimal("0"),
            balanced=False, status="matching" if seed else "draft",
        )
        self.db.add(rec); self.db.flush()
        for s in seed:
            self.db.add(mb.ReconciliationItem(
                reconciliation_id=rec.id, item_type=s["item_type"],
                amount=Decimal(str(s["amount"])), direction=s.get("direction","in"),
                source_dates=s.get("source_dates", []), notes=s.get("notes",""),
                resolved=False,
            ))
        self.db.flush()
        return rec

    # ═══════════════════════════════════════════════════
    # run_matching — 完整 4 轮匹配 + 跨期滚动 + 费用标记
    # ═══════════════════════════════════════════════════

    def run_matching(self):
        m = self._models; mb = self._models_bank

        bank_txns = self.db.query(m.BankTransaction).filter(
            m.BankTransaction.bank_account_id == self.bank_account_id,
            m.BankTransaction.account_id == self.account_id,
            m.BankTransaction.transaction_date >= self.period_start,
            m.BankTransaction.transaction_date <= self.period_end,
        ).all()

        stmt = self.db.query(mb.BankStatement).filter(
            mb.BankStatement.bank_account_id == self.bank_account_id,
            mb.BankStatement.account_id == self.account_id,
            mb.BankStatement.period_start == self.period_start,
        ).first()
        if not stmt:
            return

        stmt_lines = self.db.query(mb.BankStatementLine).filter(
            mb.BankStatementLine.statement_id == stmt.id,
        ).all()

        rec = self.db.query(mb.BankReconciliation).filter(
            mb.BankReconciliation.bank_account_id == self.bank_account_id,
            mb.BankReconciliation.account_id == self.account_id,
            mb.BankReconciliation.period == self.period,
        ).first()
        if not rec:
            return

        rec.statement_balance = stmt.closing_balance

        matched_tx_ids = set()
        matched_stmt_ids = set()

        # ── Round 1: 1:1 ----
        for sl in stmt_lines:
            if sl.id in matched_stmt_ids: continue
            sl_amount = Decimal(str(sl.amount))
            sl_dir = "in" if sl_amount >= 0 else "out"
            for tx in bank_txns:
                if tx.id in matched_tx_ids: continue
                tx_amount = Decimal(str(tx.amount))
                tx_dir = "in" if tx.transaction_type == "inflow" else "out"
                if sl_dir != tx_dir: continue
                if abs(abs(sl_amount) - abs(tx_amount)) > Decimal("0.01"): continue
                sl_d = sl.transaction_date; tx_d = tx.transaction_date
                sl_date = sl_d.date() if hasattr(sl_d, 'hour') else sl_d
                tx_date = tx_d.date() if hasattr(tx_d, 'hour') else tx_d
                if abs((sl_date - tx_date).days) > 3: continue
                sl.matched_tx_ids = [tx.id]
                matched_tx_ids.add(tx.id); matched_stmt_ids.add(sl.id)
                break

        # ── Round 2: N:1 ----
        unmatched_tx = [tx for tx in bank_txns if tx.id not in matched_tx_ids]
        unmatched_sl = [sl for sl in stmt_lines if sl.id not in matched_stmt_ids]
        self._run_combo_n1(unmatched_tx, unmatched_sl, matched_tx_ids, matched_stmt_ids, "in")
        self._run_combo_n1(unmatched_tx, unmatched_sl, matched_tx_ids, matched_stmt_ids, "out")

        # ── 未达账项 ----
        self._create_unmatched_items(rec, stmt_lines, matched_stmt_ids, bank_txns, matched_tx_ids)

        # ── 费用扫描 ----
        self._scan_fees(rec, stmt_lines, matched_stmt_ids)

        # ── 跨期滚动 ----
        self._cross_month_rollover()

        # ── 计算调节后余额 ----
        self._recalc_balances(rec)

        rec.status = "balanced" if rec.balanced else "matching"
        self.db.flush()

    # ── N:1 combo helper ──

    def _run_combo_n1(self, unmatched_tx, unmatched_sl, matched_tx_ids, matched_stmt_ids, direction):
        m = self._models; mb = self._models_bank
        utx = [tx for tx in unmatched_tx
               if (tx.transaction_type == "inflow") == (direction == "in")
               and tx.id not in matched_tx_ids]
        usl = [sl for sl in unmatched_sl
               if (Decimal(str(sl.amount)) >= 0) == (direction == "in")
               and sl.id not in matched_stmt_ids]
        if len(utx) < 2 or not usl:
            return

        for sl in usl:
            sl_amount = abs(Decimal(str(sl.amount)))
            sl_d = sl.transaction_date
            sl_date = sl_d.date() if hasattr(sl_d, 'hour') else sl_d

            # 回溯 + 剪枝 (≤10 笔)
            for r in range(2, min(len(utx) + 1, 11)):
                if self._try_combo(utx, sl, sl_amount, sl_date, r, matched_tx_ids, matched_stmt_ids):
                    break

    def _try_combo(self, utx, sl, target, sl_date, size, matched_tx_ids, matched_stmt_ids):
        from itertools import combinations
        for combo in combinations(utx, size):
            if any(tx.id in matched_tx_ids for tx in combo):
                continue
            total = sum(abs(Decimal(str(tx.amount))) for tx in combo)
            if abs(total - target) > Decimal("0.01"):
                continue
            dates = []
            for tx in combo:
                tx_d = tx.transaction_date
                dates.append(tx_d.date() if hasattr(tx_d, 'hour') else tx_d)
            max_date = max(dates)
            min_date = min(dates)
            # 4 checks
            if sl_date < max_date:  # 先后
                continue
            if (sl_date - max_date).days > 3:  # 延迟
                continue
            if (max_date - min_date).days > 15:  # 跨度
                continue
            # match!
            self._match_group_counter += 1
            gid = self._match_group_counter
            tx_ids = [tx.id for tx in combo]
            sl.matched_tx_ids = tx_ids
            sl.match_group_id = gid
            for tx in combo:
                matched_tx_ids.add(tx.id)
            matched_stmt_ids.add(sl.id)
            return True
        return False

    # ── 未达项 + 费用扫描 ──

    def _create_unmatched_items(self, rec, stmt_lines, matched_stmt_ids, bank_txns, matched_tx_ids):
        mb = self._models_bank
        for sl in stmt_lines:
            if sl.id in matched_stmt_ids: continue
            amt = abs(Decimal(str(sl.amount)))
            itype = "bank_received_not_book" if Decimal(str(sl.amount)) >= 0 else "bank_paid_not_book"
            self.db.add(mb.ReconciliationItem(
                reconciliation_id=rec.id, item_type=itype, amount=amt,
                direction="in" if Decimal(str(sl.amount)) >= 0 else "out",
                source_ids=[sl.id], source_dates=[sl.transaction_date.isoformat()],
            ))
        for tx in bank_txns:
            if tx.id in matched_tx_ids: continue
            amt = Decimal(str(tx.amount))
            itype = "book_received_not_bank" if tx.transaction_type == "inflow" else "book_paid_not_bank"
            self.db.add(mb.ReconciliationItem(
                reconciliation_id=rec.id, item_type=itype, amount=abs(amt),
                direction="in" if tx.transaction_type == "inflow" else "out",
                source_ids=[tx.id], source_dates=[tx.transaction_date.isoformat()],
            ))

    def _scan_fees(self, rec, stmt_lines, matched_stmt_ids):
        mb = self._models_bank
        items = self.db.query(mb.ReconciliationItem).filter(
            mb.ReconciliationItem.reconciliation_id == rec.id,
            mb.ReconciliationItem.item_type.in_(["bank_paid_not_book", "bank_received_not_book"]),
        ).all()
        for it in items:
            if not it.source_ids:
                continue
            sl = self.db.query(mb.BankStatementLine).filter(
                mb.BankStatementLine.id == it.source_ids[0],
            ).first()
            if sl:
                desc = (sl.description or "").lower()
                if any(kw.lower() in desc for kw in FEE_KEYWORDS):
                    sl.is_fee = True
                    it.action = "generate_entry"

    # ── 跨期滚动 ──

    def _cross_month_rollover(self):
        mb = self._models_bank
        # 上月
        prev_dt = datetime(int(self.period[:4]), int(self.period[5:7]), 1) - timedelta(days=1)
        prev_period = f"{prev_dt.year}-{prev_dt.month:02d}"
        prev_rec = self.db.query(mb.BankReconciliation).filter(
            mb.BankReconciliation.bank_account_id == self.bank_account_id,
            mb.BankReconciliation.account_id == self.account_id,
            mb.BankReconciliation.period == prev_period,
            mb.BankReconciliation.status == "confirmed",
        ).first()
        if not prev_rec:
            return

        prev_items = self.db.query(mb.ReconciliationItem).filter(
            mb.ReconciliationItem.reconciliation_id == prev_rec.id,
            mb.ReconciliationItem.item_type.in_(["book_paid_not_bank", "book_received_not_bank"]),
            mb.ReconciliationItem.resolved == False,
        ).all()

        stmt = self.db.query(mb.BankStatement).filter(
            mb.BankStatement.bank_account_id == self.bank_account_id,
            mb.BankStatement.account_id == self.account_id,
            mb.BankStatement.period_start == self.period_start,
        ).first()
        if not stmt:
            return

        stmt_lines = self.db.query(mb.BankStatementLine).filter(
            mb.BankStatementLine.statement_id == stmt.id,
        ).all()

        for pi in prev_items:
            for sl in stmt_lines:
                sl_amt = abs(Decimal(str(sl.amount)))
                sl_dir = "in" if Decimal(str(sl.amount)) >= 0 else "out"
                if pi.direction != sl_dir: continue
                if abs(sl_amt - pi.amount) > Decimal("0.01"): continue
                sl_date = sl.transaction_date.date() if hasattr(sl.transaction_date, 'hour') else sl.transaction_date
                prev_dates = pi.source_dates or []
                if prev_dates:
                    prev_last_str = prev_dates[-1]
                    if 'T' in prev_last_str:
                        prev_last_str = prev_last_str.split('T')[0]
                    prev_last = datetime.strptime(prev_last_str, "%Y-%m-%d").date()
                    if (sl_date - prev_last).days < 0 or (sl_date - prev_last).days > 10:
                        continue
                pi.resolved = True
                pi.resolved_in = self.period
                break

    # ── 调节后余额 ──

    def _recalc_balances(self, rec):
        mb = self._models_bank
        items = self.db.query(mb.ReconciliationItem).filter(
            mb.ReconciliationItem.reconciliation_id == rec.id, mb.ReconciliationItem.resolved == False,
        ).all()
        adj_book = rec.book_balance
        adj_stmt = rec.statement_balance
        for it in items:
            amt = it.amount
            if it.item_type in ("bank_received_not_book",):
                adj_book += amt
            elif it.item_type in ("bank_paid_not_book",):
                adj_book -= amt
            elif it.item_type in ("book_received_not_bank",):
                adj_stmt += amt
            elif it.item_type in ("book_paid_not_bank",):
                adj_stmt -= amt
            elif it.item_type == "adjustment":
                adj_book += amt if it.direction == "in" else -amt
        rec.adjusted_book = adj_book
        rec.adjusted_statement = adj_stmt
        rec.balanced = abs(adj_book - adj_stmt) <= Decimal("0.01")

    # ═══════════════════════════════════════════════════
    # force_match — 手动强制匹配
    # ═══════════════════════════════════════════════════

    def force_match(self, rec_id: int, stmt_line_ids: List[int],
                    bank_tx_ids: List[int], reason: str):
        m = self._models; mb = self._models_bank

        stmt_lines = self.db.query(mb.BankStatementLine).filter(
            mb.BankStatementLine.id.in_(stmt_line_ids),
        ).all()
        txs = self.db.query(m.BankTransaction).filter(
            m.BankTransaction.id.in_(bank_tx_ids),
            m.BankTransaction.account_id == self.account_id,
        ).all()

        sl_total = sum(abs(Decimal(str(sl.amount))) for sl in stmt_lines)
        tx_total = sum(abs(Decimal(str(tx.amount))) for tx in txs)
        if abs(sl_total - tx_total) > Decimal("0.01"):
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                message=f"金额不匹配: 对账单 {sl_total} vs 系统 {tx_total}")

        self._match_group_counter += 1
        gid = self._match_group_counter
        for sl in stmt_lines:
            sl.matched_tx_ids = bank_tx_ids
            sl.match_group_id = gid

        # 审计日志
        from crud.base import _log
        _log(self.db, self.account_id, "force_match", "bank_reconciliation", rec_id,
             f"强制匹配: stmt={stmt_line_ids} tx={bank_tx_ids} reason={reason}",
             operator="user")
        self.db.flush()

    # ═══════════════════════════════════════════════════
    # confirm — 确认锁定
    # ═══════════════════════════════════════════════════

    def confirm(self, rec_id: int, operator: str):
        mb = self._models_bank
        rec = self.db.query(mb.BankReconciliation).filter(
            mb.BankReconciliation.id == rec_id, mb.BankReconciliation.account_id == self.account_id,
        ).first()
        if not rec:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR, message="调节表不存在")
        if not rec.balanced:
            raise BusinessError(code=ErrorCode.VALIDATION_ERROR,
                message=f"调节不平: book={rec.adjusted_book} stmt={rec.adjusted_statement}")

        # 检查未处理的费用/利息项——必须先调 generate-entry 才能确认
        pending = self.db.query(mb.ReconciliationItem).filter(
            mb.ReconciliationItem.reconciliation_id == rec_id,
            mb.ReconciliationItem.resolved == False,
            mb.ReconciliationItem.action == "generate_entry",
        ).all()
        if pending:
            item_ids = [it.id for it in pending]
            total = sum(abs(it.amount) for it in pending)
            raise BusinessError(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"有 {len(pending)} 笔未达项需要先生成凭证（合计 {total} 元），"
                        f"请先调用 POST /api/bank/reconciliation/{rec_id}/generate-entry",
                data={"pending_item_ids": item_ids},
            )

        rec.status = "confirmed"
        rec.confirmed_at = datetime.now()
        rec.confirmed_by = operator
        self.db.flush()

    # ═══════════════════════════════════════════════════
    # generate_entries — 对未达项生成会计凭证
    # ═══════════════════════════════════════════════════

    def generate_entries(self, rec_id: int) -> list:
        mb = self._models_bank
        from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine

        items = self.db.query(mb.ReconciliationItem).filter(
            mb.ReconciliationItem.reconciliation_id == rec_id,
            mb.ReconciliationItem.resolved == False,
            mb.ReconciliationItem.action == "generate_entry",
        ).all()

        # 找总账科目
        account = self.db.query(self._models.Account).filter(
            self._models.Account.id == self.account_id).first()
        ledger = account and self.db.query(Ledger).filter(Ledger.code == account.code).first()
        ac_1002 = self.db.query(LedgerAccount).filter(
            LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "1002").first() if ledger else None
        ac_6603 = self.db.query(LedgerAccount).filter(
            LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "6603").first() if ledger else None

        generated = []
        for it in items:
            move = AccountMove(ledger_id=ledger.id, move_type="bank_fee", date=datetime.now(), state="posted")
            self.db.add(move); self.db.flush()
            amt = Decimal(str(it.amount))
            if it.item_type == "bank_paid_not_book":
                self.db.add(AccountMoveLine(move_id=move.id, ledger_account_id=ac_6603.id, debit=amt, credit=0, amount_residual=amt))
                self.db.add(AccountMoveLine(move_id=move.id, ledger_account_id=ac_1002.id, debit=0, credit=amt, amount_residual=amt))
            elif it.item_type == "bank_received_not_book":
                self.db.add(AccountMoveLine(move_id=move.id, ledger_account_id=ac_1002.id, debit=amt, credit=0, amount_residual=amt))
                self.db.add(AccountMoveLine(move_id=move.id, ledger_account_id=ac_6603.id, debit=0, credit=amt, amount_residual=amt))
            it.resolved = True
            generated.append(it.id)
        self.db.flush()
        return generated

    # ═══════════════════════════════════════════════════
    # _read_book_balance
    # ═══════════════════════════════════════════════════

    def _read_book_balance(self, cutoff: datetime) -> Decimal:
        from models_finance import Ledger, LedgerAccount, AccountMove, AccountMoveLine
        from sqlalchemy import func as sqlfunc

        account = self.db.query(self._models.Account).filter(
            self._models.Account.id == self.account_id).first()
        ledger = account and self.db.query(Ledger).filter(Ledger.code == account.code).first()
        if not ledger:
            return Decimal("0")
        d = _d(self.db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.debit), 0)).join(
            LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
            LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "1002",
            AccountMove.date <= cutoff).scalar())
        c = _d(self.db.query(sqlfunc.coalesce(sqlfunc.sum(AccountMoveLine.credit), 0)).join(
            LedgerAccount, AccountMoveLine.ledger_account_id == LedgerAccount.id
        ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id).filter(
            LedgerAccount.ledger_id == ledger.id, LedgerAccount.code == "1002",
            AccountMove.date <= cutoff).scalar())
        return (d - c).quantize(Q2)
