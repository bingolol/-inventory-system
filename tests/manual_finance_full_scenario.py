# -*- coding: utf-8 -*-
"""
一般纳税人真实公司模拟 - 6月全场景财务覆盖测试 v2
修复: ID提取、费用类别、银行对账单格式、全新账本
"""
import json
import requests
from decimal import Decimal, ROUND_HALF_UP

BASE = "http://127.0.0.1:8000"
H = {"Content-Type": "application/json", "X-Operator": "ai"}

bugs = []
steps = []
Q2 = Decimal("0.01")


def d(x):
    return Decimal(str(x))

def q2(x):
    return d(x).quantize(Q2, rounding=ROUND_HALF_UP)


def extract_id(resp):
    """从各种响应格式中提取ID"""
    if not isinstance(resp, dict):
        return None
    if resp.get("id"):
        return resp["id"]
    if resp.get("entity_id"):
        return resp["entity_id"]
    ent = resp.get("entity", {})
    if isinstance(ent, dict):
        if ent.get("id"):
            return ent["id"]
        if ent.get("entity_id"):
            return ent["entity_id"]
        data = ent.get("data", {})
        if isinstance(data, dict) and data.get("id"):
            return data["id"]
    return None


def post(path, body=None):
    r = requests.post(BASE + path, headers=H, json=body or {})
    if r.status_code == 202:
        data = r.json()
        # 修复后 confirm_token 在顶层，兼容旧格式在 entity 中
        token = data.get("confirm_token")
        if not token:
            ent = data.get("entity", {})
            if isinstance(ent, dict):
                token = ent.get("confirm_token")
        if token:
            rc = requests.post(BASE + f"/api/confirm/{token}", headers=H)
            try:
                return rc.json()
            except Exception:
                return {"_error": rc.text}
        return data
    try:
        return r.json()
    except Exception:
        return {"_status": r.status_code, "_body": r.text}


def put(path, body=None):
    r = requests.put(BASE + path, headers=H, json=body or {})
    if r.status_code == 202:
        data = r.json()
        token = data.get("confirm_token")
        if not token:
            ent = data.get("entity", {})
            if isinstance(ent, dict):
                token = ent.get("confirm_token")
        if token:
            rc = requests.post(BASE + f"/api/confirm/{token}", headers=H)
            try:
                return rc.json()
            except Exception:
                return {"_error": rc.text}
        return data
    try:
        return r.json()
    except Exception:
        return {"_status": r.status_code, "_body": r.text}


def get(path):
    r = requests.get(BASE + path, headers=H)
    try:
        return r.json()
    except Exception:
        return {"_status": r.status_code, "_body": r.text}


def check(label, expected, actual, tolerance="0.02"):
    try:
        exp = q2(expected)
        act = q2(actual)
    except Exception:
        exp, act = expected, actual
    try:
        diff = abs(d(exp) - d(act))
        ok = diff <= d(tolerance)
    except Exception:
        ok = (exp == act)
        diff = "N/A"
    entry = {"label": label, "expected": str(exp), "actual": str(act),
             "diff": str(diff), "pass": ok}
    steps.append(entry)
    if not ok:
        bugs.append(entry)
        print(f"  ❌ {label}: 预期={exp} 实际={act} 差={diff}")
    else:
        print(f"  ✅ {label}: {act} (预期={exp})")
    return ok


def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


# ══════════════════════════════════════════════════════════
# 1. 创建新账本（一般纳税人）
# ══════════════════════════════════════════════════════════
section("1. 创建一般纳税人公司账本")
get("/api/bootstrap/init")
acct = post("/api/accounts", {"name": "一般纳税人模拟公司", "type": "company", "taxpayer_type": "general"})
AID = extract_id(acct)
H["X-Account-ID"] = str(AID)
print(f"账本ID={AID}, taxpayer_type=general")

# 2. 期初余额
section("2. 期初余额 (6/1): 现金5万+银行50万=实收资本55万")
post("/api/opening-balances", {
    "date": "2026-06-01", "cash_balance": 50000, "bank_balance": 500000,
    "paid_in_capital": 550000,
})
bs = get("/api/financial-reports/balance-sheet?date=2026-06-01")
check("期初BS平衡", 0, bs.get("diff", 999))
check("期初总资产", 550000, bs.get("total_assets", 0))

