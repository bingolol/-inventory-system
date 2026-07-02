"""所得税报表测试 — 会计准则口径（利润表说话）

测试 routers/income_tax.py 和 crud/finance/tax_declarations.py 的所得税计算：
- 收入/成本/费用/利润全部取自《小企业会计准则》利润表（总账科目）。
- 确保企业所得税申报数据与财务报表一致。
"""
import pytest
from decimal import Decimal
from datetime import datetime, date

import models
import models_finance
from finance_integration import get_or_create_ledger_id
from crud.finance import generate_income_tax_prepayment


@pytest.fixture
def seed_data(db):
    """创建测试基础数据：账本、标准科目、一期凭证。"""
    account = models.Account(
        id=1, name="测试账本", type="company", code="test",
        taxpayer_type_l3="small_scale"
    )
    db.add(account)
    db.flush()

    ledger_id = get_or_create_ledger_id(db, account.id)

    # 获取需要使用的科目 ID
    def _la(code):
        return db.query(models_finance.LedgerAccount).filter(
            models_finance.LedgerAccount.ledger_id == ledger_id,
            models_finance.LedgerAccount.code == code
        ).first().id

    # 模拟一期业务凭证：
    # 1) 确认收入 10000（借：应收账款 10000 / 贷：主营业务收入 10000）
    move1 = models_finance.AccountMove(
        ledger_id=ledger_id, name="确认收入", move_type="manual",
        date_l1=date(2026, 1, 15), state="posted"
    )
    db.add(move1)
    db.flush()
    db.add_all([
        models_finance.AccountMoveLine(move_id=move1.id, ledger_account_id=_la("1122"), debit_l2=Decimal("10000"), credit_l2=Decimal("0")),
        models_finance.AccountMoveLine(move_id=move1.id, ledger_account_id=_la("6001"), debit_l2=Decimal("0"), credit_l2=Decimal("10000")),
    ])

    # 2) 结转销售成本 5000（借：主营业务成本 5000 / 贷：库存商品 5000）
    move2 = models_finance.AccountMove(
        ledger_id=ledger_id, name="结转成本", move_type="manual",
        date_l1=date(2026, 1, 15), state="posted"
    )
    db.add(move2)
    db.flush()
    db.add_all([
        models_finance.AccountMoveLine(move_id=move2.id, ledger_account_id=_la("6401"), debit_l2=Decimal("5000"), credit_l2=Decimal("0")),
        models_finance.AccountMoveLine(move_id=move2.id, ledger_account_id=_la("1405"), debit_l2=Decimal("0"), credit_l2=Decimal("5000")),
    ])

    # 3) 计提附加税 300（借：税金及附加 300 / 贷：应交税费-附加税 300）
    move3 = models_finance.AccountMove(
        ledger_id=ledger_id, name="计提附加税", move_type="manual",
        date_l1=date(2026, 1, 31), state="posted"
    )
    db.add(move3)
    db.flush()
    db.add_all([
        models_finance.AccountMoveLine(move_id=move3.id, ledger_account_id=_la("6403"), debit_l2=Decimal("300"), credit_l2=Decimal("0")),
        models_finance.AccountMoveLine(move_id=move3.id, ledger_account_id=_la("222104"), debit_l2=Decimal("0"), credit_l2=Decimal("300")),
    ])

    # 4) 发生管理费用 2000（借：管理费用 2000 / 贷：银行存款 2000）
    move4 = models_finance.AccountMove(
        ledger_id=ledger_id, name="支付费用", move_type="manual",
        date_l1=date(2026, 2, 1), state="posted"
    )
    db.add(move4)
    db.flush()
    db.add_all([
        models_finance.AccountMoveLine(move_id=move4.id, ledger_account_id=_la("6601"), debit_l2=Decimal("2000"), credit_l2=Decimal("0")),
        models_finance.AccountMoveLine(move_id=move4.id, ledger_account_id=_la("1002"), debit_l2=Decimal("0"), credit_l2=Decimal("2000")),
    ])

    db.commit()
    return {"account_id": account.id, "ledger_id": ledger_id}


class TestIncomeTaxCaliber:
    def test_tax_caliber_uses_income_statement(self, db, seed_data):
        """会计准则口径：收入/成本取自利润表"""
        from routers.income_tax import get_income_tax_report
        import asyncio

        report = asyncio.run(get_income_tax_report(
            year=2026, quarter=None, db=db, account_id=1
        ))
        # 营业收入 = 总账 6001 贷方 = 10000
        assert report.total_revenue == Decimal("10000.00")
        # 营业成本 = 总账 6401 借方 = 5000
        assert report.total_cost == Decimal("5000.00")
        # 毛利 = 10000 - 5000 = 5000
        assert report.gross_profit == Decimal("5000.00")
        # 期间费用 = 6601 = 2000（不含税金及附加 300）
        assert report.operating_expenses == Decimal("2000.00")
        # 应纳税所得额 = 利润总额 = 10000 - 5000 - 300 - 2000 = 2700
        assert report.taxable_income == Decimal("2700.00")

    def test_prepayment_uses_income_statement(self, db, seed_data):
        """预缴表：会计准则口径取数"""
        result = generate_income_tax_prepayment(db, 1, 2026, 1)
        # 营业收入 = 10000
        assert result["operating_revenue"] == Decimal("10000.00")
        # 营业成本 = 5000
        assert result["operating_cost"] == Decimal("5000.00")
        # 利润总额 = 2700
        assert result["gross_profit"] == Decimal("2700.00")
        # 期间费用 = 2000
        assert result["operating_expenses"] == Decimal("2000.00")
        # 税金及附加 = 300
        assert result["tax_and_surcharge"] == Decimal("300.00")
