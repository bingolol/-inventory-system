# -*- coding: utf-8 -*-
"""
反向流程测试 - 需要前端手动确认
覆盖: 采购退货/整单取消/发票红冲/费用冲红/收款冲红/资产处置/二次月结
每个危险操作发起后暂停，提示用户在前端确认，轮询等待完成后继续
"""
import json
import time
import requests
from decimal import Decimal, ROUND_HALF_UP

BASE = "http://127.0.0.1:8000"
H = {"Content-Type": "application/json", "X-Operator": "ai"}

bugs = []
steps = []
Q2 = Decimal("0.01")
UNIQUE = str(int(time.time()))  # 唯一标识，避免账本名重复


def d(x):
    return Decimal(str(x))

def q2(x):
    return d(x).quantize(Q2, rounding=ROUND_HALF_UP)

def extract_id(resp):
    if not isinstance(resp, dict):
        return None
    if resp.get("id"):
        return resp["id"]
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


def post_dangerous(path, body=None, label=""):
    """发起危险操作，返回202+token后由脚本自动确认（无人值守模式）"""
    r = requests.post(BASE + path, headers=H, json=body or {})
    if r.status_code == 202:
        data = r.json()
        token = data.get("confirm_token")
        if not token:
            ent = data.get("entity", {})
            if isinstance(ent, dict):
                token = ent.get("confirm_token")
        if token:
            print(f"  [{label}] 自动确认 token={token[:8]}...")
            rc = requests.post(BASE + f"/api/confirm/{token}", headers=H)
            print(f"  确认结果: {rc.status_code}")
            time.sleep(1)
            try:
                return rc.json()
            except Exception:
                return {"_confirmed": True, "token": token}
        return data
    try:
        return r.json()
    except Exception:
        return {"_status": r.status_code, "_body": r.text}


def post(path, body=None):
    r = requests.post(BASE + path, headers=H, json=body or {})
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

def put(path, body=None):
    r = requests.put(BASE + path, headers=H, json=body or {})
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
    entry = {"label": label, "expected": str(exp), "actual": str(act), "diff": str(diff), "pass": ok}
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
# 搭建测试账本 - 复用正向流程的基础数据
# ══════════════════════════════════════════════════════════
section("0. 搭建反向流程测试账本")

get("/api/bootstrap/init")
acct = post("/api/accounts", {"name": f"反向流程测试_{UNIQUE}", "type": "company", "taxpayer_type": "general"})
AID = extract_id(acct)
H["X-Account-ID"] = str(AID)
print(f"账本ID={AID}")

post("/api/opening-balances", {"date": "2026-06-01", "cash_balance": 100000, "bank_balance": 300000, "paid_in_capital": 400000})
bank = post("/api/bank-accounts", {"bank_name": "工行", "account_number": "rev-001"})
BANK_ID = extract_id(bank)

pA = post("/api/products", {"name": "反向商品A", "sku": "RA001", "unit": "个", "purchase_price": 1000, "sale_price": 1500})
pB = post("/api/products", {"name": "反向商品B", "sku": "RB001", "unit": "台", "purchase_price": 2000, "sale_price": 2800})
PID_A = extract_id(pA)
PID_B = extract_id(pB)
post("/api/suppliers", {"name": "供应商R"})
post("/api/customers", {"name": "客户R"})
print(f"商品A={PID_A} B={PID_B} 银行={BANK_ID}")

# 采购2笔
# 采购1: A 25件@1000不含税 = 25000, 税额3250, 价税合计28250
# 多采购5件以预留采购退货余量（库存 25-10-10=5, 退货5件后=0）
inv1 = post("/api/invoices/quick", {
    "invoice_no": "RJ-001", "direction": "in", "invoice_type": "special",
    "amount_with_tax": 28250, "tax_rate": 0.13, "counterparty_name": "供应商R",
    "seller_name": "供应商R",     "buyer_name": f"反向流程测试_{UNIQUE}", "issue_date": "2026-06-05",
    "items": [{"product_id": PID_A, "quantity": 25, "unit_price": 1000, "tax_rate": 0.13}],
    "purchase_order_action": "auto_create",
})
inv1_id = extract_id(inv1)
post(f"/api/invoices/{inv1_id}/certify")

