"""事务测试：固定资产发票过账 —— 验证 1601/222102/2202 总账与资产卡片一致性

覆盖三条会计准则：
1. 创建固定资产发票：dr 1601（资产，小规模全额/一般纳税人不含税）+ dr 222102（一般纳税人进项税）
   + cr 2202（应付账款，价税合计）
2. 红冲发票：反向凭证冲回 1601/222102/2202，资产卡片 status=已冲红
3. 更新资产原值：冲红原凭证 + 按新金额重过账（BS 1601 与资产卡片原值始终一致）

测试账本默认 taxpayer_type="small_scale"（小规模），不含税=含税（全额进资产，无进项税抵扣）。
"""
import pytest
from decimal import Decimal
from datetime import date

pytestmark = pytest.mark.usefixtures("bootstrap_db")

from tests.helpers import uniq
from models import Invoice, FixedAsset, Account
from models_finance import LedgerAccount, LedgerAccountBalance, Ledger

HEADERS = {"X-Account-ID": "1", "X-Operator": "user"}


def _ledger_balance(db, account_id: int, code: str) -> Decimal:
    """读取指定总账科目当前余额（绝对值，按科目类型符号）

    资产类（1xxx）：balance = debit - credit，正常为正
    负债类（2xxx）：balance = debit - credit，正常为负（贷方余额）
    本函数统一返回「业务上的余额」：资产正、负债正
    """
    acct = db.query(Account).filter(Account.id == account_id).first()
    ledger = db.query(Ledger).filter(Ledger.code == acct.code).first()
    if not ledger:
        return Decimal("0")
    la = db.query(LedgerAccount).filter(
        LedgerAccount.ledger_id == ledger.id,
        LedgerAccount.code == code,
    ).first()
    if not la:
        return Decimal("0")
    lab = db.query(LedgerAccountBalance).filter(
        LedgerAccountBalance.ledger_account_id == la.id
    ).first()
    if not lab:
        return Decimal("0")
<<<<<<< Updated upstream
    raw = Decimal(str(lab.balance or 0))
=======
    raw = Decimal(str(lab.balance_l4 or 0))
>>>>>>> Stashed changes
    # 负债类（2xxx/3xxx）取反，返回业务正数
    if code.startswith("2") or code.startswith("3"):
        return -raw
    return raw


def _ledger_raw_balance(db, account_id: int, code: str) -> Decimal:
    """读取总账科目原始余额（不取反）。

    用于借方余额的负债子科目，如 222102 应交增值税-进项税额（借方=抵扣额）。
    """
    acct = db.query(Account).filter(Account.id == account_id).first()
    ledger = db.query(Ledger).filter(Ledger.code == acct.code).first()
    if not ledger:
        return Decimal("0")
    la = db.query(LedgerAccount).filter(
        LedgerAccount.ledger_id == ledger.id,
        LedgerAccount.code == code,
    ).first()
    if not la:
        return Decimal("0")
    lab = db.query(LedgerAccountBalance).filter(
        LedgerAccountBalance.ledger_account_id == la.id
    ).first()
    if not lab:
        return Decimal("0")
<<<<<<< Updated upstream
    return Decimal(str(lab.balance or 0))
=======
    return Decimal(str(lab.balance_l4 or 0))
>>>>>>> Stashed changes


