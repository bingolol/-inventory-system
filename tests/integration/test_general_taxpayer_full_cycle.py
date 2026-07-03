"""测试剧本：一般纳税人月度经营闭环（多批次采购/销售）

测试目标：验证一般纳税人场景下，业务单据、真相源表、会计凭证、财务报表
之间的完整因果链。

场景：2026年1月，一般纳税人，增值税率13%
  1. 期初建账：银行存款 100,000，实收资本 100,000
  2. 5次采购入库（不同单价，验证移动加权平均成本）
  3. 5次采购付款
  4. 3次销售出库
  5. 3次销售收款
  6. 1笔费用报销
  7. 增值税计算
  8. 财务报表验证 + 跨表勾稽

设计预期（可手工验算）：
  采购总量 500 件，总成本 50,000 → 加权平均成本 100 元/件
  销售总量 300 件 → COGS = 30,000；期末库存 200 件 = 20,000
  销售收入 62,400；销项税 8,112
  进项税 6,500；应纳增值税 1,612
  管理费用 2,000；净利润 = 62,400 - 30,000 - 2,000 = 30,400
  期末现金 = 100,000 - 56,500 + 70,512 - 2,000 = 112,012
  资产负债表：资产 132,012 = 负债 1,612 + 权益 130,400
"""

import sys, os, pytest, tempfile, uuid
from decimal import Decimal

pytestmark = pytest.mark.golden
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import get_db, Base, init_db
import database
from models import Account, Inventory, StockMove, PurchaseOrder, SaleOrder, OpeningBalance
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from rules import enforce_rules


TEST_DB = os.path.join(tempfile.gettempdir(), f"test_general_tax_{uuid.uuid4().hex[:8]}.db")
_engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    monkeypatch.setattr(database, '_engine', _engine)
    monkeypatch.setattr(database, 'SessionLocal', _SessionLocal)
    Base.metadata.create_all(bind=_engine)
    init_db()

    from factories import ensure_default_account
    db = _SessionLocal()
    try:
        ensure_default_account(db)
        acc = db.query(Account).first()
        if acc:
            acc.taxpayer_type_l3 = "general"
            acc.enable_vat_deduction = True
            db.commit()
    finally:
        db.close()

    def _get_db():
        db = _SessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = _get_db
    yield
    Base.metadata.drop_all(bind=_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        c.headers.update({"X-Operator": "user"})
        yield c


ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID)}
UNIQUE = str(uuid.uuid4().hex[:6])


def _db():
    """获取测试用独立 DB Session，用于直接查询真相源表。"""
    return _SessionLocal()


def _ledger_balance(db, account_code: str) -> Decimal:
    """按科目编码查询期末余额（借正贷负）。"""
    la = db.query(LedgerAccount).filter(LedgerAccount.code == account_code).first()
    if not la:
        return Decimal("0")
    total = Decimal("0")
    for line in db.query(AccountMoveLine).filter(AccountMoveLine.ledger_account_id == la.id).all():
        total += Decimal(str(line.debit_l2 or 0)) - Decimal(str(line.credit_l2 or 0))
    return total


def _credit_balance(db, account_code: str) -> Decimal:
    """按科目编码查询期末贷方余额（负债/权益/收入类用）。"""
    return -_ledger_balance(db, account_code)


def _collect_move_lines(db, move):
    """汇总某凭证的分录，返回 {code: (debit, credit)}。"""
    actual = {}
    for line in move.line_ids:
        code = db.query(LedgerAccount).filter(LedgerAccount.id == line.ledger_account_id).first().code
        actual[code] = (
            actual.get(code, Decimal("0")) + Decimal(str(line.debit_l2 or 0)),
            actual.get(code, Decimal("0")) + Decimal(str(line.credit_l2 or 0)),
        )
    return actual


def _assert_move_lines(db, source_model: str, source_id: int, expected_lines: list):
    """验证某源单据生成的凭证分录。expected_lines: [(account_code, debit, credit), ...]"""
    move = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == False,
    ).first()
    assert move is not None, f"{source_model}#{source_id} 应生成凭证"
    _verify_move_lines(db, move, expected_lines, label=f"{source_model}#{source_id}")


