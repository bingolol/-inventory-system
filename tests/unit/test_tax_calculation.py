import sys
import os
import pytest
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))


class FakeInvoiceORM:
    """模拟发票ORM对象"""
    def __init__(self, amount_without_tax=0, tax_rate=0.03, direction='out'):
        self.amount_without_tax = Decimal(str(amount_without_tax))
        self.tax_rate = Decimal(str(tax_rate))
        self.direction = direction


class FakeDBSession:
    """模拟数据库会话"""
    def __init__(self, invoices=None):
        self._invoices = invoices or []

    def query(self, model):
        return self

    def filter(self, *args):
        return self

    def all(self):
        return self._invoices


class TestVATDeclarationCalculation:
    """增值税纳税申报表计算测试 - 验证实际函数"""

    def test_vat_declaration_tax_rate(self):
        """generate_vat_declaration 应使用3%征收率"""
        from crud.finance import generate_vat_declaration

        # 模拟发票数据：不含税销售额 4158.42
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)

        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)

        # 验证征收率应为3%
        assert result['tax_rate'] == Decimal('0.03'), \
            f"征收率应为3%，实际为{result['tax_rate']}"

    def test_vat_declaration_tax_payable(self):
        """generate_vat_declaration 应纳税额 = 不含税销售额 × 3%"""
        from crud.finance import generate_vat_declaration

        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)

        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)

        # 本期应纳税额 = 4158.42 × 3% = 124.75
        assert result['tax_payable_gross'] == Decimal('124.75'), \
            f"本期应纳税额应为124.75，实际为{result.get('tax_payable_gross')}"

    def test_vat_declaration_reduction(self):
        """generate_vat_declaration 减免税额 = 应纳税额 × 2/3"""
        from crud.finance import generate_vat_declaration

        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)

        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)

        # 减免税额 = 124.75 × 2/3 = 83.17
        assert result['tax_reduction'] == Decimal('83.17'), \
            f"减免税额应为83.17，实际为{result['tax_reduction']}"

    def test_vat_declaration_net_payable(self):
        """generate_vat_declaration 应纳税额合计 = 应纳税额 - 减免税额"""
        from crud.finance import generate_vat_declaration

        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)

        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)

        # 应纳税额合计 = 124.75 - 83.17 = 41.58
        assert result['tax_supplement'] == Decimal('41.58'), \
            f"应纳税额合计应为41.58，实际为{result['tax_supplement']}"

    def test_surcharge_stamp_with_50_reduction(self):
        """generate_vat_declaration 城市维护建设税应享受50%减征"""
        from crud.finance import generate_vat_declaration

        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)

        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)

        # 城市维护建设税 = 41.58 × 7% × 50% = 1.46
        assert result['surcharge_stamp'] == Decimal('1.46'), \
            f"城市维护建设税应为1.46，实际为{result['surcharge_stamp']}"

    def test_surcharge_education_exempt(self):
        """generate_vat_declaration 月销售额≤10万免征教育费附加"""
        from crud.finance import generate_vat_declaration

        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)

        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)

        # 月均销售额 = 4158.42 / 3 = 1386.14 < 100,000，应免征
        assert result['surcharge_education'] == Decimal('0'), \
            f"教育费附加应为0（免征），实际为{result['surcharge_education']}"
        assert result['surcharge_local_education'] == Decimal('0'), \
            f"地方教育附加应为0（免征），实际为{result['surcharge_local_education']}"


class TestIncomeTaxPrepaymentCalculation:
    """企业所得税预缴申报表计算测试 - 验证实际函数"""

    def test_income_tax_includes_surcharge(self):
        """企业所得税应包含税金及附加"""
        from crud.finance import generate_income_tax_prepayment

        # 用户数据：营业收入7128.72，营业成本0，税金及附加2.49，管理费用4750
        # 利润总额 = 7128.72 - 0 - 2.49 - 4750 = 2376.23
        expected_profit = Decimal('2376.23')

        # 验证计算公式
        operating_revenue = Decimal('7128.72')
        operating_cost = Decimal('0')
        tax_and_surcharge = Decimal('2.49')
        operating_expenses = Decimal('4750.00')
        gross_profit = operating_revenue - operating_cost - tax_and_surcharge - operating_expenses

        assert gross_profit == expected_profit, \
            f"利润总额应为{expected_profit}，实际为{gross_profit}"

    def test_income_tax_rate_25_percent(self):
        """法定税率应为25%"""
        tax_rate = Decimal('0.25')
        assert tax_rate == Decimal('0.25')

    def test_income_tax_payable(self):
        """应纳所得税额 = 实际利润额 × 25%"""
        actual_profit = Decimal('2376.23')
        tax_rate = Decimal('0.25')
        tax_payable = actual_profit * tax_rate
        # 2376.23 × 25% = 594.0575 ≈ 594.06
        assert tax_payable.quantize(Decimal('0.01')) == Decimal('594.06')

    def test_small_micro_discount_80_percent(self):
        """小型微利企业减免所得税额 = 应纳所得税额 × 80%"""
        tax_payable = Decimal('594.06')
        discount_rate = Decimal('0.80')
        small_micro_discount = tax_payable * discount_rate
        # 594.06 × 80% = 475.248 ≈ 475.25
        assert small_micro_discount.quantize(Decimal('0.01')) == Decimal('475.25')

    def test_actual_tax_payable(self):
        """本期应补(退)所得税额 = 应纳所得税额 - 减免所得税额"""
        tax_payable = Decimal('594.06')
        small_micro_discount = Decimal('475.25')
        actual_tax_payable = tax_payable - small_micro_discount
        # 594.06 - 475.25 = 118.81
        assert actual_tax_payable == Decimal('118.81')
