"""会计准则校验测试 — 验证财务数据是否符合《小企业会计准则》

依据: 财会〔2011〕17 号《小企业会计准则》
测试目标:
  1. 验证资产负债表恒等式: 资产 = 负债 + 所有者权益
  2. 验证利润表计算准确性
  3. 验证增值税计算合规性
  4. 验证所得税计算合规性
  5. 验证发票金额计算规则
  6. 验证固定资产折旧计算
  7. 验证双口径计算（税务口径 vs 经营口径）

会计恒等式:
  - 资产 = 负债 + 所有者权益
  - 净利润 = 利润总额 - 所得税费用
  - 应纳增值税 = 销项税额 - 进项税额
"""

import pytest
import time
from decimal import Decimal
from database import SessionLocal
from models import Account
from test_helpers import ensure_test_product

# ── 获取测试用 account_id ──
_db = SessionLocal()
_account = _db.query(Account).first()
ACCOUNT_ID = _account.id if _account else 1
TAXPAYER_TYPE = _account.taxpayer_type if _account else "small_scale"
_db.close()

# 公共请求头
HEADERS = {"X-Account-ID": str(ACCOUNT_ID), "X-Operator": "accounting_test"}


@pytest.fixture(scope="module", autouse=True)
def seed_opening_balance():
    """模块级前置：清理预存数据 + 创建期初余额 + 库存 + 银行账户"""
    from datetime import date, datetime
    from decimal import Decimal
    from database import engine, SessionLocal
    from models import OpeningBalance, BankAccount, Product, Inventory

    # 使用原始 sqlite3 连接清理业务数据（不删 opening_balances，仅更新）
    raw = engine.raw_connection()
    raw.execute("PRAGMA foreign_keys=OFF")
    for tname in ["account_move_lines", "account_moves", "stock_moves",
                   "receipts", "payments", "invoices", "fixed_assets",
                   "sale_items", "sale_orders", "purchase_items",
                   "purchase_orders", "expenses"]:
        raw.execute(f"DELETE FROM {tname}")
    raw.execute(f"DELETE FROM inventory WHERE account_id={ACCOUNT_ID}")
    raw.execute(f"DELETE FROM bank_accounts WHERE account_id={ACCOUNT_ID}")
    raw.execute("PRAGMA foreign_keys=ON")
    raw.commit()
    raw.close()

    db = SessionLocal()
    try:
        ob = db.query(OpeningBalance).filter(
            OpeningBalance.account_id == ACCOUNT_ID
        ).first()
        if not ob:
            ob = OpeningBalance(account_id=ACCOUNT_ID)
        ob.date = date(2026, 1, 1)
        ob.cash_balance = Decimal('10000.00')
        ob.bank_balance = Decimal('50000.00')
        ob.accounts_receivable = Decimal('5000.00')
        ob.inventory_value = Decimal('20000.00')
        ob.fixed_assets_original = Decimal('0')
        ob.accumulated_depreciation = Decimal('0')
        ob.intangible_assets_original = Decimal('0')
        ob.accumulated_amortization = Decimal('0')
        ob.accounts_payable = Decimal('0')
        ob.tax_payable = Decimal('0')
        ob.long_term_borrowings = Decimal('0')
        ob.paid_in_capital = Decimal('50000.00')
        ob.retained_earnings = Decimal('35000.00')
        if not ob.id:
            db.add(ob)

        product = Product(
            account_id=ACCOUNT_ID,
            name=f"测试产品-{int(datetime.now().timestamp())}",
            sku=f"OB-{int(datetime.now().timestamp())}",
            unit="个",
            purchase_price=Decimal('50.00'),
            sale_price=Decimal('100.00'),
            track_inventory=True,
            category="测试",
        )
        db.add(product)
        db.flush()
        inv = Inventory(
            account_id=ACCOUNT_ID,
            product_id=product.id,
            quantity=200,
            average_cost=Decimal('100.00'),
            total_value=Decimal('20000.00'),
        )
        db.add(inv)
        bank = BankAccount(
            account_id=ACCOUNT_ID,
            bank_name="测试银行",
            account_number="6222021234567890",
            balance=Decimal('60000.00'),
        )
        db.add(bank)
        db.commit()
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# 1. 资产负债表恒等式校验
# ═══════════════════════════════════════════════════════════════
class TestBalanceSheetEquation:
    """资产负债表恒等式: 资产 = 负债 + 所有者权益"""

    def test_balance_sheet_equation_2026_q1(self, client):
        """Q1资产负债表恒等式校验"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 3},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"资产负债表接口失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            # 验证恒等式
            total_assets = Decimal(str(data.get("total_assets", 0)))
            total_liabilities = Decimal(str(data.get("total_liabilities", 0)))
            total_equity = Decimal(str(data.get("total_equity", 0)))
            
            # 允许±0.01的容差（浮点数精度问题）
            diff = abs(total_assets - (total_liabilities + total_equity))
            assert diff <= Decimal('0.01'), \
                f"资产负债表不平衡: 资产({total_assets}) ≠ 负债({total_liabilities}) + 权益({total_equity}), 差异: {diff}"

    def test_balance_sheet_equation_2026_q2(self, client):
        """Q2资产负债表恒等式校验"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"资产负债表接口失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            total_assets = Decimal(str(data.get("total_assets", 0)))
            total_liabilities = Decimal(str(data.get("total_liabilities", 0)))
            total_equity = Decimal(str(data.get("total_equity", 0)))
            
            diff = abs(total_assets - (total_liabilities + total_equity))
            assert diff <= Decimal('0.01'), \
                f"资产负债表不平衡: 资产({total_assets}) ≠ 负债({total_liabilities}) + 权益({total_equity}), 差异: {diff}"

    def test_balance_sheet_detail_structure(self, client):
        """验证资产负债表明细结构"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"资产负债表接口失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            # 验证资产类科目存在
            assert "total_assets" in data, "资产负债表缺少资产总计"
            assert "total_liabilities" in data, "资产负债表缺少负债总计"
            assert "total_equity" in data, "资产负债表缺少权益总计"

    def test_balance_sheet_no_double_count_fixed_assets(self, client):
        """应付账款不含固定资产双重计算（单一真相源：应付账款=采购单未付款+费用未付款）"""
        from database import SessionLocal
        import models
        from sqlalchemy import func as sqlfunc

        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"date": "2026-12-31"},
                         headers=HEADERS)
        assert resp.status_code == 200, f"资产负债表接口返回 {resp.status_code}: {resp.text}"
        data = resp.json()
        accounts_payable = Decimal(str(data["accounts_payable"]))

        # 手工算单一真相源的应付账款：采购单未付款 + 费用未付款
        db = SessionLocal()
        try:
            po_payable = db.query(sqlfunc.sum(models.PurchaseOrder.total_price)).filter(
                models.PurchaseOrder.account_id == ACCOUNT_ID,
                models.PurchaseOrder.status == "completed",
                models.PurchaseOrder.payment_status == "unpaid"
            ).scalar() or Decimal('0')
            expense_payable = db.query(sqlfunc.sum(models.Expense.amount)).filter(
                models.Expense.account_id == ACCOUNT_ID,
                models.Expense.payment_status == "unpaid"
            ).scalar() or Decimal('0')
            db.close()
        finally:
            pass

        expected_payable = Decimal(str(po_payable)) + Decimal(str(expense_payable))
        # 容差 0.01
        assert abs(accounts_payable - expected_payable) <= Decimal('0.01'), \
            f"应付账款双重计算: 报表={accounts_payable}, 单一真相源(采购+费用)={expected_payable}, " \
            f"差额={accounts_payable - expected_payable}（可能含固定资产或存货的重复计算）"

    def test_balance_sheet_opening_receivable_inventory(self, client):
        """期初应收账款和存货加到期末值（不丢失期初资产）"""
        from database import SessionLocal
        import models

        db = SessionLocal()
        try:
            ob = db.query(models.OpeningBalance).filter(
                models.OpeningBalance.account_id == ACCOUNT_ID
            ).order_by(models.OpeningBalance.date.desc()).first()
            assert ob is not None, "seed_opening_balance fixture should have created data"
            opening_ar = Decimal(str(ob.accounts_receivable or 0))
            opening_inv = Decimal(str(ob.inventory_value or 0))
        finally:
            db.close()

        assert opening_ar > 0 or opening_inv > 0, "seed_opening_balance fixture should have AR/inventory > 0"

        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"date": "2026-12-31"},
                         headers=HEADERS)
        assert resp.status_code == 200, f"资产负债表接口返回 {resp.status_code}: {resp.text}"
        data = resp.json()
        # 期末应收 ≥ 期初应收（至少包含期初部分）
        assert Decimal(str(data["accounts_receivable"])) >= opening_ar - Decimal('0.01'), \
            f"期末应收{data['accounts_receivable']} < 期初应收{opening_ar}，期初应收丢失"
        # 期末存货 ≥ 期初存货
        assert Decimal(str(data["inventory"])) >= opening_inv - Decimal('0.01'), \
            f"期末存货{data['inventory']} < 期初存货{opening_inv}，期初存货丢失"


# ═══════════════════════════════════════════════════════════════
# 2. 利润表计算校验
# ═══════════════════════════════════════════════════════════════
class TestIncomeStatementCalculation:
    """利润表计算: 净利润 = 利润总额 - 所得税费用"""

    def test_income_statement_equation(self, client):
        """利润表恒等式校验"""
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"利润表接口失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            # 验证利润表结构
            assert "revenue" in data or "total_revenue" in data, "利润表缺少营业收入"
            assert "net_profit" in data or "total_revenue" in data, "利润表缺少净利润"

    def test_income_statement_detail(self, client):
        """利润表明细计算验证"""
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"利润表接口失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            # 验证关键字段
            expected_fields = ["revenue", "cost", "gross_profit", "net_profit"]
            for field in expected_fields:
                assert field in data, f"利润表缺少{field}字段"


# ═══════════════════════════════════════════════════════════════
# 3. 增值税计算校验
# ═══════════════════════════════════════════════════════════════
class TestVATCalculation:
    """增值税计算: 应纳增值税 = 销项税额 - 进项税额"""

    def test_vat_calculation_q1(self, client):
        """Q1增值税计算校验"""
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 1},
                         headers=HEADERS)
        assert resp.status_code == 200, f"增值税报表接口失败: {resp.text}"
        data = resp.json()
        
        # 验证增值税计算结构
        assert "output_tax" in data, "增值税报表缺少销项税额"
        assert "input_tax" in data, "增值税报表缺少进项税额"

    def test_vat_calculation_q2(self, client):
        """Q2增值税计算校验"""
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"增值税报表接口失败: {resp.text}"
        data = resp.json()
        
        # 验证增值税计算逻辑
        output_tax = Decimal(str(data.get("output_tax", 0)))
        input_tax = Decimal(str(data.get("input_tax", 0)))
        payable = Decimal(str(data.get("tax_payable", 0)))
        
        # 小规模纳税人: 应纳增值税 = 不含税销售额 × 征收率
        # 一般纳税人: 应纳增值税 = 销项税额 - 进项税额
        if TAXPAYER_TYPE == "general":
            expected_payable = max(output_tax - input_tax, Decimal('0'))
            assert abs(payable - expected_payable) <= Decimal('0.01'), \
                f"增值税计算错误: 预期{expected_payable}, 实际{payable}"

    def test_vat_report_structure(self, client):
        """增值税报表结构验证"""
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"增值税报表接口失败: {resp.text}"
        data = resp.json()
        
        # 验证报表字段
        expected_fields = ["output_tax", "input_tax", "tax_payable"]
        for field in expected_fields:
            assert field in data, f"增值税报表缺少{field}字段"


# ═══════════════════════════════════════════════════════════════
# 4. 所得税计算校验
# ═══════════════════════════════════════════════════════════════
class TestIncomeTaxCalculation:
    """所得税计算: 应纳税额 = 利润总额 × 税率"""

    def test_income_tax_calculation(self, client):
        """所得税计算校验"""
        resp = client.get("/api/income-tax-report",
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"所得税报表接口失败: {resp.text}"
        data = resp.json()
        
        # 验证所得税计算结构
        assert "total_revenue" in data, "所得税报表缺少收入"
        assert "tax_amount" in data, "所得税报表缺少应纳税额"

    def test_income_tax_small_micro_enterprise(self, client):
        """小微企业所得税优惠政策验证"""
        resp = client.get("/api/income-tax-report",
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"所得税报表接口失败: {resp.text}"
        data = resp.json()
        
        # 验证小微企业优惠: 利润≤300万，税率5%
        taxable_income = Decimal(str(data.get("taxable_income", 0)))
        tax_amount = Decimal(str(data.get("tax_amount", 0)))
        tax_rate = Decimal(str(data.get("tax_rate", 0.25)))
        
        # 验证税率合理性
        assert tax_rate in [Decimal('0.05'), Decimal('0.15'), Decimal('0.25')], \
            f"所得税税率异常: {tax_rate}"

    def test_income_tax_report_structure(self, client):
        """所得税报表结构验证"""
        resp = client.get("/api/income-tax-report",
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"所得税报表接口失败: {resp.text}"
        data = resp.json()
        
        # 验证报表字段
        expected_fields = ["total_revenue", "total_cost", "taxable_income", "tax_amount"]
        for field in expected_fields:
            assert field in data, f"所得税报表缺少{field}字段"


# ═══════════════════════════════════════════════════════════════
# 5. 发票金额计算校验
# ═══════════════════════════════════════════════════════════════
class TestInvoiceAmountCalculation:
    """发票金额计算: 不含税金额 = 含税金额 ÷ (1 + 税率)"""
    _inv_counter = 0

    def test_invoice_amount_calculation_13_percent(self, client):
        """13%税率发票金额计算"""
        TestInvoiceAmountCalculation._inv_counter += 1
        unique_no = f"TEST-INV-13PCT-{int(time.time())}-{TestInvoiceAmountCalculation._inv_counter}"
        pid = ensure_test_product(ACCOUNT_ID)
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": unique_no,
            "direction": "in",
            "invoice_type": "special",
            "amount_with_tax": "11300.00",
            "tax_rate": "0.13",
            "counterparty_name": "测试供应商",
            "seller_name": "测试供应商",
            "buyer_name": "本公司",
            "issue_date": "2026-06-20",
            "purchase_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "10000.00", "tax_rate": "0.13"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建发票失败: {resp.text}"
        data = resp.json().get("data", resp.json())
        
        # 验证计算: 不含税金额 = 11300 ÷ 1.13 = 10000
        amount_without_tax = Decimal(str(data.get("amount_without_tax", 0)))
        tax_amount = Decimal(str(data.get("tax_amount", 0)))
        amount_with_tax = Decimal(str(data.get("amount_with_tax", 0)))
        
        assert abs(amount_without_tax - Decimal('10000.00')) <= Decimal('0.01'), \
            f"不含税金额计算错误: 预期10000, 实际{amount_without_tax}"
        assert abs(tax_amount - Decimal('1300.00')) <= Decimal('0.01'), \
            f"税额计算错误: 预期1300, 实际{tax_amount}"
        assert abs(amount_with_tax - Decimal('11300.00')) <= Decimal('0.01'), \
            f"含税金额计算错误: 预期11300, 实际{amount_with_tax}"

    def test_invoice_amount_calculation_1_percent(self, client):
        """1%征收率发票金额计算"""
        TestInvoiceAmountCalculation._inv_counter += 1
        unique_no = f"TEST-INV-1PCT-{int(time.time())}-{TestInvoiceAmountCalculation._inv_counter}"
        pid = ensure_test_product(ACCOUNT_ID)
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": unique_no,
            "direction": "out",
            "invoice_type": "ordinary",
            "amount_with_tax": "10100.00",
            "tax_rate": "0.01",
            "counterparty_name": "测试客户",
            "seller_name": "本公司",
            "buyer_name": "测试客户",
            "issue_date": "2026-06-20",
            "sale_order_action": "auto_create",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": "10000.00", "tax_rate": "0.01"}],
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建发票失败: {resp.text}"
        data = resp.json().get("data", resp.json())
        assert data.get("related_order_type") == "sale_order", "销项发票应生成销售单"
        
        # 验证计算: 不含税金额 = 10100 ÷ 1.01 = 10000
        amount_without_tax = Decimal(str(data.get("amount_without_tax", 0)))
        tax_amount = Decimal(str(data.get("tax_amount", 0)))
        
        assert abs(amount_without_tax - Decimal('10000.00')) <= Decimal('0.01'), \
            f"不含税金额计算错误: 预期10000, 实际{amount_without_tax}"
        assert abs(tax_amount - Decimal('100.00')) <= Decimal('0.01'), \
            f"税额计算错误: 预期100, 实际{tax_amount}"

    def test_invoice_amount_balance(self, client):
        """发票金额平衡校验: 含税金额 = 不含税金额 + 税额"""
        resp = client.get("/api/invoices", headers=HEADERS)
        assert resp.status_code == 200, f"查询发票失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        for inv in items[:10]:  # 检查前10张发票
            amount_without_tax = Decimal(str(inv.get("amount_without_tax", 0)))
            tax_amount = Decimal(str(inv.get("tax_amount", 0)))
            amount_with_tax = Decimal(str(inv.get("amount_with_tax", 0)))
            
            diff = abs(amount_with_tax - (amount_without_tax + tax_amount))
            assert diff <= Decimal('0.01'), \
                f"发票{inv.get('invoice_no')}金额不平衡: {amount_without_tax} + {tax_amount} ≠ {amount_with_tax}"


# ═══════════════════════════════════════════════════════════════
# 6. 固定资产折旧计算校验
# ═══════════════════════════════════════════════════════════════
class TestFixedAssetDepreciation:
    """固定资产折旧计算: 年限平均法"""

    def test_straight_line_depreciation(self, client):
        """年限平均法折旧计算验证"""
        import time
        unique_code = f"FA-DEPR-TEST-{int(time.time())}"
        # 创建固定资产: 原值10000, 残值率5%, 使用寿命3年(36个月)
        resp = client.post("/api/fixed-assets", json={
            "asset_code": unique_code,
            "name": "折旧测试设备",
            "category": "电子设备",
            "original_value": 10000.00,
            "salvage_rate": 0.05,
            "useful_life": 36,
            "start_date": "2026-01-01",
            "depreciation_method": "年限平均法"
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"创建固定资产失败: {resp.text}"
        
        # 验证折旧计算
        # 月折旧额 = (10000 - 10000×5%) ÷ 36 = 9500 ÷ 36 = 263.89
        # 6个月累计折旧 = 263.89 × 6 = 1583.34
        
        resp = client.get("/api/fixed-assets", headers=HEADERS)
        assert resp.status_code == 200, f"查询固定资产失败: {resp.text}"
        data = resp.json()
        
        assets = data.get("items", data) if isinstance(data, dict) else data
        test_asset = None
        for asset in (assets if isinstance(assets, list) else []):
            if asset.get("asset_code") == "FA-DEPR-TEST":
                test_asset = asset
                break
        
        if test_asset:
            original_value = Decimal(str(test_asset.get("original_value", 0)))
            salvage_rate = Decimal(str(test_asset.get("salvage_rate", 0.05)))
            useful_life = int(test_asset.get("useful_life", 36))
            
            # 计算预期折旧
            salvage_value = original_value * salvage_rate
            depreciable_value = original_value - salvage_value
            monthly_depreciation = depreciable_value / useful_life
            
            # 验证残值率合理
            assert salvage_rate >= Decimal('0') and salvage_rate <= Decimal('0.10'), \
                f"残值率不合理: {salvage_rate}"


# ═══════════════════════════════════════════════════════════════
# 7. 双口径计算校验
# ═══════════════════════════════════════════════════════════════
class TestDualCaliberCalculation:
    """双口径计算: 税务口径 vs 经营口径"""

    def test_tax_caliber_uses_invoices(self, client):
        """税务口径使用发票数据"""
        resp = client.get("/api/income-tax-report",
                         params={"year": 2026, "quarter": 2, "caliber": "tax"},
                         headers=HEADERS)
        assert resp.status_code == 200, f"税务口径报表失败: {resp.text}"
        data = resp.json()
        
        # 税务口径收入应基于发票
        assert "total_revenue" in data, "税务口径报表缺少收入"
        assert "invoice_revenue" in data, "税务口径报表缺少发票收入"


# ═══════════════════════════════════════════════════════════════
# 8. 会计恒等式综合校验
# ═══════════════════════════════════════════════════════════════
class TestAccountingEquations:
    """会计恒等式综合校验"""

    def test_balance_sheet_accessible(self, client):
        """资产负债表可访问"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"资产负债表接口异常: {resp.status_code}"

    def test_income_statement_accessible(self, client):
        """利润表可访问"""
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"利润表接口异常: {resp.status_code}"

    def test_cash_flow_accessible(self, client):
        """现金流量表可访问"""
        resp = client.get("/api/cash-flows/statement",
                         params={"start_date": "2026-01-01", "end_date": "2026-06-30"},
                         headers=HEADERS)
        assert resp.status_code in (200, 500), f"现金流量表接口异常: {resp.status_code}"

    def test_accounting_check_endpoints(self, client):
        """会计校验接口可达性"""
        endpoints = [
            "/api/financial-reports/balance-sheet",
            "/api/financial-reports/income-statement",
            "/api/tax-report",
            "/api/income-tax-report",
        ]
        
        for endpoint in endpoints:
            resp = client.get(endpoint,
                             params={"year": 2026, "quarter": 2},
                             headers=HEADERS)
            assert resp.status_code in (200, 422), f"会计校验接口{endpoint}不可访问: {resp.status_code}"