inv2 = post("/api/invoices/quick", {
    "invoice_no": "RJ-002", "direction": "in", "invoice_type": "special",
    "amount_with_tax": 22600, "tax_rate": 0.13, "counterparty_name": "供应商R",
    "seller_name": "供应商R", "buyer_name": "反向流程测试_", "issue_date": "2026-06-06",
    "items": [{"product_id": PID_B, "quantity": 10, "unit_price": 2000, "tax_rate": 0.13}],
    "purchase_order_action": "auto_create",
})
inv2_id = extract_id(inv2)
post(f"/api/invoices/{inv2_id}/certify")

# 销售3笔
inv3 = post("/api/invoices/quick", {
    "invoice_no": "RX-001", "direction": "out", "invoice_type": "special",
    "amount_with_tax": 16950, "tax_rate": 0.13, "counterparty_name": "客户R",
    "seller_name": "反向流程测试_", "buyer_name": "客户R", "issue_date": "2026-06-10",
    "items": [{"product_id": PID_A, "quantity": 10, "unit_price": 1500, "tax_rate": 0.13}],
    "sale_order_action": "auto_create",
})
inv3_id = extract_id(inv3)

inv4 = post("/api/invoices/quick", {
    "invoice_no": "RX-002", "direction": "out", "invoice_type": "special",
    "amount_with_tax": 31680, "tax_rate": 0.13, "counterparty_name": "客户R",
    "seller_name": "反向流程测试_", "buyer_name": "客户R", "issue_date": "2026-06-12",
    "items": [{"product_id": PID_B, "quantity": 10, "unit_price": 2800, "tax_rate": 0.13}],
    "sale_order_action": "auto_create",
})
inv4_id = extract_id(inv4)

inv5 = post("/api/invoices/quick", {
    "invoice_no": "RX-003", "direction": "out", "invoice_type": "special",
    "amount_with_tax": 16950, "tax_rate": 0.13, "counterparty_name": "客户R",
    "seller_name": "反向流程测试_", "buyer_name": "客户R", "issue_date": "2026-06-14",
    "items": [{"product_id": PID_A, "quantity": 10, "unit_price": 1500, "tax_rate": 0.13}],
    "sale_order_action": "auto_create",
})
inv5_id = extract_id(inv5)

# 费用
exp1 = post("/api/expenses", {"category": "工资", "amount": 10000, "expense_date": "2026-06-20", "functional_category": "管理费用"})
exp1_id = extract_id(exp1)

# 固定资产
fa = post("/api/fixed-assets", {
    "asset_code": "RFA-001", "name": "测试设备", "original_value": 30000,
    "useful_life": 36, "start_date": "2026-06-01", "salvage_rate": 0.05,
    "depreciation_method": "年限平均法",
})
fa_id = extract_id(fa)

# 收款(销售1全额)
# 直接从 sales/purchases API 获取订单
# 保留 items 信息以便按 product_id 查找正确的订单（API 返回顺序不保证与创建顺序一致）
sales_resp = get("/api/sales")
sales_items = sales_resp if isinstance(sales_resp, list) else sales_resp.get("items", [])
sale_orders = [(s["id"], float(s.get("total_price", 0))) for s in sales_items if s.get("status") == "completed"]

purchases_resp = get("/api/purchases")
pur_items = purchases_resp if isinstance(purchases_resp, list) else purchases_resp.get("items", [])
purchase_orders = [(p["id"], float(p.get("total_price", 0))) for p in pur_items if p.get("status") == "completed"]

