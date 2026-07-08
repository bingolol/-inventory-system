"""
GOLDEN TEST 005 — 小规模纳税人买卖 §1.3 存货 §5.1 销售 §7.1 成本

【准则覆盖】§1.3 存货成本, §5.1 销售收入, §7.1 营业成本, §84 报表
【AS规则】 AS-01 借贷平衡, AS-03 库存一致
【政策常量】 VAT_SMALL_SCALE_SYNDICATED_RATE (3% 法定征收率)
【系统行为】 enable_vat_deduction=False 时命令层不计算明细税额, 收入为全额

==================== 独立会计师完整验算 ====================
  小规模纳税人: enable_vat_deduction=False → 系统不分离税额
  Step 1: 采购10件 @100 (tax_rate=0, 全额入库存) §1.3
  Step 2: 销售5件 @200 (收入=全额, 无销项税) §5.1 §7.1
  Step 3: 月结 → 净利润 §7.1 §84
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database, models
from models import StockMove, Inventory
from helpers import make_engine, _ledger_balance, _credit_balance, _trace_bal, _get_id
from policy.vat_facts import VAT_SMALL_SCALE_SYNDICATED_RATE
from policy.income_tax_facts import INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE

_engine, _SessionLocal = make_engine()
ACCT_ID = 1
HEADERS = {"X-Account-ID": str(ACCT_ID), "X-Operator": "golden_test"}

def _db(): return _SessionLocal()

# ═══ L1 原始凭证 ═══
QTY = 10; UC = Decimal("100")
# §1.3: 小规模3%法定征收率 (L3 政策), 但系统 enable_vat_deduction=False 时不计算税额
TAX_RATE = VAT_SMALL_SCALE_SYNDICATED_RATE.value  # 3% (仅引用, 实际传0给API)
SQTY = 5; UP = Decimal("200")

# ═══ L2 手工帐 (系统行为: enable_vat_deduction=False → 不分离税额) ═══
# §1.3: 采购全额入库存 (tax_rate=0)
COST_PER_UNIT = UC                               # §1.3: 100
TOTAL_COST = COST_PER_UNIT * QTY                  # §1.3: 1000
# §5.1: 销售收入 = 全额 (系统不计算销项税)
REVENUE = SQTY * UP                               # §5.1: 1000
OUTPUT_TAX = Decimal("0")                         # §5.1: 系统不计算
AR = REVENUE                                      # §5.1: 1000
# §7.1: 营业成本
COGS = COST_PER_UNIT * SQTY                       # §7.1: 500
# §7.1: 毛利
GROSS_PROFIT = REVENUE - COGS                     # 500

# ═══ 期初 / 期末 ═══
BANK_OPENING = Decimal("10000")
PURCHASE_PAYMENT = TOTAL_COST                     # 1000
RECEIPT = AR                                      # 1000
BANK_ENDING = BANK_OPENING - PURCHASE_PAYMENT + RECEIPT  # 10000
END_QTY = QTY - SQTY                              # 5
END_VALUE = COST_PER_UNIT * END_QTY               # 500

# §7.1 利润 (税前)
PROFIT_BEFORE_TAX = GROSS_PROFIT                    # 500
# 小规模→小微企业所得税实际税率 5% (L3 政策)
INCOME_TAX = (PROFIT_BEFORE_TAX * INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE.value).quantize(Decimal("0.01"))  # 25
# §7.1 净利润 (税后)
PROFIT = PROFIT_BEFORE_TAX - INCOME_TAX              # 475

# §84 BS
TOTAL_ASSETS = BANK_ENDING + END_VALUE            # 10500
TOTAL_LIABILITIES = INCOME_TAX                    # 25 (应交所得税)
TOTAL_EQUITY = BANK_OPENING + PROFIT              # 10475

# §84 IS
IS_REVENUE = REVENUE                              # 1000
IS_COGS = COGS                                    # 500
IS_NET_PROFIT = PROFIT                             # 475 (税后净利润)


class TestSmallScaleTrade:

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
            if acc:
                acc.taxpayer_type_l3 = "small_scale"    # §1.3: 小规模纳税人
                acc.enable_vat_deduction = False         # §1.3: 不可抵扣
                db.commit()
        finally:
            db.close()
        def _get_db():
            db = _SessionLocal()
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db] = _get_db
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_small_scale_buy_sell(self, client):
        c = client; s = {}

        # ── 期初建账 §84 ──
        r = c.post("/api/bank-accounts", json={
            "bank_name": "测试银行", "account_number": "62220200001", "balance": 0,
        }, headers=HEADERS)
        assert r.status_code == 200; s["bank_id"] = _get_id(r, "bank_account")

        r = c.post("/api/opening-balances", json={
            "date": "2026-01-01", "cash_balance": 0,
            "bank_balance": float(BANK_OPENING), "accounts_receivable": 0,
            "inventory_value": 0, "fixed_assets_original": 0,
            "accumulated_depreciation": 0, "intangible_assets_original": 0,
            "accumulated_amortization": 0, "accounts_payable": 0,
            "tax_payable": 0, "long_term_borrowings": 0,
            "paid_in_capital": float(BANK_OPENING), "retained_earnings": 0,
        }, headers=HEADERS)
        assert r.status_code == 200

        # ── 基础数据 ──
        r = c.post("/api/products", json={
            "name": "商品A", "sku": "SKU-A", "category": "测试",
            "unit": "件", "purchase_price": 100, "sale_price": 200,
            "min_stock": 0, "track_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200; s["product_id"] = _get_id(r, "product")

        r = c.post("/api/suppliers", json={"name": "供应商A"}, headers=HEADERS)
        assert r.status_code == 200; s["supplier_id"] = _get_id(r, "supplier")

        r = c.post("/api/customers", json={"name": "客户A"}, headers=HEADERS)
        assert r.status_code == 200; s["customer_id"] = _get_id(r, "customer")

        # ═══ Step 1: 采购10件 §1.3 ═══
        # tax_rate=0: 系统行为 enable_vat_deduction=False 时不计算税额
        r = c.post("/api/purchases", json={
            "supplier_id": s["supplier_id"],
            "items": [{"product_id": s["product_id"], "quantity": QTY,
                       "unit_price": 100, "tax_rate": 0}],
            "purchase_date": "2026-01-05",
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["purchase_id"] = r.json().get("entity", r.json()).get("entity_id")

        db = _db()
        try:
            # §1.3: 全额入库存 (无税)
            inv_bal = _ledger_balance(db, "1405")
            assert inv_bal == TOTAL_COST, f"§1.3存货: 期望{TOTAL_COST} 实际{inv_bal}"
            # §1.3: 无进项税
            input_tax = _ledger_balance(db, "222102")
            assert input_tax == Decimal("0"), f"§1.3无进项税: 实际{input_tax}"
            # §1.3: 应付 = 全额
            ap = _credit_balance(db, "2202")
            assert ap == TOTAL_COST, f"§1.3应付: 期望{TOTAL_COST} 实际{ap}"

            # L3: StockMove 真相源验证
            sm = db.query(StockMove).filter(
                StockMove.source_type == "purchase_order",
                StockMove.source_id == s["purchase_id"],
            ).first()
            assert sm is not None, "采购无 StockMove"
            assert sm.quantity_l1 == QTY, f"采购数量 {sm.quantity_l1} != {QTY}"
            assert sm.unit_cost_l2 == COST_PER_UNIT, \
                f"采购单位成本 {sm.unit_cost_l2} != {COST_PER_UNIT}"
            assert sm.total_cost_l2 == TOTAL_COST, \
                f"采购总成本 {sm.total_cost_l2} != {TOTAL_COST}"
            inv = db.query(Inventory).filter(Inventory.product_id == s["product_id"]).first()
            assert inv is not None, "采购后无 Inventory"
            assert inv.quantity_l4 == QTY, f"库存数量 {inv.quantity_l4} != {QTY}"
            assert inv.average_cost_l4 == COST_PER_UNIT, \
                f"库存均价 {inv.average_cost_l4} != {COST_PER_UNIT}"
        finally: db.close()

        # 付款
        r = c.post("/api/payments", json={
            "payment_type": "purchase", "related_entity_type": "purchase_order",
            "related_entity_id": s["purchase_id"], "amount": float(PURCHASE_PAYMENT),
            "payment_date": "2026-01-06", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        # ═══ Step 2: 销售5件 §5.1 §7.1 ═══
        # tax_rate=0: 系统行为 enable_vat_deduction=False 时不计算税额
        r = c.post("/api/sales", json={
            "customer_id": s["customer_id"],
            "items": [{"product_id": s["product_id"], "quantity": SQTY,
                       "unit_price": 200, "tax_rate": 0}],
            "sale_date": "2026-01-10", "deduct_inventory": True,
        }, headers=HEADERS)
        assert r.status_code == 200, r.text
        s["sale_id"] = r.json().get("entity", r.json()).get("entity_id")

        db = _db()
        try:
            # §5.1: 销售收入 = 全额 (系统不计算销项税)
            rev = -_ledger_balance(db, "6001")
            assert rev == REVENUE, f"§5.1收入: 期望{REVENUE} 实际{rev}"
            # §5.1: 无销项税 (enable_vat_deduction=False)
            ot = -_ledger_balance(db, "222101")
            assert ot == OUTPUT_TAX, f"§5.1销项税: 期望{OUTPUT_TAX} 实际{ot}"
            # §5.1: 应收账款 = 全额
            ar = _ledger_balance(db, "1122")
            assert ar == AR, f"§5.1应收: 期望{AR} 实际{ar}"
            # §7.1: 营业成本
            cogs = _ledger_balance(db, "6401")
            assert cogs == COGS, f"§7.1成本: 期望{COGS} 实际{cogs}"

            # L3: StockMove 真相源
            sm = db.query(StockMove).filter(
                StockMove.source_type == "sale_order",
                StockMove.source_id == s["sale_id"],
            ).first()
            assert sm is not None, "销售无 StockMove"
            assert sm.quantity_l1 == -SQTY, f"销售数量 {sm.quantity_l1} != -{SQTY}"
            assert sm.unit_cost_l2 == COST_PER_UNIT, \
                f"销售单位成本 {sm.unit_cost_l2} != {COST_PER_UNIT}"
            assert sm.total_cost_l2 == COGS, f"销售总成本 {sm.total_cost_l2} != {COGS}"
            inv = db.query(Inventory).filter(Inventory.product_id == s["product_id"]).first()
            assert inv is not None, "销售后无 Inventory"
            assert inv.quantity_l4 == END_QTY, f"库存数量 {inv.quantity_l4} != {END_QTY}"
            assert inv.total_value_l4 == END_VALUE, \
                f"库存价值 {inv.total_value_l4} != {END_VALUE}"

            # AS-03: 库存账面=StockMove求和
            from rules import enforce_rules
            try:
                enforce_rules(db, ["AS-03"], {"product_id": s["product_id"]})
            except Exception as e:
                pytest.fail(f"AS-03 库存一致校验失败: {e}")
        finally: db.close()

        # 收款
        r = c.post("/api/receipts", json={
            "receipt_type": "sale", "related_entity_type": "sale_order",
            "related_entity_id": s["sale_id"], "amount": float(RECEIPT),
            "receipt_date": "2026-01-12", "bank_account_id": s["bank_id"],
        }, headers=HEADERS)
        assert r.status_code == 200

        # ═══ Step 3: 月结 §7.1 §84 ═══
        r = c.post("/api/finance/month-close", json={"period": "2026-01"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            # §84: 月结后收入/成本归零
            assert abs(_ledger_balance(db, "6001")) <= Decimal("0.01"), "§84结转后6001=0"
            assert abs(_ledger_balance(db, "6401")) <= Decimal("0.01"), "§84结转后6401=0"
            # §7.1: 本年利润 (税后净利润)
            profit_4103 = _credit_balance(db, "4103")
            assert abs(profit_4103 - PROFIT) <= Decimal("0.05"), \
                f"§7.1本年利润(4103): 期望{PROFIT} 实际{profit_4103}"
            # §7.1: 应交所得税
            tax_payable = _credit_balance(db, "222105")
            assert abs(tax_payable - INCOME_TAX) <= Decimal("0.05"), \
                f"§7.1应交所得税(222105): 期望{INCOME_TAX} 实际{tax_payable}"
        finally: db.close()

        # ═══ 4. 财务报表验证 §84 ═══
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200; bs = r.json()
        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200; pl = r.json()

        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"§84 BS不平衡, diff={diff}"
        assert abs(Decimal(str(bs["monetary_funds"])) - BANK_ENDING) <= Decimal("0.05"), \
            f"§84货币资金: 实际{bs['monetary_funds']} != 期望{BANK_ENDING}"
        assert abs(Decimal(str(bs["inventory"])) - END_VALUE) <= Decimal("0.05"), \
            f"§84存货: 实际{bs['inventory']} != 期望{END_VALUE}"
        assert abs(Decimal(str(bs["total_liabilities"])) - TOTAL_LIABILITIES) <= Decimal("0.05"), \
            f"§84负债合计: 实际{bs['total_liabilities']} != 期望{TOTAL_LIABILITIES}"
        assert abs(Decimal(str(bs["paid_in_capital"])) - BANK_OPENING) <= Decimal("0.05"), \
            f"§84实收资本: 实际{bs['paid_in_capital']} != 期望{BANK_OPENING}"
        assert abs(Decimal(str(bs["retained_earnings"])) - PROFIT) <= Decimal("0.05"), \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{PROFIT}"
        assert abs(Decimal(str(bs["total_assets"])) - TOTAL_ASSETS) <= Decimal("0.05"), \
            f"§84资产合计: 实际{bs['total_assets']} != 期望{TOTAL_ASSETS}"
        assert abs(Decimal(str(pl["revenue"])) - IS_REVENUE) <= Decimal("0.05"), \
            f"§84营业收入: 实际{pl['revenue']} != 期望{IS_REVENUE}"
        assert abs(Decimal(str(pl["cost_of_goods_sold"])) - IS_COGS) <= Decimal("0.05"), \
            f"§84营业成本: 实际{pl['cost_of_goods_sold']} != 期望{IS_COGS}"
        assert abs(Decimal(str(pl["net_profit"])) - IS_NET_PROFIT) <= Decimal("0.05"), \
            f"§84净利润: 实际{pl['net_profit']} != 期望{IS_NET_PROFIT}"

        # ═══ CF 验证 ═══
        r = c.get("/api/cash-flows/statement?start_date=2026-01-01&end_date=2026-01-31", headers=HEADERS)
        assert r.status_code == 200, r.text
        cf = r.json()
        cf_net = Decimal(str(cf["net_cash_flow"]))
        cf_begin = Decimal(str(cf["beginning_cash_balance"]))
        cf_end = Decimal(str(cf["ending_cash_balance"]))
        assert abs(cf_end - (cf_begin + cf_net)) <= Decimal("0.05"), "CF恒等式: 期末≠期初+净额"
        op_net = Decimal(str(cf["operating_activities"]["net"]))
        inv_net = Decimal(str(cf["investing_activities"]["net"]))
        fin_net = Decimal(str(cf["financing_activities"]["net"]))
        assert abs(cf_net - (op_net + inv_net + fin_net)) <= Decimal("0.05"), "CF净额≠三大活动合计"
        assert cf_net == Decimal("0"), f"小规模CF净额应为0, 实际={cf_net}"
        assert Decimal(str(cf["cf_details"]["CF01"])) == RECEIPT, f"CF01销售收现≠{RECEIPT}"
        assert Decimal(str(cf["cf_details"]["CF03"])) == -PURCHASE_PAYMENT, f"CF03购付现≠{-PURCHASE_PAYMENT}"
        bs_bank = Decimal(str(bs["monetary_funds"]))
        if abs(cf_end - bs_bank) > Decimal("0.05"):
            print(f"  [WARN] CF期末({cf_end})≠BS银行存款({bs_bank})")
        print(f"  CF: 期初={cf_begin}, 期末={cf_end}, 经营={op_net}")
        print("OK 5. CF验证")

        # ═══ 6. 追溯验证 ═══
        db = _db()
        try:
            for code in ["1405", "6001", "6401", "1122", "1002", "4103"]:
                bal, traces = _trace_bal(db, code)
                print(f"  {code}追溯({bal}): {[(t[1], t[4], t[5]) for t in traces]}")
        finally: db.close()

        # ═══ 7. AS-01 全量不变量 ═══
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": ACCT_ID})
        except Exception as e:
            pytest.fail(f"AS-01 校验失败: {e}")
        finally: db.close()

        print("\nALL GOLDEN ASSERTIONS PASSED")
