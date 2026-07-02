"""E 工资个税偏差修复测试

验证业务因果链 E:发放工资时借2211(应发)、贷1002(实发)、贷222108(代扣个税)

测试覆盖:
1. 科目 222108 已注册到 CHART_OF_ACCOUNTS
2. Payment 模型有 withholding_tax_amount_l1 字段
3. PaymentCreate schema 有 withholding_tax_amount 字段
4. _build_payment 凭证生成:
   - withholding_tax=0 → 2 行(向后兼容)
   - withholding_tax>0 → 3 行(借2211总额/贷1002实发/贷222108代扣)
5. API 集成:计提工资 + 发放工资(带代扣) → 凭证正确
6. 校验:非工资场景传 withholding_tax_amount → VALIDATION_ERROR
7. 冲红:反向凭证正确冲回 222108
8. 资产负债表:222108 纳入 tax_payable

运行:python -m pytest tests/transaction/test_salary_iit_withholding.py -v
"""
import sys
import pytest
from decimal import Decimal
from pathlib import Path
from datetime import datetime

# 把 backend 加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}


# ═══════════════════════════════════════════════════════════════
# 一、基础结构验证(不需 db)
# ═══════════════════════════════════════════════════════════════

class TestIITAccountStructure:
    """验证 222108 科目和 Payment 字段结构"""

    def test_222108科目已注册(self):
        from finance_integration import CHART_OF_ACCOUNTS
        codes = [c[0] for c in CHART_OF_ACCOUNTS]
        assert "222108" in codes, "CHART_OF_ACCOUNTS 缺少 222108 应交个人所得税"

    def test_222108科目名称正确(self):
        from finance_integration import CHART_OF_ACCOUNTS
        for code, name, atype in CHART_OF_ACCOUNTS:
            if code == "222108":
                assert "个人所得税" in name, f"222108 名称应为应交个人所得税,实际 {name}"
                assert atype == "liability"
                return
        pytest.fail("222108 未找到")

    def test_Payment模型有withholding字段(self):
        from models import Payment
        col = Payment.__table__.columns.get("withholding_tax_amount_l1")
        assert col is not None, "Payment 模型缺少 withholding_tax_amount_l1 字段"
        assert col.info.get("tier") == "L1"
        assert col.info.get("source") == "external"

    def test_PaymentCreate有withholding字段(self):
        from schemas.payment import PaymentCreate
        schema = PaymentCreate.model_json_schema()
        assert "withholding_tax_amount" in schema["properties"], \
            "PaymentCreate schema 缺少 withholding_tax_amount 字段"

    def test_PaymentOut有withholding字段(self):
        from schemas.payment import PaymentOut
        # PaymentOut 用 validation_alias="withholding_tax_amount_l1",
        # JSON schema 会用 alias 名,直接检查模型字段
        assert "withholding_tax_amount" in PaymentOut.model_fields, \
            "PaymentOut 缺少 withholding_tax_amount 字段"


# ═══════════════════════════════════════════════════════════════
# 二、_build_payment 凭证生成单元测试
# ═══════════════════════════════════════════════════════════════