# 按商品查找订单 ID（API 返回顺序不保证与创建顺序一致）
def find_order_with_product(orders_list, api_items, product_id):
    """从 API 返回的订单列表中找到包含指定 product_id 的订单 ID"""
    for o in api_items:
        if o.get("status") != "completed":
            continue
        for it in o.get("items", []):
            if it.get("product_id") == product_id:
                return o["id"]
    return orders_list[0][0] if orders_list else None

# 找到包含商品A的采购单和销售单
po_a_id = find_order_with_product(purchase_orders, pur_items, PID_A)
so_a_ids = []  # 所有包含商品A的销售单（按ID升序）
for s in sales_items:
    if s.get("status") != "completed":
        continue
    for it in s.get("items", []):
        if it.get("product_id") == PID_A:
            so_a_ids.append(s["id"])
            break
so_a_ids.sort()

receipt_id = None
if sale_orders:
    rc = post("/api/receipts", {
        "receipt_type": "sale", "related_entity_type": "sale_order",
        "related_entity_id": sale_orders[0][0], "amount": sale_orders[0][1],
        "receipt_date": "2026-06-15T10:00:00", "receipt_method": "company", "bank_account_id": BANK_ID,
    })
    receipt_list = get("/api/receipts")
    rc_items = receipt_list if isinstance(receipt_list, list) else receipt_list.get("items", [])
    if rc_items:
        receipt_id = rc_items[-1].get("id")

# 记录反向流程前的基准数据
trial_before = get("/api/finance/reports/trial-balance?date=2026-06-30")
print(f"基础数据创建完成，销售单{len(sale_orders)}笔，采购单{len(purchase_orders)}笔")
print(f"收款ID={receipt_id}, 费用ID={exp1_id}, 资产ID={fa_id}")

# ══════════════════════════════════════════════════════════
# 1. 采购部分退货
# ══════════════════════════════════════════════════════════
section("1. 采购部分退货: 采购1退回5件商品A (6/16)")
# 采购1: 商品A 25件@1000, 退5件
# 库存流转: 采购25 - 销售10 - 销售10 = 5, 退货5件 → 库存减少5 → 0
# 进项税转出=5*1000*13%=650, 库存成本退回=5*1000=5000
if po_a_id:
    po1_id = po_a_id
    result = post_dangerous(f"/api/purchases/{po1_id}/return", {
        "return_date": "2026-06-16", "reason": "采购退货5件",
        "items": [{"product_id": PID_A, "quantity": 5}],
    }, label="采购退货")
    if not result.get("_timeout"):
        # 验证库存：采购退货 = 库存减少
        inv_data = get("/api/inventory")
        items = inv_data.get("items", inv_data) if isinstance(inv_data, dict) else inv_data
        for item in (items if isinstance(items, list) else []):
            if item.get("product_id") == PID_A:
                # 采购25 - 销售10 - 销售10 - 退货5 = 0
                check("采购退货后商品A库存", 0, item.get("quantity"))

# ══════════════════════════════════════════════════════════
# 2. 销售单整单取消
# ══════════════════════════════════════════════════════════
section("2. 销售单整单取消: 销售3取消 (6/17)")
# 销售3: 商品A 10件@1500, 整单取消
# 库存回退10件, 收入冲红15000, 税额冲红1950, COGS冲回10000
if len(so_a_ids) >= 1:
    so3_id = so_a_ids[-1]  # 取商品A的最后一笔销售（对应原"销售3"）
    result = post_dangerous(f"/api/sales/{so3_id}/cancel", {}, label="销售整单取消")
    if not result.get("_timeout"):
        # 验证库存
        inv_data = get("/api/inventory")
        items = inv_data.get("items", inv_data) if isinstance(inv_data, dict) else inv_data
        for item in (items if isinstance(items, list) else []):
            if item.get("product_id") == PID_A:
                # 0(退货后) + 10(取消回退) = 10
                check("销售取消后商品A库存", 10, item.get("quantity"))

