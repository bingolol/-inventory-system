"""
GOLDEN TEST 001v2 — 全业务闭环，逐行对照《小企业会计准则》

每条期望值后标注 【依据：§章-节/条】，引号内为准则原文。

【准则覆盖】§1.3 存货成本, §5.1 销售收入, §7.1 营业成本, §31 折旧, §84 报表
【AS规则】 AS-01 借贷平衡, AS-03 库存一致, AS-05 折旧公式
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from models import StockMove, Inventory
from helpers import (
    make_engine, _ledger_balance, _credit_balance, _get_id,
)
from policy.vat_facts import VAT_GENERAL_DEFAULT_RATE
from policy.income_tax_facts import INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE

_engine, _SessionLocal = make_engine()
ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}

def _db(): return _SessionLocal()

# ═══════════════════════════════════════════════════════
# L1 原始凭证 — 外部事实，不依赖系统
# ═══════════════════════════════════════════════════════
QTY_BUY = 10
UNIT_COST = Decimal("100")
# §1.3: 一般纳税人销售货物适用 13% 税率 (L3 政策: vat_facts.py)
TAX_RATE = VAT_GENERAL_DEFAULT_RATE.value

QTY_SELL = 5
UNIT_PRICE = Decimal("200")

EXPENSE = Decimal("100")

ASSET_COST = Decimal("2000")
ASSET_MONTHS = 60  # 60月=5年
ASSET_START = "2025-12-01"

# 【依据：§31 折旧公式】
# "月折旧额 = 原值 × (1 - 残值率) ÷ 使用月数"
ASSET_MONTHLY = (ASSET_COST / Decimal(str(ASSET_MONTHS))).quantize(Decimal("0.01"))

# ═══════════════════════════════════════════════════════
# L2 独立会计师手工帐
# ═══════════════════════════════════════════════════════

# 采购 【依据：§1.3 存货成本】
# "外购存货成本 = 购买价款 + 相关税费"
AMT = QTY_BUY * UNIT_COST                     # §1.3: 1000
TAX = (AMT * TAX_RATE).quantize(Decimal("0.01"))  # §1.3: 130
TOTAL = AMT + TAX                               # §1.3: 1130

# 销售 COGS 【依据：§7.1 加权平均】
# 成本 = 移动加权平均 × 数量 = 100 × 5
COGS = UNIT_COST * QTY_SELL                    # §7.1: 500

# 销售收入 【依据：§5.1 第五十九条】
# "发货时确认收入"
REVENUE = QTY_SELL * UNIT_PRICE                 # §5.1: 1000
OUTPUT_TAX = (REVENUE * TAX_RATE).quantize(Decimal("0.01"))  # §5.1: 130
AR = REVENUE + OUTPUT_TAX                       # §5.1: 1130

# 利润 【依据：§7.1 第七十一条】
# "利润总额 = 营业收入 - 营业成本 - 管理费用 - 财务费用 - 销售费用"
GROSS = REVENUE - COGS                          # §7.1: 500
TOTAL_EXPENSE = EXPENSE + ASSET_MONTHLY         # §6.1 §31: 133.33
PROFIT_BEFORE_TAX = (GROSS - TOTAL_EXPENSE).quantize(Decimal("0.01"))  # §7.1: 366.67
# §7.1: 小微企业实际所得税负 5% (L3 政策: income_tax_facts.py, 20%×25%)
INCOME_TAX = (PROFIT_BEFORE_TAX * INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE.value).quantize(Decimal("0.01"))  # 18.33
NET_PROFIT = (PROFIT_BEFORE_TAX - INCOME_TAX).quantize(Decimal("0.01"))  # §7.1: 348.34

# 期末银行 【依据：§6.1 银行存款】
BANK_OPEN = Decimal("10000")
BANK_END = (BANK_OPEN - TOTAL + AR - EXPENSE).quantize(Decimal("0.01"))  # §6.1: 9900

# 期末库存 【依据：§1.3 存货】
END_QTY = QTY_BUY - QTY_SELL                    # §1.3: 5
END_INV = UNIT_COST * END_QTY                   # §1.3: 500

# 资产负债表 §84
TOTAL_ASSETS = BANK_END + END_INV + ASSET_COST - ASSET_MONTHLY  # §84: 12366.67
TOTAL_LIABILITIES = ASSET_COST + INCOME_TAX  # §84: 2018.33
TOTAL_EQUITY = BANK_OPEN + NET_PROFIT  # §84: 10348.34


class TestGolden001v2:

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        monkeypatch.setattr(database, '_engine', _engine)
        monkeypatch.setattr(database, 'SessionLocal', _SessionLocal)
        Base.metadata.create_all(bind=_engine)
        init_db()
        from factories import ensure_default_account
        db = _SessionLocal()
        try:
            ensure_default_account(db)
            acc = db.query(models.Account).first()
            acc.taxpayer_type_l3 = "general"
            acc.enable_vat_deduction = True
            db.commit()
        finally:
            db.close()
        def _get_db():
            db = _SessionLocal()
            try:
                yield db
            finally:
                db.close()
        app.dependency_overrides[get_db] = _get_db
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_accounting_rules_compliance(self, client):
        c = client
        s = {}

        # ── 期初建账 【§84】 "所有者权益包括实收资本"
        r = c.post("/api/bank-accounts", json={
            "bank_name": "准则银行", "account_number": "KJ2201", "balance": 0}, headers=HEADERS)
        assert r.status_code == 200
        s["bank_id"] = r.json().get("entity", r.json()).get("id")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPEN), "inventory_value": 0,
            "accounts_receivable": 0, "accounts_payable": 0,
            "fixed_assets_original": 0, "accumulated_depreciation": 0,
            "intangible_assets_original": 0, "accumulated_amortization": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPEN), "retained_earnings": 0,
        }, headers=HEADERS)
        assert r.status_code == 200

        r = c.post("/api/products", json={
            "name": "准则产品", "sku": "KJ", "category": "原材料", "unit": "件",
            "purchase_price": float(UNIT_COST), "sale_price": float(UNIT_PRICE),
            "min_stock": 0, "track_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200
        s["pid"] = r.json().get("entity", r.json()).get("entity_id")

        r = c.post("/api/suppliers", json={"name": "准则供应商"}, headers=HEADERS)
        s["sup_id"] = r.json().get("entity", r.json()).get("entity_id")
        r = c.post("/api/customers", json={"name": "准则客户"}, headers=HEADERS)
        s["cus_id"] = r.json().get("entity", r.json()).get("entity_id")

        # ═══ 1. 采购入库 §1.3 ═══
        # "外购存货成本 = 购买价款 + 相关税费"
        # 一般纳税人进项抵扣: cost = 不含税金额, tax 单列 (222102)
        r = c.post("/api/purchases", json={
            "supplier_id": s["sup_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_BUY,
                       "unit_price": float(UNIT_COST), "tax_rate": float(TAX_RATE)}],
            "purchase_date": "2026-01-05",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["po"] = r.json().get("entity", r.json()).get("entity_id")

        db = _db()
        try:
            # §1.3 库存价值 = 不含税金额
            assert _ledger_balance(db, "1405") == AMT, \
                f"§1.3库存入账: 期望{AMT}, 实际{_ledger_balance(db, '1405')}"

            # §1.3 进项税额 = 不含税金额 × 税率
            input_tax = _ledger_balance(db, "222102")
            assert input_tax == TAX, \
                f"§1.3进项税额: 期望{TAX}, 实际{input_tax}"

            # §1.3 应付账款 = 价税合计
            ap = _credit_balance(db, "2202")
            assert ap == TOTAL, \
                f"§1.3应付账款: 期望{TOTAL}, 实际{ap}"

            # L3: StockMove 真相源
            sm = db.query(StockMove).filter(
                StockMove.source_type == "purchase_order",
                StockMove.source_id == s["po"],
            ).first()
            assert sm is not None, "采购无 StockMove"
            assert sm.quantity_l1 == QTY_BUY, f"采购数量 {sm.quantity_l1} != {QTY_BUY}"
            assert sm.unit_cost_l2 == UNIT_COST, f"采购单位成本 {sm.unit_cost_l2} != {UNIT_COST}"
            assert sm.total_cost_l2 == AMT, f"采购总成本 {sm.total_cost_l2} != {AMT}"
            inv = db.query(Inventory).filter(Inventory.product_id == s["pid"]).first()
            assert inv is not None, "采购后无 Inventory 缓存"
            assert inv.quantity_l4 == QTY_BUY, f"库存数量 {inv.quantity_l4} != {QTY_BUY}"
            assert inv.average_cost_l4 == UNIT_COST, f"库存均价 {inv.average_cost_l4} != {UNIT_COST}"

            # AS-03: 库存账面=StockMove求和
            from rules import enforce_rules
            try:
                enforce_rules(db, ["AS-03"], {"product_id": s["pid"]})
            except Exception as e:
                pytest.fail(f"AS-03 库存一致校验失败(采购后): {e}")
        finally:
            db.close()

        # ═══ 2. 采购付款 §6.1 ═══
        r = c.post("/api/payments", json={
            "payment_type": "purchase", "related_entity_type": "purchase_order",
            "related_entity_id": s["po"], "amount": float(TOTAL),
            "payment_date": "2026-01-06", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        db = _db()
        try:
            assert _credit_balance(db, "2202") == Decimal("0"), "§6.1 付款后应付清零"
        finally:
            db.close()

        # ═══ 3. 销售出库 §5.1 §7.1 ═══
        # "发货时确认收入" §5.1
        # "营业成本"即出库成本 §7.1
        r = c.post("/api/sales", json={
            "customer_id": s["cus_id"],
            "items": [{"product_id": s["pid"], "quantity": QTY_SELL,
                       "unit_price": float(UNIT_PRICE), "tax_rate": float(TAX_RATE)}],
            "sale_date": "2026-01-10", "deduct_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["so"] = r.json().get("entity", r.json()).get("entity_id")

        db = _db()
        try:
            # §7.1 出库成本 = 移动加权平均 × 数量
            cogs_actual = _ledger_balance(db, "6401")
            # §1.3 库存减少
            inv_val = _ledger_balance(db, "1405")
            # §5.1 收入确认
            rev_actual = -_ledger_balance(db, "6001")
            # §5.1 销项税额
            out_tax = -_ledger_balance(db, "222101")
            # §5.1 应收账款
            ar = _ledger_balance(db, "1122")

            assert cogs_actual == COGS, f"§7.1销售成本: 期望{COGS}, 实际{cogs_actual}"
            assert inv_val == END_INV, f"§1.3销售后库存: 期望{END_INV}, 实际{inv_val}"
            assert rev_actual == REVENUE, f"§5.1销售收入: 期望{REVENUE}, 实际{rev_actual}"
            assert out_tax == OUTPUT_TAX, f"§5.1销项税额: 期望{OUTPUT_TAX}, 实际{out_tax}"
            assert ar == AR, f"§5.1应收账款: 期望{AR}, 实际{ar}"

            # L3: StockMove 真相源
            sm = db.query(StockMove).filter(
                StockMove.source_type == "sale_order",
                StockMove.source_id == s["so"],
            ).first()
            assert sm is not None, "销售无 StockMove"
            assert sm.quantity_l1 == -QTY_SELL, f"销售数量 {sm.quantity_l1} != -{QTY_SELL}"
            assert sm.unit_cost_l2 == UNIT_COST, f"销售单位成本 {sm.unit_cost_l2} != {UNIT_COST}"
            assert sm.total_cost_l2 == COGS, f"销售总成本 {sm.total_cost_l2} != {COGS}"
            inv = db.query(Inventory).filter(Inventory.product_id == s["pid"]).first()
            assert inv is not None, "销售后无 Inventory 缓存"
            assert inv.quantity_l4 == END_QTY, f"库存数量 {inv.quantity_l4} != {END_QTY}"
            assert inv.total_value_l4 == END_INV, f"库存价值 {inv.total_value_l4} != {END_INV}"

            # AS-03: 库存一致
            from rules import enforce_rules
            try:
                enforce_rules(db, ["AS-03"], {"product_id": s["pid"]})
            except Exception as e:
                pytest.fail(f"AS-03 库存一致校验失败(销售后): {e}")

            print(f"  成本={cogs_actual} 库存={inv_val} 收入={rev_actual} 销项={out_tax} 应收={ar}")
        finally:
            db.close()

        # ═══ 4. 收款 §5.1 ═══
        r = c.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order",
            "related_entity_id": s["so"], "amount": float(AR),
            "receipt_date": "2026-01-13", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        db = _db()
        try:
            assert _ledger_balance(db, "1122") == Decimal("0"), "§5.1 收款后应收清零"
        finally:
            db.close()

        # ═══ 5. 费用 §6.1 ═══
        # "管理费用(6601) = 行政管理部门发生的费用"
        r = c.post("/api/expenses", json={
            "category": "办公用品", "functional_category": "管理费用",
            "amount": float(EXPENSE), "expense_date": "2026-01-15",
            "payment_method": "company",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text

        r = c.post("/api/payments", json={
            "payment_type": "expense", "related_entity_type": "expense",
            "related_entity_id": r.json().get("entity", r.json()).get("entity_id"),
            "amount": float(EXPENSE), "payment_date": "2026-01-15",
            "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        db = _db()
        try:
            assert _ledger_balance(db, "6601") == EXPENSE, \
                f"§6.1管理费用: 期望{EXPENSE}, 实际{_ledger_balance(db, '6601')}"
        finally:
            db.close()

        # ═══ 6. 固定资产 §31 ═══
        # "月折旧额 = 原值 × (1 - 残值率) ÷ 使用月数"
        # "当月增加当月不计提，下月起计提" (§31)
        r = c.post("/api/fixed-assets", json={
            "asset_code": "KJ-FA01", "name": "准则设备", "category": "机器设备",
            "original_value": float(ASSET_COST), "salvage_rate": 0,
            "useful_life": ASSET_MONTHS, "depreciation_method": "年限平均法",
            "start_date": ASSET_START,  # 上月，本月可提
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        fa_id = _get_id(r, "fixed_asset")

        # ═══ 7. 月结 §7.1 §84 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            # §31 折旧验证
            depr = abs(_ledger_balance(db, "1602"))
            print(f"  折旧={depr} (期{ASSET_MONTHLY})")
            assert abs(depr - ASSET_MONTHLY) <= Decimal("0.02"), \
                f"§31折旧公式: 期望{ASSET_MONTHLY}, 实际{depr}"

            # §84 损益结转后归零
            assert abs(_ledger_balance(db, "6001")) <= Decimal("0.01"), "§84结转后收入=0"
            assert abs(_ledger_balance(db, "6401")) <= Decimal("0.01"), "§84结转后成本=0"
            assert abs(_ledger_balance(db, "6601")) <= Decimal("0.01"), "§84结转后费用=0"
            assert abs(_ledger_balance(db, "6801")) <= Decimal("0.01"), "§84结转后所得税费用=0"

            # §7.1 4103 本年利润 = 税后净利润
            profit_4103 = _credit_balance(db, "4103")
            assert abs(profit_4103 - NET_PROFIT) <= Decimal("0.05"), \
                f"§7.1本年利润(4103): 期望{NET_PROFIT}, 实际{profit_4103}"

            # §7.1 应交所得税
            tax_payable = _credit_balance(db, "222105")
            assert abs(tax_payable - INCOME_TAX) <= Decimal("0.05"), \
                f"§7.1应交所得税(222105): 期望{INCOME_TAX}, 实际{tax_payable}"

            # AS-05: 折旧公式校验
            from rules import enforce_rules
            try:
                enforce_rules(db, ["AS-05"], {"asset_id": fa_id})
            except Exception as e:
                pytest.fail(f"AS-05 折旧公式校验失败: {e}")
        finally:
            db.close()

        # ═══ 8. 报表 §84 ═══
        # "小企业财务报表包括资产负债表、利润表、现金流量表"
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        bs = r.json()

        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        pl = r.json()

        # §84 BS平衡: A = L + E
        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"§84 BS不平衡 diff={diff}"

        # L3: 报表科目与独立会计师手算值对照
        assert abs(Decimal(str(bs["monetary_funds"])) - BANK_END) <= Decimal("0.05"), \
            f"§84货币资金: 实际{bs['monetary_funds']} != 期望{BANK_END}"
        assert abs(Decimal(str(bs["inventory"])) - END_INV) <= Decimal("0.05"), \
            f"§84存货: 实际{bs['inventory']} != 期望{END_INV}"
        assert abs(Decimal(str(bs["fixed_assets_net"])) - (ASSET_COST - ASSET_MONTHLY)) <= Decimal("0.05"), \
            f"§84固定资产净值: 实际{bs['fixed_assets_net']} != 期望{ASSET_COST - ASSET_MONTHLY}"
        assert abs(Decimal(str(bs["total_liabilities"])) - TOTAL_LIABILITIES) <= Decimal("0.05"), \
            f"§84负债合计: 实际{bs['total_liabilities']} != 期望{TOTAL_LIABILITIES}"
        assert abs(Decimal(str(bs["paid_in_capital"])) - BANK_OPEN) <= Decimal("0.05"), \
            f"§84实收资本: 实际{bs['paid_in_capital']} != 期望{BANK_OPEN}"
        assert abs(Decimal(str(bs["retained_earnings"])) - NET_PROFIT) <= Decimal("0.05"), \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{NET_PROFIT}"
        assert abs(Decimal(str(bs["total_assets"])) - TOTAL_ASSETS) <= Decimal("0.05"), \
            f"§84资产合计: 实际{bs['total_assets']} != 期望{TOTAL_ASSETS}"

        assert abs(Decimal(str(pl["revenue"])) - REVENUE) <= Decimal("0.05"), \
            f"§84营业收入: 实际{pl['revenue']} != 期望{REVENUE}"
        assert abs(Decimal(str(pl["cost_of_goods_sold"])) - COGS) <= Decimal("0.05"), \
            f"§84营业成本: 实际{pl['cost_of_goods_sold']} != 期望{COGS}"
        assert abs(Decimal(str(pl["income_tax_expense"])) - INCOME_TAX) <= Decimal("0.05"), \
            f"§84所得税费用: 实际{pl['income_tax_expense']} != 期望{INCOME_TAX}"
        assert abs(Decimal(str(pl["net_profit"])) - NET_PROFIT) <= Decimal("0.05"), \
            f"§84净利润: 实际{pl['net_profit']} != 期望{NET_PROFIT}"

        print(f"  BS: 资产={bs['total_assets']}, L+E={bs['total_liabilities_and_equity']}, diff={diff}")
        print(f"  IS: revenue={pl.get('revenue')}, cogs={pl.get('cost_of_goods_sold')}, net={pl.get('net_profit')}")

        # AS-01 稽核
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        except Exception as e:
            pytest.fail(f"AS-01 校验失败: {e}")
        finally:
            db.close()

        print("\nALL ACCOUNTING RULES VERIFIED")
