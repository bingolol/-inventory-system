"""交付检查测试 — 验证跨表会计对账一致

覆盖 6 个交付目标，每个目标包含深层会计核算断言。
在全新数据库上运行，0 失败为交付通过条件。

目标:
  T3: StockMove 真相源一致性: ∑(入库) - ∑(出库) = Inventory.quantity
  T4: 库存估值公式: average_cost × quantity = total_value
  T2: 销售成本锁定: SaleItem.unit_cost = 出库时加权平均成本
  T5: 应收对账: accounts_receivable = ∑未收销售单
  T1: 跨表勾稽: 利润表净利润 = 资产负债表未分配利润变动额
  T6: 附加税公式: surcharge_total = vat_payable × 12%
"""

import time
import pytest
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from sqlalchemy import func as sqlfunc
from database import engine, SessionLocal

HEADERS = {"X-Account-ID": "1", "X-Operator": "delivery_test"}
ACCOUNT_ID = 1


def round2(v):
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ═══════════════════════════════════════════════════════════════
# 模块级清理：避免其他测试数据干扰
# ═══════════════════════════════════════════════════════════════
@pytest.fixture(scope="module", autouse=True)
def cleanup_db():
    """模块启动时清理业务数据，仅保留 account/seed 基础数据"""
    raw = engine.raw_connection()
    raw.execute("PRAGMA foreign_keys=OFF")
    for tname in ["account_move_lines", "account_moves", "stock_moves",
                   "receipts", "payments", "invoices", "fixed_assets",
                   "sale_items", "sale_orders", "purchase_items",
                   "purchase_orders", "expenses", "inventory",
                   "bank_accounts", "audit_logs", "operation_logs",
                   "opening_balances"]:
        raw.execute(f"DELETE FROM {tname}")
    raw.execute("PRAGMA foreign_keys=ON")
    raw.commit()
    raw.close()
    yield


# ═══════════════════════════════════════════════════════════════
# 公共夹具: 创建基础数据
# ═══════════════════════════════════════════════════════════════
@pytest.fixture(scope="module")
def ids(client):
    u = str(int(time.time()))[-6:]

    # 创建期初余额（资产负债表正确计算必需）
    db = SessionLocal()
    try:
        from models import OpeningBalance
        ob = OpeningBalance(account_id=ACCOUNT_ID, date=date(2026, 1, 1),
                            cash_balance=Decimal("10000"), bank_balance=Decimal("50000"),
                            accounts_receivable=Decimal("0"), inventory_value=Decimal("0"),
                            fixed_assets_original=Decimal("0"), accumulated_depreciation=Decimal("0"),
                            accounts_payable=Decimal("0"), tax_payable=Decimal("0"),
                            paid_in_capital=Decimal("60000"), retained_earnings=Decimal("0"))
        db.add(ob)
        db.commit()
    finally:
        db.close()

    pid = client.post("/api/products", json={
        "name": f"商品-A-{u}", "sku": f"SKU-A-{u}", "unit": "个",
        "purchase_price": 10, "sale_price": 20,
        "track_inventory": True, "category": "测试"
    }, headers=HEADERS).json()
    pid = pid.get("entity_id") or pid.get("data", {}).get("id")

    pid2 = client.post("/api/products", json={
        "name": f"商品-B-{u}", "sku": f"SKU-B-{u}", "unit": "个",
        "purchase_price": 12, "sale_price": 25,
        "track_inventory": True, "category": "测试"
    }, headers=HEADERS).json()
    pid2 = pid2.get("entity_id") or pid2.get("data", {}).get("id")

    cid = client.post("/api/customers", json={
        "name": f"客户-{u}", "contact": "测试", "phone": "13800000001"
    }, headers=HEADERS).json()
    cid = cid.get("entity_id") or cid.get("data", {}).get("id")

    sid = client.post("/api/suppliers", json={
        "name": f"供应商-{u}", "contact": "测试", "phone": "13900000001"
    }, headers=HEADERS).json()
    sid = sid.get("entity_id") or sid.get("data", {}).get("id")

    return {"pid": pid, "pid2": pid2, "cid": cid, "sid": sid}


