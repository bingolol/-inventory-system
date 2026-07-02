<<<<<<< Updated upstream
﻿"""事务测试：其他应付款/个人垫付全流程
=======
"""事务测试：其他应付款/个人垫付全流程
>>>>>>> Stashed changes

覆盖：
  1. 创建垫付单 → 生成 PA-YYYY-NNNN 单号 + dr 借方科目 / cr 2241 凭证
  2. 偿还（部分 + 全额）→ status 流转 unpaid→partial→paid + 银行余额扣减 + 凭证
  3. 红冲垫付单的前置约束（有未冲红偿还 → 拒绝）
  4. 红冲单笔偿还 → 反向银行流水 + 状态重算
  5. 红冲垫付单（清空偿还后）→ 凭证冲红 + is_reversed=True
  6. readonly_middleware 拦截 DELETE
  7. BS 报表 2241 计入 other_payable / total_current_liabilities
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.usefixtures("bootstrap_db")

from tests.helpers import get_entity_id, uniq
from models import PersonalAdvance, BankAccount, BankTransaction
from models_finance import AccountMove

HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}


def _seed_ledger_balance(db, account_code, amount):
    """直接向指定总账科目注入借方余额（绕过 OpeningBalance 流程）

    用于测试 fixture：注入 1001 库存现金 / 1002 银行存款 余额，
    避开 LedgerEngine 对资产类账户"余额不得为负"的约束。
    """
    from decimal import Decimal as _D
    from models_finance import Ledger, LedgerAccount, LedgerAccountBalance
    from models import Account as _Account

    acct = db.query(_Account).filter(_Account.id == 1).first()
    ledger = db.query(Ledger).filter(Ledger.code == acct.code).first()
    if not ledger:
        return
    la = db.query(LedgerAccount).filter(
        LedgerAccount.ledger_id == ledger.id,
        LedgerAccount.code == account_code,
    ).first()
    if not la:
        return
    lab = db.query(LedgerAccountBalance).filter(
        LedgerAccountBalance.ledger_account_id == la.id
    ).first()
    if not lab:
        lab = LedgerAccountBalance(
            ledger_account_id=la.id,
<<<<<<< Updated upstream
            balance=_D("0"),
            debit_total=_D("0"),
            credit_total=_D("0"),
=======
            balance_l4=_D("0"),
            debit_total_l4=_D("0"),
            credit_total_l4=_D("0"),
>>>>>>> Stashed changes
        )
        db.add(lab)
        db.flush()
    amt = _D(str(amount))
<<<<<<< Updated upstream
    lab.balance = (lab.balance or 0) + amt
    lab.debit_total = (lab.debit_total or 0) + amt
=======
    lab.balance_l4 = (lab.balance_l4 or 0) + amt
    lab.debit_total_l4 = (lab.debit_total_l4 or 0) + amt
>>>>>>> Stashed changes
    db.commit()


def _create_bank_account(client, db, balance=10000):
    """创建一个银行账户，初始余额为 balance

    注：银行账户 API 拒绝非零初始余额（必须走 OpeningBalance 流程过账到总账 1002），
    测试中为简化，开户后直接通过 db fixture 设置 BankAccount.balance，
    并通过 _seed_ledger_balance 同步总账 1002 借方余额。
    """
    resp = client.post("/api/bank-accounts", json={
        "bank_name": uniq("测试银行-"),
        "account_number": uniq("ACCT-"),
        "balance": "0",
        "description": "测试账户",
    }, headers=HEADERS)
    assert resp.status_code == 200, resp.text
    bid = resp.json().get("id") or resp.json().get("data", {}).get("id")

    if balance > 0:
        # 直接 db 写银行账户余额（绕过 API 限制）
        from decimal import Decimal as _D
        bank = db.query(BankAccount).filter(BankAccount.id == bid).first()
<<<<<<< Updated upstream
        bank.balance = _D(str(balance)).quantize(_D("0.01"))
=======
        bank.balance_l4 = _D(str(balance)).quantize(_D("0.01"))
>>>>>>> Stashed changes
        db.commit()
        # 同步总账 1002 借方余额
        _seed_ledger_balance(db, "1002", balance)
    return bid


