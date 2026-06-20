"""期初余额校验回归测试

验证：资产 = 负债 + 权益 的校验包含非流动资产和非流动负债
"""
import pytest
from decimal import Decimal
from commands.base import dispatch
from commands.finance_commands import CreateOpeningBalance, UpdateOpeningBalance
from errors import BusinessError
from models import Account


@pytest.fixture
def account(db):
    return db.query(Account).first()


class TestCreateOpeningBalanceValidation:
    """创建期初余额校验"""

    def test_basic_balance_passes(self, db, account):
        """流动资产(100) = 流动负债(60) + 权益(40) → 通过"""
        cmd = CreateOpeningBalance(
            account_id=account.id,
            operator="test",
            date="2026-11-01",
            cash_balance=Decimal("100"),
            bank_balance=Decimal("0"),
            accounts_receivable=Decimal("0"),
            inventory_value=Decimal("0"),
            accounts_payable=Decimal("60"),
            tax_payable=Decimal("0"),
            paid_in_capital=Decimal("40"),
            retained_earnings=Decimal("0"),
        )
        result = dispatch(cmd, db)
        assert result is not None

    def test_with_fixed_assets_validates_total(self, db, account):
        """总资产(100+50-10=140) = 负债(60) + 权益(80) → 通过"""
        cmd = CreateOpeningBalance(
            account_id=account.id,
            operator="test",
            date="2026-11-02",
            cash_balance=Decimal("100"),
            bank_balance=Decimal("0"),
            accounts_receivable=Decimal("0"),
            inventory_value=Decimal("0"),
            fixed_assets_original=Decimal("50"),
            accumulated_depreciation=Decimal("10"),
            intangible_assets_original=Decimal("0"),
            accumulated_amortization=Decimal("0"),
            accounts_payable=Decimal("60"),
            tax_payable=Decimal("0"),
            long_term_borrowings=Decimal("0"),
            paid_in_capital=Decimal("80"),
            retained_earnings=Decimal("0"),
        )
        result = dispatch(cmd, db)
        assert result is not None

    def test_with_intangible_assets_validates_total(self, db, account):
        """总资产(100+30-5=125) = 负债(50+20=70) + 权益(55) → 通过"""
        cmd = CreateOpeningBalance(
            account_id=account.id,
            operator="test",
            date="2026-11-03",
            cash_balance=Decimal("100"),
            bank_balance=Decimal("0"),
            accounts_receivable=Decimal("0"),
            inventory_value=Decimal("0"),
            fixed_assets_original=Decimal("0"),
            accumulated_depreciation=Decimal("0"),
            intangible_assets_original=Decimal("30"),
            accumulated_amortization=Decimal("5"),
            accounts_payable=Decimal("50"),
            tax_payable=Decimal("0"),
            long_term_borrowings=Decimal("20"),
            paid_in_capital=Decimal("55"),
            retained_earnings=Decimal("0"),
        )
        result = dispatch(cmd, db)
        assert result is not None

    def test_unbalanced_raises_error(self, db, account):
        """总资产(100) ≠ 负债(60) + 权益(30) → 报错"""
        cmd = CreateOpeningBalance(
            account_id=account.id,
            operator="test",
            date="2026-11-04",
            cash_balance=Decimal("100"),
            bank_balance=Decimal("0"),
            accounts_receivable=Decimal("0"),
            inventory_value=Decimal("0"),
            accounts_payable=Decimal("60"),
            tax_payable=Decimal("0"),
            paid_in_capital=Decimal("30"),
            retained_earnings=Decimal("0"),
        )
        with pytest.raises(BusinessError) as exc_info:
            dispatch(cmd, db)
        assert exc_info.value.code == "BALANCE_SHEET_UNBALANCED"

    def test_non_current_assets_must_be_counted(self, db, account):
        """总资产(100+50-10=140) ≠ 负债(60) + 权益(40) → 报错（非流动资产必须计入校验）"""
        cmd = CreateOpeningBalance(
            account_id=account.id,
            operator="test",
            date="2026-11-05",
            cash_balance=Decimal("100"),
            bank_balance=Decimal("0"),
            accounts_receivable=Decimal("0"),
            inventory_value=Decimal("0"),
            fixed_assets_original=Decimal("50"),
            accumulated_depreciation=Decimal("10"),
            intangible_assets_original=Decimal("0"),
            accumulated_amortization=Decimal("0"),
            accounts_payable=Decimal("60"),
            tax_payable=Decimal("0"),
            long_term_borrowings=Decimal("0"),
            paid_in_capital=Decimal("40"),
            retained_earnings=Decimal("0"),
        )
        with pytest.raises(BusinessError) as exc_info:
            dispatch(cmd, db)
        assert exc_info.value.code == "BALANCE_SHEET_UNBALANCED"


class TestUpdateOpeningBalanceValidation:
    """更新期初余额校验"""

    def test_update_to_unbalanced_raises_error(self, db, account):
        """更新后总资产(100) ≠ 负债(60) + 权益(30) → 报错"""
        # 先创建一个平衡的期初余额
        create_cmd = CreateOpeningBalance(
            account_id=account.id,
            operator="test",
            date="2026-11-06",
            cash_balance=Decimal("100"),
            bank_balance=Decimal("0"),
            accounts_receivable=Decimal("0"),
            inventory_value=Decimal("0"),
            accounts_payable=Decimal("60"),
            tax_payable=Decimal("0"),
            paid_in_capital=Decimal("40"),
            retained_earnings=Decimal("0"),
        )
        ob = dispatch(create_cmd, db)

        # 更新权益使其不平衡
        update_cmd = UpdateOpeningBalance(
            account_id=account.id,
            operator="test",
            opening_balance_id=ob.id,
            paid_in_capital=Decimal("30"),
        )
        with pytest.raises(BusinessError) as exc_info:
            dispatch(update_cmd, db)
        assert exc_info.value.code == "BALANCE_SHEET_UNBALANCED"