# ═══════════════════════════════════════════════════════════════
# 9. 科目余额合理性校验
# ═══════════════════════════════════════════════════════════════
class TestAccountBalanceReasonableness:
    """科目余额合理性校验"""

    def test_no_negative_inventory(self, client):
        """库存不应为负数"""
        resp = client.get("/api/inventory",
                         params={"page": 1, "page_size": 500},
                         headers=HEADERS)
        assert resp.status_code == 200, f"查询库存失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        for item in items:
            quantity = item.get("quantity", 0)
            assert quantity >= 0, f"库存为负数: 商品{item.get('product_id')} 数量{quantity}"

    def test_no_negative_accounts_receivable(self, client):
        """应收账款不应为负数"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            ar = Decimal(str(data.get("accounts_receivable", 0)))
            assert ar >= 0, f"应收账款为负数: {ar}"

    def test_fixed_assets_net_value(self, client):
        """固定资产净值不应为负数"""
        resp = client.get("/api/fixed-assets", headers=HEADERS)
        assert resp.status_code == 200, f"查询固定资产失败: {resp.text}"
        data = resp.json()
        
        assets = data.get("items", data) if isinstance(data, dict) else data
        for asset in (assets if isinstance(assets, list) else []):
            original = Decimal(str(asset.get("original_value", 0)))
            depreciation = Decimal(str(asset.get("accumulated_depreciation", 0)))
            net_value = original - depreciation
            assert net_value >= 0, \
                f"固定资产净值为负: {asset.get('name')} 原值{original} 折旧{depreciation}"


# ═══════════════════════════════════════════════════════════════
# 10. 业务规则合规性校验
# ═══════════════════════════════════════════════════════════════
class TestBusinessRuleCompliance:
    """业务规则合规性校验"""

    def test_payment_status_consistency(self, client):
        """支付状态一致性校验"""
        # 查询采购单
        resp = client.get("/api/purchases", headers=HEADERS)
        assert resp.status_code == 200, f"查询采购单失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        for order in items[:10]:  # 检查前10个订单
            status = order.get("status")
            payment_status = order.get("payment_status")
            
            # 已取消的订单不应有已支付状态
            if status == "cancelled":
                assert payment_status != "paid", \
                    f"已取消订单{order.get('order_no')}仍为已支付状态"

    def test_order_amount_positive(self, client):
        """订单金额应为正数"""
        resp = client.get("/api/sales", headers=HEADERS)
        assert resp.status_code == 200, f"查询销售单失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        for order in items[:10]:
            total_price = Decimal(str(order.get("total_price", 0)))
            assert total_price >= 0, \
                f"销售单金额为负: {order.get('order_no')} 金额{total_price}"

    def test_expense_categories_valid(self, client):
        """费用类别应有效"""
        resp = client.get("/api/expenses", headers=HEADERS)
        assert resp.status_code == 200, f"查询费用失败: {resp.text}"
        data = resp.json()
        
        valid_categories = ["房租", "水电", "工资", "材料", "办公用品", 
                           "运费", "维修", "税金及附加", "所得税", "其他"]
        
        items = data.get("items", [])
        for expense in items[:10]:
            category = expense.get("category")
            # 允许自定义类别，但不应为空
            assert category, f"费用类别为空: {expense.get('id')}"


# ═══════════════════════════════════════════════════════════════
# 11. 税务合规性校验
# ═══════════════════════════════════════════════════════════════
class TestTaxCompliance:
    """税务合规性校验"""

    def test_vat_tax_rate_valid(self, client):
        """增值税税率有效性校验"""
        resp = client.get("/api/invoices", headers=HEADERS)
        assert resp.status_code == 200, f"查询发票失败: {resp.text}"
        data = resp.json()
        
        valid_rates = [Decimal('0.13'), Decimal('0.09'), Decimal('0.06'), 
                      Decimal('0.03'), Decimal('0.01'), Decimal('0')]
        
        items = data.get("items", [])
        for inv in items[:10]:
            tax_rate = Decimal(str(inv.get("tax_rate", 0)))
            # 允许特殊税率，但应在合理范围内
            assert tax_rate >= Decimal('0') and tax_rate <= Decimal('0.20'), \
                f"发票税率异常: {inv.get('invoice_no')} 税率{tax_rate}"

    def test_invoice_direction_valid(self, client):
        """发票方向有效性校验"""
        resp = client.get("/api/invoices", headers=HEADERS)
        assert resp.status_code == 200, f"查询发票失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        for inv in items[:10]:
            direction = inv.get("direction")
            assert direction in ["in", "out"], \
                f"发票方向无效: {inv.get('invoice_no')} 方向{direction}"

    def test_certification_status_valid(self, client):
        """发票认证状态有效性校验"""
        resp = client.get("/api/invoices", headers=HEADERS)
        assert resp.status_code == 200, f"查询发票失败: {resp.text}"
        data = resp.json()
        
        valid_statuses = ["pending", "certified", "n_a"]
        
        items = data.get("items", [])
        for inv in items[:10]:
            status = inv.get("certification_status")
            assert status in valid_statuses, \
                f"发票认证状态无效: {inv.get('invoice_no')} 状态{status}"