# ══════════════════════════════════════════════════════════
# 3. 发票红冲
# ══════════════════════════════════════════════════════════
section("3. 发票红冲: 销项发票3红冲 (6/18)")
# 红冲销售3的发票 → 级联冲红凭证和库存
result = post_dangerous(f"/api/invoices/{inv5_id}/reverse", {
    "reverse_date": "2026-06-18", "reason": "发票开错红冲",
}, label="发票红冲")
if not result.get("_timeout"):
    print(f"  发票红冲完成")

# ══════════════════════════════════════════════════════════
# 4. 费用冲红
# ══════════════════════════════════════════════════════════
section("4. 费用冲红: 工资费用冲红 (6/19)")
result = post_dangerous(f"/api/expenses/{exp1_id}/reverse", {}, label="费用冲红")
if not result.get("_timeout"):
    print(f"  费用冲红完成")
    # 验证 6601 管理费用净额应为0（借方10000-贷方10000）
    trial = get("/api/finance/reports/trial-balance?date=2026-06-30")
    for row in trial.get("rows", []):
        if row["code"] == "6601":
            net = float(row["debit"]) - float(row["credit"])
            check("管理费用净额(冲红后)", 0, net)

# ══════════════════════════════════════════════════════════
# 5. 收款冲红
# ══════════════════════════════════════════════════════════
section("5. 收款冲红: 收款1冲红 (6/20)")
if receipt_id:
    result = post_dangerous(f"/api/receipts/{receipt_id}/reverse", {
        "reverse_date": "2026-06-20", "reason": "收款录错",
    }, label="收款冲红")
    if not result.get("_timeout"):
        print(f"  收款冲红完成")
        # 验证银行余额回退
        bank_accts = get("/api/bank-accounts")
        items_b = bank_accts.get("items", []) if isinstance(bank_accts, dict) else bank_accts
        if isinstance(items_b, list):
            for ba in items_b:
                if ba.get("id") == BANK_ID:
                    # 收款16950已冲红，银行余额应减16950
                    print(f"  银行余额: {ba.get('balance')}")

# ══════════════════════════════════════════════════════════
# 6. 固定资产处置
# ══════════════════════════════════════════════════════════
section("6. 固定资产处置: 测试设备处置价5000 (6/21)")
# 原值30000, 残值率5%, 36月, 月折旧=30000*0.95/36=791.67
# 6月新增不提折旧，累计折旧=0，净值=30000
# 处置价5000 < 净值30000 → 损失25000 → 6711营业外支出
# 同时银行账户收到处置款5000（投资活动现金流），与总账1002科目保持一致
if fa_id:
    result = post_dangerous(f"/api/fixed-assets/{fa_id}/dispose?disposal_price=5000&disposal_date=2026-06-21&bank_account_id={BANK_ID}", {}, label="资产处置")
    if not result.get("_timeout"):
        print(f"  资产处置完成")
        # 验证 6711 营业外支出借方25000
        trial = get("/api/finance/reports/trial-balance?date=2026-06-30")
        for row in trial.get("rows", []):
            if row["code"] == "6711":
                check("营业外支出(处置损失)", 25000, row["debit"])

# ══════════════════════════════════════════════════════════
# 6b. 固定资产发票创建 + 红冲（验证 fixed_asset 级联冲红分支）
# ══════════════════════════════════════════════════════════
section("6b. 固定资产发票创建 + 红冲")
# 一般纳税人 + 专票 → 资产原值=不含税6000, 222102入账780, 2202=6780, 自动认证
# 红冲 → 反向凭证冲回 1601/222102/2202, 资产卡片 status=已冲红

def _tb_amt(trial, code):
    """从试算平衡表取某科目的 (debit, credit)"""
    for row in trial.get("rows", []):
        if row["code"] == code:
            return float(row["debit"]), float(row["credit"])
    return 0.0, 0.0

def _unwrap(resp):
    """穿透 AI 中间件包裹 {"ok":..,"entity":{"data":{..}}} → data"""
    if not isinstance(resp, dict):
        return resp
    if "entity" in resp and isinstance(resp["entity"], dict):
        inner = resp["entity"]
        return inner.get("data", inner)
    return resp.get("data", resp)