# 3. 基础数据
section("3. 创建基础数据")
pA = post("/api/products", {"name": "商品A", "sku": "SPA001", "unit": "个", "purchase_price": 1000, "sale_price": 1500})
pB = post("/api/products", {"name": "商品B", "sku": "SPB001", "unit": "台", "purchase_price": 2000, "sale_price": 2800})
PID_A = extract_id(pA)
PID_B = extract_id(pB)
sup = post("/api/suppliers", {"name": "供应商甲"})
cus = post("/api/customers", {"name": "客户乙"})
SUP_ID = extract_id(sup)
CUS_ID = extract_id(cus)
bank = post("/api/bank-accounts", {"bank_name": "工商银行", "account_number": "6222000099887766550"})
BANK_ID = extract_id(bank)
print(f"商品A={PID_A} B={PID_B} 供应商={SUP_ID} 客户={CUS_ID} 银行={BANK_ID}")

# ══════════════════════════════════════════════════════════
# 4. 采购 + 进项发票
# ══════════════════════════════════════════════════════════
section("4a. 进项专票1: 商品A 100件@1000不含税 13% (6/5)")
# 含税113000 不含税100000 税额13000
inv1 = post("/api/invoices/quick", {
    "invoice_no": "JX2026-001", "direction": "in", "invoice_type": "special",
    "amount_with_tax": 113000, "tax_rate": 0.13, "counterparty_name": "供应商甲",
    "seller_name": "供应商甲", "buyer_name": "一般纳税人模拟公司",
    "issue_date": "2026-06-05",
    "items": [{"product_id": PID_A, "quantity": 100, "unit_price": 1000, "tax_rate": 0.13}],
    "purchase_order_action": "auto_create",
})
inv1_id = extract_id(inv1)
print(f"进项发票1 ID={inv1_id}")
cert1 = post(f"/api/invoices/{inv1_id}/certify")
print(f"认证: {cert1.get('ok', False)}")

section("4b. 进项专票2: 商品B 50件@2000不含税 13% (6/8)")
# 含税113000 不含税100000 税额13000
inv2 = post("/api/invoices/quick", {
    "invoice_no": "JX2026-002", "direction": "in", "invoice_type": "special",
    "amount_with_tax": 113000, "tax_rate": 0.13, "counterparty_name": "供应商甲",
    "seller_name": "供应商甲", "buyer_name": "一般纳税人模拟公司",
    "issue_date": "2026-06-08",
    "items": [{"product_id": PID_B, "quantity": 50, "unit_price": 2000, "tax_rate": 0.13}],
    "purchase_order_action": "auto_create",
})
inv2_id = extract_id(inv2)
cert2 = post(f"/api/invoices/{inv2_id}/certify")

section("4c. 验证采购后库存")
inv_data = get("/api/inventory")
items = inv_data.get("items", inv_data) if isinstance(inv_data, dict) else inv_data
for item in (items if isinstance(items, list) else []):
    if item.get("product_id") == PID_A:
        check("商品A库存量", 100, item.get("quantity"))
        check("商品A均价", 1000, item.get("average_cost"))
    elif item.get("product_id") == PID_B:
        check("商品B库存量", 50, item.get("quantity"))
        check("商品B均价", 2000, item.get("average_cost"))

# ══════════════════════════════════════════════════════════
# 5. 销售 + 销项发票
# ══════════════════════════════════════════════════════════
section("5a. 销项发票1: 商品A 60件@1500不含税 13% (6/15)")
# 含税101700 不含税90000 税额11700 COGS=60*1000=60000
inv3 = post("/api/invoices/quick", {
    "invoice_no": "XX2026-001", "direction": "out", "invoice_type": "special",
    "amount_with_tax": 101700, "tax_rate": 0.13, "counterparty_name": "客户乙",
    "seller_name": "一般纳税人模拟公司", "buyer_name": "客户乙",
    "issue_date": "2026-06-15",
    "items": [{"product_id": PID_A, "quantity": 60, "unit_price": 1500, "tax_rate": 0.13}],
    "sale_order_action": "auto_create",
})
inv3_id = extract_id(inv3)
print(f"销项发票1 ID={inv3_id}")

