"""
GOLDEN TEST 002 — 退货与红冲，逐条对照小企业会计准则

【准则覆盖】§1.3 存货成本, §5.1 销售收入, §7.1 营业成本, §31 折旧, §84 报表
【AS规则】 AS-01 借贷平衡, AS-02 价税分离, AS-03 库存一致, AS-05 折旧公式
"""
import pytest
from decimal import Decimal

pytestmark = pytest.mark.golden

from main import app
from database import get_db, Base, init_db
import database
import models
from models import StockMove, Inventory
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from helpers import (
    make_engine, _ledger_balance as _lb, _credit_balance as _cb,
    _trace_bal, _get_id, _assert_move_lines,
)
from policy.vat_facts import VAT_GENERAL_DEFAULT_RATE
from policy.income_tax_facts import INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE

_engine, _SessionLocal = make_engine()
AID, H = 1, {"X-Account-ID": "1", "X-Operator": "golden_test"}

def _db(): return _SessionLocal()

# ═══ L1 原始凭证 ═══
QTY = 10; UC = Decimal("100")
TAX = VAT_GENERAL_DEFAULT_RATE.value                    # §1.3: 合法税率13% (L3 政策)
RQTY = 2; SQTY = 5; UP = Decimal("200")
EXP = Decimal("100"); AFC = Decimal("2000"); AFM = 60  # 60月=5年
ADM = (AFC / Decimal(str(AFM))).quantize(Decimal("0.01"))  # §31: 月折旧 = 原值÷月数

# ═══ L2 手工帐 = §小企业会计准则 ═══
AMT = QTY * UC                                                    # §1.3: 存货成本 1000
TAXAMT = (AMT * TAX).quantize(Decimal("0.01"))                    # 130
TOT = AMT + TAXAMT                                                # 1130
RATIO = Decimal(str(RQTY)) / Decimal(str(QTY))                    # 0.2
RAMT = (AMT * RATIO).quantize(Decimal("0.01"))                    # §1.3退货: 200
RTAX = (TAXAMT * RATIO).quantize(Decimal("0.01"))                 # 26
RTOT = RAMT + RTAX                                                # 226
PAY = TOT - RTOT                                                  # 904
COGS = UC * SQTY                                                  # §7.1: 500
REV = SQTY * UP                                                   # §5.1: 1000
OTAX = (REV * TAX).quantize(Decimal("0.01"))                      # 130
AR = REV + OTAX                                                   # 1130
PROFIT_BEFORE_TAX = (REV - COGS - EXP - ADM).quantize(Decimal("0.01"))  # §7.1: 366.67
# 小微企业实际所得税负 5%（L3 政策: income_tax_facts.py）
INCOME_TAX = (PROFIT_BEFORE_TAX * INCOME_TAX_SMALL_MICRO_EFFECTIVE_RATE.value).quantize(Decimal("0.01"))  # 18.33
PROFIT = (PROFIT_BEFORE_TAX - INCOME_TAX).quantize(Decimal("0.01"))  # 348.34
ENDQ = QTY - RQTY - SQTY; ENDV = UC * ENDQ                        # 3件, 300
BANK = Decimal("10000") - PAY + AR - EXP

# 资产负债表
ASSET_NET = AFC - ADM  # §31: 1966.67
TOTAL_ASSETS = BANK + ENDV + ASSET_NET
TOTAL_LIABILITIES = AFC + OTAX - (TAXAMT - RTAX) + INCOME_TAX  # §1.3: 2044.33
# 验证: 资产 = 负债 + 权益
assert TOTAL_ASSETS == (TOTAL_LIABILITIES + Decimal("10000") + PROFIT).quantize(Decimal("0.01"))


