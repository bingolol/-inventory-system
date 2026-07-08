"""模板 10：固定资产

业务流程：
- 购入：进项发票 + fixed_asset 块（同事务原子创建发票+资产+认证，推荐）
       或独立 POST /api/fixed-assets（不开发票直接入账）
- 月末折旧：批量计提
- 处置：危险操作，需用户确认
"""
import sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, r"C:\Users\Administrator\Desktop\-inventory-system\docs\操作模板")
from _client import (post, get, extract_id,
                     post_pending, confirm, cancel_pending)


def _calc_invoice_amounts(amount_with_tax, tax_rate):
    """根据价税合计和税率计算不含税金额与税额（BR-27：税额外部输入，模板内推导仅做示例）。"""
    q2 = Decimal("0.01")
    total = Decimal(str(amount_with_tax))
    rate = Decimal(str(tax_rate))
    without_tax = (total / (Decimal("1") + rate)).quantize(q2, rounding=ROUND_HALF_UP)
    tax = (total - without_tax).quantize(q2, rounding=ROUND_HALF_UP)
    return float(without_tax), float(tax)


# === 购入方式 A：发票 + 固定资产（原子事务，推荐） ===

def create_fixed_asset_via_invoice(invoice_no, amount_with_tax, tax_rate,
                                    counterparty_name, seller_name, buyer_name,
                                    issue_date, asset_code, asset_name,
                                    useful_life, start_date,
                                    invoice_type="special",
                                    salvage_rate=0.05,
                                    depreciation_method="年限平均法",
                                    category=None, items=None,
                                    notes=None):
    """购入固定资产（同事务创建进项发票 + 固定资产 + 自动关联）。

    走 POST /api/invoices/quick + fixed_asset 块。
    - 一般纳税人专票会自动认证 + 抵扣进项税额
    - 资产原值 = amount_with_tax（含税总额作为原值）
    - items 必填（系统要求至少 1 行），但可填一行占位（系统按发票总额入账）

    参数：
        invoice_no: 发票号
        amount_with_tax: 价税合计（同时作为资产原值）
        tax_rate: 税率（如 0.13）
        counterparty_name: 交易对方
        seller_name: 销方（一般填供应商名）
        buyer_name: 购方（一般填本公司名）
        issue_date: 开票日期 "YYYY-MM-DD"
        asset_code: 资产编码（如 "FA-2026-001"）
        asset_name: 资产名称
        useful_life: 使用寿命（月数，如 60）
        start_date: 开始折旧日期 "YYYY-MM-DD"
        invoice_type: "special"（专票，默认）或 "ordinary"（普票）
        salvage_rate: 残值率（默认 0.05）
        depreciation_method: 折旧方法（默认 "年限平均法"）
        category: 资产类别（如 "office_equipment"）
        items: 商品明细行（必填，至少 1 行；可填占位行）
               默认用 asset_name + amount_with_tax 自动生成一行
        notes: 备注
    """
    if items is None:
        unit_price = round(float(amount_with_tax) / (1 + float(tax_rate)), 6)
        items = [{
            "product_id": 0,
            "quantity": 1,
            "unit_price": unit_price,
            "tax_rate": tax_rate,
        }]
    _, tax_amount = _calc_invoice_amounts(amount_with_tax, tax_rate)
    body = {
        "invoice_no": invoice_no,
        "direction": "in",
        "invoice_type": invoice_type,
        "tax_rate": tax_rate,
        "amount_with_tax": amount_with_tax,
        "tax_amount": tax_amount,
        "counterparty_name": counterparty_name,
        "seller_name": seller_name,
        "buyer_name": buyer_name,
        "issue_date": issue_date,
        "items": items,
        "fixed_asset": {
            "asset_code": asset_code,
            "asset_name": asset_name,
            "useful_life": useful_life,
            "start_date": start_date,
            "salvage_rate": salvage_rate,
            "depreciation_method": depreciation_method,
        },
    }
    if category: body["fixed_asset"]["category"] = category
    if notes: body["notes"] = notes
    return post("/api/invoices/quick", body)


# === 购入方式 B：独立创建（无发票） ===