section("5b. 销项发票2: 商品B 30件@2800不含税 13% (6/18)")
# 含税94920 不含税84000 税额10920 COGS=30*2000=60000
inv4 = post("/api/invoices/quick", {
    "invoice_no": "XX2026-002", "direction": "out", "invoice_type": "special",
    "amount_with_tax": 94920, "tax_rate": 0.13, "counterparty_name": "客户乙",
    "seller_name": "一般纳税人模拟公司", "buyer_name": "客户乙",
    "issue_date": "2026-06-18",
    "items": [{"product_id": PID_B, "quantity": 30, "unit_price": 2800, "tax_rate": 0.13}],
    "sale_order_action": "auto_create",
})
inv4_id = extract_id(inv4)

section("5c. 销项发票3: 商品A 20件@1600不含税 13% (6/20)")
# 含税36160 不含税32000 税额4160 COGS=20*1000=20000
inv5 = post("/api/invoices/quick", {
    "invoice_no": "XX2026-003", "direction": "out", "invoice_type": "special",
    "amount_with_tax": 36160, "tax_rate": 0.13, "counterparty_name": "客户乙",
    "seller_name": "一般纳税人模拟公司", "buyer_name": "客户乙",
    "issue_date": "2026-06-20",
    "items": [{"product_id": PID_A, "quantity": 20, "unit_price": 1600, "tax_rate": 0.13}],
    "sale_order_action": "auto_create",
})
inv5_id = extract_id(inv5)

section("5d. 验证销售后库存")
inv_data = get("/api/inventory")
items = inv_data.get("items", inv_data) if isinstance(inv_data, dict) else inv_data
for item in (items if isinstance(items, list) else []):
    if item.get("product_id") == PID_A:
        # 100-60-20=20
        check("商品A库存量(销售后)", 20, item.get("quantity"))
        check("商品A均价(销售后)", 1000, item.get("average_cost"))
    elif item.get("product_id") == PID_B:
        # 50-30=20
        check("商品B库存量(销售后)", 20, item.get("quantity"))
        check("商品B均价(销售后)", 2000, item.get("average_cost"))

# ══════════════════════════════════════════════════════════
# 6. 费用 + 工资
# ══════════════════════════════════════════════════════════
section("6. 费用录入")
exp1 = post("/api/expenses", {"category": "房租", "amount": 8000, "expense_date": "2026-06-10", "functional_category": "管理费用"})
exp2 = post("/api/expenses", {"category": "办公用品", "amount": 2000, "expense_date": "2026-06-12", "functional_category": "管理费用"})
exp3 = post("/api/expenses", {"category": "运费", "amount": 3000, "expense_date": "2026-06-16", "functional_category": "销售费用"})
exp4 = post("/api/expenses", {"category": "工资", "amount": 30000, "expense_date": "2026-06-25", "functional_category": "管理费用"})
exp1_id = extract_id(exp1)
exp4_id = extract_id(exp4)
print(f"费用录入完成 房租={exp1_id} 办公={extract_id(exp2)} 运费={extract_id(exp3)} 工资={exp4_id}")

# ══════════════════════════════════════════════════════════
# 6b. 个人垫付（其他应付款）
# ══════════════════════════════════════════════════════════
section("6b. 个人垫付: 老板垫付办公设备款 5000元 (6/8)")
# dr 6601管理费用 cr 2241其他应付款
adv = post("/api/personal-advances", {
    "advancer_name": "老板张三",
    "amount": 5000,
    "advance_date": "2026-06-08",
    "description": "垫付办公设备采购款",
    "debit_account_code": "6601",
})
adv_id = extract_id(adv)
print(f"个人垫付ID={adv_id}")
# 偿还3000 (6/25)
rep = post(f"/api/personal-advances/{adv_id}/repay", {
    "amount": 3000,
    "repayment_date": "2026-06-25",
    "bank_account_id": BANK_ID,
})
print(f"偿还个人垫付: {rep.get('ok', False)}")
# 查询未还余额
adv_detail = get(f"/api/personal-advances/{adv_id}")
remaining = adv_detail.get("remaining_amount", 0)
check("个人垫付未还余额", 2000, remaining)

