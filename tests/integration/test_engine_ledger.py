"""LedgerEngine 集成测试"""
import pytest
from datetime import date as date_obj
from decimal import Decimal
from models_finance import (
    Ledger, LedgerAccount, LedgerAccountBalance, AccountMove, AccountMoveLine,
)
from accounting_engine import AccountingError
from engine_ledger import LedgerEngine


import uuid

@pytest.fixture
def ledger(db):
    suffix = uuid.uuid4().hex[:8]
    l = Ledger(name="测试账本", type="company", code=f"test_{suffix}")
    db.add(l)
    db.commit()
    return l


@pytest.fixture
def accounts(db, ledger):
    """创建科目树：一个父级非叶子 + 两个叶子子科目 + 库存现金"""
    parent = LedgerAccount(
        ledger_id=ledger.id, code="2000", name="测试负债类",
        account_type="liability", is_leaf=False,
    )
    db.add(parent)
    db.flush()

    child1 = LedgerAccount(
        ledger_id=ledger.id, code="2100", name="测试应付账款",
        account_type="liability_payable", is_leaf=True, parent_id=parent.id,
    )
    db.add(child1)
    db.flush()

    child2 = LedgerAccount(
        ledger_id=ledger.id, code="2101", name="测试其他应付款",
        account_type="liability", is_leaf=True, parent_id=parent.id,
    )
    db.add(child2)
    db.flush()

    cash = LedgerAccount(
        ledger_id=ledger.id, code="1001", name="库存现金",
        account_type="asset", is_leaf=True,
    )
    db.add(cash)
    db.flush()

    db.commit()
    return {"parent": parent, "child1": child1, "child2": child2, "cash": cash}


def make_line(db, account_id, debit=Decimal("0"), credit=Decimal("0"),
              partner_id=None, partner_type=None, move_date=None,
              ledger_id=1):
    """辅助：创建一条分录行（关联一个虚拟凭证）"""
    move = AccountMove(
        ledger_id=ledger_id, move_type="test",
        date=move_date or date_obj(2026, 6, 1),
        state="draft",
    )
    db.add(move)
    db.flush()
    line = AccountMoveLine(
        move_id=move.id,
        ledger_account_id=account_id,
        debit=debit,
        credit=credit,
        partner_id=partner_id,
        partner_type=partner_type,
        amount_residual=debit or credit,
    )
    db.add(line)
    db.flush()
    return line


class TestNonLeafAccountGuard:
    """非叶子科目不能记账"""

    def test_raises_on_non_leaf(self, db, accounts):
        engine = LedgerEngine(db)
        line = make_line(db, accounts["parent"].id, debit=Decimal("100"))
        with pytest.raises(AccountingError) as exc:
            engine.update_balance(line)
        assert exc.value.code == "NON_LEAF_ACCOUNT"

    def test_passes_on_leaf(self, db, accounts):
        engine = LedgerEngine(db)
        line = make_line(db, accounts["child1"].id, debit=Decimal("100"))
        engine.update_balance(line)
        db.commit()

        bal = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["child1"].id
        ).first()
        assert bal is not None
        assert bal.balance == Decimal("100")


class TestLeafBalanceUpdate:
    """叶子科目余额更新正确"""

    def test_debit_increases_balance(self, db, accounts):
        engine = LedgerEngine(db)
        line = make_line(db, accounts["child1"].id, debit=Decimal("200"))
        engine.update_balance(line)
        db.commit()

        bal = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["child1"].id
        ).first()
        assert bal.balance == Decimal("200")
        assert bal.debit_total == Decimal("200")
        assert bal.credit_total == Decimal("0")

    def test_credit_decreases_balance(self, db, accounts):
        engine = LedgerEngine(db)
        line1 = make_line(db, accounts["child1"].id, debit=Decimal("500"))
        engine.update_balance(line1)
        line2 = make_line(db, accounts["child1"].id, credit=Decimal("300"))
        engine.update_balance(line2)
        db.commit()

        bal = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["child1"].id
        ).first()
        assert bal.balance == Decimal("200")
        assert bal.debit_total == Decimal("500")
        assert bal.credit_total == Decimal("300")

    def test_multiple_leaf_accounts_independent(self, db, accounts):
        engine = LedgerEngine(db)
        engine.update_balance(make_line(db, accounts["child1"].id, debit=Decimal("100")))
        engine.update_balance(make_line(db, accounts["child2"].id, debit=Decimal("200")))
        db.commit()

        b1 = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["child1"].id
        ).first().balance
        b2 = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["child2"].id
        ).first().balance
        assert b1 == Decimal("100")
        assert b2 == Decimal("200")


