"""PostingLedger — 单笔业务过账一致性对账器

会计本质：一笔业务数据进入系统后，所有下游记录金额必须能勾稽。
- StockMove.total_cost          （库存台账）
- Inventory.total_value 增量    （库存缓存）
- AccountMoveLine debit/credit  （凭证分录）
- LedgerAccount 余额增量        （总账余额）
- 业务表金额（SaleOrder/PurchaseOrder/Receipt/Payment/Expense）

任何一处对不上 = 记账错了。任何一处缺失 = 流程不完整。

用法：
    trace = PostingLedger(db, account_id=1)
    trace.snapshot_before()
    dispatch(CreatePurchaseOrder(...), db)
    trace.snapshot_after("purchase_order") \
          .expect_stock_move(total_cost=1000, source_type="purchase_order", product_id=p.id) \
          .expect_inventory_delta(Decimal("1000"), product_id=p.id) \
          .expect_voucher_line("1405", debit=Decimal("1000")) \
          .expect_voucher_line("222102", debit=Decimal("130")) \
          .expect_voucher_line("2202", credit=Decimal("1130")) \
          .expect_ledger_delta("1405", debit_delta=Decimal("1000")) \
          .expect_flow_complete("purchase_order") \
          .assert_all()
"""
from decimal import Decimal
from typing import Optional


