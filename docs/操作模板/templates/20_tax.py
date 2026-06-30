"""模板 20：增值税报表与税务核对

业务流程：查询季度/月度增值税报表，执行税务核对验证一致性
"""
import sys
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import get


def get_quarterly_tax_report(year, quarter):
    """查询季度增值税报表。走 GET /api/tax-report?year=&quarter=

    参数：
        year: 年份（如 2026）
        quarter: 季度（1-4）

    返回字段：
        output_total: 销项不含税合计
        output_tax: 销项税额（含红字发票负数冲减）
        input_total: 进项不含税合计
        input_tax: 进项税额（一般纳税人仅算已认证专票）
        tax_payable: 应纳税额（= 销项 - 进项，可为负=留抵）
        invoice_list: 期间内所有发票明细
    """
    return get(f"/api/tax-report?year={year}&quarter={quarter}")


def get_monthly_tax_report(year, month):
    """查询月度增值税报表。走 GET /api/tax-report/monthly?year=&month=

    参数：
        year: 年份
        month: 月份（1-12）
    """
    return get(f"/api/tax-report/monthly?year={year}&month={month}")


def check_tax_consistency(period, sales, output_vat, input_vat,
                          unpaid_vat, income_tax, surcharge,
                          vat_payable, gross_profit):
    """执行税务核对：验证账本数据与预期一致。

    走 GET /api/tax/check?period=&sales=&output_vat=&...

    AI 用法：先按业务预期算出各字段值，传入让系统核对实际账本是否符合。

    参数：
        period: 核对期间 "YYYY-MM"（如 "2026-06"）
        sales: 预期营业收入
        output_vat: 预期销项税额
        input_vat: 预期进项税额
        unpaid_vat: 预期未交增值税（= max(销项-进项, 0)，留抵时为 0）
        income_tax: 预期所得税
        surcharge: 预期附加税合计
        vat_payable: 预期应交增值税（同 unpaid_vat）
        gross_profit: 预期利润总额

    返回字段：
        all_passed: True 表示全部核对通过
        checks: 各项明细 [{"name":..., "passed":bool, ...]
    """
    return get(
        f"/api/tax/check?period={period}"
        f"&sales={sales}&output_vat={output_vat}&input_vat={input_vat}"
        f"&unpaid_vat={unpaid_vat}&income_tax={income_tax}&surcharge={surcharge}"
        f"&vat_payable={vat_payable}&gross_profit={gross_profit}"
    )


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)

    print("1. 查询 Q2 增值税报表")
    tax = get_quarterly_tax_report(year=2026, quarter=2)
    print(f"   销项税额：{tax.get('output_tax')}")
    print(f"   进项税额：{tax.get('input_tax')}")
    print(f"   应纳税额：{tax.get('tax_payable')}（负数=留抵）")

    print("\n2. 执行税务核对")
    check = check_tax_consistency(
        period="2026-06",
        sales=198000,
        output_vat=25740,
        input_vat=26780,
        unpaid_vat=0,
        income_tax=3767.50,
        surcharge=0,
        vat_payable=0,
        gross_profit=14950,
    )
    print(f"   all_passed={check.get('all_passed')}")
    if not check.get("all_passed"):
        print(f"   详情：{check}")
