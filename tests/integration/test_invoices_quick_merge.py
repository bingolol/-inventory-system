"""集成测试：/quick 合并 fixed_asset 能力（合并自原 POST /with-fixed-asset）

验证：
  1. POST /api/invoices/quick 携带 fixed_asset 嵌套对象 → 发票+资产原子创建，
     related_order_type=="fixed_asset"，响应 data.fixed_asset.id > 0
  2. POST /api/invoices/quick 不带 fixed_asset → 仅创建发票（回归，确认合并未破坏基础路径）
"""
import uuid
import pytest
from datetime import datetime
from database import SessionLocal
from models import Account, Invoice, FixedAsset
from test_helpers import ensure_test_product
from helpers import uniq


def _create_small_scale_account():
    """创建专用小规模纳税人账本，避免被其他测试（如 golden / general_taxpayer）共享的 account 1 影响"""
    from database import set_maintenance_mode
    from finance_integration import get_or_create_ledger_id
    set_maintenance_mode(True)
    db = SessionLocal()
    try:
        tag = uuid.uuid4().hex[:6]
        acc = Account(
            name=f"测试账本-{tag}",
            code=f"quick-test-{tag}",
            type="company",
            taxpayer_type_l3="small_scale",
        )
        db.add(acc)
        db.flush()
        get_or_create_ledger_id(db, acc.id)
        db.commit()
        return acc.id
    finally:
        db.close()
        set_maintenance_mode(False)


_SMALL_SCALE_AID = _create_small_scale_account()


def _base_invoice_payload(account_id=None):
    pid = ensure_test_product(account_id or _SMALL_SCALE_AID)
    return {
        "invoice_no": uniq("INV-QUICK"),
        "direction": "in",
        "invoice_type": "special",
        "amount_with_tax": "11300.00",
        "tax_rate": "0.13",
        "tax_amount": "1300.00",
        "counterparty_name": "测试供应商",
        "seller_name": "测试供应商",
        "buyer_name": "本公司",
        "issue_date": "2026-06-01",
        "notes": "quick 合并测试",
        "purchase_order_action": "auto_create",
        "items": [
            {"product_id": pid, "quantity": 1, "unit_price": "10000.00", "tax_rate": "0.13"}
        ]
    }


@pytest.mark.integration
class TestQuickMergeFixedAsset:
    """POST /api/invoices/quick + fixed_asset 嵌套对象"""

    def test_quick_with_fixed_asset_creates_both(self, client):
        """带 fixed_asset → 发票+资产原子创建，related_order_type==fixed_asset"""
        aid = _SMALL_SCALE_AID
        asset_code = uniq("FA-QUICK")
        payload = _base_invoice_payload(aid)
        payload["fixed_asset"] = {
            "asset_code": asset_code,
            "asset_name": "测试设备",
            "category": "电子设备",
            "salvage_rate": "0.05",
            "useful_life": 60,
            "depreciation_method": "年限平均法",
            "start_date": "2026-06-01",
            "accumulated_depreciation": "0",
            "asset_status": "在用",
        }
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        # 发票已创建并关联固定资产
        assert data["related_order_type"] == "fixed_asset"
        assert data["related_order_id"] is not None
        # 嵌套返回固定资产信息
        assert data["fixed_asset"]["id"] > 0
        assert data["fixed_asset"]["asset_code"] == asset_code
        # 本测试账本是 small_scale 纳税人，进项税不可抵扣，资产原值 = 含税金额
        assert data["fixed_asset"]["original_value"] == "11300.00"

    def test_quick_with_fixed_asset_persisted(self, client):
        """DB 中发票与资产记录关联一致"""
        aid = _SMALL_SCALE_AID
        asset_code = uniq("FA-PERSIST")
        inv_no = uniq("INV-PERSIST")
        payload = _base_invoice_payload(aid)
        payload["invoice_no"] = inv_no
        payload["fixed_asset"] = {
            "asset_code": asset_code,
            "asset_name": "持久化测试设备",
            "salvage_rate": "0.05",
            "useful_life": 36,
            "start_date": "2026-06-01",
        }
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        asset_id = r.json()["data"]["fixed_asset"]["id"]

        db = SessionLocal()
        try:
            inv = db.query(Invoice).filter(Invoice.invoice_no == inv_no).first()
            assert inv is not None
            assert inv.related_order_type == "fixed_asset"
            assert inv.related_order_id == asset_id
            asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
            assert asset is not None
            assert asset.asset_code == asset_code
            assert asset.name == "持久化测试设备"
        finally:
            db.close()

    def test_quick_without_fixed_asset_creates_invoice_only(self, client):
        """不带 fixed_asset → 仅创建发票（回归：合并未破坏基础路径）"""
        aid = _SMALL_SCALE_AID
        payload = _base_invoice_payload(aid)
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        # 进项发票自动生成采购单（不再是 None）
        assert data["related_order_type"] == "purchase_order"
        assert "fixed_asset" not in data

    def test_quick_image_url_passthrough(self, client):
        """image_url 透传到 DB（修复原 handler 丢弃 image_url 的 bug）"""
        aid = _SMALL_SCALE_AID
        inv_no = uniq("INV-IMG")
        payload = _base_invoice_payload(aid)
        payload["invoice_no"] = inv_no
        payload["image_url"] = "/uploads/invoice/test.png"
        r = client.post("/api/invoices/quick", json=payload,
                        headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code == 200, r.text
        db = SessionLocal()
        try:
            inv = db.query(Invoice).filter(Invoice.invoice_no == inv_no).first()
            assert inv is not None
            assert inv.image_url == "/uploads/invoice/test.png"
        finally:
            db.close()

    def test_with_fixed_asset_endpoint_removed(self, client):
        """原 /with-fixed-asset 端点已删除 → 404/405（前端零引用，安全删除）

        FastAPI 路由会将 /with-fixed-asset 匹配到 /api/invoices/{invoice_id}，
        但该路径只注册了 PUT/DELETE，故 POST 返回 405 Method Not Allowed；
        无论 404 还是 405 都证明专用变体端点已不存在（不再返回 200 创建）。
        """
        aid = _SMALL_SCALE_AID
        r = client.post("/api/invoices/with-fixed-asset", json={
            "invoice_no": uniq("INV-GONE"),
            "direction": "in", "invoice_type": "ordinary",
            "tax_rate": "0.13", "amount_with_tax": "1000.00",
            "counterparty_name": "x", "issue_date": "2026-06-01",
            "asset_code": uniq("FA-GONE"), "asset_name": "x",
            "useful_life": 12, "start_date": "2026-06-01",
        }, headers={"X-Account-ID": str(aid), "X-Operator": "user"})
        assert r.status_code in (404, 405)