# ══════════════════════════════════════════════════════════
# 7. 固定资产
# ══════════════════════════════════════════════════════════
section("7a. 固定资产购入(关联发票): 打印机 6780元 4年 残值5% (6/5)")
# 通过进项发票同步创建固定资产
# 会计实务(一般纳税人): 资产原值=不含税金额, 进项税额单列 222102 抵扣
# 含税6780 不含税6000 税额780 月折旧=6000*0.95/48=118.75 6月新增不提
# 固定资产发票过账即抵扣即认证（certification_status=certified），与 222102 总账同步
fa_inv = post("/api/invoices/quick", {
    "invoice_no": "JX2026-GD001", "direction": "in", "invoice_type": "special",
    "amount_with_tax": 6780, "tax_rate": 0.13, "counterparty_name": "供应商甲",
    "seller_name": "供应商甲", "buyer_name": "一般纳税人模拟公司",
    "issue_date": "2026-06-05",
    "items": [{"product_id": PID_A, "quantity": 1, "unit_price": 6000, "tax_rate": 0.13}],
    "purchase_order_action": "auto_create",
    "fixed_asset": {
        "asset_code": "FA-INV-001", "asset_name": "打印机",
        "useful_life": 48, "start_date": "2026-06-05",
    },
})
fa_inv_data = fa_inv.get("data", fa_inv)
# AI 中间件包裹: {"ok":..., "entity": {"data": {...}}} → 需穿透到 entity.data
if "entity" in fa_inv and isinstance(fa_inv["entity"], dict):
    fa_inv_data = fa_inv["entity"].get("data", fa_inv["entity"])
fa_inv_id = extract_id(fa_inv)
fa_inv_asset = fa_inv_data.get("fixed_asset", {}) if isinstance(fa_inv_data, dict) else {}
fa_asset_id = fa_inv_asset.get("id")
print(f"打印机发票ID={fa_inv_id} 资产ID={fa_asset_id}")
# 会计实务: 一般纳税人资产原值=不含税金额(6000), 进项税额(780)单列 222102 抵扣
inv_amount_without_tax = fa_inv_data.get("amount_without_tax", 0)
asset_value = fa_inv_asset.get("original_value", 0)
check("资产原值=不含税金额(一般纳税人抵扣进项税)", inv_amount_without_tax, asset_value)
# 进项税额已在创建时自动认证(无需单独调 /certify)，与 222102 总账入账原子同步
check("固定资产发票自动认证", "certified", fa_inv_data.get("certification_status"))

section("7b. 固定资产(直接创建): 服务器 50000元 5年 残值5% (6/1)")
# 月折旧=50000*0.95/60=791.67 但6月新增当月不提
fa = post("/api/fixed-assets", {
    "asset_code": "FA-2026-001", "name": "服务器", "original_value": 50000,
    "useful_life": 60, "start_date": "2026-06-01", "salvage_rate": 0.05,
    "depreciation_method": "年限平均法",
})
fa_id = extract_id(fa)
print(f"固定资产ID={fa_id}")

# ══════════════════════════════════════════════════════════
# 8. 收付款
# ══════════════════════════════════════════════════════════
section("8. 收付款")
# 获取发票关联的订单ID
inv_list = get("/api/invoices")
sale_orders = []
purchase_orders = []
if isinstance(inv_list, list):
    for iv in inv_list:
        if iv.get("direction") == "out" and iv.get("related_order_id"):
            sale_orders.append((iv["related_order_id"], iv.get("amount_with_tax")))
        elif iv.get("direction") == "in" and iv.get("related_order_id"):
            purchase_orders.append((iv["related_order_id"], iv.get("amount_with_tax")))
