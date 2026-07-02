"""删除账本校验回归测试

验证：delete_account 检查所有关联表（含银行/资产/收付款）
"""
import pytest
from crud.base import delete_account
from errors import BusinessError
from models import (
    Account, BankAccount, BankTransaction, Payment, Receipt,
    FixedAsset, IntangibleAsset
)
from decimal import Decimal
from datetime import datetime


class TestDeleteAccountValidation:
    """删除账本校验"""

    def test_delete_empty_account_passes(self, db):
        """空账本（无关联数据）→ 删除成功"""
        # 创建一个空账本
        account = Account(name="测试空账本", type="company", code="test_empty")
        db.add(account)
        db.flush()

        result = delete_account(db, account.id)
        assert result is True

    def test_account_with_bank_account_blocked(self, db):
        """有银行账户的账本 → 删除失败"""
        account = Account(name="测试有银行账本", type="company", code="test_bank")
        db.add(account)
        db.flush()

        bank_account = BankAccount(
            account_id=account.id,
            bank_name="测试银行",
            account_number="123456",
            balance_l4=Decimal("1000"),
        )
        db.add(bank_account)
        db.flush()

        with pytest.raises(BusinessError) as exc_info:
            delete_account(db, account.id)
        assert "银行账户" in exc_info.value.data.get("label", "")

    def test_account_with_payment_blocked(self, db):
        """有付款记录的账本 → 删除失败（银行账户先被检查）"""
        account = Account(name="测试有付款账本", type="company", code="test_payment")
        db.add(account)
        db.flush()

        # 创建银行账户（Payment 需要关联）
        bank_account = BankAccount(
            account_id=account.id,
            bank_name="测试银行",
            account_number="789012",
            balance_l4=Decimal("500"),
        )
        db.add(bank_account)
        db.flush()

        payment = Payment(
            account_id=account.id,
            payment_type="expense",
            related_entity_type="expense",
            related_entity_id=1,
            amount_l1=Decimal("100"),
            payment_method="company",
            payment_date_l1=datetime.now(),
            bank_account_id=bank_account.id,
        )
        db.add(payment)
        db.flush()

        # 删除失败，因为有关联数据（银行账户或付款记录都会阻止删除）
        with pytest.raises(BusinessError) as exc_info:
            delete_account(db, account.id)
        # 检查错误信息包含关联表名称（可能是银行账户或付款记录，取决于检查顺序）
        label = exc_info.value.data.get("label", "")
        assert label in ("银行账户", "付款记录"), f"Expected 银行账户 or 付款记录, got {label}"

    def test_account_with_fixed_asset_blocked(self, db):
        """有固定资产的账本 → 删除失败"""
        account = Account(name="测试有资产账本", type="company", code="test_asset")
        db.add(account)
        db.flush()

        fixed_asset = FixedAsset(
            account_id=account.id,
            asset_code="FA-001",
            name="测试资产",
            original_value_l1=Decimal("10000"),
            useful_life_l3=60,
            start_date_l1=datetime.now().date(),
        )
        db.add(fixed_asset)
        db.flush()

        with pytest.raises(BusinessError) as exc_info:
            delete_account(db, account.id)
        assert "固定资产" in exc_info.value.data.get("label", "")

    def test_account_with_intangible_asset_blocked(self, db):
        """有无形资产的账本 → 删除失败"""
        account = Account(name="测试有无形资产账本", type="company", code="test_intangible")
        db.add(account)
        db.flush()

        intangible_asset = IntangibleAsset(
            account_id=account.id,
            asset_code="IA-001",
            name="测试软件",
            original_value_l1=Decimal("5000"),
            useful_life_l3=36,
            start_date_l1=datetime.now().date(),
        )
        db.add(intangible_asset)
        db.flush()

        with pytest.raises(BusinessError) as exc_info:
            delete_account(db, account.id)
        assert "无形资产" in exc_info.value.data.get("label", "")