class TestCashBalanceCheck:
    """库存现金(1001)硬性余额不足校验"""

    def test_cash_negative_raises(self, db, accounts):
        engine = LedgerEngine(db)
        # 先存 100 现金
        engine.update_balance(make_line(db, accounts["cash"].id, debit=Decimal("100")))
        db.commit()
        # 试图取出 200 → 余额不足
        line = make_line(db, accounts["cash"].id, credit=Decimal("200"))
        with pytest.raises(AccountingError) as exc:
            engine.update_balance(line)
        assert exc.value.code == "INSUFFICIENT_BALANCE"

    def test_cash_exact_withdrawal_ok(self, db, accounts):
        engine = LedgerEngine(db)
        engine.update_balance(make_line(db, accounts["cash"].id, debit=Decimal("100")))
        db.commit()
        engine.update_balance(make_line(db, accounts["cash"].id, credit=Decimal("100")))
        db.commit()

        bal = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == accounts["cash"].id
        ).first()
        assert bal.balance == Decimal("0")

    def test_receivable_negative_allowed(self, db, accounts):
        """应收账款(asset_receivable)允许负数（视为预收）
        child1 是 liability_payable，但我们用 cash 的 code=1001 硬编码检查，
        所以应收账款类型即使负也不会报错。
        """
        engine = LedgerEngine(db)
        # 创建一个 asset_receivable 类型的科目
        receivable = LedgerAccount(
            ledger_id=accounts["child1"].ledger_id, code="1122", name="应收账款",
            account_type="asset_receivable", is_leaf=True,
        )
        db.add(receivable)
        db.flush()
        db.commit()

        # 贷方 > 借方 → 余额为负（客户多付=预收），不应报错
        line = make_line(db, receivable.id, credit=Decimal("500"))
        engine.update_balance(line)
        db.commit()

        bal = db.query(LedgerAccountBalance).filter(
            LedgerAccountBalance.ledger_account_id == receivable.id
        ).first()
        assert bal.balance == Decimal("-500")


class TestGetBalance:
    """查询余额"""

    def test_leaf_without_date(self, db, accounts):
        engine = LedgerEngine(db)
        engine.update_balance(make_line(db, accounts["child1"].id, debit=Decimal("300")))
        db.commit()
        bal = engine.get_balance(accounts["child1"].id)
        assert bal == Decimal("300")

    def test_leaf_with_date_asset(self, db, accounts):
        """资产类科目 date 查询：balance = debit - credit"""
        engine = LedgerEngine(db)
        engine.update_balance(make_line(db, accounts["cash"].id, debit=Decimal("300")))
        db.commit()
        bal = engine.get_balance(accounts["cash"].id, date="2026-06-01")
        assert bal == Decimal("300")

    def test_leaf_with_date_liability(self, db, accounts):
        """负债类科目 date 查询：balance = credit - debit（会计方向）"""
        engine = LedgerEngine(db)
        engine.update_balance(make_line(db, accounts["child1"].id, debit=Decimal("300")))
        db.commit()
        bal = engine.get_balance(accounts["child1"].id, date="2026-06-01")
        assert bal == Decimal("-300")

    def test_leaf_with_date_before_move(self, db, accounts):
        engine = LedgerEngine(db)
        engine.update_balance(make_line(db, accounts["child1"].id, debit=Decimal("300")))
        db.commit()
        bal = engine.get_balance(accounts["child1"].id, date="2026-05-01")
        assert bal == Decimal("0")


class TestTrialBalance:
    """试算平衡表"""

    def test_basic_trial_balance(self, db, accounts):
        engine = LedgerEngine(db)
        engine.update_balance(make_line(db, accounts["child1"].id, debit=Decimal("400")))
        engine.update_balance(make_line(db, accounts["child2"].id, credit=Decimal("400")))
        db.commit()

        tb = engine.get_trial_balance(accounts["child1"].ledger_id, date="2026-12-31")
        assert tb["balanced"] is True
        assert tb["total_debit"] == Decimal("400")
        assert tb["total_credit"] == Decimal("400")
        assert len(tb["rows"]) == 2