def create_fixed_asset_standalone(asset_code, name, original_value,
                                  useful_life, start_date,
                                  salvage_rate=0.05,
                                  depreciation_method="年限平均法",
                                  category=None, status="在用",
                                  accumulated_depreciation=0):
    """独立创建固定资产（不走发票，直接入账）。

    适用：未取得发票的购入、盘盈、捐赠等。
    """
    body = {
        "asset_code": asset_code,
        "name": name,
        "original_value": original_value,
        "useful_life": useful_life,
        "start_date": start_date,
        "salvage_rate": salvage_rate,
        "depreciation_method": depreciation_method,
        "status": status,
        "accumulated_depreciation": accumulated_depreciation,
    }
    if category: body["category"] = category
    return post("/api/fixed-assets", body)


# === 查询 ===

def list_fixed_assets(status=None):
    """查询固定资产列表。

    参数：
        status: 按状态筛选（"在用" / "停用" / "报废" / "已冲红"），None 则全部
        ⚠️ 后端不支持 category 筛选（按 category 查询会失效）
    """
    q = []
    if status: q.append(f"status={status}")
    qs = ("?" + "&".join(q)) if q else ""
    return get(f"/api/fixed-assets{qs}")


def get_fixed_asset(asset_id):
    """查询单个资产（含累计折旧、净值）。"""
    return get(f"/api/fixed-assets/{asset_id}")


# === 折旧（月结时执行） ===

def run_depreciation(year, month):
    """执行月度折旧计提（批量处理当月在用资产）。

    参数：
        year, month: 计提期间（如 2026, 6 表示 6 月折旧）
    """
    return post("/api/fixed-assets/depreciate", {
        "year": year,
        "month": month,
    })


# === 处置（危险操作：三步走 发起→转告用户→confirm/cancel_pending） ===

def dispose_fixed_asset_pending(asset_id, disposal_date, disposal_price,
                                bank_account_id=None):
    """发起资产处置（返回 confirm_token，不立即执行）。

    ⚠️ 后端用 URL 查询参数（Query）接收，不是 JSON body。

    参数：
        asset_id: 资产 ID
        disposal_date: 处置日期 "YYYY-MM-DD"（必填）
        disposal_price: 处置价格（>0 时自动生成银行收款 + 投资活动现金流）
        bank_account_id: 收款银行账户 ID（disposal_price>0 时推荐提供，同步银行流水和余额）
    """
    from urllib.parse import urlencode
    params = {
        "disposal_date": disposal_date,
        "disposal_price": disposal_price,
    }
    if bank_account_id:
        params["bank_account_id"] = bank_account_id
    return post_pending(f"/api/fixed-assets/{asset_id}/dispose?{urlencode(params)}", {})


# === 端到端示例 ===
if __name__ == "__main__":
    from _client import set_account
    set_account(1)
    BANK_ID = 1

    print("=== 方式 A：发票 + 固定资产（推荐） ===")
    fa = create_fixed_asset_via_invoice(
        invoice_no="IN20260610001",
        amount_with_tax=7800.00,
        tax_rate=0.13,
        counterparty_name="供应商甲",
        seller_name="供应商甲",
        buyer_name="本公司",
        issue_date="2026-06-10",
        asset_code="FA-2026-001",
        asset_name="惠普打印机",
        useful_life=60,
        start_date="2026-06-10",
        invoice_type="special",
        category="office_equipment",
        notes="办公室打印机",
    )
    print(f"   {fa}")
    fa_id = extract_id(fa)

    print("\n=== 方式 B：独立创建（无发票） ===")
    fa2 = create_fixed_asset_standalone(
        asset_code="FA-2026-002",
        name="盘盈设备",
        original_value=5000.00,
        useful_life=36,
        start_date="2026-06-10",
        category="machinery",
    )
    print(f"   {fa2}")

    print("\n3. 月末计提折旧")
    dep = run_depreciation(year=2026, month=6)
    print(f"   {dep}")

    print("\n4. 发起资产处置（危险操作）")
    pending = dispose_fixed_asset_pending(
        asset_id=fa_id,
        disposal_date="2026-06-30",
        disposal_price=5000.00,
        bank_account_id=BANK_ID,
        disposal_reason="更换新设备",
    )
    print(f"   {pending}")
    token = pending.get("confirm_token")
    if token:
        print(f"   系统提示：{pending.get('message')}")
        print("   → AI 应停在这里问用户：是否确认执行？")
