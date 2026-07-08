"""端到端验证：跑通 20 个业务模板

测试目标：
1. 每个模板的接口路径、参数名都和后端真实接口对得上
2. AI 录账流程能跑通

覆盖模板：
01 init / 02-05 基础数据 / 06 采购 / 07 销售 / 08 费用 / 09 垫付
10 固定资产 / 11 收款 / 12 付款 / 13 银行分录
14 银行对账 / 15 月结 / 16-17 退货 / 18 红冲 / 19-20 报表税务
"""
import sys
import time
import os

_DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
_TEMPLATES_DIR = os.path.join(_DOCS_DIR, "templates")
sys.path.insert(0, _DOCS_DIR)
sys.path.insert(0, _TEMPLATES_DIR)
from _client import (post, get, put, extract_id, set_account, ping,
                     post_pending, confirm, cancel_pending,
                     is_ok, extract_data, format_for_user)

# 唯一标识：每次运行用不同 code，避免账本重复创建失败
RUN_TAG = f"v{int(time.time())}"

import importlib
t02 = importlib.import_module("02_products")
t03 = importlib.import_module("03_suppliers")
t04 = importlib.import_module("04_customers")
t05 = importlib.import_module("05_bank_accounts")
t06 = importlib.import_module("06_purchases")
t07 = importlib.import_module("07_sales")
t08 = importlib.import_module("08_expenses")
t09 = importlib.import_module("09_personal_advances")
t10 = importlib.import_module("10_fixed_assets")
t11 = importlib.import_module("11_receipts")
t12 = importlib.import_module("12_payments")
t13 = importlib.import_module("13_bank_entries")
t14 = importlib.import_module("14_bank_reconcile")
t15 = importlib.import_module("15_month_close")
t16 = importlib.import_module("16_sale_returns")
t17 = importlib.import_module("17_purchase_returns")
t18 = importlib.import_module("18_other_reversals")
t19 = importlib.import_module("19_reports")
t20 = importlib.import_module("20_tax")

CHECKS = []
def check(name, cond, detail=""):
    CHECKS.append((name, cond, detail))
    mark = "✅" if cond else "❌"
    print(f"   {mark} {name}{' — ' + detail if detail and not cond else ''}")


print("=== 0. 检查后端 ===")
print(f"ping: {ping()}")

print("\n=== 01 初始化（建账本+期初）===")
get("/api/bootstrap/init")
acct = post("/api/accounts", {
    "name": "AI模板验证公司",
    "type": "company",
    "taxpayer_type": "general",
    "code": RUN_TAG,
})
ACCT_ID = extract_id(acct)
if ACCT_ID:
    set_account(ACCT_ID)
print(f"   账本 ID: {ACCT_ID}")
if not ACCT_ID:
    print(f"   ❌ 建账本失败，响应: {acct}")
    sys.exit(1)

ob = post("/api/opening-balances", {
    "date": "2026-06-01",
    "cash_balance": 50000,
    "bank_balance": 500000,
    "paid_in_capital": 550000,
})
check("01 init 建账本+期初", ACCT_ID > 0 and is_ok(ob),
      f"acct={acct}, ob={format_for_user(ob, '期初')[:120]}")


print("\n=== 02 商品（含服务类 track_inventory=False）===")
p_real = t02.create_product(name="实物商品A", sku=f"REAL001_{RUN_TAG}", unit="个",
                             purchase_price=1000, sale_price=1500, initial_stock=100)
REAL_ID = extract_id(p_real)
check("02 create_product 实物", REAL_ID > 0)

p_svc = t02.create_service_product(name="维修服务", sku=f"SVC001_{RUN_TAG}", sale_price=500)
SVC_ID = extract_id(p_svc)
svc_data = extract_data(p_svc) or {}
check("02 create_service_product", SVC_ID > 0)
check("02 服务商品 track_inventory=False",
      svc_data.get("track_inventory") is False,
      f"实际: {svc_data.get('track_inventory')}")