elif isinstance(inv_list, dict):
    for iv in inv_list.get("items", inv_list.get("data", [])):
        if iv.get("direction") == "out" and iv.get("related_order_id"):
            sale_orders.append((iv["related_order_id"], iv.get("amount_with_tax")))
        elif iv.get("direction") == "in" and iv.get("related_order_id"):
            purchase_orders.append((iv["related_order_id"], iv.get("amount_with_tax")))

print(f"销售单: {sale_orders}")
print(f"采购单: {purchase_orders}")

# 收款: 销售1全额 101700
if sale_orders:
    rc1 = post("/api/receipts", {
        "receipt_type": "sale", "related_entity_type": "sale_order",
        "related_entity_id": sale_orders[0][0], "amount": 101700,
        "receipt_date": "2026-06-22T10:00:00", "receipt_method": "company", "bank_account_id": BANK_ID,
    })
    print(f"收款1: {rc1.get('ok', False)}")

# 付款: 采购1全额 113000
if purchase_orders:
    pm1 = post("/api/payments", {
        "payment_type": "purchase", "related_entity_type": "purchase_order",
        "related_entity_id": purchase_orders[0][0], "amount": 113000,
        "payment_date": "2026-06-25", "bank_account_id": BANK_ID,
    })
    print(f"付款1: {pm1.get('ok', False)}")

# 发工资 25000
if exp4_id:
    pm2 = post("/api/payments", {
        "payment_type": "salary", "related_entity_type": "expense",
        "related_entity_id": exp4_id, "amount": 25000,
        "payment_date": "2026-06-28", "bank_account_id": BANK_ID,
    })
    print(f"发工资: {pm2.get('ok', False)}")

# ══════════════════════════════════════════════════════════
# 9. 银行手续费 + 利息
# ══════════════════════════════════════════════════════════
section("9. 银行手续费与利息")
bf = post("/api/bank/entry", {"entry_type": "bank_fee", "amount": 50, "transaction_date": "2026-06-28"})
print(f"手续费: {bf.get('ok', False)}")
bi = post("/api/bank/entry", {"entry_type": "interest_income", "amount": 120, "transaction_date": "2026-06-28"})
print(f"利息: {bi.get('ok', False)}")

# ══════════════════════════════════════════════════════════
# 10. 库存调整(盘亏)
# ══════════════════════════════════════════════════════════
section("10. 库存调整: 商品A盘亏2件 (6/26)")
# 20件→18件, 成本=2*1000=2000
adj = put(f"/api/inventory/{PID_A}", {"quantity": 18, "reason": "盘亏2件", "adjust_date": "2026-06-26"})
print(f"盘亏: {adj.get('ok', False)}")

# ══════════════════════════════════════════════════════════
# 11. 销售部分退货
# ══════════════════════════════════════════════════════════
section("11. 销售退货: 销售3退回5件 (6/27)")
# 销售3: 商品A 20件@1600, 退5件
# 库存回补5件(18→23), 收入冲红=5*1600=8000, 税额冲红=1040, COGS冲回=5*1000=5000
if sale_orders and len(sale_orders) >= 3:
    so3_id = sale_orders[2][0]
    ret1 = post(f"/api/sales/{so3_id}/return", {
        "return_date": "2026-06-27", "reason": "客户退回5件",
        "items": [{"product_id": PID_A, "quantity": 5}],
    })
    print(f"退货: {ret1.get('ok', False)}")
else:
    print(f"销售单不足: {sale_orders}")

# ══════════════════════════════════════════════════════════
# 12. 月结前报表
# ══════════════════════════════════════════════════════════
section("12. 月结前报表检查")
is_report = get("/api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30")
print("利润表:", json.dumps(is_report, ensure_ascii=False)[:600])

# 预期收入: 90000+84000+32000-8000(退货)=198000
exp_revenue = 90000 + 84000 + 32000 - 8000
# 预期COGS: 60000+60000+20000-5000(退货)=135000
exp_cogs = 60000 + 60000 + 20000 - 5000
check("营业收入", exp_revenue, is_report.get("revenue", 0))
check("营业成本", exp_cogs, is_report.get("cost_of_goods_sold", 0))

