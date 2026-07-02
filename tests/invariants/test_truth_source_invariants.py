"""不变量测试套件 — 防止 "Truth Source Bypass"（同一凭证借贷用了不同数据源）

这类 bug 的典型表现：
- 采购退货借方应付用原发票单价，贷方库存用移动加权平均成本 → 借贷不平衡
- 反向 StockMove.total_cost 用 avg_cost 而非原入库金额 → 库存账面价值偏离

本测试套件用"先入低价货 → 后入高价货 A → 退货 A"的场景，
强制让 A 的 StockMove.unit_cost 被稀释（≠ 原发票单价），
断言凭证借贷和 StockMove 必须用同一真相源（原发票单价）。

运行：pytest tests/invariants/test_truth_source_invariants.py -v
"""
import pytest
from decimal import Decimal
from datetime import datetime

pytestmark = pytest.mark.usefixtures("bootstrap_db")

from commands.base import dispatch
from commands.purchase_commands import CreatePurchaseOrder, ReturnPurchaseOrder
from models import Account, StockMove, Inventory
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from tests.factories import make_product, make_supplier

PURCHASE_DATE = datetime(2026, 6, 10)


@pytest.fixture(scope="function")
def general_account(db, bootstrap_db):
    """建一般纳税人账本（用于测试进项税额分离）"""
    acc = db.query(Account).filter(Account.id == 1).first()
    if acc:
<<<<<<< Updated upstream
        acc.taxpayer_type = "general"
    else:
        acc = Account(name="一般纳税人测试", type="company", code="inv_test", taxpayer_type="general")
=======
        acc.taxpayer_type_l3 = "general"
    else:
        acc = Account(name="一般纳税人测试", type="company", code="inv_test", taxpayer_type_l3="general")
>>>>>>> Stashed changes
        db.add(acc)
        db.flush()
    db.commit()
    return acc


def _get_ledger_account(db, code):
    """按科目代码查 LedgerAccount"""
    return db.query(LedgerAccount).filter(LedgerAccount.code == code).first()


def _get_move_lines_by_source(db, source_model, source_id=None):
    """按 source_model (+ source_id) 查凭证分录行，不传 source_id 则取最新一条"""
    q = db.query(AccountMove).filter(AccountMove.source_model == source_model)
    if source_id is not None:
        q = q.filter(AccountMove.source_id == source_id)
    else:
        q = q.order_by(AccountMove.id.desc())
    moves = q.all()
    lines = []
    for m in moves:
        lines.extend(db.query(AccountMoveLine).filter(AccountMoveLine.move_id == m.id).all())
    return lines


def _line_amount(lines, account_code, ledger_db):
    """取某科目代码的借贷金额"""
    la = _get_ledger_account(ledger_db, account_code)
    if not la:
        return Decimal("0"), Decimal("0")
    matched = [l for l in lines if l.ledger_account_id == la.id]
<<<<<<< Updated upstream
    debit = sum((l.debit or Decimal("0")) for l in matched)
    credit = sum((l.credit or Decimal("0")) for l in matched)
=======
    debit = sum((l.debit_l2 or Decimal("0")) for l in matched)
    credit = sum((l.credit_l2 or Decimal("0")) for l in matched)
>>>>>>> Stashed changes
    return debit, credit


def _setup_diluted_stock(db):
    """搭建"均价被稀释"的测试场景。

    先入低价货 5 件单价 500 → 库存 5 件均价 500
    再入高价货 A 10 件单价 1000 → A 入库时均价 = (2500+10000)/15 = 833.33
    → A 的 StockMove.unit_cost = 833.33（被稀释），但 A 的原发票单价是 1000

    返回 (product, order_a) — order_a 是被退货的采购单。
    """
    p = make_product(db, account_id=1, purchase_price=Decimal("1000"), sale_price=Decimal("1500"))
    s = make_supplier(db, account_id=1)

    # 1. 先入低价货（稀释均价）
    dispatch(CreatePurchaseOrder(
        account_id=1, operator="test",
        supplier_id=s.id, purchase_date=PURCHASE_DATE,
        items=[{"product_id": p.id, "quantity": 5, "unit_price": 500, "tax_rate": 0.13}],
    ), db)

    # 2. 再入高价货 A（A 的 unit_cost 被稀释到 833.33）
    order_a = dispatch(CreatePurchaseOrder(
        account_id=1, operator="test",
        supplier_id=s.id, purchase_date=PURCHASE_DATE,
        items=[{"product_id": p.id, "quantity": 10, "unit_price": 1000, "tax_rate": 0.13}],
    ), db)

    return p, order_a