def _verify_move_lines(db, move, expected_lines: list, label: str = ""):
    """直接验证给定凭证的分录。"""
    actual = _collect_move_lines(db, move)
    for code, exp_debit, exp_credit in expected_lines:
        act_debit, act_credit = actual.get(code, (Decimal("0"), Decimal("0")))
        assert abs(act_debit - Decimal(str(exp_debit))) <= Decimal("0.01"), \
            f"{label} 科目{code} 借方应为{exp_debit}，实际{act_debit}"
        assert abs(act_credit - Decimal(str(exp_credit))) <= Decimal("0.01"), \
            f"{label} 科目{code} 贷方应为{exp_credit}，实际{act_credit}"


def _assert_bank_move(db, move_type: str, amount: Decimal):
    """收付款凭证没有 source_model/source_id，按 move_type + 金额匹配。"""
    moves = db.query(AccountMove).filter(
        AccountMove.move_type == move_type,
        AccountMove.is_reversal == False,
    ).all()
    for move in moves:
        total = sum(Decimal(str(line.debit_l2 or 0)) for line in move.line_ids)
        if abs(total - amount) <= Decimal("0.01"):
            return move
    raise AssertionError(f"未找到 {move_type} 金额={amount} 的凭证")


class TestGeneralTaxpayerFullCycle:

    def test_full_monthly_cycle(self, client):
        c = client
        s = {}

        # ═══════════════════════════════════════════
        # 第一幕：期初建账
        # ═══════════════════════════════════════════

        # 1a. 创建银行账户
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行",
            "account_number": f"622202{UNIQUE}",
            "balance": 0,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["bank_id"] = r.json()["id"]

        # 1b. 录入期初余额
        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01",
            "bank_balance": 100000,
            "paid_in_capital": 100000,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        # 1c. 资产负债表平衡验证
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-01", headers=HEADERS)
        assert r.status_code == 200, r.text
        bs = r.json()
        assert Decimal(str(bs["total_assets"])) == Decimal(str(bs["total_liabilities_and_equity"]))
        assert float(bs["monetary_funds"]) == 100000.0
        assert float(bs["paid_in_capital"]) == 100000.0

        # 1d. 创建基础数据
        r = c.post("/api/products", json={
            "name": f"商品X-{UNIQUE}", "sku": f"X-{UNIQUE}",
            "purchase_price": 100, "sale_price": 200,
            "unit": "个", "track_inventory": True, "category": "测试",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["pid"] = r.json()["entity_id"]

        r = c.post("/api/suppliers", json={"name": f"供应商A-{UNIQUE}"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["supplier_id"] = r.json()["entity_id"]

        r = c.post("/api/customers", json={"name": f"客户B-{UNIQUE}"}, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["customer_id"] = r.json()["entity_id"]

        # ═══════════════════════════════════════════
        # 第二幕：5次采购入库（不同单价）
        # ═══════════════════════════════════════════

        purchases = [
            # (day, qty, unit_price, amount, tax, total)
            (5, 100, Decimal("100"), Decimal("10000"), Decimal("1300"), Decimal("11300")),
            (6, 50,  Decimal("120"), Decimal("6000"),  Decimal("780"),  Decimal("6780")),
            (7, 200, Decimal("90"),  Decimal("18000"), Decimal("2340"), Decimal("20340")),
            (8, 100, Decimal("110"), Decimal("11000"), Decimal("1430"), Decimal("12430")),
            (9, 50,  Decimal("100"), Decimal("5000"),  Decimal("650"),  Decimal("5650")),
        ]

        purchase_ids = []
        for idx, (day, qty, price, amount, tax, total) in enumerate(purchases, 1):
            r = c.post("/api/purchases", json={
                "supplier_id": s["supplier_id"],
                "items": [{
                    "product_id": s["pid"],
                    "quantity": qty,
                    "unit_price": float(price),
                    "tax_rate": 0.13,
                }],
                "purchase_date": f"2026-01-{day:02d}T10:00:00",
            }, headers=HEADERS)
            assert r.status_code == 200, r.text
            pid = r.json()["entity_id"]
            purchase_ids.append(pid)

            # 真相源：StockMove
            db = _db()
            try:
                sm = db.query(StockMove).filter(
                    StockMove.account_id == ACCT_ID,
                    StockMove.product_id == s["pid"],
                    StockMove.source_type == "purchase_order",
                    StockMove.source_id == pid,
                ).first()
                assert sm is not None, f"第{idx}次采购应生成 StockMove"
                assert int(sm.quantity_l1) == qty, f"第{idx}次采购入库数量应为{qty}，实际{sm.quantity_l1}"

                # 凭证分录：借 1405 库存，借 222102 进项税，贷 2202 应付账款
                _assert_move_lines(db, "purchase_order", pid, [
                    ("1405", amount, Decimal("0")),
                    ("222102", tax, Decimal("0")),
                    ("2202", Decimal("0"), total),
                ])
            finally:
                db.close()

        # 累计采购后库存校验
        total_qty = sum(p[1] for p in purchases)          # 500
        total_cost = sum(p[3] for p in purchases)         # 50,000
        total_input_tax = sum(p[4] for p in purchases)    # 6,500
        total_payable = sum(p[5] for p in purchases)      # 56,500

        db = _db()
        try:
            inv = db.query(Inventory).filter(
                Inventory.account_id == ACCT_ID,
                Inventory.product_id == s["pid"],
            ).first()
            assert inv is not None
            assert inv.quantity_l4 == total_qty, f"采购后库存数量应为{total_qty}，实际{inv.quantity_l4}"
            assert Decimal(str(inv.average_cost_l4)) == Decimal("100.00"), \
                f"移动加权平均成本应为100，实际{inv.average_cost_l4}"
            assert Decimal(str(inv.total_value_l4)) == total_cost, \
                f"采购后库存价值应为{total_cost}，实际{inv.total_value_l4}"

            assert _ledger_balance(db, "1405") == total_cost, f"库存商品科目应为{total_cost}"
            assert _ledger_balance(db, "222102") == total_input_tax, f"进项税额科目应为{total_input_tax}"
            assert _credit_balance(db, "2202") == total_payable, f"应付账款科目应为{total_payable}"

            enforce_rules(db, ["AS-03"], {"product_id": s["pid"]})
        finally:
            db.close()

        print(f"✅ 第二幕完成：5次采购入库，共 {total_qty} 件，总成本 {total_cost}")

        # ═══════════════════════════════════════════
        # 第三幕：5次采购付款
        # ═══════════════════════════════════════════

        for idx, (day, qty, price, amount, tax, total) in enumerate(purchases, 1):
            r = c.post("/api/payments", json={
                "payment_type": "purchase",
                "related_entity_type": "purchase_order",
                "related_entity_id": purchase_ids[idx - 1],
                "amount": float(total),
                "payment_date": f"2026-01-{day + 1:02d}T00:00:00",
                "bank_account_id": s["bank_id"],
                "description": f"支付第{idx}笔采购货款",
            }, headers=HEADERS)
            assert r.status_code == 200, r.text
            payment_id = r.json()["data"]["id"]

            db = _db()
            try:
                # 付款凭证：借 2202 应付，贷 1002 银行
                move = _assert_bank_move(db, "payment", total)
                _verify_move_lines(db, move, [
                    ("2202", total, Decimal("0")),
                    ("1002", Decimal("0"), total),
                ], label=f"payment#{payment_id}")
            finally:
                db.close()

        db = _db()
        try:
            assert _credit_balance(db, "2202") == Decimal("0"), "采购付款后应付账款应为0"
        finally:
            db.close()

        print("✅ 第三幕完成：5次采购付款")

        # ═══════════════════════════════════════════
        # 第四幕：3次销售出库
        # ═══════════════════════════════════════════

        sales = [
            # (day, qty, unit_price, revenue, tax, total)
            (15, 80,  Decimal("200"), Decimal("16000"), Decimal("2080"), Decimal("18080")),
            (16, 120, Decimal("220"), Decimal("26400"), Decimal("3432"), Decimal("29832")),
            (17, 100, Decimal("200"), Decimal("20000"), Decimal("2600"), Decimal("22600")),
        ]

        sale_ids = []
        for idx, (day, qty, price, revenue, tax, total) in enumerate(sales, 1):
            r = c.post("/api/sales", json={
                "customer_id": s["customer_id"],
                "deduct_inventory": True,
                "payment_status": "unpaid",
                "sale_date": f"2026-01-{day:02d}T10:00:00",
                "items": [{
                    "product_id": s["pid"],
                    "quantity": qty,
                    "unit_price": float(price),
                    "tax_rate": 0.13,
                }],
            }, headers=HEADERS)
            assert r.status_code == 200, r.text
            sid = r.json()["entity_id"]
            sale_ids.append(sid)

            db = _db()
            try:
                # 真相源：销售出库 StockMove
                sm = db.query(StockMove).filter(
                    StockMove.account_id == ACCT_ID,
                    StockMove.product_id == s["pid"],
                    StockMove.source_type == "sale_order",
                    StockMove.source_id == sid,
                ).first()
                assert sm is not None, f"第{idx}次销售应生成 StockMove"
                assert int(sm.quantity_l1) == -qty, f"第{idx}次销售出库数量应为-{qty}，实际{sm.quantity_l1}"
                cogs = (Decimal(str(qty)) * Decimal("100")).quantize(Decimal("0.01"))
                assert Decimal(str(sm.total_cost_l2)) == cogs, f"第{idx}次销售成本应为{cogs}，实际{sm.total_cost_l2}"

                # 凭证分录：借 1122 应收，贷 6001 收入，贷 222101 销项税；
                #           借 6401 成本，贷 1405 库存
                _assert_move_lines(db, "sale_order", sid, [
                    ("1122", total, Decimal("0")),
                    ("6001", Decimal("0"), revenue),
                    ("222101", Decimal("0"), tax),
                    ("6401", cogs, Decimal("0")),
                    ("1405", Decimal("0"), cogs),
                ])
            finally:
                db.close()

        total_sold = sum(s[1] for s in sales)             # 300
        total_revenue = sum(s[3] for s in sales)          # 62,400
        total_output_tax = sum(s[4] for s in sales)       # 8,112
        total_ar = sum(s[5] for s in sales)               # 70,512
        total_cogs = total_sold * Decimal("100")          # 30,000
        ending_inventory_qty = total_qty - total_sold     # 200
        ending_inventory_value = total_cost - total_cogs  # 20,000

        db = _db()
        try:
            inv = db.query(Inventory).filter(
                Inventory.account_id == ACCT_ID,
                Inventory.product_id == s["pid"],
            ).first()
            assert inv.quantity_l4 == ending_inventory_qty
            assert Decimal(str(inv.total_value_l4)) == ending_inventory_value

            assert _ledger_balance(db, "1122") == total_ar, f"应收账款应为{total_ar}"
            assert _credit_balance(db, "6001") == total_revenue, f"主营业务收入应为{total_revenue}"
            assert _credit_balance(db, "222101") == total_output_tax, f"销项税额应为{total_output_tax}"
            assert _ledger_balance(db, "6401") == total_cogs, f"主营业务成本应为{total_cogs}"
            assert _ledger_balance(db, "1405") == ending_inventory_value, f"库存商品应为{ending_inventory_value}"

            enforce_rules(db, ["AS-03"], {"product_id": s["pid"]})
        finally:
            db.close()

        print(f"✅ 第四幕完成：3次销售出库，共 {total_sold} 件，收入 {total_revenue}，COGS {total_cogs}")

        # ═══════════════════════════════════════════
        # 第五幕：3次销售收款
        # ═══════════════════════════════════════════

        for idx, (day, qty, price, revenue, tax, total) in enumerate(sales, 1):
            r = c.post("/api/receipts", json={
                "receipt_type": "sale",
                "related_entity_type": "sale_order",
                "related_entity_id": sale_ids[idx - 1],
                "amount": float(total),
                "receipt_date": f"2026-01-{day + 1:02d}T10:00:00",
                "bank_account_id": s["bank_id"],
                "description": f"收到第{idx}笔销售货款",
            }, headers=HEADERS)
            assert r.status_code == 200, r.text

            db = _db()
            try:
                move = _assert_bank_move(db, "receipt", total)
                _verify_move_lines(db, move, [
                    ("1002", total, Decimal("0")),
                    ("1122", Decimal("0"), total),
                ], label=f"receipt for sale#{sale_ids[idx - 1]}")
            finally:
                db.close()

        db = _db()
        try:
            assert _ledger_balance(db, "1122") == Decimal("0"), "销售收款后应收账款应为0"
        finally:
            db.close()

        print("✅ 第五幕完成：3次销售收款")

        # ═══════════════════════════════════════════
        # 第六幕：费用报销
        # ═══════════════════════════════════════════

        r = c.post("/api/expenses", json={
            "category": "房租",
            "functional_category": "管理费用",
            "amount": 2000,
            "expense_date": "2026-01-25T00:00:00",
            "payment_method": "company",
            "description": "办公室房租",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        expense_id = r.json().get("data", r.json())["id"]

        db = _db()
        try:
            # 费用创建凭证：借 6601 管理费用，贷 2202 其他应付款
            _assert_move_lines(db, "expense", expense_id, [
                ("6601", Decimal("2000"), Decimal("0")),
                ("2202", Decimal("0"), Decimal("2000")),
            ])
        finally:
            db.close()

        r = c.post("/api/payments", json={
            "payment_type": "expense",
            "related_entity_type": "expense",
            "related_entity_id": expense_id,
            "amount": 2000,
            "payment_date": "2026-01-25T00:00:00",
            "bank_account_id": s["bank_id"],
            "description": "支付房租",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            # 费用付款凭证：借 2202 其他应付款，贷 1002 银行存款
            move = _assert_bank_move(db, "payment", Decimal("2000"))
            _verify_move_lines(db, move, [
                ("2202", Decimal("2000"), Decimal("0")),
                ("1002", Decimal("0"), Decimal("2000")),
            ], label=f"payment for expense#{expense_id}")
            assert _ledger_balance(db, "6601") == Decimal("2000.00"), "管理费用应为2,000"
            assert _credit_balance(db, "2202") == Decimal("0"), "费用付款后 2202 应为0"
        finally:
            db.close()

        print("✅ 第六幕完成：费用报销")

        # ═══════════════════════════════════════════
        # 第七幕：增值税验证
        # ═══════════════════════════════════════════

        for idx, (day, qty, price, amount, tax, total) in enumerate(purchases, 1):
            r = c.post("/api/invoices", json={
                "invoice_no": f"INV-IN-{UNIQUE}-{idx}",
                "direction": "in",
                "invoice_type": "special",
                "amount_without_tax": float(amount),
                "tax_rate": 0.13,
                "tax_amount": float(tax),
                "amount_with_tax": float(total),
                "counterparty_name": f"供应商A-{UNIQUE}",
                "issue_date": f"2026-01-{day:02d}",
                "related_order_id": purchase_ids[idx - 1],
                "related_order_type": "purchase_order",
                "certification_status": "certified",
            }, headers=HEADERS)
            assert r.status_code in (200, 201), r.text

        for idx, (day, qty, price, revenue, tax, total) in enumerate(sales, 1):
            r = c.post("/api/invoices", json={
                "invoice_no": f"INV-OUT-{UNIQUE}-{idx}",
                "direction": "out",
                "invoice_type": "ordinary",
                "amount_without_tax": float(revenue),
                "tax_rate": 0.13,
                "tax_amount": float(tax),
                "amount_with_tax": float(total),
                "counterparty_name": f"客户B-{UNIQUE}",
                "issue_date": f"2026-01-{day:02d}",
                "related_order_id": sale_ids[idx - 1],
                "related_order_type": "sale_order",
                "certification_status": "n_a",
            }, headers=HEADERS)
            assert r.status_code in (200, 201), r.text

        r = c.get("/api/tax-report/monthly?year=2026&month=1", headers=HEADERS)
        assert r.status_code == 200, r.text
        tax = r.json()
        assert Decimal(str(tax["output_tax"])) == total_output_tax, f"销项税={tax['output_tax']}"
        assert Decimal(str(tax["input_tax"])) == total_input_tax, f"进项税={tax['input_tax']}"
        expected_tax_payable = total_output_tax - total_input_tax
        assert Decimal(str(tax["tax_payable"])) == expected_tax_payable, f"应纳增值税={tax['tax_payable']}"

        print(f"✅ 第七幕完成：销项税 {total_output_tax}，进项税 {total_input_tax}，应纳 {expected_tax_payable}")

        # ═══════════════════════════════════════════
        # 第八幕：财务报表验证
        # ═══════════════════════════════════════════

        r = c.get("/api/financial-reports/income-statement?start_date=2026-01-01&end_date=2026-01-31",
                  headers=HEADERS)
        assert r.status_code == 200, r.text
        pl = r.json()

        expected_net_profit = total_revenue - total_cogs - Decimal("2000")
        assert Decimal(str(pl["revenue"])) == total_revenue
        assert Decimal(str(pl["cost_of_goods_sold"])) == total_cogs
        assert Decimal(str(pl["administrative_expenses"])) == Decimal("2000.00")
        assert Decimal(str(pl["net_profit"])) == expected_net_profit

        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        bs = r.json()

        expected_cash = (Decimal("100000") - total_payable + total_ar - Decimal("2000")).quantize(Decimal("0.01"))
        assert Decimal(str(bs["monetary_funds"])) == expected_cash, f"货币资金应为{expected_cash}"
        assert Decimal(str(bs["inventory"])) == ending_inventory_value
        assert Decimal(str(bs["accounts_receivable"])) == Decimal("0")
        assert Decimal(str(bs["accounts_payable"])) == Decimal("0")
        # 应交税费在月结前为 0（销项/进项分别在 222101/222102），月结后才转入 222107
        # 此处不直接断言 tax_payable，避免与 tax-report 口径混淆

        # 净利润 = 未分配利润变动
        db = _db()
        try:
            opening_re = Decimal("0")
            ob = db.query(OpeningBalance).filter(OpeningBalance.account_id == ACCT_ID).first()
            if ob:
                opening_re = Decimal(str(ob.retained_earnings_l1 or 0))
            ending_re = Decimal(str(bs["retained_earnings"]))
            delta_re = ending_re - opening_re
            assert abs(Decimal(str(pl["net_profit"])) - delta_re) <= Decimal("0.01"), \
                f"净利润({pl['net_profit']}) ≠ 未分配利润变动({delta_re})"

            # AS-01：全月凭证借贷平衡
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        finally:
            db.close()

        # 资产负债表恒等式
        # BS 已正确处理应交增值税净额（销项-进项=1,612）及留抵资产，diff 必须为 0。
        diff = (Decimal(str(bs["total_assets"]))
                - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff == Decimal("0"), \
            f"资产负债表不平衡，实际缺口={diff}"

        print("✅ 第八幕：财务报表验证完成")
        print(f"\n{'='*60}")
        print(f"🏁 全场景测试完成")
        print(f"期末现金：{expected_cash} | 库存：{ending_inventory_qty}件 | 存货价值：{ending_inventory_value}")
        print(f"营业收入：{total_revenue} | 营业成本：{total_cogs} | 管理费用：2000")
        print(f"净利润：{expected_net_profit}")
        print(f"销项税：{total_output_tax} | 进项税：{total_input_tax} | 应纳增值税：{expected_tax_payable}")
        print(f"{'='*60}")