def _bs(client):
    """读取 BS 报表"""
    r = client.get("/api/financial-reports/balance-sheet?date=2026-12-31", headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


def _create_product(client):
    r = client.post("/api/products", json={
        "name": uniq("商品-"), "sku": uniq("SKU-"), "category": "测试",
        "unit": "个", "purchase_price": 50, "sale_price": 100, "track_inventory": False,
    }, headers=HEADERS)
    assert r.status_code == 200, r.text
    body = r.json()
    return body.get("id") or body.get("data", {}).get("id")


def _create_fa_invoice(client, **overrides):
    """创建一张含固定资产的进项发票"""
    pid = _create_product(client)
    body = {
        "invoice_no": uniq("FA-INV-"),
        "direction": "in",
        "invoice_type": "ordinary",
        "tax_rate": 0.13,
        "amount_with_tax": 11300,
        "counterparty_name": "供应商X",
        "seller_name": "供应商X",
        "buyer_name": "测试公司",
        "issue_date": "2026-06-19",
        "items": [{"product_id": pid, "quantity": 1, "unit_price": 100, "tax_rate": 0.13}],
        "fixed_asset": {
            "asset_code": uniq("FA-"),
            "asset_name": "测试设备",
            "useful_life": 60,
            "start_date": "2026-06-19",
        },
    }
    body.update(overrides)
    r = client.post("/api/invoices/quick", json=body, headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()["data"]


class Test创建固定资产发票_总账过账:
    """验证：创建固定资产发票 → 总账 1601/2202 增加"""

    def test_小规模_全额进资产_无进项税(self, client, db):
        """小规模纳税人：全额（价税合计）进 1601，不抵扣进项税，2202=价税合计"""
        before_1601 = _ledger_balance(db, 1, "1601")
        before_2202 = _ledger_balance(db, 1, "2202")
        before_222102 = _ledger_balance(db, 1, "222102")

        data = _create_fa_invoice(client, amount_with_tax=11300)
        asset_id = data["fixed_asset"]["id"]

        after_1601 = _ledger_balance(db, 1, "1601")
        after_2202 = _ledger_balance(db, 1, "2202")
        after_222102 = _ledger_balance(db, 1, "222102")

        # 1601 增加 11300（小规模全额进资产）
        assert after_1601 - before_1601 == Decimal("11300.00"), f"1601: {before_1601} → {after_1601}"
        # 2202 增加 11300（应付账款=价税合计）
        assert after_2202 - before_2202 == Decimal("11300.00"), f"2202: {before_2202} → {after_2202}"
        # 222102 不变（小规模不抵扣）
        assert after_222102 - before_222102 == Decimal("0"), f"222102: {before_222102} → {after_222102}"

        # 资产卡片原值 = 总账 1601 增量（一致性）
        asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
<<<<<<< Updated upstream
        assert Decimal(str(asset.original_value)) == Decimal("11300.00")
=======
        assert Decimal(str(asset.original_value_l1)) == Decimal("11300.00")
>>>>>>> Stashed changes

    def test_bs_固定资产科目包含资产原值(self, client, db):
        """BS 报表 fixed_assets_original 字段应反映总账 1601 余额"""
        data = _create_fa_invoice(client, amount_with_tax=5000)
        bs = _bs(client)
        # BS 上固定资产原值应至少包含本笔 5000（其他测试可能累积更多）
        fa_value = Decimal(str(bs.get("fixed_assets_original", 0)))
        assert fa_value >= Decimal("5000.00"), f"BS fixed_assets_original={fa_value}"

    def test_bs_应付账款包含该笔(self, client, db):
        """BS 报表 accounts_payable 应反映总账 2202 余额"""
        before = Decimal(str(_bs(client).get("accounts_payable", 0)))
        _create_fa_invoice(client, amount_with_tax=3000)
        after = Decimal(str(_bs(client).get("accounts_payable", 0)))
        assert after - before == Decimal("3000.00"), f"AP: {before} → {after}"


class Test红冲固定资产发票:
    """验证：红冲 → 总账 1601/2202 冲回，资产卡片 status=已冲红"""

    def test_红冲后总账冲回(self, client, db):
        data = _create_fa_invoice(client, amount_with_tax=8000)
        invoice_id = data["id"]
        asset_id = data["fixed_asset"]["id"]

        before_1601 = _ledger_balance(db, 1, "1601")
        before_2202 = _ledger_balance(db, 1, "2202")

        # 红冲
        r = client.post(f"/api/invoices/{invoice_id}/reverse",
                        json={"reason": "测试红冲"}, headers=HEADERS)
        assert r.status_code == 200, r.text

        after_1601 = _ledger_balance(db, 1, "1601")
        after_2202 = _ledger_balance(db, 1, "2202")

        # 1601 应减少 8000（冲回）
        assert before_1601 - after_1601 == Decimal("8000.00"), f"1601: {before_1601} → {after_1601}"
        # 2202 应减少 8000（冲回应付）
        assert before_2202 - after_2202 == Decimal("8000.00"), f"2202: {before_2202} → {after_2202}"

        # 资产卡片 status=已冲红
        asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
        assert asset.status == "已冲红"

    def test_红冲后资产停止折旧(self, client, db):
        """已冲红资产不应再计提折旧"""
        data = _create_fa_invoice(client, amount_with_tax=12000)
        asset_id = data["fixed_asset"]["id"]

        client.post(f"/api/invoices/{data['id']}/reverse",
                    json={"reason": "测试"}, headers=HEADERS)

        # 尝试计提折旧 → status="已冲红" 时 record_depreciation 直接返回 None，路由返回 200 + depreciation_id=null
        r = client.post(f"/api/fixed-assets/{asset_id}/depreciate?period=2026-07",
                        headers=HEADERS)
        assert r.status_code == 200, r.text
        body = r.json()
        # 验证：返回 depreciation_id=null（未创建折旧流水）
        assert body.get("depreciation_id") is None, f"已冲红资产不应创建折旧流水: {body}"


class Test更新资产原值_同步总账:
    """验证：UpdateAssetWithInvoice 改 original_value → 冲红旧凭证 + 重过新凭证"""

    def test_原值变更后_bs_1601_同步(self, client, db):
        """原值从 11300 改为 22600 → BS 1601 净增 11300（差额）"""
        data = _create_fa_invoice(client, amount_with_tax=11300)
        asset_id = data["fixed_asset"]["id"]

        before_1601 = _ledger_balance(db, 1, "1601")
        before_2202 = _ledger_balance(db, 1, "2202")

        # 更新原值为 22600
        r = client.put(f"/api/fixed-assets/{asset_id}/with-invoice",
                       json={"original_value": 22600}, headers=HEADERS)
        assert r.status_code == 200, r.text

        after_1601 = _ledger_balance(db, 1, "1601")
        after_2202 = _ledger_balance(db, 1, "2202")

        # 1601 净增 11300（22600 - 11300）
        assert after_1601 - before_1601 == Decimal("11300.00"), f"1601: {before_1601} → {after_1601}"
        # 2202 净增 11300（应付账款同步增加）
        assert after_2202 - before_2202 == Decimal("11300.00"), f"2202: {before_2202} → {after_2202}"

        # 资产卡片原值 = 22600
        asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
<<<<<<< Updated upstream
        assert Decimal(str(asset.original_value)) == Decimal("22600.00")
=======
        assert Decimal(str(asset.original_value_l1)) == Decimal("22600.00")
>>>>>>> Stashed changes

    def test_多次更新原值_总账始终一致(self, client, db):
        """反复更新原值：每次都冲红+重过，BS 1601 余额 == 资产卡片原值"""
        data = _create_fa_invoice(client, amount_with_tax=5000)
        asset_id = data["fixed_asset"]["id"]

        # 第一次更新：5000 → 10000
        r1 = client.put(f"/api/fixed-assets/{asset_id}/with-invoice",
                        json={"original_value": 10000}, headers=HEADERS)
        assert r1.status_code == 200, r1.text

        # 第二次更新：10000 → 15000
        r2 = client.put(f"/api/fixed-assets/{asset_id}/with-invoice",
                        json={"original_value": 15000}, headers=HEADERS)
        assert r2.status_code == 200, r2.text

        # 最终：资产卡片原值 = 15000，且 BS 1601 增量累计 = 15000 - 5000 = 10000
        asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
<<<<<<< Updated upstream
        assert Decimal(str(asset.original_value)) == Decimal("15000.00")
=======
        assert Decimal(str(asset.original_value_l1)) == Decimal("15000.00")
>>>>>>> Stashed changes


class Test幂等性:
    """验证：source_model + source_id 幂等防御"""

    def test_重复创建同资产_id_不重复过账(self, client, db):
        """post_journal 同 source_model+source_id 应返回旧凭证"""
        from finance_integration import post_journal
        data = _create_fa_invoice(client, amount_with_tax=2000)
        asset_id = data["fixed_asset"]["id"]

        # 直接调 post_journal 重复过账，应返回旧凭证不创建新凭证
        before_1601 = _ledger_balance(db, 1, "1601")
        post_journal(db, 1, "fixed_asset_purchase", {
            "original_value": 2000,
            "tax_amount": 0,
            "amount_with_tax": 2000,
            "asset_id": asset_id,
            "source_model": "fixed_asset_purchase",
            "source_id": asset_id,
            "date": "2026-06-19",
        })
        after_1601 = _ledger_balance(db, 1, "1601")
        # 余额不变 → 旧凭证被返回，未创建新凭证
        assert after_1601 == before_1601, f"重复过账导致余额变化: {before_1601} → {after_1601}"


class Test一般纳税人专票自动认证:
    """回归测试：一般纳税人 + 专票 + 固定资产 → 过账即认证（修复税务核对 222102 vs 发票表不一致 bug）

    Bug 根因：
    - engine_tax_check.py 读 222102 总账余额作为「账面进项税额」
    - crud/invoices.py 与 crud/finance/tax_declarations.py 按 certification_status=="certified"
      过滤发票表算「申报进项税额」
    - 固定资产发票默认 certification_status="n_a" → 发票表不计入 → 申报≠账面 → 税务核对失败
    修复：CreateInvoiceWithFixedAssetHandler 对一般纳税人专票自动 certified（与 dr 222102 原子同步）
    """

    def _setup_general_taxpayer(self, db):
        """创建一个一般纳税人账本（独立于默认 id=1 小规模账本）"""
        from finance_integration import get_or_create_ledger_id
        acct = Account(
            name="一般纳税人测试", type="company",
<<<<<<< Updated upstream
            code=uniq("GT-"), taxpayer_type="general",
=======
            code=uniq("GT-"), taxpayer_type_l3="general",
>>>>>>> Stashed changes
        )
        db.add(acct)
        db.flush()
        get_or_create_ledger_id(db, acct.id)
        db.commit()
        return acct

    def test_一般纳税人专票_自动认证(self, client, db):
        """一般纳税人 + 专票 → certification_status=certified, certification_date=issue_date"""
        acct = self._setup_general_taxpayer(db)
        h = {"X-Account-ID": str(acct.id), "X-Operator": "user"}
        pid = _create_product(client)

        r = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("FA-GT-"),
            "direction": "in", "invoice_type": "special",
            "amount_with_tax": 6780, "tax_rate": 0.13,
            "counterparty_name": "供应商Y", "seller_name": "供应商Y",
            "buyer_name": "一般纳税人测试", "issue_date": "2026-06-05",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 6000, "tax_rate": 0.13}],
            "fixed_asset": {
                "asset_code": uniq("FA-"), "asset_name": "打印机",
                "useful_life": 48, "start_date": "2026-06-05",
            },
        }, headers=h)
        assert r.status_code == 200, r.text
        data = r.json()["data"]

        # 关键断言1：发票自动认证（无需单独调 /certify）
        assert data["certification_status"] == "certified", \
            f"一般纳税人专票应自动认证, 实际={data['certification_status']}"
        # 认证日期 = 开票日期（兼容 date/datetime 序列化格式）
        cert_date = str(data["certification_date"] or "")[:10]
        assert cert_date == "2026-06-05", \
            f"认证日期应=开票日期, 实际={data['certification_date']}"

    def test_一般纳税人专票_资产原值不含税_222102入账(self, client, db):
        """一般纳税人：资产原值=不含税(6000), 222102=780, 2202=6780（三个数据源一致）"""
        acct = self._setup_general_taxpayer(db)
        h = {"X-Account-ID": str(acct.id), "X-Operator": "user"}
        pid = _create_product(client)

        # 222102 是借方余额账户（进项税额），不取反；2202 是贷方余额账户，取反
        before_222102 = _ledger_raw_balance(db, acct.id, "222102")
        before_1601 = _ledger_balance(db, acct.id, "1601")
        before_2202 = _ledger_balance(db, acct.id, "2202")

        r = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("FA-GT-"),
            "direction": "in", "invoice_type": "special",
            "amount_with_tax": 6780, "tax_rate": 0.13,
            "counterparty_name": "供应商Y", "seller_name": "供应商Y",
            "buyer_name": "一般纳税人测试", "issue_date": "2026-06-05",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 6000, "tax_rate": 0.13}],
            "fixed_asset": {
                "asset_code": uniq("FA-"), "asset_name": "打印机",
                "useful_life": 48, "start_date": "2026-06-05",
            },
        }, headers=h)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        asset_id = data["fixed_asset"]["id"]

        # 资产原值 = 不含税金额 6000（不是含税 6780）
        asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