def _create_advance(client, **overrides):
    payload = {
        "advancer_name": "张三",
        "amount": "2000.00",
        "advance_date": "2026-06-15",
        "debit_account_code": "6601",
        "description": "替公司垫付6月办公费",
    }
    payload.update(overrides)
    resp = client.post("/api/personal-advances", json=payload, headers=HEADERS)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _balance_2241(client):
    """读取总账 2241 其他应付款余额"""
    resp = client.get("/api/financial-reports/balance-sheet?date=2026-12-31", headers=HEADERS)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════════
# 1. 创建垫付单
# ═══════════════════════════════════════════════════════════════

class Test创建垫付单:

    def test_create_success_returns_PA_no_and_journal(self, client, db):
        r = _create_advance(client, advancer_name="测试A")
        advance_id = get_entity_id(r)
        assert advance_id > 0
        # 单号格式 PA-YYYY-NNNN
        advance_no = r["data"]["advance_no"]
        assert advance_no.startswith("PA-2026-")
        # 状态 unpaid + paid_amount=0
        assert r["data"]["repayment_status"] == "unpaid"
        assert Decimal(r["data"]["paid_amount"]) == Decimal("0")
        # remaining_amount = amount
        assert Decimal(r["data"]["remaining_amount"]) == Decimal("2000.00")
        # OperationResult 字段
        assert r["success"] is True
        assert r["entity_type"] == "personal_advance"
        assert "+2000.00" in str(r["changes"])  # other_payable +2000

        # 验证凭证已过账：dr 6601 / cr 2241
        moves = db.query(AccountMove).filter(
            AccountMove.source_model == "personal_advance",
            AccountMove.source_id == advance_id,
            AccountMove.is_reversal == False,
        ).all()
        assert len(moves) == 1
        # 验证余额：6601 借 2000，2241 贷 2000
<<<<<<< Updated upstream
        assert Decimal(str(moves[0].amount_total)) == Decimal("2000.00")
=======
        assert Decimal(str(moves[0].amount_total_l2)) == Decimal("2000.00")
>>>>>>> Stashed changes

    def test_create_invalid_debit_account_rejected(self, client):
        """借方科目不在白名单 → 422"""
        resp = client.post("/api/personal-advances", json={
            "advancer_name": "X",
            "amount": "100",
            "advance_date": "2026-06-15",
            "debit_account_code": "9999",  # 不在白名单
        }, headers=HEADERS)
        assert resp.status_code in (400, 422)

    def test_create_zero_amount_rejected(self, client):
        resp = client.post("/api/personal-advances", json={
            "advancer_name": "X",
            "amount": "0",
            "advance_date": "2026-06-15",
        }, headers=HEADERS)
        assert resp.status_code in (400, 422)

    def test_create_empty_advancer_rejected(self, client):
        resp = client.post("/api/personal-advances", json={
            "advancer_name": "",
            "amount": "100",
            "advance_date": "2026-06-15",
        }, headers=HEADERS)
        assert resp.status_code in (400, 422)

    def test_advance_no_increments_per_account(self, client, db):
        """同一账本内多笔垫付单号递增"""
        r1 = _create_advance(client, advancer_name="A")
        r2 = _create_advance(client, advancer_name="B")
        n1 = r1["data"]["advance_no"]
        n2 = r2["data"]["advance_no"]
        assert n1 != n2
        # 后一张序号大于前一张
        s1 = int(n1.split("-")[-1])
        s2 = int(n2.split("-")[-1])
        assert s2 == s1 + 1


# ═══════════════════════════════════════════════════════════════
# 2. 偿还
# ═══════════════════════════════════════════════════════════════