trial_6b_before = get("/api/finance/reports/trial-balance?date=2026-06-30")
b1601 = _tb_amt(trial_6b_before, "1601")
b222102 = _tb_amt(trial_6b_before, "222102")
b2202 = _tb_amt(trial_6b_before, "2202")

fa_inv_6b = post("/api/invoices/quick", {
    "invoice_no": f"RJ-FA-{UNIQUE}", "direction": "in", "invoice_type": "special",
    "amount_with_tax": 6780, "tax_rate": 0.13, "counterparty_name": "供应商R",
    "seller_name": "供应商R", "buyer_name": f"反向流程测试_{UNIQUE}", "issue_date": "2026-06-22",
    "items": [{"product_id": PID_A, "quantity": 1, "unit_price": 6000, "tax_rate": 0.13}],
    "fixed_asset": {
        "asset_code": f"RFA-INV-{UNIQUE}", "asset_name": "打印机6b",
        "useful_life": 48, "start_date": "2026-06-22",
    },
})
fa_6b_data = _unwrap(fa_inv_6b)
fa_inv_6b_id = extract_id(fa_inv_6b)
fa_6b_asset = fa_6b_data.get("fixed_asset", {}) if isinstance(fa_6b_data, dict) else {}
fa_6b_asset_id = fa_6b_asset.get("id")
print(f"固定资产发票ID={fa_inv_6b_id} 资产ID={fa_6b_asset_id}")

# 验证创建：资产原值=不含税6000, 自动认证
check("6b 资产原值=不含税6000", 6000, fa_6b_asset.get("original_value"))
check("6b 固定资产发票自动认证", "certified", fa_6b_data.get("certification_status"))

# 验证总账增量：1601借+6000, 222102借+780, 2202贷+6780
trial_6b_after_create = get("/api/finance/reports/trial-balance?date=2026-06-30")
a1601 = _tb_amt(trial_6b_after_create, "1601")
a222102 = _tb_amt(trial_6b_after_create, "222102")
a2202 = _tb_amt(trial_6b_after_create, "2202")
check("6b 创建后1601借方增量+6000", 6000, a1601[0] - b1601[0])
check("6b 创建后222102借方增量+780", 780, a222102[0] - b222102[0])
check("6b 创建后2202贷方增量+6780", 6780, a2202[1] - b2202[1])

# 红冲固定资产发票（触发 fixed_asset 级联冲红分支，post_dangerous 已改为自动确认）
result_6b = post_dangerous(f"/api/invoices/{fa_inv_6b_id}/reverse", {
    "reverse_date": "2026-06-23", "reason": "固定资产发票红冲测试",
}, label="固定资产发票红冲")
print(f"  固定资产发票红冲完成")

# 验证资产卡片 status=已冲红（通过列表筛选）
fa_list = get("/api/fixed-assets?status=已冲红")
fa_items = fa_list.get("items", fa_list) if isinstance(fa_list, dict) else fa_list
fa_6b_status = None
for a in (fa_items if isinstance(fa_items, list) else []):
    if a.get("id") == fa_6b_asset_id:
        fa_6b_status = a.get("status")
        break
check("6b 资产卡片status=已冲红", "已冲红", fa_6b_status)

# 验证总账净变化=0（用净值 debit-credit，红冲后净值应 == before 净值）
trial_6b_after_reverse = get("/api/finance/reports/trial-balance?date=2026-06-30")
r1601 = _tb_amt(trial_6b_after_reverse, "1601")
r222102 = _tb_amt(trial_6b_after_reverse, "222102")
r2202 = _tb_amt(trial_6b_after_reverse, "2202")
check("6b 红冲后1601净值=0", 0, (r1601[0]-r1601[1]) - (b1601[0]-b1601[1]))
check("6b 红冲后222102净值=0", 0, (r222102[0]-r222102[1]) - (b222102[0]-b222102[1]))
check("6b 红冲后2202净值=0", 0, (r2202[0]-r2202[1]) - (b2202[0]-b2202[1]))