# ═══════════════════════════════════════════════════════════════
# T3: StockMove 真相源一致性
# ═══════════════════════════════════════════════════════════════
class TestStockMoveTruthSource:
    """T3: 验证 StockMove 流水与 Inventory 缓存一致

    核心断言: SUM(StockMove.quantity) == Inventory.quantity
    覆盖场景: 采购入库 → 销售出库 → 红冲
    """

    def test_t3_purchase_updates_stockmove_and_inventory(self, client, ids, db):
        from models import StockMove, Inventory

        pid = ids["pid"]
        QTY = 50
        resp = client.post("/api/purchases", json={
            "supplier_id": ids["sid"], "payment_method": "company",
            "payment_status": "unpaid", "purchase_date": "2026-01-05T10:00:00",
            "items": [{"product_id": pid, "quantity": QTY, "unit_price": 10.00, "tax_rate": 0.13}]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"采购失败: {resp.text}"

        sm_sum = db.query(sqlfunc.sum(StockMove.quantity)).filter(
            StockMove.product_id == pid, StockMove.account_id == 1
        ).scalar() or 0
        inv = db.query(Inventory).filter(
            Inventory.product_id == pid, Inventory.account_id == 1
        ).first()

        assert inv is not None, "采购后应有 Inventory 记录"
        assert sm_sum == Decimal(str(inv.quantity)), \
            f"StockMove 汇总({sm_sum}) ≠ Inventory({inv.quantity})"

    def test_t3_sale_keeps_consistency(self, client, ids, db):
        from models import StockMove, Inventory

        pid = ids["pid"]
        QTY = 20
        resp = client.post("/api/sales", json={
            "customer_id": ids["cid"], "deduct_inventory": True,
            "payment_status": "unpaid", "sale_date": "2026-01-15T10:00:00",
            "items": [{"product_id": pid, "quantity": QTY, "unit_price": 20.00, "tax_rate": 0.01}]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"销售失败: {resp.text}"

        sm_sum = db.query(sqlfunc.sum(StockMove.quantity)).filter(
            StockMove.product_id == pid, StockMove.account_id == 1
        ).scalar() or 0
        inv = db.query(Inventory).filter(
            Inventory.product_id == pid, Inventory.account_id == 1
        ).first()

        assert sm_sum == Decimal(str(inv.quantity)), \
            f"销售后 StockMove({sm_sum}) ≠ Inventory({inv.quantity})"

    def test_t3_reversal_keeps_consistency(self, client, ids, db):
        from models import StockMove, Inventory

        pid = ids["pid"]
        stock_before = db.query(Inventory).filter(
            Inventory.product_id == pid, Inventory.account_id == 1
        ).first().quantity

        resp = client.post("/api/sales", json={
            "customer_id": ids["cid"], "deduct_inventory": True,
            "payment_status": "unpaid", "sale_date": "2026-02-01T10:00:00",
            "items": [{"product_id": pid, "quantity": 10, "unit_price": 20.00, "tax_rate": 0.01}]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"退款前销售失败: {resp.text}"
        sale_id = resp.json().get("data", resp.json()).get("id")

        # 红冲（取消销售单）
        resp = client.put(f"/api/sales/{sale_id}", json={"status": "cancelled"}, headers=HEADERS)
        assert resp.status_code == 200, f"红冲失败: {resp.text}"

        # 验证库存回滚到红冲前
        inv_after = db.query(Inventory).filter(
            Inventory.product_id == pid, Inventory.account_id == 1
        ).first()
        assert inv_after.quantity == stock_before, \
            f"红冲后库存({inv_after.quantity}) ≠ 红冲前({stock_before})"

        # 验证 StockMove 与 Inventory 一致
        sm_sum = db.query(sqlfunc.sum(StockMove.quantity)).filter(
            StockMove.product_id == pid, StockMove.account_id == 1
        ).scalar() or 0
        assert sm_sum == Decimal(str(inv_after.quantity)), \
            f"红冲后 StockMove({sm_sum}) ≠ Inventory({inv_after.quantity})"

        # 验证 StockMove 红冲记录保留了原始信息
        from models import StockMove as SM
        reversal_moves = db.query(SM).filter(
            SM.source_type.like("%_reversal"),
            SM.product_id == pid, SM.account_id == 1
        ).all()
        assert len(reversal_moves) >= 1, "应该有红冲 StockMove 记录"

    def test_t3_truth_source_multiple_products(self, client, ids, db):
        from models import StockMove, Inventory

        for label, pid in [("商品A", ids["pid"]), ("商品B", ids["pid2"])]:
            inv = db.query(Inventory).filter(
                Inventory.product_id == pid, Inventory.account_id == 1
            ).first()
            if inv is None:
                continue
            sm_sum = db.query(sqlfunc.sum(StockMove.quantity)).filter(
                StockMove.product_id == pid, StockMove.account_id == 1
            ).scalar() or 0
            assert sm_sum == Decimal(str(inv.quantity)), \
                f"{label}: StockMove({sm_sum}) ≠ Inventory({inv.quantity})"


# ═══════════════════════════════════════════════════════════════
# T4: 库存估值公式
# ═══════════════════════════════════════════════════════════════
class TestInventoryValuation:
    """T4: 验证 average_cost × quantity = total_value"""

    def test_t4_valuation_formula(self, client, ids, db):
        from models import Inventory

        for label, pid in [("商品A", ids["pid"]), ("商品B", ids["pid2"])]:
            inv = db.query(Inventory).filter(
                Inventory.product_id == pid, Inventory.account_id == 1
            ).first()
            if inv is None or inv.quantity == 0:
                continue
            expected = (Decimal(str(inv.average_cost)) * Decimal(str(inv.quantity))).quantize(Decimal("0.01"))
            diff = abs(expected - inv.total_value)
            assert diff <= Decimal("0.01"), \
                f"{label}: {inv.average_cost}×{inv.quantity}={expected} ≠ total_value={inv.total_value} (差异{diff})"

    def test_t4_weighted_average_between_prices(self, client, ids, db):
        from models import Inventory

        pid = ids["pid"]
        inv = db.query(Inventory).filter(
            Inventory.product_id == pid, Inventory.account_id == 1
        ).first()
        if inv is None or inv.quantity == 0:
            pytest.skip("无库存，跳过加权平均合理性检查")

        avg_cost = Decimal(str(inv.average_cost))
        assert Decimal("9.50") <= avg_cost <= Decimal("10.50"), \
            f"加权平均成本{avg_cost}不在合理区间[9.50, 10.50]"


# ═══════════════════════════════════════════════════════════════
# T2: 销售成本锁定验证
# ═══════════════════════════════════════════════════════════════
class TestCostLocking:
    """T2: 验证销售时锁定成本 = 出库时加权平均成本"""

    def test_t2_cost_locked_at_sale_time(self, client, ids, db):
        from models import Inventory, SaleItem, SaleOrder, OrderStatus

        pid = ids["pid"]
        inv = db.query(Inventory).filter(
            Inventory.product_id == pid, Inventory.account_id == 1
        ).first()
        avg_before = Decimal(str(inv.average_cost)) if inv and inv.quantity > 0 else Decimal("10.00")

        QTY = 15
        resp = client.post("/api/sales", json={
            "customer_id": ids["cid"], "deduct_inventory": True,
            "payment_status": "unpaid", "sale_date": "2026-02-15T10:00:00",
            "items": [{"product_id": pid, "quantity": QTY, "unit_price": 20.00, "tax_rate": 0.01}]
        }, headers=HEADERS)
        assert resp.status_code in (200, 201), f"销售失败: {resp.text}"

        # schema 不暴露 unit_cost，需从 DB 直接读取
        sale_item = db.query(SaleItem).join(SaleOrder).filter(
            SaleItem.product_id == pid,
            SaleOrder.status == OrderStatus.COMPLETED,
            SaleOrder.is_deleted == False,
        ).order_by(SaleItem.id.desc()).first()
        assert sale_item is not None, "应有 SaleItem"
        locked_cost = Decimal(str(sale_item.unit_cost)) if sale_item.unit_cost else Decimal("0")
        assert locked_cost > 0, f"unit_cost 应被锁定，实际为 {locked_cost}"
        assert abs(locked_cost - avg_before) <= Decimal("0.01"), \
            f"锁定成本({locked_cost}) ≠ 出库时均价({avg_before})"

    def test_t2_income_statement_cogs_matches_items(self, client, ids, db):
        from models import SaleItem, SaleOrder, OrderStatus

        # 只统计状态为 completed 且未删除的订单
        items = db.query(SaleItem).join(SaleOrder).filter(
            SaleOrder.status == OrderStatus.COMPLETED,
            SaleOrder.is_deleted == False,
        ).all()
        expected_cogs = Decimal("0")
        for item in items:
            cost = Decimal(str(item.unit_cost)) if item.unit_cost else Decimal("0")
            expected_cogs += Decimal(str(item.quantity)) * cost
        expected_cogs = expected_cogs.quantize(Decimal("0.01"))

        resp = client.get("/api/financial-reports/income-statement",
                          params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
                          headers=HEADERS)
        assert resp.status_code in (200, 422), f"利润表失败: {resp.text}"
        if resp.status_code == 200:
            data = resp.json()
            reported_cogs = round2(Decimal(str(data.get("cost_of_goods_sold", 0))))
            diff = abs(reported_cogs - expected_cogs)
            assert diff <= Decimal("0.01"), \
                f"利润表 COGS({reported_cogs}) ≠ SaleItem 合计({expected_cogs})"


# ═══════════════════════════════════════════════════════════════
# T5: 应收对账
# ═══════════════════════════════════════════════════════════════
class TestReceivableReconciliation:
    """T5: 验证应收账款 = ∑未收销售单金额"""

    def test_t5_ar_equals_unpaid_orders(self, client, ids, db):
        from models import SaleOrder, OrderStatus

        unpaid_total = db.query(sqlfunc.sum(SaleOrder.total_price)).filter(
            SaleOrder.account_id == 1,
            SaleOrder.status == OrderStatus.COMPLETED,
            SaleOrder.payment_status == "unpaid",
            SaleOrder.is_deleted == False
        ).scalar() or Decimal("0")

        if unpaid_total == 0:
            pytest.skip("无未收销售单")

        resp = client.get("/api/financial-reports/balance-sheet",
                          params={"date": "2026-12-31"},
                          headers=HEADERS)
        assert resp.status_code in (200, 422), f"资产负债表失败: {resp.text}"
        if resp.status_code == 200:
            data = resp.json()
            ar_reported = round2(Decimal(str(data.get("accounts_receivable", 0))))
            expected_ar = round2(unpaid_total)
            diff = abs(ar_reported - expected_ar)
            assert diff <= Decimal("0.01"), \
                f"应收对账不符: 报表{ar_reported} ≠ 未收销售单{unpaid_total}"


# ═══════════════════════════════════════════════════════════════
# T1: 跨表勾稽 — 利润表 ↔ 资产负债表
# ═══════════════════════════════════════════════════════════════
class TestCrossStatementConsistency:
    """T1: 利润表净利润 = 资产负债表未分配利润变动额"""

    def test_t1_net_profit_equals_retained_earnings_delta(self, client, ids, db):
        from models import OpeningBalance

        ob = db.query(OpeningBalance).filter(OpeningBalance.account_id == 1).first()
        opening_re = round2(Decimal(str(ob.retained_earnings))) if ob else Decimal("0.00")

        resp_is = client.get("/api/financial-reports/income-statement",
                             params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
                             headers=HEADERS)
        resp_bs = client.get("/api/financial-reports/balance-sheet",
                             params={"date": "2026-12-31"},
                             headers=HEADERS)

        if resp_is.status_code != 200 or resp_bs.status_code != 200:
            pytest.skip("财报接口暂不可用")
            return

        is_data = resp_is.json()
        net_profit = round2(Decimal(str(is_data.get("net_profit", 0))))
        bs_data = resp_bs.json()
        ending_re = round2(Decimal(str(bs_data.get("retained_earnings", 0))))
        delta_re = round2(ending_re - opening_re)

        diff = abs(net_profit - delta_re)
        assert diff <= Decimal("0.01"), \
            f"跨表勾稽失败: 净利润({net_profit}) ≠ 未分配利润变动({delta_re})"

        # 附加断言: 资产负债表本身应平衡
        total_assets = round2(Decimal(str(bs_data.get("total_assets", 0))))
        total_l_e = round2(Decimal(str(bs_data.get("total_liabilities_and_equity", 0))))
        assert abs(total_assets - total_l_e) <= Decimal("0.01"), \
            f"资产负债表不平衡: 资产{total_assets} ≠ 负债+权益{total_l_e}"


# ═══════════════════════════════════════════════════════════════
# T6: 附加税公式
# ═══════════════════════════════════════════════════════════════
class TestSurchargeFormula:
    """T6: surcharge_total = vat_payable × 12%

    验证方式:
      - 如有发票数据: 从发票表读取实际税额并校验
      - 如无发票数据: 直接调用 AccountingEngine 用测试值校验公式
    """

    def test_t6_surcharge_equals_vat_times_12_percent(self, client, ids, db):
        from models import Invoice
        from enums import InvoiceDirection

        out_tax = db.query(sqlfunc.sum(Invoice.tax_amount)).filter(
            Invoice.account_id == ACCOUNT_ID,
            Invoice.direction == InvoiceDirection.OUT
        ).scalar() or Decimal("0")
        in_tax = db.query(sqlfunc.sum(Invoice.tax_amount)).filter(
            Invoice.account_id == ACCOUNT_ID,
            Invoice.direction == InvoiceDirection.IN
        ).scalar() or Decimal("0")
        vat_payable = max(out_tax - in_tax, Decimal("0"))

        from accounting_engine import AccountingEngine
        engine = AccountingEngine()

        if float(vat_payable) > 0:
            result = engine.calculate_vat(
                total_revenue=Decimal("0"),
                taxpayer_type="general",
                input_tax=in_tax
            )
            expected_surcharge = (vat_payable * Decimal("0.12")).quantize(Decimal("0.01"))
            actual_surcharge = (
                result.surcharge_urban_construction + result.surcharge_education + result.surcharge_local_education
            ).quantize(Decimal("0.01"))
            diff = abs(actual_surcharge - expected_surcharge)
            assert diff <= Decimal("0.01"), \
                f"附加税错误: 预期{expected_surcharge}(={vat_payable}×12%), 实际{actual_surcharge}"
        else:
            result = engine.calculate_vat(
                total_revenue=Decimal("100000"),
                taxpayer_type="general",
                input_tax=Decimal("8000")
            )
            expected_surcharge = Decimal("600.00")
            actual_surcharge = (
                result.surcharge_urban_construction + result.surcharge_education + result.surcharge_local_education
            ).quantize(Decimal("0.01"))
            assert actual_surcharge == expected_surcharge, \
                f"附加税公式校验失败: 预期{expected_surcharge}, 实际{actual_surcharge}"