def is_list_ok(resp):
    """list 端点直接返回 dict（无 entity 嵌套），用 total 字段判断。"""
    if not isinstance(resp, dict):
        return False
    return "total" in resp or "items" in resp

products = t02.list_products(category="服务")
check("02 list_products by category",
      is_list_ok(products) and products.get("total", 0) >= 1)


print("\n=== 03 供应商 ===")
sup = t03.create_supplier(name="供应商甲", contact_person="张三", phone="13800000000")
SUP_ID = extract_id(sup)
check("03 create_supplier", SUP_ID > 0)


print("\n=== 04 客户 ===")
cus = t04.create_customer(name="客户乙", contact_person="李四", phone="13900000000")
CUS_ID = extract_id(cus)
check("04 create_customer", CUS_ID > 0)


print("\n=== 05 银行账户 ===")
bank = t05.create_bank_account(bank_name="工商银行", account_number=f"6222{RUN_TAG}")
BANK_ID = extract_id(bank)
check("05 create_bank_account", BANK_ID > 0)


print("\n=== 06 采购（进项发票 auto_create）===")
inv_in = t06.create_input_invoice_quick(
    invoice_no=f"IN20260615001_{RUN_TAG}",
    invoice_type="special",
    tax_rate=0.13,
    amount_with_tax=11300.00,
    counterparty_name="供应商甲",
    seller_name="供应商甲",
    buyer_name="本公司",
    issue_date="2026-06-15",
    items=[{"product_id": REAL_ID, "quantity": 10, "unit_price": 1000.00, "tax_rate": 0.13}],
    purchase_order_action="auto_create",
)
INV_IN_ID = extract_id(inv_in)
print(f"   进项发票响应: {inv_in}")
check("06 create_input_invoice_quick auto_create", INV_IN_ID and INV_IN_ID > 0)

if INV_IN_ID:
    cer = t06.certify_invoice(INV_IN_ID)
    check("06 certify_invoice", is_ok(cer))

purchases = t06.list_purchase_orders(start_date="2026-06-01", end_date="2026-06-30")
check("06 list_purchase_orders", is_list_ok(purchases))

inv_list = t06.list_invoices(direction="in", invoice_type="special", certification_status="certified")
check("06 list_invoices 筛选", is_list_ok(inv_list))


print("\n=== 07 销售（销项发票 auto_create + 服务商品）===")
inv_out = t07.create_output_invoice_quick(
    invoice_no=f"OUT20260620001_{RUN_TAG}",
    invoice_type="ordinary",
    tax_rate=0.06,
    amount_with_tax=2120.00,
    counterparty_name="客户乙",
    seller_name="本公司",
    buyer_name="客户乙",
    issue_date="2026-06-20",
    items=[{"product_id": SVC_ID, "quantity": 4, "unit_price": 500.00, "tax_rate": 0.06}],
    sale_order_action="auto_create",
)
INV_OUT_ID = extract_id(inv_out)
print(f"   销项发票响应: {inv_out}")
check("07 销项发票+服务商品 auto_create", INV_OUT_ID and INV_OUT_ID > 0,
      f"返回: {format_for_user(inv_out, '销项发票')[:200]}")

if INV_OUT_ID:
    sales = t07.list_sale_orders(start_date="2026-06-01", end_date="2026-06-30")
    check("07 list_sale_orders", is_list_ok(sales))


print("\n=== 08 费用（含 pay_expense）===")
exp = t08.create_expense("房租", 5000, "2026-06-15", "管理费用",
                          description="2026年6月房租，付房东王老板")
EXP_ID = extract_id(exp)
check("08 create_expense", EXP_ID > 0)

if EXP_ID:
    pay = t08.pay_expense(EXP_ID, 5000, "2026-06-15", BANK_ID)
    check("08 pay_expense", is_ok(pay))

exp_list = t08.list_expenses(category="房租", year=2026)
check("08 list_expenses 筛选", is_list_ok(exp_list))