class Test偿还:

    def test_partial_repay_via_bank(self, client, db):
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="2000.00")
        aid = get_entity_id(r)

        # 部分偿还 1000
        repay_resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "1000.00",
            "repayment_date": "2026-07-01",
            "bank_account_id": bid,
            "description": "首笔偿还",
        }, headers=HEADERS)
        assert repay_resp.status_code == 200, repay_resp.text
        body = repay_resp.json()
        assert body["entity_type"] == "personal_advance_repayment"
        assert body["data"]["advance"]["repayment_status"] == "partial"
        assert Decimal(body["data"]["advance"]["paid_amount"]) == Decimal("1000.00")
        assert Decimal(body["data"]["advance"]["remaining_amount"]) == Decimal("1000.00")

        # 银行余额扣减 1000
        bank = db.query(BankAccount).filter(BankAccount.id == bid).first()
<<<<<<< Updated upstream
        assert Decimal(str(bank.balance)) == Decimal("9000.00")
=======
        assert Decimal(str(bank.balance_l4)) == Decimal("9000.00")
>>>>>>> Stashed changes

        # 银行流水已生成
        tx = db.query(BankTransaction).filter(
            BankTransaction.related_entity_type == "personal_advance_repayment"
        ).first()
        assert tx is not None
<<<<<<< Updated upstream
        assert Decimal(str(tx.amount)) == Decimal("1000.00")
=======
        assert Decimal(str(tx.amount_l2)) == Decimal("1000.00")
>>>>>>> Stashed changes
        assert tx.transaction_type == "outflow"

        # 偿还凭证已过账：dr 2241 / cr 1002
        repay_id = body["entity_id"]
        moves = db.query(AccountMove).filter(
            AccountMove.source_model == "personal_advance_repay",
            AccountMove.source_id == repay_id,
            AccountMove.is_reversal == False,
        ).all()
        assert len(moves) == 1

    def test_full_repay_transitions_to_paid(self, client, db):
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="2000.00")
        aid = get_entity_id(r)

        # 全额偿还
        resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "2000.00",
            "repayment_date": "2026-07-01",
            "bank_account_id": bid,
        }, headers=HEADERS)
        assert resp.status_code == 200, resp.text
        advance = resp.json()["data"]["advance"]
        assert advance["repayment_status"] == "paid"
        assert Decimal(advance["paid_amount"]) == Decimal("2000.00")
        assert Decimal(advance["remaining_amount"]) == Decimal("0.00")

    def test_cash_repay_no_bank_account(self, client, db):
        """bank_account_id=None → 贷 1001 库存现金，不创建 BankTransaction"""
        # 注入 1001 库存现金余额（避开 LedgerEngine 对 1001 余额不得为负的约束）
        _seed_ledger_balance(db, "1001", 10000)
        r = _create_advance(client, amount="500.00")
        aid = get_entity_id(r)
        resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "500.00",
            "repayment_date": "2026-07-01",
            "bank_account_id": None,
        }, headers=HEADERS)
        assert resp.status_code == 200, resp.text
        # 验证未生成 BankTransaction（现金偿还无银行流水）
        from models import BankTransaction
        txs = db.query(BankTransaction).filter(
            BankTransaction.related_entity_type == "personal_advance_repayment"
        ).all()
        # 该笔 repay 无 bank_transaction_id
        repay_data = resp.json()["data"]["repayment"]
        assert repay_data["bank_transaction_id"] is None

    def test_overpay_rejected(self, client, db):
        """偿还超过未还余额 → 400"""
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="1000.00")
        aid = get_entity_id(r)
        resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "1500.00",  # 超过 1000
            "repayment_date": "2026-07-01",
            "bank_account_id": bid,
        }, headers=HEADERS)
        assert resp.status_code in (400, 422)
        body = resp.json()
        assert "余额" in body["error"]["message"] or "超额" in body["error"]["message"]

    def test_bank_balance_insufficient_rejected(self, client, db):
        """银行余额不足 → 拒绝"""
        bid = _create_bank_account(client, db, balance=100)  # 余额 100
        r = _create_advance(client, amount="1000.00")
        aid = get_entity_id(r)
        resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "500.00",
            "repayment_date": "2026-07-01",
            "bank_account_id": bid,
        }, headers=HEADERS)
        assert resp.status_code in (400, 422)

    def test_repay_reversed_advance_rejected(self, client, db):
        """已冲红的垫付单不能偿还"""
        r = _create_advance(client, amount="500.00")
        aid = get_entity_id(r)
        # 先冲红
        client.post(f"/api/personal-advances/{aid}/reverse", headers=HEADERS)
        # 偿还应失败
        resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "100.00",
            "repayment_date": "2026-07-01",
        }, headers=HEADERS)
        assert resp.status_code in (400, 422)