class PostingLedger:
    """单笔业务过账一致性对账器"""

    def __init__(self, db, account_id: int):
        self.db = db
        self.account_id = account_id
        self._before_snapshot = None
        self._after_snapshot = None
        self._expectations = []  # list of (kind, kwargs)
        self._current_source_model = None

    # ── 快照 ──

    def snapshot_before(self) -> "PostingLedger":
        """记录业务发生前的库存余额、总账余额"""
        self._before_snapshot = self._take_snapshot()
        return self

    def snapshot_after(self, source_model: str) -> "PostingLedger":
        """记录业务发生后的状态，并锁定当前 source_model（后续 expect 默认查这个）"""
        self._after_snapshot = self._take_snapshot()
        self._current_source_model = source_model
        return self

    def _take_snapshot(self) -> dict:
        """快照所有真相源的当前状态"""
        from models import Inventory, StockMove
        from models_finance import LedgerAccount, AccountMoveLine, AccountMove

        # 库存缓存快照
        inventory_map = {}
        for inv in self.db.query(Inventory).filter(Inventory.account_id == self.account_id).all():
            inventory_map[inv.product_id] = Decimal(str(inv.total_value or 0))

        # 总账余额快照（按科目代码）
        ledger_map = {}
        from sqlalchemy import func as sqlfunc
        for la in self.db.query(LedgerAccount).all():
            debit_sum = self.db.query(sqlfunc.sum(AccountMoveLine.debit)).filter(
                AccountMoveLine.ledger_account_id == la.id
            ).scalar() or Decimal("0")
            credit_sum = self.db.query(sqlfunc.sum(AccountMoveLine.credit)).filter(
                AccountMoveLine.ledger_account_id == la.id
            ).scalar() or Decimal("0")
            ledger_map[la.code] = {
                "debit": Decimal(str(debit_sum)),
                "credit": Decimal(str(credit_sum)),
                "balance": Decimal(str(debit_sum)) - Decimal(str(credit_sum)),
            }

        return {
            "inventory": inventory_map,
            "ledger": ledger_map,
        }

    # ── 期望链 ──

    def expect_stock_move(
        self,
        total_cost: Optional[Decimal] = None,
        source_type: Optional[str] = None,
        product_id: Optional[int] = None,
        quantity: Optional[Decimal] = None,
    ) -> "PostingLedger":
        """断言 StockMove 的字段值"""
        self._expectations.append({
            "kind": "stock_move",
            "total_cost": Decimal(str(total_cost)) if total_cost is not None else None,
            "source_type": source_type,
            "product_id": product_id,
            "quantity": Decimal(str(quantity)) if quantity is not None else None,
        })
        return self

    def expect_inventory_delta(self, total_value_delta: Decimal, product_id: int) -> "PostingLedger":
        """断言 Inventory.total_value 的增量"""
        self._expectations.append({
            "kind": "inventory_delta",
            "expected_delta": Decimal(str(total_value_delta)),
            "product_id": product_id,
        })
        return self

    def expect_voucher_line(
        self,
        account_code: str,
        debit: Optional[Decimal] = None,
        credit: Optional[Decimal] = None,
        source_model: Optional[str] = None,
    ) -> "PostingLedger":
        """断言凭证分录中指定科目的借方/贷方金额"""
        self._expectations.append({
            "kind": "voucher_line",
            "account_code": account_code,
            "debit": Decimal(str(debit)) if debit is not None else None,
            "credit": Decimal(str(credit)) if credit is not None else None,
            "source_model": source_model or self._current_source_model,
        })
        return self

    def expect_ledger_delta(
        self,
        account_code: str,
        debit_delta: Optional[Decimal] = None,
        credit_delta: Optional[Decimal] = None,
    ) -> "PostingLedger":
        """断言总账科目余额的增量（借方发生额 / 贷方发生额）"""
        self._expectations.append({
            "kind": "ledger_delta",
            "account_code": account_code,
            "debit_delta": Decimal(str(debit_delta)) if debit_delta is not None else None,
            "credit_delta": Decimal(str(credit_delta)) if credit_delta is not None else None,
        })
        return self

    def expect_flow_complete(self, *source_models: str) -> "PostingLedger":
        """断言业务流程完整性：每个 source_model 都必须生成凭证"""
        self._expectations.append({
            "kind": "flow_complete",
            "source_models": list(source_models) if source_models else [self._current_source_model],
        })
        return self

    # ── 断言执行 ──

    def assert_all(self) -> "PostingLedger":
        """执行所有期望断言，任何一条失败抛 AssertionError"""
        errors = []
        for exp in self._expectations:
            try:
                self._check_one(exp)
            except AssertionError as e:
                errors.append(str(e))

        if errors:
            raise AssertionError("\n".join(errors))
        return self

    def _check_one(self, exp: dict):
        kind = exp["kind"]
        if kind == "stock_move":
            self._check_stock_move(exp)
        elif kind == "inventory_delta":
            self._check_inventory_delta(exp)
        elif kind == "voucher_line":
            self._check_voucher_line(exp)
        elif kind == "ledger_delta":
            self._check_ledger_delta(exp)
        elif kind == "flow_complete":
            self._check_flow_complete(exp)
        else:
            raise AssertionError(f"未知期望类型: {kind}")

    def _check_stock_move(self, exp: dict):
        from models import StockMove
        q = self.db.query(StockMove).filter(StockMove.account_id == self.account_id)
        if exp.get("source_type"):
            q = q.filter(StockMove.source_type == exp["source_type"])
        if exp.get("product_id"):
            q = q.filter(StockMove.product_id == exp["product_id"])
        moves = q.all()
        if not moves:
            raise AssertionError(
                f"StockMove 不存在: source_type={exp.get('source_type')}, "
                f"product_id={exp.get('product_id')}"
            )
        # 取最新一条
        move = moves[-1]
        if exp["total_cost"] is not None:
            actual = Decimal(str(move.total_cost or 0))
            if abs(actual - exp["total_cost"]) > Decimal("0.01"):
                raise AssertionError(
                    f"StockMove.total_cost 期望 {exp['total_cost']}，实际 {actual} "
                    f"(source_type={exp.get('source_type')}, product_id={exp.get('product_id')})"
                )
        if exp["quantity"] is not None:
            actual = Decimal(str(move.quantity or 0))
            if abs(actual - exp["quantity"]) > Decimal("0.01"):
                raise AssertionError(
                    f"StockMove.quantity 期望 {exp['quantity']}，实际 {actual}"
                )

    def _check_inventory_delta(self, exp: dict):
        from models import Inventory
        if not self._before_snapshot or not self._after_snapshot:
            raise AssertionError("必须先调用 snapshot_before/snapshot_after")

        before = self._before_snapshot["inventory"].get(exp["product_id"], Decimal("0"))
        after = self._after_snapshot["inventory"].get(exp["product_id"], Decimal("0"))
        actual_delta = after - before

        if abs(actual_delta - exp["expected_delta"]) > Decimal("0.01"):
            raise AssertionError(
                f"Inventory.total_value 增量 期望 {exp['expected_delta']}，实际 {actual_delta} "
                f"(product_id={exp['product_id']}, before={before}, after={after})"
            )

    def _check_voucher_line(self, exp: dict):
        from models_finance import AccountMove, AccountMoveLine, LedgerAccount
        from models import Account
        from finance_integration import get_or_create_ledger_id

        # AccountMove 用 ledger_id 关联，需要先查 ledger_id
        ledger_id = get_or_create_ledger_id(self.db, self.account_id)

        # 查指定 source_model 的凭证
        q = self.db.query(AccountMove).filter(AccountMove.ledger_id == ledger_id)
        if exp["source_model"]:
            q = q.filter(AccountMove.source_model == exp["source_model"])
        moves = q.order_by(AccountMove.id.desc()).all()
        if not moves:
            raise AssertionError(
                f"凭证不存在: source_model={exp['source_model']}"
            )

        # 取最新一张凭证的所有分录
        latest_move = moves[0]
        lines = self.db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == latest_move.id
        ).all()

        # 按科目代码过滤
        la = self.db.query(LedgerAccount).filter(LedgerAccount.code == exp["account_code"]).first()
        if not la:
            raise AssertionError(f"科目代码 {exp['account_code']} 不存在")

        matched = [l for l in lines if l.ledger_account_id == la.id]
        debit_sum = sum((Decimal(str(l.debit or 0)) for l in matched), Decimal("0"))
        credit_sum = sum((Decimal(str(l.credit or 0)) for l in matched), Decimal("0"))

        if exp["debit"] is not None and abs(debit_sum - exp["debit"]) > Decimal("0.01"):
            raise AssertionError(
                f"凭证 {exp['account_code']} 借方 期望 {exp['debit']}，实际 {debit_sum} "
                f"(source_model={exp['source_model']}, move_id={latest_move.id})"
            )
        if exp["credit"] is not None and abs(credit_sum - exp["credit"]) > Decimal("0.01"):
            raise AssertionError(
                f"凭证 {exp['account_code']} 贷方 期望 {exp['credit']}，实际 {credit_sum} "
                f"(source_model={exp['source_model']}, move_id={latest_move.id})"
            )

    def _check_ledger_delta(self, exp: dict):
        if not self._before_snapshot or not self._after_snapshot:
            raise AssertionError("必须先调用 snapshot_before/snapshot_after")

        code = exp["account_code"]
        before = self._before_snapshot["ledger"].get(code)
        after = self._after_snapshot["ledger"].get(code)
        if not before or not after:
            raise AssertionError(f"科目 {code} 在快照中不存在")

        debit_delta = after["debit"] - before["debit"]
        credit_delta = after["credit"] - before["credit"]

        if exp["debit_delta"] is not None and abs(debit_delta - exp["debit_delta"]) > Decimal("0.01"):
            raise AssertionError(
                f"总账 {code} 借方发生额 期望 {exp['debit_delta']}，实际 {debit_delta} "
                f"(before={before['debit']}, after={after['debit']})"
            )
        if exp["credit_delta"] is not None and abs(credit_delta - exp["credit_delta"]) > Decimal("0.01"):
            raise AssertionError(
                f"总账 {code} 贷方发生额 期望 {exp['credit_delta']}，实际 {credit_delta} "
                f"(before={before['credit']}, after={after['credit']})"
            )

    def _check_flow_complete(self, exp: dict):
        from models_finance import AccountMove
        from finance_integration import get_or_create_ledger_id
        ledger_id = get_or_create_ledger_id(self.db, self.account_id)
        for src in exp["source_models"]:
            count = self.db.query(AccountMove).filter(
                AccountMove.ledger_id == ledger_id,
                AccountMove.source_model == src,
            ).count()
            if count == 0:
                raise AssertionError(
                    f"流程不完整：source_model={src} 未生成任何凭证 "
                    f"(期望至少 1 张，实际 0 张)"
                )

    # ── 便捷查询（非断言，供测试代码读取）──

    def inventory_delta(self, product_id: int) -> Decimal:
        """读取 Inventory.total_value 增量（非断言）"""
        if not self._before_snapshot or not self._after_snapshot:
            raise AssertionError("必须先调用 snapshot_before/snapshot_after")
        before = self._before_snapshot["inventory"].get(product_id, Decimal("0"))
        after = self._after_snapshot["inventory"].get(product_id, Decimal("0"))
        return after - before

    def voucher_line(self, account_code: str, source_model: Optional[str] = None) -> tuple:
        """读取指定科目的借方/贷方金额（非断言），返回 (debit, credit)"""
        from models_finance import AccountMove, AccountMoveLine, LedgerAccount
        from finance_integration import get_or_create_ledger_id

        src = source_model or self._current_source_model
        ledger_id = get_or_create_ledger_id(self.db, self.account_id)
        q = self.db.query(AccountMove).filter(AccountMove.ledger_id == ledger_id)
        if src:
            q = q.filter(AccountMove.source_model == src)
        moves = q.order_by(AccountMove.id.desc()).all()
        if not moves:
            return Decimal("0"), Decimal("0")

        latest_move = moves[0]
        lines = self.db.query(AccountMoveLine).filter(
            AccountMoveLine.move_id == latest_move.id
        ).all()

        la = self.db.query(LedgerAccount).filter(LedgerAccount.code == account_code).first()
        if not la:
            return Decimal("0"), Decimal("0")

        matched = [l for l in lines if l.ledger_account_id == la.id]
        debit = sum((Decimal(str(l.debit or 0)) for l in matched), Decimal("0"))
        credit = sum((Decimal(str(l.credit or 0)) for l in matched), Decimal("0"))
        return debit, credit

    def ledger_delta(self, account_code: str) -> tuple:
        """读取总账科目借方/贷方增量（非断言），返回 (debit_delta, credit_delta)"""
        if not self._before_snapshot or not self._after_snapshot:
            raise AssertionError("必须先调用 snapshot_before/snapshot_after")
        before = self._before_snapshot["ledger"].get(account_code)
        after = self._after_snapshot["ledger"].get(account_code)
        if not before or not after:
            return Decimal("0"), Decimal("0")
        return after["debit"] - before["debit"], after["credit"] - before["credit"]