class TestBuildPaymentIIT:
    """_build_payment 函数凭证生成测试"""

    def test_无代扣个税生成2行凭证(self):
        """withholding_tax=0 → 2 行(借应付/贷银行),向后兼容"""
        from engine_journal import JournalEngine
        engine = JournalEngine.__new__(JournalEngine)

        source = {
            "amount": Decimal("10000"),
            "debit_account_code": "2211",
            "bank_account_id": 1,
        }
        lines, move_type, opts = engine._build_payment(source)

        assert len(lines) == 2
        assert lines[0]["account_code"] == "2211"
        assert lines[0]["debit"] == Decimal("10000")
        assert lines[1]["account_code"] == "1002"
        assert lines[1]["credit"] == Decimal("10000")

    def test_有代扣个税生成3行凭证(self):
        """withholding_tax>0 → 3 行(借2211应发/贷1002实发/贷222108代扣)"""
        from engine_journal import JournalEngine
        engine = JournalEngine.__new__(JournalEngine)

        source = {
            "amount": Decimal("25000"),          # 实发
            "withholding_tax_amount": Decimal("5000"),  # 代扣
            "debit_account_code": "2211",
            "bank_account_id": 1,
        }
        lines, move_type, opts = engine._build_payment(source)

        assert len(lines) == 3, f"应有 3 行凭证,实际 {len(lines)} 行"

        # 借方:2211 应付职工薪酬(应发 = 实发 + 代扣 = 30000)
        assert lines[0]["account_code"] == "2211"
        assert lines[0]["debit"] == Decimal("30000"), \
            f"借2211应为应发 30000,实际 {lines[0]['debit']}"

        # 贷方1:1002 银行存款(实发 = 25000)
        assert lines[1]["account_code"] == "1002"
        assert lines[1]["credit"] == Decimal("25000"), \
            f"贷1002应为实发 25000,实际 {lines[1]['credit']}"

        # 贷方2:222108 应交个人所得税(代扣 = 5000)
        assert lines[2]["account_code"] == "222108"
        assert lines[2]["credit"] == Decimal("5000"), \
            f"贷222108应为代扣 5000,实际 {lines[2]['credit']}"

    def test_三行凭证借贷平衡(self):
        """3 行凭证:借方总额 == 贷方总额"""
        from engine_journal import JournalEngine
        engine = JournalEngine.__new__(JournalEngine)

        source = {
            "amount": Decimal("25000"),
            "withholding_tax_amount": Decimal("5000"),
            "debit_account_code": "2211",
            "bank_account_id": 1,
        }
        lines, _, _ = engine._build_payment(source)

        total_debit = sum(l["debit"] for l in lines)
        total_credit = sum(l["credit"] for l in lines)
        assert total_debit == total_credit, \
            f"借贷不平:借方 {total_debit} ≠ 贷方 {total_credit}"

    def test_无银行账户用1001现金科目(self):
        """bank_account_id=None → 贷方用 1001 库存现金"""
        from engine_journal import JournalEngine
        engine = JournalEngine.__new__(JournalEngine)

        source = {
            "amount": Decimal("25000"),
            "withholding_tax_amount": Decimal("5000"),
            "debit_account_code": "2211",
            "bank_account_id": None,
        }
        lines, _, _ = engine._build_payment(source)

        assert lines[1]["account_code"] == "1001", \
            f"无银行账户时应贷 1001,实际 {lines[1]['account_code']}"

    def test_自定义withholding科目代码(self):
        """可自定义 withholding_tax_account_code(默认 222108)"""
        from engine_journal import JournalEngine
        engine = JournalEngine.__new__(JournalEngine)

        source = {
            "amount": Decimal("25000"),
            "withholding_tax_amount": Decimal("5000"),
            "debit_account_code": "2211",
            "bank_account_id": 1,
            "withholding_tax_account_code": "2241",  # 自定义
        }
        lines, _, _ = engine._build_payment(source)

        assert lines[2]["account_code"] == "2241", \
            f"自定义代扣科目应为 2241,实际 {lines[2]['account_code']}"