class TestGolden002:
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
            acc.taxpayer_type_l3 = "general"; acc.enable_vat_deduction = True
            db.commit()
        finally: db.close()
        def _g():
            db = _SessionLocal()
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db] = _g
        yield
        Base.metadata.drop_all(bind=_engine)
        app.dependency_overrides.clear()

    def test_returns_compliance(self, client):
        c = client; s = {}

        # 期初
        r = c.post("/api/bank-accounts", json={
            "bank_name":"t","account_number":"62222","balance":0}, headers=H)
        assert r.status_code == 200; s["bk"] = r.json().get("entity",r.json())["id"]
        r = c.post("/api/opening-balances", json={
            "date":"2026-01-01","cash_balance":0,"bank_balance":10000,
            "accounts_receivable":0,"inventory_value":0,"fixed_assets_original":0,
            "accumulated_depreciation":0,"intangible_assets_original":0,
            "accumulated_amortization":0,"accounts_payable":0,"tax_payable":0,
            "long_term_borrowings":0,"paid_in_capital":10000,"retained_earnings":0,
        }, headers=H); assert r.status_code == 200

        r = c.post("/api/products", json={
            "name":"P","sku":"R","category":"原","unit":"件",
            "purchase_price":100,"sale_price":200,"min_stock":0,"track_inventory":True,
        }, headers=H); assert r.status_code == 200
        s["p"] = r.json().get("entity",r.json()).get("entity_id")
        r = c.post("/api/suppliers", json={"name":"S"}, headers=H)
        s["s"] = r.json().get("entity",r.json()).get("entity_id")
        r = c.post("/api/customers", json={"name":"C"}, headers=H)
        s["c"] = r.json().get("entity",r.json()).get("entity_id")

        # 1. 采购入库 §1.3
        r = c.post("/api/purchases", json={
            "supplier_id":s["s"],
            "items":[{"product_id":s["p"],"quantity":QTY,"unit_price":100,"tax_rate":float(TAX)}],
            "purchase_date":"2026-01-05",
        }, headers=H); assert r.status_code == 200, r.text
        s["po"] = r.json().get("entity",r.json()).get("entity_id")

        db = _db()
        try:
            assert _lb(db,"1405") == AMT, f"§1.3库存: 期{AMT} 实{_lb(db,'1405')}"
            assert _lb(db,"222102") == TAXAMT, f"§1.3进项: 期{TAXAMT} 实{_lb(db,'222102')}"
            assert _cb(db,"2202") == TOT, f"§1.3应付: 期{TOT} 实{_cb(db,'2202')}"

            # L3: StockMove 真相源
            sm = db.query(StockMove).filter(
                StockMove.source_type == "purchase_order",
                StockMove.source_id == s["po"],
            ).first()
            assert sm is not None, "采购无 StockMove"
            assert sm.quantity_l1 == QTY, f"采购数量 {sm.quantity_l1} != {QTY}"
            assert sm.unit_cost_l2 == UC, f"采购单位成本 {sm.unit_cost_l2} != {UC}"
            assert sm.total_cost_l2 == AMT, f"采购总成本 {sm.total_cost_l2} != {AMT}"
            inv = db.query(Inventory).filter(Inventory.product_id == s["p"]).first()
            assert inv is not None, "采购后无 Inventory 缓存"
            assert inv.quantity_l4 == QTY, f"库存数量 {inv.quantity_l4} != {QTY}"
            assert inv.average_cost_l4 == UC, f"库存均价 {inv.average_cost_l4} != {UC}"
        finally: db.close()

        # 2. 录进项发票 (退货前提) — AS-02 价税分离
        r = c.post("/api/invoices/quick", json={
            "invoice_no":"INV-R02-IN","direction":"in","invoice_type":"special",
            "seller_name":"S","buyer_name":"本公司",
            "amount_without_tax":float(AMT),"tax_rate":float(TAX),"tax_amount":float(TAXAMT),
            "amount_with_tax":float(TOT),"counterparty_name":"S",
            "issue_date":"2026-01-05","related_order_id":s["po"],
            "related_order_type":"purchase_order","certification_status":"certified",
            "purchase_order_action":"link_existing",
            "items":[{"product_id":s["p"],"quantity":QTY,"unit_price":100,"tax_rate":float(TAX)}],
        }, headers=H)
        assert r.status_code in (200,201), f"Invoice fail: {r.text}"
        s["inv"] = _get_id(r, "invoice")

        # AS-02: 价税分离校验
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-02"], {"invoice_id": s["inv"]})
        except Exception as e:
            pytest.fail(f"AS-02 价税分离校验失败: {e}")
        finally: db.close()

        # 3. 采购退货 §1.3 进货退出扣减
        r = c.post(f"/api/purchases/{s['po']}/return", json={
            "return_date":"2026-01-06","reason":"质量",
            "items":[{"product_id":s["p"],"quantity":RQTY}],
        }, headers=H)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            assert _lb(db,"1405") == AMT - RAMT, f"§1.3退货后库存: {_lb(db,'1405')}"
            assert _lb(db,"222102") == TAXAMT - RTAX, f"§1.3退货后进项: {_lb(db,'222102')}"
        finally: db.close()

        # 4. 付款
        r = c.post("/api/payments", json={
            "payment_type":"purchase","related_entity_type":"purchase_order",
            "related_entity_id":s["po"],"amount":float(PAY),
            "payment_date":"2026-01-07","bank_account_id":s["bk"],
        }, headers=H); assert r.status_code == 200

        # 5. 销售出库 §5.1 §7.1
        r = c.post("/api/sales", json={
            "customer_id":s["c"],
            "items":[{"product_id":s["p"],"quantity":SQTY,"unit_price":200,"tax_rate":float(TAX)}],
            "sale_date":"2026-01-10","deduct_inventory":True,
        }, headers=H); assert r.status_code == 200, r.text
        s["so"] = r.json().get("entity",r.json()).get("entity_id")

        db = _db()
        try:
            assert _lb(db,"6401") == COGS, f"§7.1成本: 期{COGS} 实{_lb(db,'6401')}"
            assert -_lb(db,"6001") == REV, f"§5.1收入: 期{REV} 实{-_lb(db,'6001')}"
            assert -_lb(db,"222101") == OTAX, f"§5.1销项: 期{OTAX} 实{-_lb(db,'222101')}"
            assert _lb(db,"1122") == AR, f"§5.1应收: 期{AR} 实{_lb(db,'1122')}"

            # L3: StockMove 真相源
            sm = db.query(StockMove).filter(
                StockMove.source_type == "sale_order",
                StockMove.source_id == s["so"],
            ).first()
            assert sm is not None, "销售无 StockMove"
            assert sm.quantity_l1 == -SQTY, f"销售数量 {sm.quantity_l1} != -{SQTY}"
            assert sm.unit_cost_l2 == UC, f"销售单位成本 {sm.unit_cost_l2} != {UC}"
            assert sm.total_cost_l2 == COGS, f"销售总成本 {sm.total_cost_l2} != {COGS}"
            inv = db.query(Inventory).filter(Inventory.product_id == s["p"]).first()
            assert inv is not None, "销售后无 Inventory 缓存"
            assert inv.quantity_l4 == ENDQ, f"库存数量 {inv.quantity_l4} != {ENDQ}"
            assert inv.total_value_l4 == ENDV, f"库存价值 {inv.total_value_l4} != {ENDV}"

            # AS-03: 库存账面=StockMove求和
            enforce_rules(db, ["AS-03"], {"product_id": s["p"]})
        except Exception as e:
            if "AS-03" in str(e) or "AS-02" in str(e):
                pytest.fail(f"AS规则校验失败: {e}")
            raise
        finally: db.close()

        # 6. 收款
        r = c.post("/api/receipts", json={
            "receipt_type":"sale","related_entity_type":"sale_order",
            "related_entity_id":s["so"],"amount":float(AR),
            "receipt_date":"2026-01-13","bank_account_id":s["bk"],
        }, headers=H); assert r.status_code == 200

        # 7. 费用 §6.1
        r = c.post("/api/expenses", json={
            "category":"办公用品","functional_category":"管理费用",
            "amount":float(EXP),"expense_date":"2026-01-15","payment_method":"company",
        }, headers=H); assert r.status_code == 200
        ex_id = r.json().get("entity",r.json()).get("entity_id")
        r = c.post("/api/payments", json={
            "payment_type":"expense","related_entity_type":"expense",
            "related_entity_id":ex_id,"amount":float(EXP),
            "payment_date":"2026-01-15","bank_account_id":s["bk"],
        }, headers=H); assert r.status_code == 200

        # 8. 固资 §31
        r = c.post("/api/fixed-assets", json={
            "asset_code":"F01","name":"设备","category":"机器","original_value":float(AFC),
            "salvage_rate":0,"useful_life":AFM,"depreciation_method":"年限平均法",
            "start_date":"2025-12-01",
        }, headers=H); assert r.status_code == 200
        s["fa"] = _get_id(r, "fixed_asset")

        # 9. 月结
        r = c.post("/api/finance/month-close", json={"period":"2026-01"}, headers=H)
        assert r.status_code == 200, r.text

        db = _db()
        try:
            depr = abs(_lb(db,"1602"))
            assert abs(depr - ADM) <= Decimal("0.02"), f"§31折旧: {depr} != {ADM}"
            assert abs(_lb(db,"6001")) <= Decimal("0.01"), "§84结转后收入=0"
            assert abs(_lb(db,"6401")) <= Decimal("0.01"), "§84结转后成本=0"
            assert abs(_lb(db,"6601")) <= Decimal("0.01"), "§84结转后费用=0"
            assert abs(_lb(db,"6801")) <= Decimal("0.01"), "§84结转后所得税=0"
            profit_4103 = _cb(db, "4103")
            assert abs(profit_4103 - PROFIT) <= Decimal("0.05"), \
                f"§7.1本年利润(4103): 期望{PROFIT}, 实际{profit_4103}"
            tax_payable_222105 = _cb(db, "222105")
            assert abs(tax_payable_222105 - INCOME_TAX) <= Decimal("0.05"), \
                f"§7.1应交所得税(222105): 期望{INCOME_TAX}, 实际{tax_payable_222105}"

            # AS-05: 折旧公式校验
            enforce_rules(db, ["AS-05"], {"asset_id": s["fa"]})
        except Exception as e:
            if "AS-05" in str(e):
                pytest.fail(f"AS-05 折旧公式校验失败: {e}")
            raise
        finally: db.close()

        # BS §84
        r = c.get("/api/financial-reports/balance-sheet?date=2026-01-31", headers=H)
        assert r.status_code == 200; bs = r.json()
        diff = abs(Decimal(str(bs["total_assets"])) - Decimal(str(bs["total_liabilities_and_equity"])))
        assert diff <= Decimal("0.05"), f"§84 BS不平衡 diff={diff}"

        assert abs(Decimal(str(bs["monetary_funds"])) - BANK) <= Decimal("0.05"), \
            f"§84货币资金: 实际{bs['monetary_funds']} != 期望{BANK}"
        assert abs(Decimal(str(bs["inventory"])) - ENDV) <= Decimal("0.05"), \
            f"§84存货: 实际{bs['inventory']} != 期望{ENDV}"
        assert abs(Decimal(str(bs["fixed_assets_net"])) - ASSET_NET) <= Decimal("0.05"), \
            f"§84固定资产净值: 实际{bs['fixed_assets_net']} != 期望{ASSET_NET}"
        assert abs(Decimal(str(bs["total_liabilities"])) - TOTAL_LIABILITIES) <= Decimal("0.05"), \
            f"§84负债合计: 实际{bs['total_liabilities']} != 期望{TOTAL_LIABILITIES}"
        assert abs(Decimal(str(bs["paid_in_capital"])) - Decimal("10000")) <= Decimal("0.05"), \
            f"§84实收资本: 实际{bs['paid_in_capital']} != 期望10000"
        assert abs(Decimal(str(bs["retained_earnings"])) - PROFIT) <= Decimal("0.05"), \
            f"§84留存收益: 实际{bs['retained_earnings']} != 期望{PROFIT}"
        assert abs(Decimal(str(bs["total_assets"])) - TOTAL_ASSETS) <= Decimal("0.05"), \
            f"§84资产合计: 实际{bs['total_assets']} != 期望{TOTAL_ASSETS}"

        # IS §84
        r = c.get("/api/financial-reports/income-statement"
                  "?start_date=2026-01-01&end_date=2026-01-31", headers=H)
        assert r.status_code == 200; pl = r.json()
        assert abs(Decimal(str(pl["revenue"])) - REV) <= Decimal("0.05"), \
            f"§84营业收入: 实际{pl['revenue']} != 期望{REV}"
        assert abs(Decimal(str(pl["cost_of_goods_sold"])) - COGS) <= Decimal("0.05"), \
            f"§84营业成本: 实际{pl['cost_of_goods_sold']} != 期望{COGS}"
        assert abs(Decimal(str(pl["income_tax_expense"])) - INCOME_TAX) <= Decimal("0.05"), \
            f"§84所得税费用: 实际{pl['income_tax_expense']} != 期望{INCOME_TAX}"
        assert abs(Decimal(str(pl["net_profit"])) - PROFIT) <= Decimal("0.05"), \
            f"§84净利润: 实际{pl['net_profit']} != 期望{PROFIT}"

        # AS-01: BS 恒等式
        from rules import enforce_rules
        db = _db()
        try:
            enforce_rules(db, ["AS-01"], {"account_id": AID})
        except Exception as e:
            pytest.fail(f"AS-01 校验失败: {e}")
        finally: db.close()

        print(f"ALL RETURNS CHECKS PASSED")
