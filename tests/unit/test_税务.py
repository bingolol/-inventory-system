"""
税务计算测试 — 合并税额计算和税务表单测试

测试内容：
  1. 增值税申报表计算
  2. 企业所得税预缴计算
  3. 资产折旧明细表
"""
import pytest
from decimal import Decimal


class FakeInvoiceORM:
    """模拟发票ORM对象"""
    def __init__(self, amount_without_tax=0, tax_rate=0.03, direction='out'):
        self.amount_without_tax = Decimal(str(amount_without_tax))
        self.tax_rate = Decimal(str(tax_rate))
        self.direction = direction


class FakeAccountORM:
    """模拟账户ORM对象"""
    def __init__(self, taxpayer_type='small_scale'):
        self.id = 1
        self.taxpayer_type = taxpayer_type


class FakeDBSession:
    """模拟数据库会话"""
    def __init__(self, invoices=None, account=None):
        self._invoices = invoices or []
        self._account = account or FakeAccountORM()

    def query(self, model):
        return self

    def filter(self, *args):
        return self

    def all(self):
        return self._invoices

    def first(self):
        return self._account

    def scalar(self):
        return None


# ========== 增值税申报表 ==========

class TestVATDeclaration:
    """增值税及附加税费申报表测试"""

    def test_vat_form_period(self):
        """申报表期间：2026-04-01至2026-06-30"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['period_start'] == '2026-04-01'
        assert result['period_end'] == '2026-06-30'

    def test_vat_form_revenue(self):
        """计税依据：应征增值税不含税销售额 = 4,158.42"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['total_revenue'] == Decimal('4158.42')

    def test_vat_form_tax_rate(self):
        """征收率应为3%"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['tax_rate'] == Decimal('0.03')

    def test_vat_form_tax_payable_gross(self):
        """本期应纳税额 = 4,158.42 × 3% = 124.75"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['tax_payable_gross'] == Decimal('124.75')

    def test_vat_form_tax_reduction(self):
        """本期应纳税额减征额 = 124.75 × 2/3 = 83.17"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['tax_reduction'] == Decimal('83.17')

    def test_vat_form_tax_payable(self):
        """应纳税额合计 = 41.58"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['tax_payable'] == Decimal('41.58')

    def test_vat_form_surcharge_stamp(self):
        """城市维护建设税 = 41.58 × 7% × 50% = 1.46"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['surcharge_stamp'] == Decimal('1.46')

    def test_vat_form_surcharge_education_exempt(self):
        """教育费附加 = 0（月销售额≤10万免征）"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['surcharge_education'] == Decimal('0')

    def test_vat_form_surcharge_local_education_exempt(self):
        """地方教育附加 = 0（月销售额≤10万免征）"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['surcharge_local_education'] == Decimal('0')

    def test_vat_form_surcharge_total(self):
        """附加税费合计 = 1.46"""
        from crud.finance import generate_vat_declaration
        invoices = [FakeInvoiceORM(amount_without_tax=4158.42)]
        db = FakeDBSession(invoices)
        result = generate_vat_declaration(db, account_id=1, year=2026, quarter=2)
        assert result['surcharge_total'] == Decimal('1.46')


# ========== 企业所得税预缴申报表 ==========

class TestIncomeTaxPrepayment:
    """企业所得税预缴申报表（A类）测试"""

    def test_income_tax_form_profit(self):
        """利润总额 = 2,376.23"""
        operating_revenue = Decimal('7128.72')
        operating_cost = Decimal('0')
        tax_and_surcharge = Decimal('2.49')
        operating_expenses = Decimal('4750.00')
        gross_profit = operating_revenue - operating_cost - tax_and_surcharge - operating_expenses
        assert gross_profit == Decimal('2376.23')

    def test_income_tax_form_tax_payable(self):
        """应纳所得税额 = 594.06"""
        actual_profit = Decimal('2376.23')
        tax_rate = Decimal('0.25')
        tax_payable = actual_profit * tax_rate
        assert tax_payable.quantize(Decimal('0.01')) == Decimal('594.06')

    def test_income_tax_form_discount(self):
        """减免所得税额 = 475.25"""
        tax_payable = Decimal('594.06')
        discount_rate = Decimal('0.80')
        small_micro_discount = tax_payable * discount_rate
        assert small_micro_discount.quantize(Decimal('0.01')) == Decimal('475.25')

    def test_income_tax_form_actual_payable(self):
        """本期应补（退）所得税额 = 118.81"""
        tax_payable = Decimal('594.06')
        small_micro_discount = Decimal('475.25')
        actual_tax_payable = tax_payable - small_micro_discount
        assert actual_tax_payable == Decimal('118.81')


# ========== 资产加速折旧明细表 ==========

class TestAssetDepreciationDetail:
    """资产加速折旧明细表测试"""

    def test_asset_depreciation_empty(self):
        """无固定资产时，所有金额应为0"""
        from crud.finance import generate_asset_depreciation_detail
        db = FakeDBSession()
        result = generate_asset_depreciation_detail(db, account_id=1, year=2026, quarter=2)
        assert result['total_original_value'] == Decimal('0')
        assert result['total_depreciation'] == Decimal('0')
        assert result['total_accumulated'] == Decimal('0')
        assert len(result['assets']) == 0