print("\n=== 09 个人垫付 ===")
adv = t09.create_personal_advance(
    advancer_name="老板张三", amount=2000, advance_date="2026-06-08",
    debit_account_code="6601", description="垫付办公设备款",
)
ADV_ID = extract_id(adv)
check("09 create_personal_advance", ADV_ID > 0)

if ADV_ID:
    repay = t09.repay_personal_advance(ADV_ID, 1000, "2026-06-25", BANK_ID)
    check("09 repay_personal_advance", is_ok(repay))


print("\n=== 10 固定资产（发票+资产原子创建）===")
fa = t10.create_fixed_asset_via_invoice(
    invoice_no=f"IN20260610001_{RUN_TAG}",
    amount_with_tax=7800.00,
    tax_rate=0.13,
    counterparty_name="供应商甲",
    seller_name="供应商甲",
    buyer_name="本公司",
    issue_date="2026-06-10",
    asset_code=f"FA-2026-{RUN_TAG}",
    asset_name="惠普打印机",
    useful_life=60,
    start_date="2026-06-10",
    invoice_type="special",
    category="office_equipment",
)
FA_ID = extract_data(fa).get("fixed_asset", {}).get("id") or extract_id(fa)
print(f"   固定资产响应: {fa}")
check("10 create_fixed_asset_via_invoice", FA_ID and FA_ID > 0,
      f"返回: {format_for_user(fa, '固定资产')[:200]}")

fa_list = t10.list_fixed_assets(status="在用")
check("10 list_fixed_assets", is_list_ok(fa_list) or isinstance(fa_list, list))

# dispose 三步走（disposal_price=0 不产生银行流水，避免影响后续对账）
if FA_ID:
    pending = t10.dispose_fixed_asset_pending(
        asset_id=FA_ID, disposal_date="2026-06-28", disposal_price=0,
    )
    token = pending.get("confirm_token")
    if token:
        print(f"   系统提示：{pending.get('message')}")
        result = confirm(token)
        check("10 dispose 三步走确认", is_ok(result),
              f"返回: {format_for_user(result, '处置')[:200]}")
    else:
        check("10 dispose pending", False, f"未拿到 token: {pending}")


print("\n=== 11 收款（先建销售单再收款）===")
so_for_rc = t07.create_sale_order(
    customer_id=CUS_ID,
    items=[{"product_id": REAL_ID, "quantity": 2, "unit_price": 1300.00}],
    sale_date="2026-06-22",
    tax_rate=0.13,
)
SO_RC_ID = extract_id(so_for_rc)
check("11 前置：create_sale_order", SO_RC_ID > 0)

if SO_RC_ID:
    rc = t11.create_receipt(
        receipt_type="sale",
        related_entity_type="sale_order",
        related_entity_id=SO_RC_ID,
        amount=2938.00,
        receipt_date="2026-06-22T10:00:00",
        bank_account_id=BANK_ID,
    )
    check("11 create_receipt", is_ok(rc))


print("\n=== 12 付款（付采购款）===")
po_for_pay = t06.create_purchase_order(
    supplier_id=SUP_ID,
    items=[{"product_id": REAL_ID, "quantity": 5, "unit_price": 1000.00}],
    purchase_date="2026-06-25",
    tax_rate=0.13,
)
PO_PAY_ID = extract_id(po_for_pay)
check("12 前置：create_purchase_order", PO_PAY_ID > 0)

if PO_PAY_ID:
    pay_po = t12.pay_purchase(PO_PAY_ID, 5650.00, "2026-06-25", BANK_ID)
    check("12 pay_purchase", is_ok(pay_po))


print("\n=== 13 银行分录（手续费/利息）===")
be_fee = t13.create_bank_entry("bank_fee", 50, "2026-06-28")
check("13 create_bank_entry bank_fee", is_ok(be_fee))