# ═══════════════════════════════════════════════════════════════
# 3. 红冲垫付单 + 偿还记录
# ═══════════════════════════════════════════════════════════════

class Test红冲:

    def test_reverse_advance_with_active_repayments_rejected(self, client, db):
        """有未冲红偿还 → 拒绝红冲垫付单"""
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="1000.00")
        aid = get_entity_id(r)
        # 偿还一笔
        client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "500.00", "repayment_date": "2026-07-01", "bank_account_id": bid,
        }, headers=HEADERS)
        # 尝试红冲垫付单 → 拒绝
        resp = client.post(f"/api/personal-advances/{aid}/reverse", headers=HEADERS)
        assert resp.status_code in (400, 422)

    def test_reverse_repayment_reverses_bank_and_status(self, client, db):
        """红冲单笔偿还：银行流水反向 + 状态 partial→unpaid"""
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="1000.00")
        aid = get_entity_id(r)
        repay_resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "500.00", "repayment_date": "2026-07-01", "bank_account_id": bid,
        }, headers=HEADERS)
        repay_id = repay_resp.json()["entity_id"]

        # 红冲前：余额 9500，状态 partial
        bank = db.query(BankAccount).filter(BankAccount.id == bid).first()
<<<<<<< Updated upstream
        assert Decimal(str(bank.balance)) == Decimal("9500.00")
=======
        assert Decimal(str(bank.balance_l4)) == Decimal("9500.00")
>>>>>>> Stashed changes
        advance = db.query(PersonalAdvance).filter(PersonalAdvance.id == aid).first()
        assert advance.repayment_status == "partial"

        # 红冲偿还
        rev_resp = client.post(
            f"/api/personal-advances/{aid}/repayments/{repay_id}/reverse", headers=HEADERS
        )
        assert rev_resp.status_code == 200, rev_resp.text

        # 红冲后：余额恢复 10000，状态 unpaid
        db.refresh(bank)
<<<<<<< Updated upstream
        assert Decimal(str(bank.balance)) == Decimal("10000.00")
        db.refresh(advance)
        assert advance.repayment_status == "unpaid"
        assert Decimal(str(advance.paid_amount)) == Decimal("0.00")
=======
        assert Decimal(str(bank.balance_l4)) == Decimal("10000.00")
        db.refresh(advance)
        assert advance.repayment_status == "unpaid"
        assert Decimal(str(advance.paid_amount_l4)) == Decimal("0.00")
>>>>>>> Stashed changes

        # 偿还记录已标记冲红
        db.expire_all()
        from models import PersonalAdvanceRepayment
        rp = db.query(PersonalAdvanceRepayment).filter(
            PersonalAdvanceRepayment.id == repay_id
        ).first()
        assert rp.is_reversed is True

    def test_reverse_advance_after_all_repayments_reversed(self, client, db):
        """所有偿还已冲红 → 可红冲垫付单"""
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="1000.00")
        aid = get_entity_id(r)
        repay_resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "500.00", "repayment_date": "2026-07-01", "bank_account_id": bid,
        }, headers=HEADERS)
        repay_id = repay_resp.json()["entity_id"]

        # 先红冲偿还
        client.post(f"/api/personal-advances/{aid}/repayments/{repay_id}/reverse", headers=HEADERS)
        # 再红冲垫付单
        rev = client.post(f"/api/personal-advances/{aid}/reverse", headers=HEADERS)
        assert rev.status_code == 200, rev.text
        db.expire_all()
        advance = db.query(PersonalAdvance).filter(PersonalAdvance.id == aid).first()
        assert advance.is_reversed is True
        assert advance.reversed_at is not None


# ═══════════════════════════════════════════════════════════════
# 4. 中间件拦截
# ═══════════════════════════════════════════════════════════════