# ═══════════════════════════════════════════════════════════════
# 三、API 集成测试(需 db + client)
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def db():
    import os
    import uuid
    import tempfile
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base
    import models  # noqa: F401
    import models_finance  # noqa: F401

    db_path = os.path.join(tempfile.gettempdir(), f"iit_{uuid.uuid4().hex[:12]}.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="module")
def bootstrap_db(db):
    from models import Account, BankAccount
    if db.query(Account).filter(Account.id == 1).first():
        return
    account = Account(name="测试账本", type="company", code="company", taxpayer_type_l3="small_scale")
    db.add(account)
    db.flush()
    from finance_integration import get_or_create_ledger_id
    get_or_create_ledger_id(db, account.id)
    # 创建银行账户(余额充足)
    bank = BankAccount(account_id=1, bank_name="测试银行", account_number="6228", balance_l4=Decimal("1000000"))
    db.add(bank)
    db.commit()


@pytest.fixture(scope="module")
def client(db):
    from fastapi.testclient import TestClient
    from main import app
    from database import get_db
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        c.headers.update(HEADERS)
        yield c
    app.dependency_overrides.clear()


class TestSalaryIITAPI:
    """工资个税 API 集成测试"""

    def test_计提工资_发放工资带代扣_凭证正确(self, client, bootstrap_db):
        """完整流程:计提工资(费用) → 发放工资(付款,带代扣个税) → 验证返回"""
        # 1. 计提工资(应发 30000)
        resp = client.post("/api/expenses", json={
            "category": "工资",
            "amount": 30000,
            "expense_date": "2026-06-30",
            "functional_category": "管理费用",
            "description": "6月工资",
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"计提工资失败: {resp.text}"
        expense_id = resp.json()["data"]["id"]

        # 2. 发放工资(实发 25000,代扣 5000)
        resp = client.post("/api/payments", json={
            "payment_type": "salary",
            "related_entity_type": "expense",
            "related_entity_id": expense_id,
            "amount": 25000,
            "withholding_tax_amount": 5000,
            "payment_date": "2026-06-30T10:00:00",
            "bank_account_id": 1,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"发放工资失败: {resp.text}"
        payment_data = resp.json()["data"]
        # PaymentOut 用 validation_alias,序列化时字段名是 withholding_tax_amount
        # 但因为 populate_by_name=True + validation_alias,输出键可能是 alias 名
        wht = payment_data.get("withholding_tax_amount") or payment_data.get("withholding_tax_amount_l1", 0)
        assert float(wht) == 5000.0, f"代扣个税应为 5000,实际 {wht}"

    def test_非工资场景传代扣个税报错(self, client, bootstrap_db):
        """payment_type=expense + withholding_tax_amount>0 → 422 VALIDATION_ERROR"""
        # 先建一个非工资费用
        resp = client.post("/api/expenses", json={
            "category": "房租",
            "amount": 5000,
            "expense_date": "2026-06-15",
            "functional_category": "管理费用",
        }, headers=HEADERS)
        expense_id = resp.json()["data"]["id"]

        # 付款时传 withholding_tax_amount 但 payment_type=expense
        resp = client.post("/api/payments", json={
            "payment_type": "expense",
            "related_entity_type": "expense",
            "related_entity_id": expense_id,
            "amount": 5000,
            "withholding_tax_amount": 500,  # 非工资场景不应传
            "payment_date": "2026-06-15T10:00:00",
            "bank_account_id": 1,
        }, headers=HEADERS)
        # VALIDATION_ERROR HTTP 状态码 = 422
        assert resp.status_code == 422, f"应拒绝非工资场景的代扣,实际 {resp.status_code}: {resp.text}"
        assert "withholding_tax_amount" in resp.text or "salary" in resp.text

    def test_工资无代扣向后兼容(self, client, bootstrap_db):
        """payment_type=salary + withholding_tax_amount=0(默认) → 2 行凭证,向后兼容"""
        # 计提工资
        resp = client.post("/api/expenses", json={
            "category": "工资",
            "amount": 10000,
            "expense_date": "2026-07-15",
            "functional_category": "管理费用",
        }, headers=HEADERS)
        expense_id = resp.json()["data"]["id"]

        # 发放工资(无代扣)
        resp = client.post("/api/payments", json={
            "payment_type": "salary",
            "related_entity_type": "expense",
            "related_entity_id": expense_id,
            "amount": 10000,
            "payment_date": "2026-07-15T10:00:00",
            "bank_account_id": 1,
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"无代扣发放工资失败: {resp.text}"
        assert float(resp.json()["data"]["withholding_tax_amount"]) == 0.0


# ═══════════════════════════════════════════════════════════════
# 四、凭证验证(直接查 db)
# ═══════════════════════════════════════════════════════════════

class TestSalaryIITJournalEntries:
    """直接查 db 验证凭证行"""

    def test_发放工资带代扣_凭证三行正确(self, db, bootstrap_db):
        """验证:计提+发放后,2211 余额=0,222108 余额=5000,1002 减少 25000"""
        from models import Expense, Payment, BankAccount
        from models_finance import AccountMove, AccountMoveLine, LedgerAccount
        from finance_integration import post_journal, get_or_create_ledger_id
        from uow import unit_of_work

        ledger_id = get_or_create_ledger_id(db, 1)

        # 记录银行初始余额
        bank = db.query(BankAccount).filter(BankAccount.id == 1).first()
        bank_before = bank.balance_l4

        # 1. 计提工资 30000
        with unit_of_work(db):
            expense = Expense(
                account_id=1, category="工资", functional_category="管理费用",
                amount_l1=Decimal("30000"), expense_date_l1=datetime(2026, 7, 1),
                payment_method="company", payment_status="unpaid",
                description="IIT测试工资",
            )
            db.add(expense)
            db.flush()
            post_journal(db, 1, "expense", {
                "amount": Decimal("30000"),
                "date": "2026-07-01",
                "expense_account_code": "6601",
                "credit_account_code": "2211",
                "bank_account_id": None,
                "partner_id": None,
                "partner_type": None,
                "source_model": "expense",
                "source_id": expense.id,
            })
        db.commit()

        # 2. 发放工资(实发 25000,代扣 5000)
        with unit_of_work(db):
            payment = Payment(
                account_id=1, payment_type="salary",
                related_entity_type="expense", related_entity_id=expense.id,
                amount_l1=Decimal("25000"),
                withholding_tax_amount_l1=Decimal("5000"),
                payment_method="company",
                payment_date_l1=datetime(2026, 7, 2),
                bank_account_id=1, description="IIT测试发放",
            )
            db.add(payment)
            db.flush()

            # 银行余额更新
            bank = db.query(BankAccount).filter(BankAccount.id == 1).with_for_update().first()
            new_balance = bank.balance_l4 - Decimal("25000")
            bank.balance_l4 = new_balance

            # 过账
            post_journal(db, 1, "payment", {
                "amount": Decimal("25000"),
                "withholding_tax_amount": Decimal("5000"),
                "date": "2026-07-02",
                "debit_account_code": "2211",
                "partner_id": expense.id,
                "partner_type": "supplier",
                "bank_account_id": 1,
                "source_model": "payment",
                "source_id": payment.id,
            })
        db.commit()

        # 3. 验证凭证行
        # 查付款凭证的行
        move = db.query(AccountMove).filter(
            AccountMove.source_model == "payment",
            AccountMove.source_id == payment.id,
            AccountMove.is_reversal == False,
        ).first()
        assert move is not None, "付款凭证未生成"

        lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == move.id).all()
        assert len(lines) == 3, f"付款凭证应有 3 行,实际 {len(lines)} 行"

        # 按科目分组验证
        line_map = {}
        for l in lines:
            la = db.query(LedgerAccount).filter(LedgerAccount.id == l.ledger_account_id).first()
            line_map[la.code] = (l.debit_l2 or Decimal("0"), l.credit_l2 or Decimal("0"))

        # 2211 借方 30000(应发)
        assert "2211" in line_map, f"凭证缺少 2211 行,已有: {list(line_map.keys())}"
        assert line_map["2211"][0] == Decimal("30000"), \
            f"2211 借方应为 30000,实际 {line_map['2211'][0]}"

        # 1002 贷方 25000(实发)
        assert "1002" in line_map, f"凭证缺少 1002 行,已有: {list(line_map.keys())}"
        assert line_map["1002"][1] == Decimal("25000"), \
            f"1002 贷方应为 25000,实际 {line_map['1002'][1]}"

        # 222108 贷方 5000(代扣)
        assert "222108" in line_map, f"凭证缺少 222108 行,已有: {list(line_map.keys())}"
        assert line_map["222108"][1] == Decimal("5000"), \
            f"222108 贷方应为 5000,实际 {line_map['222108'][1]}"

        # 4. 验证 222108 有贷方余额(代扣负债),且被纳入 tax_payable
        # 注意:API 测试可能也在同一 db 创建了 IIT,所以用 >= 而非 ==
        from crud.finance.balance_sheet import generate_balance_sheet
        bs = generate_balance_sheet(db, account_id=1, date="2026-07-02")
        assert float(bs["personal_income_tax_liability"]) >= 5000.0, \
            f"BS 222108 余额应 >= 5000(本次代扣),实际 {bs['personal_income_tax_liability']}"
        # tax_payable 应包含 222108
        assert float(bs["tax_payable"]) >= 5000.0, \
            f"tax_payable 应包含 222108 的 5000,实际 {bs['tax_payable']}"


# ═══════════════════════════════════════════════════════════════
# 五、冲红测试
# ═══════════════════════════════════════════════════════════════

class TestSalaryIITReversal:
    """冲红工资付款应正确冲回 222108"""

    def test_冲红工资付款_222108被冲回(self, db, bootstrap_db):
        from models import Expense, Payment, BankAccount
        from models_finance import AccountMove, AccountMoveLine, LedgerAccount
        from finance_integration import post_journal, reverse_journal, get_or_create_ledger_id
        from uow import unit_of_work

        # 1. 计提+发放(同上)
        with unit_of_work(db):
            expense = Expense(
                account_id=1, category="工资", functional_category="管理费用",
                amount_l1=Decimal("20000"), expense_date_l1=datetime(2026, 8, 1),
                payment_method="company", payment_status="unpaid",
                description="冲红测试工资",
            )
            db.add(expense)
            db.flush()
            post_journal(db, 1, "expense", {
                "amount": Decimal("20000"), "date": "2026-08-01",
                "expense_account_code": "6601", "credit_account_code": "2211",
                "bank_account_id": None, "partner_id": None, "partner_type": None,
                "source_model": "expense", "source_id": expense.id,
            })
        db.commit()

        with unit_of_work(db):
            payment = Payment(
                account_id=1, payment_type="salary",
                related_entity_type="expense", related_entity_id=expense.id,
                amount_l1=Decimal("16000"),
                withholding_tax_amount_l1=Decimal("4000"),
                payment_method="company",
                payment_date_l1=datetime(2026, 8, 2),
                bank_account_id=1, description="冲红测试发放",
            )
            db.add(payment)
            db.flush()
            bank = db.query(BankAccount).filter(BankAccount.id == 1).with_for_update().first()
            bank.balance_l4 = bank.balance_l4 - Decimal("16000")
            post_journal(db, 1, "payment", {
                "amount": Decimal("16000"), "withholding_tax_amount": Decimal("4000"),
                "date": "2026-08-02", "debit_account_code": "2211",
                "partner_id": expense.id, "partner_type": "supplier",
                "bank_account_id": 1, "source_model": "payment", "source_id": payment.id,
            })
        db.commit()

        # 2. 冲红付款凭证
        with unit_of_work(db):
            reversal = reverse_journal(db, 1, "payment", payment.id)
            assert reversal is not None, "冲红失败"
        db.commit()

        # 3. 验证冲红凭证有 222108 借方 4000
        rev_move = db.query(AccountMove).filter(
            AccountMove.source_model == "payment",
            AccountMove.source_id == payment.id,
            AccountMove.is_reversal == True,
        ).first()
        assert rev_move is not None, "冲红凭证未生成"

        rev_lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == rev_move.id).all()
        assert len(rev_lines) == 3, f"冲红凭证应有 3 行,实际 {len(rev_lines)} 行"

        # 验证 222108 有借方 4000(冲回代扣负债)
        for rl in rev_lines:
            la = db.query(LedgerAccount).filter(LedgerAccount.id == rl.ledger_account_id).first()
            if la.code == "222108":
                assert rl.debit_l2 == Decimal("4000"), \
                    f"冲红 222108 借方应为 4000,实际 {rl.debit_l2}"
                return
        pytest.fail("冲红凭证缺少 222108 行")