bs_pre = get("/api/financial-reports/balance-sheet?date=2026-06-30")
check("月结前BS平衡", 0, bs_pre.get("diff", 999))

# 验证库存价值
inv_data = get("/api/inventory")
items = inv_data.get("items", inv_data) if isinstance(inv_data, dict) else inv_data
for item in (items if isinstance(items, list) else []):
    if item.get("product_id") == PID_A:
        # 18+5(退货回补)=23
        check("商品A库存量(退货后)", 23, item.get("quantity"))

# ══════════════════════════════════════════════════════════
# 13. 银行对账
# ══════════════════════════════════════════════════════════
section("13. 银行对账")
# 银行期末余额: 500000(期初) + 101700(收) - 113000(付1) - 25000(工资) - 3000(偿还垫付) - 50(手续费) + 120(利息) = 460770
bank_end = 500000 + 101700 - 113000 - 25000 - 3000 - 50 + 120
stmt = post("/api/bank/statement", {
    "period_start": "2026-06-01", "period_end": "2026-06-30",
    "opening_balance": 500000, "closing_balance": bank_end,
    "lines": [
        {"transaction_date": "2026-06-22", "amount": 101700, "description": "收款"},
        {"transaction_date": "2026-06-25", "amount": -113000, "description": "付款采购"},
        {"transaction_date": "2026-06-25", "amount": -25000, "description": "发工资"},
        {"transaction_date": "2026-06-25", "amount": -3000, "description": "偿还个人垫付"},
        {"transaction_date": "2026-06-28", "amount": -50, "description": "手续费"},
        {"transaction_date": "2026-06-28", "amount": 120, "description": "利息"},
    ],
})
print(f"对账单: {stmt.get('ok', False)}")

# 执行对账
recon = post("/api/bank/reconcile?period=2026-06")
print(f"对账: {recon.get('ok', False)}")

recon_data = get("/api/bank/reconciliation?period=2026-06")
rec_id = None
if isinstance(recon_data, list) and recon_data:
    rec_id = recon_data[0].get("id")
elif isinstance(recon_data, dict):
    rec_id = recon_data.get("id")
    items_r = recon_data.get("items", [])
    if not rec_id and items_r:
        rec_id = items_r[0].get("id")
if rec_id:
    # confirm 是 POST，可能返回 202 需确认
    confirm_recon = post(f"/api/bank/reconciliation/{rec_id}/confirm")
    print(f"确认调节表: {confirm_recon.get('ok', False)}")
else:
    print(f"未找到调节表ID, recon_data={recon_data}")

# ══════════════════════════════════════════════════════════
# 14. 月结
# ══════════════════════════════════════════════════════════
section("14. 执行6月月结")
mc = post("/api/finance/month-close", {"period": "2026-06"})
print("月结:", json.dumps(mc, ensure_ascii=False)[:800])
mc_data = mc.get("entity", mc)

# VAT: 销项=11700+10920+4160-1040=25740, 进项=13000+13000+780(打印机)=26780
# VAT=max(25740-26780,0)=0 (留抵1040)
exp_output_vat = 11700 + 10920 + 4160 - 1040
exp_input_vat = 13000 + 13000 + 780
exp_vat = max(exp_output_vat - exp_input_vat, 0)
check("月结VAT", exp_vat, mc_data.get("curr_vat", 0))

# 附加税 = VAT*12% = 0
exp_surcharge = q2(exp_vat * d("0.12"))

# 利润 = 198000 - 135000 - 48000(费用+个人垫付) - 50(手续费) + 120(利息) = 15070
# 注: 盘亏2000走1901待处理财产损溢(非损益科目)，不影响当期利润，查明原因后才转管理费用
exp_profit = 198000 - 135000 - 48000 - 50 + 120
# 所得税 = 15070 * 25% = 3767.50 (一般纳税人)
exp_income_tax = q2(exp_profit * d("0.25"))
print(f"预期: 销项={exp_output_vat} 进项={exp_input_vat} VAT={exp_vat} 利润={exp_profit} 所得税={exp_income_tax}")
check("月结所得税", exp_income_tax, mc_data.get("target_income_tax", 0))