class Test中间件:

    def test_readonly_blocks_delete_advance(self, client):
        """DELETE /api/personal-advances/{id} → 403"""
        r = _create_advance(client, amount="100.00")
        aid = get_entity_id(r)
        resp = client.delete(f"/api/personal-advances/{aid}", headers=HEADERS)
        assert resp.status_code == 403
        assert "reverse" in resp.json()["error"]["message"]

    def test_readonly_blocks_delete_repayment(self, client, db):
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="500.00")
        aid = get_entity_id(r)
        repay_resp = client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "200.00", "repayment_date": "2026-07-01", "bank_account_id": bid,
        }, headers=HEADERS)
        repay_id = repay_resp.json()["entity_id"]
        resp = client.delete(
            f"/api/personal-advances/{aid}/repayments/{repay_id}", headers=HEADERS
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════
# 5. BS 报表 2241
# ═══════════════════════════════════════════════════════════════

class Test资产负债表2241:

    def test_other_payable_included_in_bs(self, client):
        """BS 报表应包含 other_payable 字段且计入 total_current_liabilities"""
        _create_advance(client, amount="2000.00")
        bs = _balance_2241(client)
        assert "other_payable" in bs
        assert Decimal(str(bs["other_payable"])) >= Decimal("2000.00")
        # total_current_liabilities 应至少包含 other_payable
        assert Decimal(str(bs["total_current_liabilities"])) >= Decimal(str(bs["other_payable"]))

    def test_repay_reduces_other_payable(self, client, db):
        """偿还后 BS other_payable 应减少相应金额

        注：模块级 db 会累积其他测试创建的垫付单（2241 余额不隔离），
        因此用 before/after 差值断言而非绝对值。
        """
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="2000.00")
        aid = get_entity_id(r)
        bs_before = _balance_2241(client)
        before = Decimal(str(bs_before["other_payable"]))
        # 偿还 1000
        client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "1000.00", "repayment_date": "2026-07-01", "bank_account_id": bid,
        }, headers=HEADERS)
        bs_after = _balance_2241(client)
        after = Decimal(str(bs_after["other_payable"]))
        # other_payable 应正好减少 1000
        assert before - after == Decimal("1000.00"), f"before={before}, after={after}"


# ═══════════════════════════════════════════════════════════════
# 6. 查询接口
# ═══════════════════════════════════════════════════════════════

class Test查询:

    def test_list_with_filters(self, client):
        _create_advance(client, advancer_name="李四")
        resp = client.get("/api/personal-advances?advancer_name=李四", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for it in data["items"]:
            assert "李四" in it["advancer_name"]

    def test_get_single_not_found(self, client):
        resp = client.get("/api/personal-advances/999999", headers=HEADERS)
        assert resp.status_code in (400, 404)

    def test_totals_card(self, client):
        _create_advance(client, amount="3000.00")
        resp = client.get("/api/personal-advances/totals", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(str(data["total_amount"])) >= Decimal("3000.00")
        assert Decimal(str(data["remaining_amount"])) == Decimal(str(data["total_amount"])) - Decimal(str(data["paid_amount"]))

    def test_summary_by_advancer(self, client):
        _create_advance(client, advancer_name="王五", amount="500.00")
        _create_advance(client, advancer_name="王五", amount="700.00")
        resp = client.get("/api/personal-advances/summary", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        wang = next((r for r in data if r["advancer_name"] == "王五"), None)
        assert wang is not None
        assert wang["advance_count"] == 2
        assert Decimal(str(wang["total_amount"])) == Decimal("1200.00")

    def test_repayments_listing(self, client, db):
        bid = _create_bank_account(client, db, balance=10000)
        r = _create_advance(client, amount="1000.00")
        aid = get_entity_id(r)
        client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "300.00", "repayment_date": "2026-07-01", "bank_account_id": bid,
        }, headers=HEADERS)
        client.post(f"/api/personal-advances/{aid}/repay", json={
            "amount": "700.00", "repayment_date": "2026-07-15", "bank_account_id": bid,
        }, headers=HEADERS)
        resp = client.get(f"/api/personal-advances/{aid}/repayments", headers=HEADERS)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2

