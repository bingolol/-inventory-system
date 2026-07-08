"""Golden Tests 公共辅助函数

消除 AP-2（分散的 fixture）和代码重复。
所有 8 个黄金测试文件共享这些工具函数。
"""
import os
import tempfile
import uuid
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from utils import _d


def make_engine():
    """创建独立的临时 SQLite 引擎（每个测试文件隔离）"""
    TEST_DB = os.path.join(tempfile.gettempdir(), f"test_golden_{uuid.uuid4().hex[:8]}.db")
    _engine = create_engine(
        f"sqlite:///{TEST_DB}",
        connect_args={"check_same_thread": False},
    )
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine, _SessionLocal


def _db(_SessionLocal):
    """返回一个新的 db session"""
    return _SessionLocal()


def _ledger_balance(db, code):
    """计算指定科目代码的总账余额（借-贷）"""
    la = db.query(LedgerAccount).filter(LedgerAccount.code == code).first()
    if not la:
        return Decimal("0")
    total = Decimal("0")
    for line in db.query(AccountMoveLine).filter(
        AccountMoveLine.ledger_account_id == la.id
    ).all():
        total += _d(line.debit_l2) - _d(line.credit_l2)
    return total


def _credit_balance(db, code):
    """计算贷方余额（-借+贷）"""
    return -_ledger_balance(db, code)


# 别名：002/003 使用的短名
_lb = _ledger_balance
_cb = _credit_balance


def _trace_bal(db, code):
    """追溯余额到凭证行

    返回 (余额, [(aml_id, source_model, source_id, is_reversal, debit, credit)])
    """
    la = db.query(LedgerAccount).filter(LedgerAccount.code == code).first()
    if not la:
        return Decimal("0"), []
    rows = (
        db.query(AccountMoveLine, AccountMove)
        .join(AccountMove, AccountMove.id == AccountMoveLine.move_id)
        .filter(AccountMoveLine.ledger_account_id == la.id)
        .all()
    )
    balance = Decimal("0")
    traces = []
    for aml, am in rows:
        balance += _d(aml.debit_l2) - _d(aml.credit_l2)
        traces.append((
            aml.id, am.source_model, am.source_id, am.is_reversal,
            _d(aml.debit_l2), _d(aml.credit_l2),
        ))
    return balance, traces


def _get_id(resp, label=""):
    """从各种响应格式中提取 entity ID"""
    data = resp.json()
    eid = data.get("entity_id") or data.get("id")
    if eid is None and "entity" in data:
        eid = data["entity"].get("entity_id") or data["entity"].get("id")
    if eid is None and "data" in data:
        if isinstance(data["data"], dict):
            eid = data["data"].get("id") or data["data"].get("entity_id")
    if eid is None and isinstance(data.get("data"), dict) and "advance" in data["data"]:
        eid = data["data"]["advance"].get("id")
    assert eid is not None, f"No entity id in {label} response: {data}"
    return int(eid)


def _collect_move_lines(db, move):
    """收集一张凭证的所有分录，按科目代码聚合 (debit, credit)"""
    actual = {}
    lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == move.id).all()
    for line in lines:
        account = db.query(LedgerAccount).filter(
            LedgerAccount.id == line.ledger_account_id
        ).first()
        if not account:
            continue
        code = account.code
        prev_debit, prev_credit = actual.get(code, (Decimal("0"), Decimal("0")))
        actual[code] = (
            prev_debit + _d(line.debit_l2),
            prev_credit + _d(line.credit_l2),
        )
    return actual


def _verify_move_lines(db, move, expected_lines, label=""):
    """验证凭证分录与期望值一致（容差 0.02）"""
    actual = _collect_move_lines(db, move)
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for code, exp_debit, exp_credit in expected_lines:
        act_debit, act_credit = actual.get(code, (Decimal("0"), Decimal("0")))
        assert abs(act_debit - _d(exp_debit)) <= Decimal("0.02"), \
            f"{label} 科目{code} 借方 {act_debit} != 期望 {exp_debit}"
        assert abs(act_credit - _d(exp_credit)) <= Decimal("0.02"), \
            f"{label} 科目{code} 贷方 {act_credit} != 期望 {exp_credit}"
        total_debit += act_debit
        total_credit += act_credit
    assert abs(total_debit - total_credit) <= Decimal("0.02"), \
        f"{label} 凭证借贷不平: 借方{total_debit} != 贷方{total_credit}"


def _assert_move_lines(db, source_model, source_id, expected_lines):
    """查找指定来源的凭证并验证分录"""
    move = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == False,
    ).first()
    assert move is not None, f"{source_model}#{source_id} 无凭证"
    _verify_move_lines(db, move, expected_lines, label=f"{source_model}#{source_id}")