be_int = t13.create_bank_entry("interest_income", 120, "2026-06-28")
check("13 create_bank_entry interest_income", is_ok(be_int))


print("\n=== 14 银行对账（对账单 → 调节表 → 确认）===")
bank_end = 500000 + 2938 + 120 - 5650 - 5000 - 1000 - 50
stmt = t14.create_bank_statement(
    period_start="2026-06-01", period_end="2026-06-30",
    opening_balance=500000, closing_balance=bank_end,
    lines=[
        {"transaction_date": "2026-06-22", "amount": 2938, "description": "收款"},
        {"transaction_date": "2026-06-25", "amount": -5650, "description": "付采购"},
        {"transaction_date": "2026-06-25", "amount": -5000, "description": "付房租"},
        {"transaction_date": "2026-06-25", "amount": -1000, "description": "还垫付"},
        {"transaction_date": "2026-06-28", "amount": -50, "description": "手续费"},
        {"transaction_date": "2026-06-28", "amount": 120, "description": "利息"},
    ],
)
check("14 create_bank_statement", is_ok(stmt))

recon = t14.run_bank_reconcile(period="2026-06")
check("14 run_bank_reconcile", is_ok(recon))

rec_data = t14.get_bank_reconciliation(period="2026-06")
REC_ID = None
if isinstance(rec_data, list) and rec_data:
    REC_ID = rec_data[0].get("id")
elif isinstance(rec_data, dict):
    REC_ID = rec_data.get("id")
    if not REC_ID:
        items_r = rec_data.get("items", [])
        if items_r:
            REC_ID = items_r[0].get("id")
check("14 get_bank_reconciliation", REC_ID is not None,
      f"返回: {format_for_user(rec_data, '调节表')[:200]}")

if REC_ID:
    conf = t14.confirm_bank_reconciliation(REC_ID)
    check("14 confirm_bank_reconciliation", is_ok(conf))


print("\n=== 16 销售退货（危险操作三步走）===")
so_for_ret = t07.create_sale_order(
    customer_id=CUS_ID,
    items=[{"product_id": REAL_ID, "quantity": 3, "unit_price": 1300.00}],
    sale_date="2026-06-26",
    tax_rate=0.13,
)
SO_RET_ID = extract_id(so_for_ret)
if SO_RET_ID:
    pending = t16.sale_return_pending(
        sale_order_id=SO_RET_ID,
        return_date="2026-06-27",
        items=[{"product_id": REAL_ID, "quantity": 1}],
        reason="客户退回 1 件次品",
    )
    token = pending.get("confirm_token")
    if token:
        print(f"   系统提示：{pending.get('message')}")
        result = confirm(token)
        check("16 sale_return 三步走确认", is_ok(result))
    else:
        check("16 sale_return pending", False, f"未拿到 token: {pending}")


print("\n=== 17 采购退货（危险操作三步走）===")
# 先建一个新采购单入库，确保有足够库存可退
po_for_ret = t06.create_purchase_order(
    supplier_id=SUP_ID,
    items=[{"product_id": REAL_ID, "quantity": 50, "unit_price": 1000.00}],
    purchase_date="2026-06-26",
    tax_rate=0.13,
)
PO_RET_ID = extract_id(po_for_ret)
check("17 前置：create_purchase_order", PO_RET_ID > 0)

if PO_RET_ID:
    inv_for_ret = t06.create_input_invoice_quick(
        invoice_no=f"IN20260626001_{RUN_TAG}",
        invoice_type="special",
        tax_rate=0.13,
        amount_with_tax=56500.00,
        counterparty_name="供应商甲",
        seller_name="供应商甲",
        buyer_name="本公司",
        issue_date="2026-06-26",
        items=[{"product_id": REAL_ID, "quantity": 50, "unit_price": 1000.00, "tax_rate": 0.13}],
        purchase_order_action="link_existing",
        related_order_id=PO_RET_ID,
    )
    check("17 前置：为采购单录入进项发票", is_ok(inv_for_ret))

    pending = t17.purchase_return_pending(
        purchase_order_id=PO_RET_ID,
        return_date="2026-06-27",
        items=[{"product_id": REAL_ID, "quantity": 1}],
        reason="退回 1 件次品",
    )
    token = pending.get("confirm_token")
    if token:
        print(f"   系统提示：{pending.get('message')}")
        result = confirm(token)
        check("17 purchase_return 三步走确认", is_ok(result),
              f"返回: {str(result)[:200]}")
    else:
        check("17 purchase_return pending", False, f"未拿到 token: {pending}")