class Test采购退货借贷同源:
    """不变量：采购退货的借方应付 / 贷方库存 / 贷方税额 必须用同一数据源（原发票单价）

    场景：先入低价 5×500 → 再入高价 A 10×1000
    → A 的 StockMove.unit_cost 被稀释为 833.33（≠ 原发票单价 1000）
    → 退货 A 中 1 件
    → 必须用 A 的原发票单价 1000，不能用稀释后的 avg_cost 833.33
    """

    def test_场景验证_A的unit_cost被稀释(self, db, general_account):
        """前置验证：确认 A 的 StockMove.unit_cost 被稀释到 833.33（否则测试场景失效）"""
        p, order_a = _setup_diluted_stock(db)
        move_a = db.query(StockMove).filter(
            StockMove.source_type == "purchase_order",
            StockMove.source_id == order_a.id,
            StockMove.product_id == p.id,
        ).first()
<<<<<<< Updated upstream
        assert move_a.unit_cost == Decimal("833.333333"), (
            f"A 的 unit_cost 应被稀释到 833.33，实际 {move_a.unit_cost}。"
=======
        assert move_a.unit_cost_l2 == Decimal("833.333333"), (
            f"A 的 unit_cost 应被稀释到 833.33，实际 {move_a.unit_cost_l2}。"
>>>>>>> Stashed changes
            f"若为 1000 说明测试场景失效，无法检测 bug。"
        )

    def test_采购退货贷方库存等于原发票单价乘数量(self, db, general_account):
        """不变量：Cr 1405 库存 == 原发票单价 1000 × 退货数量 1 = 1000

        若用 avg_cost 则会变成 833.33，借贷不平衡。
        """
        p, order_a = _setup_diluted_stock(db)

        ret = dispatch(ReturnPurchaseOrder(
            account_id=1, operator="test",
            order_id=order_a.id,
            return_date="2026-06-20",
            reason="测试退货",
            items=[{"product_id": p.id, "quantity": 1}],
        ), db)

        lines = _get_move_lines_by_source(db, "purchase_return")
        assert lines, "退货凭证应生成分录"

        debit_1405, credit_1405 = _line_amount(lines, "1405", db)
        assert credit_1405 == Decimal("1000.00"), (
            f"贷方库存必须用原发票单价：期望 1000.00，实际 {credit_1405}。"
            f"若为 833.33 说明误用了移动加权平均成本（avg_cost）"
        )

    def test_采购退货贷方税额等于原发票单价乘税率(self, db, general_account):
        """不变量：Cr 222102 进项税额转出 = 1000 × 0.13 = 130"""
        p, order_a = _setup_diluted_stock(db)

        dispatch(ReturnPurchaseOrder(
            account_id=1, operator="test",
            order_id=order_a.id,
            return_date="2026-06-20",
            reason="测试退货",
            items=[{"product_id": p.id, "quantity": 1}],
        ), db)

        lines = _get_move_lines_by_source(db, "purchase_return")
        _, credit_222102 = _line_amount(lines, "222102", db)
        assert credit_222102 == Decimal("130.00"), (
            f"贷方税额转出应为原发票单价×税率：期望 130.00，实际 {credit_222102}"
        )

    def test_采购退货借方应付等于价税合计(self, db, general_account):
        """不变量：Dr 2202 应付 = 1000 × 1.13 = 1130"""
        p, order_a = _setup_diluted_stock(db)

        dispatch(ReturnPurchaseOrder(
            account_id=1, operator="test",
            order_id=order_a.id,
            return_date="2026-06-20",
            reason="测试退货",
            items=[{"product_id": p.id, "quantity": 1}],
        ), db)

        lines = _get_move_lines_by_source(db, "purchase_return")
        debit_2202, _ = _line_amount(lines, "2202", db)
        assert debit_2202 == Decimal("1130.00"), (
            f"借方应付应为原发票价税合计：期望 1130.00，实际 {debit_2202}"
        )

    def test_采购退货借贷平衡且三方同源(self, db, general_account):
        """综合不变量：Dr 2202 == Cr 1405 + Cr 222102，且都基于原发票单价"""
        p, order_a = _setup_diluted_stock(db)

        dispatch(ReturnPurchaseOrder(
            account_id=1, operator="test",
            order_id=order_a.id,
            return_date="2026-06-20",
            reason="测试退货",
            items=[{"product_id": p.id, "quantity": 1}],
        ), db)

        lines = _get_move_lines_by_source(db, "purchase_return")
        debit_2202, _ = _line_amount(lines, "2202", db)
        _, credit_1405 = _line_amount(lines, "1405", db)
        _, credit_222102 = _line_amount(lines, "222102", db)

        # 借贷平衡
        assert debit_2202 == credit_1405 + credit_222102, (
            f"借贷不平衡：Dr 2202={debit_2202}, Cr 1405={credit_1405} + Cr 222102={credit_222102}"
        )
        # 三方同源：都基于原发票单价 1000
        assert debit_2202 == Decimal("1130.00")
        assert credit_1405 == Decimal("1000.00")
        assert credit_222102 == Decimal("130.00")


class Test反向StockMove同源:
    """不变量：反向 StockMove.total_cost 必须按原入库 total_cost 比例分摊

    场景：先入低价 5×500 → 再入高价 A 10×1000
    → A 的 StockMove.total_cost = 10000（原发票金额），unit_cost = 833.33（稀释后）
    → 退货 A 中 1 件
    → 反向 StockMove.total_cost 必须是 1000（=10000/10×1），不是 833.33
    """

    def test_反向StockMove总成本等于原入库按比例分摊(self, db, general_account):
        p, order_a = _setup_diluted_stock(db)

        dispatch(ReturnPurchaseOrder(
            account_id=1, operator="test",
            order_id=order_a.id,
            return_date="2026-06-20",
            reason="测试退货",
            items=[{"product_id": p.id, "quantity": 1}],
        ), db)

        rev_move = db.query(StockMove).filter(
            StockMove.source_type == "purchase_order_reversal",
            StockMove.product_id == p.id,
        ).first()
        assert rev_move, "应生成反向 StockMove"

        # 反向 total_cost = 原入库单价 × 退货数量 = 1000
<<<<<<< Updated upstream
        assert rev_move.total_cost == Decimal("1000.00"), (
            f"反向 StockMove.total_cost 必须按原入库金额比例分摊："
            f"期望 1000.00，实际 {rev_move.total_cost}。"
=======
        assert rev_move.total_cost_l2 == Decimal("1000.00"), (
            f"反向 StockMove.total_cost 必须按原入库金额比例分摊："
            f"期望 1000.00，实际 {rev_move.total_cost_l2}。"
>>>>>>> Stashed changes
            f"若为 833.33 说明误用了 avg_cost"
        )

    def test_库存账面价值等于StockMove求和(self, db, general_account):
        """不变量：Inventory.total_value == sum(方向 × StockMove.total_cost)

        如果反向 StockMove 用错成本源，两者会偏离。
        """
        p, order_a = _setup_diluted_stock(db)

        dispatch(ReturnPurchaseOrder(
            account_id=1, operator="test",
            order_id=order_a.id,
            return_date="2026-06-20",
            reason="测试退货",
            items=[{"product_id": p.id, "quantity": 1}],
        ), db)

        inv = db.query(Inventory).filter(Inventory.product_id == p.id).first()
        moves = db.query(StockMove).filter(StockMove.product_id == p.id).all()
        # 求和时考虑方向：quantity>0 入库加，quantity<0 出库/退货减
        sum_total_cost = sum(
<<<<<<< Updated upstream
            (Decimal(str(m.total_cost or 0)) if Decimal(str(m.quantity)) > 0
             else -Decimal(str(m.total_cost or 0)))
            for m in moves
        )

        assert inv.total_value == sum_total_cost, (
            f"库存账面价值 {inv.total_value} ≠ StockMove 求和 {sum_total_cost}。"
=======
            (Decimal(str(m.total_cost_l2 or 0)) if Decimal(str(m.quantity_l1)) > 0
             else -Decimal(str(m.total_cost_l2 or 0)))
            for m in moves
        )

        assert inv.total_value_l4 == sum_total_cost, (
            f"库存账面价值 {inv.total_value_l4} ≠ StockMove 求和 {sum_total_cost}。"
>>>>>>> Stashed changes
            f"差异说明反向冲销用了错误成本源。"
        )