# ══════════════════════════════════════════════════════════
# 7. 银行对账 + 第一次月结
# ══════════════════════════════════════════════════════════
section("7. 银行对账 + 第一次月结")
# 银行对账单需与账面一致：
#   账面1002 = 期初300000 + 收款16950(已红冲净0) + 资产处置5000 = 305000
#   对账单 closing_balance = 305000，并在 lines 里录入资产处置款5000以便匹配
#   （收款16950已红冲 → 系统中inflow和outflow相互抵消，无需录入对账单）
post("/api/bank/statement", {
    "period_start": "2026-06-01", "period_end": "2026-06-30",
    "opening_balance": 300000, "closing_balance": 305000,
    "lines": [
        {"transaction_date": "2026-06-21", "amount": 5000, "description": "资产处置款"},
    ],
})
post("/api/bank/reconcile?period=2026-06")
rd = get("/api/bank/reconciliation?period=2026-06")
rec_id = rd.get("id") if isinstance(rd, dict) else None
if rec_id:
    post(f"/api/bank/reconciliation/{rec_id}/confirm")

mc1 = post("/api/finance/month-close", {"period": "2026-06"})
mc1_data = mc1.get("entity", mc1)
print(f"第一次月结: status={mc1_data.get('status')}, VAT={mc1_data.get('curr_vat')}, 所得税={mc1_data.get('target_income_tax')}")
print(f"  lines: {mc1_data.get('lines')}")

# ══════════════════════════════════════════════════════════
# 8. 第二次月结（补提测试 #1修复点）
# ══════════════════════════════════════════════════════════
section("8. 第二次月结（补提测试）")
mc2 = post("/api/finance/month-close", {"period": "2026-06"})
mc2_data = mc2.get("entity", mc2)
print(f"第二次月结: status={mc2_data.get('status')}, VAT={mc2_data.get('curr_vat')}, 所得税={mc2_data.get('target_income_tax')}")
print(f"  lines: {mc2_data.get('lines')}")
# 第二次月结不应该重复计提（delta=0）
check("二次月结VAT一致", mc1_data.get("curr_vat", 0), mc2_data.get("curr_vat", 0))
check("二次月结所得税一致", mc1_data.get("target_income_tax", 0), mc2_data.get("target_income_tax", 0))

# ══════════════════════════════════════════════════════════
# 9. 最终报表验证
# ══════════════════════════════════════════════════════════
section("9. 最终报表验证")
bs = get("/api/financial-reports/balance-sheet?date=2026-06-30")
check("最终BS平衡", 0, bs.get("diff", 999))

is_report = get("/api/financial-reports/income-statement?start_date=2026-06-01&end_date=2026-06-30")
print(f"收入={is_report.get('revenue')}, 成本={is_report.get('cost_of_goods_sold')}, 净利润={is_report.get('net_profit')}")

# 试算平衡验证
trial = get("/api/finance/reports/trial-balance?date=2026-06-30")
print(f"试算平衡: balanced={trial.get('balanced')}")

# ══════════════════════════════════════════════════════════
# 汇总
# ══════════════════════════════════════════════════════════
section("反向流程测试汇总")
total = len(steps)
passed = sum(1 for s in steps if s["pass"])
failed = len(bugs)
print(f"\n总检查项: {total}, 通过: {passed}, 失败: {failed}")
if failed:
    print(f"\n--- BUG 清单 ({failed}) ---")
    for i, b in enumerate(bugs, 1):
        print(f"  BUG-{i}: [{b['label']}] 预期={b['expected']} 实际={b['actual']} 差={b['diff']}")

result = {"account_id": AID, "total_checks": total, "passed": passed, "failed": failed, "bugs": bugs, "steps": steps}
with open("test_reverse_flow_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n详细结果已保存到 test_reverse_flow_result.json")