print("\n=== 18 其他红冲（费用冲红）===")
exp_for_rev = t08.create_expense("办公用品", 100, "2026-06-28", "管理费用",
                                  description="待冲红的测试费用")
EXP_REV_ID = extract_id(exp_for_rev)
if EXP_REV_ID:
    pending = t18.reverse_expense_pending(EXP_REV_ID)
    token = pending.get("confirm_token")
    if token:
        print(f"   系统提示：{pending.get('message')}")
        result = confirm(token)
        check("18 reverse_expense 三步走确认", is_ok(result))
    else:
        check("18 reverse_expense pending", False, f"未拿到 token: {pending}")


print("\n=== 15 月结 ===")
if REC_ID:
    mc = t15.run_month_close(period="2026-06")
    check("15 run_month_close", is_ok(mc) or "结账" in str(mc),
          f"返回: {format_for_user(mc, '月结')[:200]}")


print("\n=== 19 报表 ===")
bs = t19.get_balance_sheet("2026-06-30")
print(f"   BS 原始响应: {bs}")
bs_data = extract_data(bs) or {}
print(f"   BS 解析后: {bs_data}")

# --- L3 诊断：关键科目余额 ---
print("\n   [L3 关键科目余额]")
chart = get("/api/finance/accounts/chart")
key_codes = ["1001", "1002", "1122", "1405", "1601", "1602", "2202", "222101", "222102", "222103", "4103", "4104", "6001", "6401", "6601", "6602", "6603", "6701"]
for item in chart.get("items", []):
    if item.get("code") in key_codes:
        print(f"      {item['code']} {item['name']}: {item.get('balance')}")

diff = bs_data.get("diff")
if diff is None and "total_assets" in bs_data and "total_liabilities_and_equity" in bs_data:
    diff = round(bs_data["total_assets"] - bs_data["total_liabilities_and_equity"], 2)
check("19 BS diff=0", diff == 0, f"diff={diff}")

trial = t19.get_trial_balance("2026-06-30")
trial_data = extract_data(trial) or {}
check("19 试算 balanced=True", trial_data.get("balanced") is True,
      f"balanced={trial_data.get('balanced')}")


print("\n=== 20 税务 ===")
tax_q = t20.get_quarterly_tax_report(year=2026, quarter=2)
check("20 季度增值税报表", isinstance(tax_q, dict) and "output_tax" in tax_q,
      f"返回: {str(tax_q)[:200]}")

tax_m = t20.get_monthly_tax_report(year=2026, month=6)
check("20 月度增值税报表", isinstance(tax_m, dict) and "output_tax" in tax_m,
      f"返回: {str(tax_m)[:200]}")

tax_check = t20.check_tax_consistency(
    period="2026-06", sales=2000, output_vat=120, input_vat=1300,
    unpaid_vat=0, income_tax=0, surcharge=0, vat_payable=0, gross_profit=2000,
)
check("20 税务核对", isinstance(tax_check, dict),
      f"返回: {str(tax_check)[:200]}")


print("\n" + "=" * 60)
passed = sum(1 for _, c, _ in CHECKS if c)
total = len(CHECKS)
failed = total - passed
print(f"汇总：{passed}/{total} 通过，{failed} 失败")
if failed:
    print("\n失败项：")
    for name, c, detail in CHECKS:
        if not c:
            print(f"   ❌ {name} — {detail}")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