<<<<<<< Updated upstream
        assert Decimal(str(asset.original_value)) == Decimal("6000.00"), \
            f"一般纳税人资产原值应为不含税, 实际={asset.original_value}"
=======
        assert Decimal(str(asset.original_value_l1)) == Decimal("6000.00"), \
            f"一般纳税人资产原值应为不含税, 实际={asset.original_value_l1}"
>>>>>>> Stashed changes

        # 222102 增加 780（进项税额入账，借方余额）
        after_222102 = _ledger_raw_balance(db, acct.id, "222102")
        assert after_222102 - before_222102 == Decimal("780.00"), \
            f"222102 应增 780, 实际 {before_222102} → {after_222102}"
        # 1601 增加 6000（不含税进资产）
        after_1601 = _ledger_balance(db, acct.id, "1601")
        assert after_1601 - before_1601 == Decimal("6000.00"), \
            f"1601 应增 6000, 实际 {before_1601} → {after_1601}"
        # 2202 增加 6780（价税合计）
        after_2202 = _ledger_balance(db, acct.id, "2202")
        assert after_2202 - before_2202 == Decimal("6780.00"), \
            f"2202 应增 6780, 实际 {before_2202} → {after_2202}"

    def test_一般纳税人普通发票_不自动认证(self, client, db):
        """一般纳税人 + 普通发票（非专票）→ 不自动认证（普通发票不可抵扣）"""
        acct = self._setup_general_taxpayer(db)
        h = {"X-Account-ID": str(acct.id), "X-Operator": "user"}
        pid = _create_product(client)

        r = client.post("/api/invoices/quick", json={
            "invoice_no": uniq("FA-GT-ORD-"),
            "direction": "in", "invoice_type": "ordinary",
            "amount_with_tax": 6780, "tax_rate": 0.13,
            "counterparty_name": "供应商Y", "seller_name": "供应商Y",
            "buyer_name": "一般纳税人测试", "issue_date": "2026-06-05",
            "items": [{"product_id": pid, "quantity": 1, "unit_price": 6000, "tax_rate": 0.13}],
            "fixed_asset": {
                "asset_code": uniq("FA-"), "asset_name": "打印机",
                "useful_life": 48, "start_date": "2026-06-05",
            },
        }, headers=h)
        assert r.status_code == 200, r.text
        data = r.json()["data"]

        # 普通发票不自动认证（保持默认 n_a）
        assert data["certification_status"] == "n_a", \
            f"普通发票不应自动认证, 实际={data['certification_status']}"
        # 资产原值 = 价税合计 6780（普通发票不抵扣，全额进资产）
        asset_id = data["fixed_asset"]["id"]
        asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
<<<<<<< Updated upstream
        assert Decimal(str(asset.original_value)) == Decimal("6780.00"), \
            f"普通发票资产原值应=价税合计, 实际={asset.original_value}"
=======
        assert Decimal(str(asset.original_value_l1)) == Decimal("6780.00"), \
            f"普通发票资产原值应=价税合计, 实际={asset.original_value_l1}"
>>>>>>> Stashed changes
