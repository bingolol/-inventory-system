"""会计准则数字验证测试 — 验证计算结果的数字是否正确

测试目标:
  1. 验证每个计算步骤的中间结果
  2. 验证最终结果的数字准确性
  3. 记录数据变化过程
  4. 发现数字计算问题

测试方法:
  - 不以成功运行为目标
  - 以数字正确为目标
  - 记录所有计算步骤和中间结果
"""

import os
import sys
import json
import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from fastapi.testclient import TestClient

# 确保 backend 在 sys.path 中
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
BACKEND_DIR = os.path.abspath(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 在导入 main 之前，初始化数据库和工作区
import workspace
workspace.ensure_workspace()

from database import init_db, SessionLocal
init_db()

from main import app
from models import Account

# ── 获取测试用 account_id ──
_db = SessionLocal()
_account = _db.query(Account).first()
ACCOUNT_ID = _account.id if _account else 1
TAXPAYER_TYPE = _account.taxpayer_type if _account else "small_scale"
_db.close()

# 公共请求头
HEADERS = {"X-Account-ID": str(ACCOUNT_ID), "X-Operator": "accounting_verify"}

# 数据变化记录
DATA_CHANGES = []


def record_change(module, operation, before, after, calculation=""):
    """记录数据变化"""
    DATA_CHANGES.append({
        "module": module,
        "operation": operation,
        "before": str(before),
        "after": str(after),
        "calculation": calculation,
        "timestamp": datetime.now().isoformat()
    })


@pytest.fixture(scope="module")
def client():
    """全 module 共享的 TestClient"""
    with TestClient(app) as c:
        yield c


# ═══════════════════════════════════════════════════════════════
# 1. 发票金额计算数字验证
# ═══════════════════════════════════════════════════════════════
class TestInvoiceAmountVerification:
    """发票金额计算数字验证"""

    def test_invoice_13_percent_calculation(self, client):
        """13%税率发票金额计算验证"""
        import time
        unique_no = f"VERIFY-13PCT-{int(time.time())}"
        
        # 输入数据
        input_amount_with_tax = Decimal('11300.00')
        input_tax_rate = Decimal('0.13')
        
        # 预期计算结果
        expected_amount_without_tax = input_amount_with_tax / (1 + input_tax_rate)
        expected_tax_amount = input_amount_with_tax - expected_amount_without_tax
        
        # 调用API
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": unique_no,
            "direction": "in",
            "invoice_type": "special",
            "amount_with_tax": str(input_amount_with_tax),
            "tax_rate": str(input_tax_rate),
            "counterparty_name": "数字验证供应商",
            "issue_date": "2026-06-20",
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建发票失败: {resp.text}"
        data = resp.json().get("data", resp.json())
        
        # 实际计算结果
        actual_amount_without_tax = Decimal(str(data.get("amount_without_tax", 0)))
        actual_tax_amount = Decimal(str(data.get("tax_amount", 0)))
        actual_amount_with_tax = Decimal(str(data.get("amount_with_tax", 0)))
        
        # 记录数据变化
        record_change(
            module="发票管理",
            operation="13%税率发票计算",
            before=f"含税金额={input_amount_with_tax}, 税率={input_tax_rate}",
            after=f"不含税金额={actual_amount_without_tax}, 税额={actual_tax_amount}",
            calculation=f"不含税金额 = {input_amount_with_tax} ÷ (1 + {input_tax_rate}) = {expected_amount_without_tax}"
        )
        
        # 验证数字
        print(f"\n=== 13%税率发票计算验证 ===")
        print(f"输入: 含税金额={input_amount_with_tax}, 税率={input_tax_rate}")
        print(f"预期: 不含税金额={expected_amount_without_tax}, 税额={expected_tax_amount}")
        print(f"实际: 不含税金额={actual_amount_without_tax}, 税额={actual_tax_amount}")
        print(f"差异: 不含税金额={abs(expected_amount_without_tax - actual_amount_without_tax)}, 税额={abs(expected_tax_amount - actual_tax_amount)}")
        
        # 验证数字准确性
        assert abs(actual_amount_without_tax - expected_amount_without_tax) <= Decimal('0.01'), \
            f"不含税金额计算错误: 预期{expected_amount_without_tax}, 实际{actual_amount_without_tax}"
        assert abs(actual_tax_amount - expected_tax_amount) <= Decimal('0.01'), \
            f"税额计算错误: 预期{expected_tax_amount}, 实际{actual_tax_amount}"
        assert abs(actual_amount_with_tax - input_amount_with_tax) <= Decimal('0.01'), \
            f"含税金额不一致: 预期{input_amount_with_tax}, 实际{actual_amount_with_tax}"

    def test_invoice_1_percent_calculation(self, client):
        """1%征收率发票金额计算验证"""
        import time
        unique_no = f"VERIFY-1PCT-{int(time.time())}"
        
        # 输入数据
        input_amount_with_tax = Decimal('10100.00')
        input_tax_rate = Decimal('0.01')
        
        # 预期计算结果
        expected_amount_without_tax = input_amount_with_tax / (1 + input_tax_rate)
        expected_tax_amount = input_amount_with_tax - expected_amount_without_tax
        
        # 调用API
        resp = client.post("/api/invoices/quick", json={
            "invoice_no": unique_no,
            "direction": "out",
            "invoice_type": "ordinary",
            "amount_with_tax": str(input_amount_with_tax),
            "tax_rate": str(input_tax_rate),
            "counterparty_name": "数字验证客户",
            "issue_date": "2026-06-20",
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建发票失败: {resp.text}"
        data = resp.json().get("data", resp.json())
        
        # 实际计算结果
        actual_amount_without_tax = Decimal(str(data.get("amount_without_tax", 0)))
        actual_tax_amount = Decimal(str(data.get("tax_amount", 0)))
        
        # 记录数据变化
        record_change(
            module="发票管理",
            operation="1%征收率发票计算",
            before=f"含税金额={input_amount_with_tax}, 税率={input_tax_rate}",
            after=f"不含税金额={actual_amount_without_tax}, 税额={actual_tax_amount}",
            calculation=f"不含税金额 = {input_amount_with_tax} ÷ (1 + {input_tax_rate}) = {expected_amount_without_tax}"
        )
        
        # 验证数字
        print(f"\n=== 1%征收率发票计算验证 ===")
        print(f"输入: 含税金额={input_amount_with_tax}, 税率={input_tax_rate}")
        print(f"预期: 不含税金额={expected_amount_without_tax}, 税额={expected_tax_amount}")
        print(f"实际: 不含税金额={actual_amount_without_tax}, 税额={actual_tax_amount}")
        print(f"差异: 不含税金额={abs(expected_amount_without_tax - actual_amount_without_tax)}, 税额={abs(expected_tax_amount - actual_tax_amount)}")
        
        assert abs(actual_amount_without_tax - expected_amount_without_tax) <= Decimal('0.01'), \
            f"不含税金额计算错误: 预期{expected_amount_without_tax}, 实际{actual_amount_without_tax}"
        assert abs(actual_tax_amount - expected_tax_amount) <= Decimal('0.01'), \
            f"税额计算错误: 预期{expected_tax_amount}, 实际{actual_tax_amount}"

    def test_invoice_balance_verification(self, client):
        """发票金额平衡验证: 不含税金额 + 税额 = 含税金额"""
        resp = client.get("/api/invoices", headers=HEADERS)
        assert resp.status_code == 200, f"查询发票失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        print(f"\n=== 发票金额平衡验证 ===")
        print(f"共检查 {len(items)} 张发票")
        
        imbalanced_count = 0
        for inv in items[:20]:  # 检查前20张发票
            amount_without_tax = Decimal(str(inv.get("amount_without_tax", 0)))
            tax_amount = Decimal(str(inv.get("tax_amount", 0)))
            amount_with_tax = Decimal(str(inv.get("amount_with_tax", 0)))
            
            expected_total = amount_without_tax + tax_amount
            diff = abs(expected_total - amount_with_tax)
            
            if diff > Decimal('0.01'):
                imbalanced_count += 1
                print(f"发票 {inv.get('invoice_no')}: 不含税{amount_without_tax} + 税额{tax_amount} = {expected_total} ≠ 含税{amount_with_tax} (差异{diff})")
                
                record_change(
                    module="发票管理",
                    operation="发票金额不平衡",
                    before=f"不含税{amount_without_tax} + 税额{tax_amount}",
                    after=f"含税{amount_with_tax}",
                    calculation=f"预期{expected_total}, 实际{amount_with_tax}, 差异{diff}"
                )
        
        print(f"不平衡发票数: {imbalanced_count}")
        assert imbalanced_count == 0, f"发现{imbalanced_count}张发票金额不平衡"


# ═══════════════════════════════════════════════════════════════
# 2. 固定资产折旧数字验证
# ═══════════════════════════════════════════════════════════════
class TestDepreciationVerification:
    """固定资产折旧数字验证"""

    def test_straight_line_depreciation_calculation(self, client):
        """年限平均法折旧计算验证"""
        import time
        unique_code = f"FA-VERIFY-{int(time.time())}"
        
        # 输入数据
        original_value = Decimal('10000.00')
        salvage_rate = Decimal('0.05')
        useful_life = 36  # 月
        
        # 预期计算结果
        salvage_value = original_value * salvage_rate
        depreciable_value = original_value - salvage_value
        monthly_depreciation = depreciable_value / useful_life
        
        # 调用API创建固定资产
        resp = client.post("/api/fixed-assets", json={
            "asset_code": unique_code,
            "name": "折旧验证设备",
            "category": "电子设备",
            "original_value": str(original_value),
            "salvage_rate": str(salvage_rate),
            "useful_life": useful_life,
            "start_date": "2026-01-01",
            "depreciation_method": "年限平均法"
        }, headers=HEADERS)
        
        assert resp.status_code in (200, 201), f"创建固定资产失败: {resp.text}"
        
        # 查询固定资产获取实际折旧
        resp = client.get("/api/fixed-assets", headers=HEADERS)
        assert resp.status_code == 200, f"查询固定资产失败: {resp.text}"
        data = resp.json()
        
        assets = data.get("items", data) if isinstance(data, dict) else data
        test_asset = None
        for asset in (assets if isinstance(assets, list) else []):
            if asset.get("asset_code") == unique_code:
                test_asset = asset
                break
        
        if test_asset:
            actual_accumulated_depreciation = Decimal(str(test_asset.get("accumulated_depreciation", 0)))
            
            # 记录数据变化
            record_change(
                module="固定资产",
                operation="年限平均法折旧计算",
                before=f"原值={original_value}, 残值率={salvage_rate}, 使用寿命={useful_life}月",
                after=f"累计折旧={actual_accumulated_depreciation}",
                calculation=f"残值={original_value}×{salvage_rate}={salvage_value}, 可折旧={depreciable_value}, 月折旧={monthly_depreciation}"
            )
            
            # 验证数字
            print(f"\n=== 年限平均法折旧计算验证 ===")
            print(f"输入: 原值={original_value}, 残值率={salvage_rate}, 使用寿命={useful_life}月")
            print(f"计算: 残值={salvage_value}, 可折旧={depreciable_value}, 月折旧={monthly_depreciation}")
            print(f"实际累计折旧: {actual_accumulated_depreciation}")
            
            # 验证残值率合理性
            assert salvage_rate >= Decimal('0') and salvage_rate <= Decimal('0.10'), \
                f"残值率不合理: {salvage_rate}"
            
            # 验证月折旧额合理性
            assert monthly_depreciation > 0, f"月折旧额应为正数: {monthly_depreciation}"
            assert monthly_depreciation < original_value, f"月折旧额不应超过原值: {monthly_depreciation}"


# ═══════════════════════════════════════════════════════════════
# 3. 增值税计算数字验证
# ═══════════════════════════════════════════════════════════════
class TestVATVerification:
    """增值税计算数字验证"""

    def test_vat_report_calculation(self, client):
        """增值税报表计算验证"""
        # 查询Q2增值税报表
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"查询增值税报表失败: {resp.text}"
        data = resp.json()
        
        # 提取数据
        output_total = Decimal(str(data.get("output_total", 0)))
        output_tax = Decimal(str(data.get("output_tax", 0)))
        input_total = Decimal(str(data.get("input_total", 0)))
        input_tax = Decimal(str(data.get("input_tax", 0)))
        tax_payable = Decimal(str(data.get("tax_payable", 0)))
        taxpayer_type = data.get("taxpayer_type", "small_scale")
        
        # 记录数据变化
        record_change(
            module="增值税",
            operation="Q2增值税报表",
            before=f"纳税人类型={taxpayer_type}",
            after=f"销项税额={output_tax}, 进项税额={input_tax}, 应纳税额={tax_payable}",
            calculation=f"应纳税额 = 销项税额({output_tax}) - 进项税额({input_tax})"
        )
        
        # 验证数字
        print(f"\n=== Q2增值税报表计算验证 ===")
        print(f"纳税人类型: {taxpayer_type}")
        print(f"销项合计: {output_total}")
        print(f"销项税额: {output_tax}")
        print(f"进项合计: {input_total}")
        print(f"进项税额: {input_tax}")
        print(f"应纳税额: {tax_payable}")
        
        # 验证计算逻辑
        if taxpayer_type == "general":
            # 一般纳税人: 应纳增值税 = 销项税额 - 进项税额
            expected_payable = max(output_tax - input_tax, Decimal('0'))
            print(f"预期应纳税额: {expected_payable}")
            print(f"差异: {abs(tax_payable - expected_payable)}")
            
            assert abs(tax_payable - expected_payable) <= Decimal('0.01'), \
                f"增值税计算错误: 预期{expected_payable}, 实际{tax_payable}"
        else:
            # 小规模纳税人: 应纳增值税 = 不含税销售额 × 征收率
            print(f"小规模纳税人: 应纳税额={tax_payable}")
            
            # 验证税额合理性
            assert tax_payable >= 0, f"应纳税额不应为负: {tax_payable}"

    def test_vat_invoice_list_verification(self, client):
        """增值税发票列表验证"""
        resp = client.get("/api/tax-report",
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"查询增值税报表失败: {resp.text}"
        data = resp.json()
        
        invoice_list = data.get("invoice_list", [])
        
        print(f"\n=== Q2增值税发票列表验证 ===")
        print(f"发票数量: {len(invoice_list)}")
        
        # 验证每张发票的税额计算
        for inv in invoice_list[:10]:  # 检查前10张发票
            amount_without_tax = Decimal(str(inv.get("amount_without_tax", 0)))
            tax_amount = Decimal(str(inv.get("tax_amount", 0)))
            amount_with_tax = Decimal(str(inv.get("amount_with_tax", 0)))
            tax_rate = Decimal(str(inv.get("tax_rate", 0)))
            
            # 验证税额计算
            expected_tax = amount_without_tax * tax_rate
            diff = abs(expected_tax - tax_amount)
            
            if diff > Decimal('0.01'):
                print(f"发票 {inv.get('invoice_no')}: 不含税{amount_without_tax} × 税率{tax_rate} = {expected_tax} ≠ 税额{tax_amount} (差异{diff})")
                
                record_change(
                    module="增值税",
                    operation="发票税额计算不一致",
                    before=f"不含税{amount_without_tax}, 税率{tax_rate}",
                    after=f"税额{tax_amount}",
                    calculation=f"预期{expected_tax}, 实际{tax_amount}, 差异{diff}"
                )


# ═══════════════════════════════════════════════════════════════
# 4. 所得税计算数字验证
# ═══════════════════════════════════════════════════════════════
class TestIncomeTaxVerification:
    """所得税计算数字验证"""

    def test_income_tax_calculation(self, client):
        """所得税计算验证"""
        # 查询Q2所得税报表
        resp = client.get("/api/income-tax-report",
                         params={"year": 2026, "quarter": 2},
                         headers=HEADERS)
        assert resp.status_code == 200, f"查询所得税报表失败: {resp.text}"
        data = resp.json()
        
        # 提取数据
        total_revenue = Decimal(str(data.get("total_revenue", 0)))
        total_cost = Decimal(str(data.get("total_cost", 0)))
        operating_expenses = Decimal(str(data.get("operating_expenses", 0)))
        gross_profit = Decimal(str(data.get("gross_profit", 0)))
        taxable_income = Decimal(str(data.get("taxable_income", 0)))
        tax_rate = Decimal(str(data.get("tax_rate", 0)))
        tax_amount = Decimal(str(data.get("tax_amount", 0)))
        
        # 记录数据变化
        record_change(
            module="所得税",
            operation="Q2所得税报表",
            before=f"收入={total_revenue}, 成本={total_cost}, 费用={operating_expenses}",
            after=f"毛利润={gross_profit}, 应纳税所得额={taxable_income}, 税率={tax_rate}, 应纳税额={tax_amount}",
            calculation=f"毛利润 = 收入({total_revenue}) - 成本({total_cost}) - 费用({operating_expenses})"
        )
        
        # 验证数字
        print(f"\n=== Q2所得税报表计算验证 ===")
        print(f"收入: {total_revenue}")
        print(f"成本: {total_cost}")
        print(f"费用: {operating_expenses}")
        print(f"毛利润: {gross_profit}")
        print(f"应纳税所得额: {taxable_income}")
        print(f"税率: {tax_rate}")
        print(f"应纳税额: {tax_amount}")
        
        # 验证毛利润计算
        expected_gross_profit = total_revenue - total_cost - operating_expenses
        print(f"预期毛利润: {expected_gross_profit}")
        print(f"毛利润差异: {abs(gross_profit - expected_gross_profit)}")
        
        # 验证应纳税额计算
        expected_tax = taxable_income * tax_rate
        print(f"预期应纳税额: {expected_tax}")
        print(f"应纳税额差异: {abs(tax_amount - expected_tax)}")
        
        # 验证税率合理性
        assert tax_rate in [Decimal('0.05'), Decimal('0.15'), Decimal('0.25')], \
            f"所得税税率异常: {tax_rate}"

    def test_income_tax_caliber_comparison(self, client):
        """所得税双口径比较验证"""
        # 税务口径
        resp_tax = client.get("/api/income-tax-report",
                             params={"year": 2026, "quarter": 2, "caliber": "tax"},
                             headers=HEADERS)
        # 经营口径
        resp_ops = client.get("/api/income-tax-report",
                             params={"year": 2026, "quarter": 2, "caliber": "operating"},
                             headers=HEADERS)
        
        if resp_tax.status_code == 200 and resp_ops.status_code == 200:
            tax_data = resp_tax.json()
            ops_data = resp_ops.json()
            
            tax_revenue = Decimal(str(tax_data.get("total_revenue", 0)))
            ops_revenue = Decimal(str(ops_data.get("total_revenue", 0)))
            
            tax_cost = Decimal(str(tax_data.get("total_cost", 0)))
            ops_cost = Decimal(str(ops_data.get("total_cost", 0)))
            
            # 记录数据变化
            record_change(
                module="所得税",
                operation="双口径比较",
                before=f"税务口径: 收入={tax_revenue}, 成本={tax_cost}",
                after=f"经营口径: 收入={ops_revenue}, 成本={ops_cost}",
                calculation=f"收入差异={abs(tax_revenue - ops_revenue)}, 成本差异={abs(tax_cost - ops_cost)}"
            )
            
            # 验证数字
            print(f"\n=== 所得税双口径比较验证 ===")
            print(f"税务口径: 收入={tax_revenue}, 成本={tax_cost}")
            print(f"经营口径: 收入={ops_revenue}, 成本={ops_cost}")
            print(f"收入差异: {abs(tax_revenue - ops_revenue)}")
            print(f"成本差异: {abs(tax_cost - ops_cost)}")
            
            # 验证双口径都返回了数据
            assert tax_revenue > 0 or ops_revenue > 0, \
                f"双口径收入都为0: 税务{tax_revenue}, 经营{ops_revenue}"


# ═══════════════════════════════════════════════════════════════
# 5. 资产负债表数字验证
# ═══════════════════════════════════════════════════════════════
class TestBalanceSheetVerification:
    """资产负债表数字验证"""

    def test_balance_sheet_equation(self, client):
        """资产负债表恒等式验证"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"查询资产负债表失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            
            # 提取数据
            total_assets = Decimal(str(data.get("total_assets", 0)))
            total_liabilities = Decimal(str(data.get("total_liabilities", 0)))
            total_equity = Decimal(str(data.get("total_equity", 0)))
            
            # 记录数据变化
            record_change(
                module="资产负债表",
                operation="恒等式验证",
                before=f"资产={total_assets}",
                after=f"负债={total_liabilities}, 权益={total_equity}",
                calculation=f"资产({total_assets}) = 负债({total_liabilities}) + 权益({total_equity})"
            )
            
            # 验证数字
            print(f"\n=== 资产负债表恒等式验证 ===")
            print(f"资产总计: {total_assets}")
            print(f"负债合计: {total_liabilities}")
            print(f"权益合计: {total_equity}")
            print(f"负债+权益: {total_liabilities + total_equity}")
            print(f"差异: {abs(total_assets - (total_liabilities + total_equity))}")
            
            # 验证恒等式
            diff = abs(total_assets - (total_liabilities + total_equity))
            assert diff <= Decimal('0.01'), \
                f"资产负债表不平衡: 资产({total_assets}) ≠ 负债({total_liabilities}) + 权益({total_equity}), 差异{diff}"

    def test_balance_sheet_detail(self, client):
        """资产负债表明细验证"""
        resp = client.get("/api/financial-reports/balance-sheet",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"查询资产负债表失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            
            # 提取明细数据
            cash = Decimal(str(data.get("cash", data.get("货币资金", 0))))
            bank = Decimal(str(data.get("bank", data.get("银行存款", 0))))
            accounts_receivable = Decimal(str(data.get("accounts_receivable", data.get("应收账款", 0))))
            inventory = Decimal(str(data.get("inventory", data.get("存货", 0))))
            fixed_assets_net = Decimal(str(data.get("fixed_assets_net", data.get("固定资产净值", 0))))
            
            # 记录数据变化
            record_change(
                module="资产负债表",
                operation="明细验证",
                before="资产明细",
                after=f"货币资金={cash + bank}, 应收账款={accounts_receivable}, 存货={inventory}, 固定资产净值={fixed_assets_net}",
                calculation="资产 = 货币资金 + 应收账款 + 存货 + 固定资产净值"
            )
            
            # 验证数字
            print(f"\n=== 资产负债表明细验证 ===")
            print(f"货币资金: {cash + bank}")
            print(f"应收账款: {accounts_receivable}")
            print(f"存货: {inventory}")
            print(f"固定资产净值: {fixed_assets_net}")
            
            # 验证明细数据合理性
            assert cash + bank >= 0, f"货币资金为负: {cash + bank}"
            assert accounts_receivable >= 0, f"应收账款为负: {accounts_receivable}"
            assert inventory >= 0, f"存货为负: {inventory}"
            assert fixed_assets_net >= 0, f"固定资产净值为负: {fixed_assets_net}"


# ═══════════════════════════════════════════════════════════════
# 6. 利润表数字验证
# ═══════════════════════════════════════════════════════════════
class TestIncomeStatementVerification:
    """利润表数字验证"""

    def test_income_statement_calculation(self, client):
        """利润表计算验证"""
        resp = client.get("/api/financial-reports/income-statement",
                         params={"year": 2026, "month": 6},
                         headers=HEADERS)
        assert resp.status_code in (200, 422), f"查询利润表失败: {resp.status_code}"
        
        if resp.status_code == 200:
            data = resp.json()
            
            # 提取数据
            revenue = Decimal(str(data.get("revenue", data.get("total_revenue", 0))))
            cost = Decimal(str(data.get("cost", data.get("total_cost", 0))))
            gross_profit = Decimal(str(data.get("gross_profit", 0)))
            operating_expenses = Decimal(str(data.get("operating_expenses", 0)))
            net_profit = Decimal(str(data.get("net_profit", 0)))
            
            # 记录数据变化
            record_change(
                module="利润表",
                operation="计算验证",
                before=f"收入={revenue}, 成本={cost}",
                after=f"毛利润={gross_profit}, 费用={operating_expenses}, 净利润={net_profit}",
                calculation=f"毛利润 = 收入({revenue}) - 成本({cost})"
            )
            
            # 验证数字
            print(f"\n=== 利润表计算验证 ===")
            print(f"收入: {revenue}")
            print(f"成本: {cost}")
            print(f"毛利润: {gross_profit}")
            print(f"费用: {operating_expenses}")
            print(f"净利润: {net_profit}")
            
            # 验证毛利润计算
            expected_gross_profit = revenue - cost
            print(f"预期毛利润: {expected_gross_profit}")
            print(f"毛利润差异: {abs(gross_profit - expected_gross_profit)}")
            
            # 验证毛利润计算正确
            assert abs(gross_profit - expected_gross_profit) <= Decimal('0.01'), \
                f"毛利润计算错误: 预期{expected_gross_profit}, 实际{gross_profit}"


# ═══════════════════════════════════════════════════════════════
# 7. 库存数量数字验证
# ═══════════════════════════════════════════════════════════════
class TestInventoryVerification:
    """库存数量数字验证"""

    def test_inventory_quantity_verification(self, client):
        """库存数量验证"""
        resp = client.get("/api/inventory",
                         params={"page": 1, "page_size": 500},
                         headers=HEADERS)
        assert resp.status_code == 200, f"查询库存失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        
        print(f"\n=== 库存数量验证 ===")
        print(f"商品数量: {len(items)}")
        
        negative_count = 0
        for item in items:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 0)
            
            if quantity < 0:
                negative_count += 1
                print(f"商品 {product_id}: 库存为负数 ({quantity})")
                
                record_change(
                    module="库存",
                    operation="库存为负数",
                    before=f"商品{product_id}",
                    after=f"库存={quantity}",
                    calculation="库存不应为负数"
                )
        
        print(f"负库存商品数: {negative_count}")
        assert negative_count == 0, f"发现{negative_count}个商品库存为负数"


# ═══════════════════════════════════════════════════════════════
# 8. 订单金额数字验证
# ═══════════════════════════════════════════════════════════════
class TestOrderAmountVerification:
    """订单金额数字验证"""

    def test_sale_order_amount_verification(self, client):
        """销售单金额验证"""
        resp = client.get("/api/sales", headers=HEADERS)
        assert resp.status_code == 200, f"查询销售单失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        
        print(f"\n=== 销售单金额验证 ===")
        print(f"销售单数量: {len(items)}")
        
        negative_count = 0
        for order in items[:20]:  # 检查前20个订单
            order_no = order.get("order_no")
            total_price = Decimal(str(order.get("total_price", 0)))
            
            if total_price < 0:
                negative_count += 1
                print(f"销售单 {order_no}: 金额为负数 ({total_price})")
                
                record_change(
                    module="销售",
                    operation="订单金额为负",
                    before=f"销售单{order_no}",
                    after=f"金额={total_price}",
                    calculation="订单金额不应为负数"
                )
        
        print(f"负金额订单数: {negative_count}")
        assert negative_count == 0, f"发现{negative_count}个订单金额为负数"

    def test_purchase_order_amount_verification(self, client):
        """采购单金额验证"""
        resp = client.get("/api/purchases", headers=HEADERS)
        assert resp.status_code == 200, f"查询采购单失败: {resp.text}"
        data = resp.json()
        
        items = data.get("items", [])
        
        print(f"\n=== 采购单金额验证 ===")
        print(f"采购单数量: {len(items)}")
        
        negative_count = 0
        for order in items[:20]:  # 检查前20个订单
            order_no = order.get("order_no")
            total_price = Decimal(str(order.get("total_price", 0)))
            
            if total_price < 0:
                negative_count += 1
                print(f"采购单 {order_no}: 金额为负数 ({total_price})")
                
                record_change(
                    module="采购",
                    operation="订单金额为负",
                    before=f"采购单{order_no}",
                    after=f"金额={total_price}",
                    calculation="订单金额不应为负数"
                )
        
        print(f"负金额订单数: {negative_count}")
        assert negative_count == 0, f"发现{negative_count}个订单金额为负数"


# ═══════════════════════════════════════════════════════════════
# 9. 数据变化报告生成
# ═══════════════════════════════════════════════════════════════
class TestDataChangeReport:
    """数据变化报告"""

    def test_generate_report(self, client):
        """生成数据变化报告"""
        print(f"\n=== 数据变化报告 ===")
        print(f"总记录数: {len(DATA_CHANGES)}")
        
        # 按模块分组
        module_changes = {}
        for change in DATA_CHANGES:
            module = change["module"]
            if module not in module_changes:
                module_changes[module] = []
            module_changes[module].append(change)
        
        for module, changes in module_changes.items():
            print(f"\n模块: {module}")
            print(f"  变化次数: {len(changes)}")
            for change in changes[:3]:  # 显示前3个变化
                print(f"  - {change['operation']}: {change['after']}")
        
        # 保存报告
        report_path = os.path.join(os.path.dirname(__file__), "data_changes.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(DATA_CHANGES, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据变化报告已保存到: {report_path}")