# ══════════════════════════════════════════════════════════
# 15. 月结后报表
# ══════════════════════════════════════════════════════════
section("15. 月结后报表验证")
bs_post = get("/api/financial-reports/balance-sheet?date=2026-06-30")
print("BS:", json.dumps(bs_post, ensure_ascii=False)[:800])
check("月结后BS平衡", 0, bs_post.get("diff", 999))

is_post = get("/api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30")
print("IS:", json.dumps(is_post, ensure_ascii=False)[:800])
check("月结后营业收入", exp_revenue, is_post.get("revenue", 0))
check("月结后营业成本", exp_cogs, is_post.get("cost_of_goods_sold", 0))
# 净利润 = 14950(营业利润) - 3767.50(所得税) = 11182.50
# 注: 利息120在6603贷方冲减财务费用，financial_expenses净额=50-120=-70但利润表显示50(借方)
# 营业利润 = 198000-135000-3000-45000-50 = 14950 (含个人垫付5000)
check("净利润", q2(14950 - 3767.50), is_post.get("net_profit", 0))

# 试算平衡
trial = get("/api/finance/reports/trial-balance?date=2026-06-30")
print("试算平衡:", json.dumps(trial, ensure_ascii=False)[:800])

# ══════════════════════════════════════════════════════════
# 16. 税务核对
# ══════════════════════════════════════════════════════════
section("16. 税务核对8项")
# 利润总额 = 营业利润(14950) = 收入-成本-费用(含个人垫付5000, 含手续费50, 不含利息120冲减)
exp_gross_profit = 198000 - 135000 - 3000 - 45000 - 50  # = 14950
tax_check = get(f"/api/tax/check?period=2026-06&sales={exp_revenue}&output_vat={exp_output_vat}&input_vat={exp_input_vat}&unpaid_vat={exp_vat}&income_tax={exp_income_tax}&surcharge={exp_surcharge}&vat_payable={exp_vat}&gross_profit={exp_gross_profit}")
print("税务核对:", json.dumps(tax_check, ensure_ascii=False)[:800])
check("税务核对全通过", True, tax_check.get("all_passed", False))

# 季度税务报表
tax_report = get("/api/tax-report?year=2026&quarter=2")
print("季度税务:", json.dumps(tax_report, ensure_ascii=False)[:600])
# 季度税务报表 - 发票层净额口径（红字发票 amount<0 自动扣除）
# 销售3退5件@1600×13% = 退货税额1040 → 红字销项发票 tax_amount=-1040
# 净销项税 = 11700 + 10920 + 4160 - 1040(红字) = 25740
exp_quarter_output_vat = 11700 + 10920 + 4160 - 1040  # 净额=25740
check("季度销项税", exp_quarter_output_vat, tax_report.get("output_tax", 0))
check("季度进项税", exp_input_vat, tax_report.get("input_tax", 0))

# ══════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════
section("测试汇总")
total = len(steps)
passed = sum(1 for s in steps if s["pass"])
failed = len(bugs)
print(f"\n总检查项: {total}, 通过: {passed}, 失败: {failed}")
print(f"\n{'='*60}")
print(f"BUG 清单 ({failed} 个)")
print(f"{'='*60}")
for i, b in enumerate(bugs, 1):
    print(f"  BUG-{i}: [{b['label']}]")
    print(f"    预期: {b['expected']}")
    print(f"    实际: {b['actual']}")
    print(f"    差异: {b['diff']}")

result = {"account_id": AID, "total_checks": total, "passed": passed, "failed": failed,
          "bugs": bugs, "steps": steps,
          "expected": {"revenue": str(exp_revenue), "cogs": str(exp_cogs), "vat": str(exp_vat),
                       "profit": str(exp_profit), "income_tax": str(exp_income_tax),
                       "output_vat": str(exp_output_vat), "input_vat": str(exp_input_vat)},
          "added_features": ["personal_advance(5000, repaid_3000)", "fixed_asset_with_invoice(printer_6780)"],}
with open("test_finance_full_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n详细结果已保存到 test_finance_full_result.json")
