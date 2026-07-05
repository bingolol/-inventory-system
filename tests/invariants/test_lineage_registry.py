"""装饰器注册表完整性测试

验证 @writes/@reads/@derives 装饰器注册表的完整性与一致性：
- 关键引擎方法都声明了 @writes
- 关键报表函数都声明了 @reads
- 装饰器声明的 tier 与字段名后缀一致
- 无 TS01 双算法违规

运行：pytest tests/invariants/test_lineage_registry.py -v
"""
import sys
import importlib
from pathlib import Path

import pytest

# 把 backend 加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="module", autouse=True)
def loaded_registry():
    """确保所有相关模块已导入，触发装饰器注册"""
    from lineage import REGISTRY

    parents = ["crud", "crud.finance", "commands"]
    for p in parents:
        if p not in sys.modules:
            importlib.import_module(p)

    modules = [
        "engine_inventory",
        "engine_journal",
        "engine_ledger",
        "engine_bank",
        "engine_fixed_asset",
        "crud.reports",
        "crud.finance.balance_sheet",
        "crud.finance.income_statement",
        "crud.finance.cash_flow",
        "crud.finance.tax_declarations",
        "crud.finance.fixed_assets",
        "crud.finance.intangible_assets",
        "crud.products",
        "finance_integration",
        "commands.product_commands",
        "commands.account_commands",
        "commands.cash_commands",
        "commands.finance_commands",
        "commands.orders",
        "routers.personal_advances",
    ]
    for mod_name in modules:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            pytest.skip(f"无法导入 {mod_name}: {e}")

    return REGISTRY


class TestRegistryCompleteness:
    """注册表完整性：关键写入/读取方都已声明"""

    def test_引擎方法已声明writes(self, loaded_registry):
        """关键引擎方法都注册了 @writes"""
        written_fields = loaded_registry.all_written_fields()

        # 库存引擎必须声明写入 StockMove
        assert "StockMove.quantity_l1" in written_fields
        assert "StockMove.unit_cost_l2" in written_fields
        assert "StockMove.total_cost_l2" in written_fields

        # 凭证引擎必须声明写入 AccountMove/AccountMoveLine
        assert "AccountMove.amount_total_l2" in written_fields
        assert "AccountMoveLine.debit_l2" in written_fields
        assert "AccountMoveLine.credit_l2" in written_fields
        assert "AccountMoveLine.amount_residual_l2" in written_fields

    def test_BankEngine集中写入声明(self, loaded_registry):
        """BankTransaction 所有 L2 真相源字段由 BankEngine.record_transaction 声明"""
        written = loaded_registry.all_written_fields()
        # BankTransaction L2 真相源
        assert "BankTransaction.amount_l2" in written, "BankTransaction.amount_l2 缺少 @writes"
        assert "BankTransaction.flow_category_l2" in written, "BankTransaction.flow_category_l2 缺少 @writes"
        # BankTransaction L1 外部输入
        assert "BankTransaction.transaction_date_l1" in written, "BankTransaction.transaction_date_l1 缺少 @writes"
        # BankAccount.balance_l4 应有 @derives
        derives_balance = [
            w for w in loaded_registry.writes
            if w.is_derived and w.field.path == "BankAccount.balance_l4"
        ]
        assert len(derives_balance) > 0, "BankAccount.balance_l4 缺少 @derives 声明"

    def test_销售链路writes声明(self, loaded_registry):
        """SaleOrder/SaleItem 真相源字段已声明 @writes"""
        written = loaded_registry.all_written_fields()
        # SaleItem.unit_cost_l2 是 COGS 真相源（项目记忆硬约束）
        assert "SaleItem.unit_cost_l2" in written, "SaleItem.unit_cost_l2 (COGS 真相源) 缺少 @writes"
        # SaleItem L1 外部输入
        assert "SaleItem.quantity_l1" in written
        assert "SaleItem.unit_price_l1" in written
        assert "SaleItem.tax_rate_l1" in written
        # SaleOrder L1
        assert "SaleOrder.total_price_l1" in written
        assert "SaleOrder.sale_date_l1" in written

    def test_采购链路writes声明(self, loaded_registry):
        """PurchaseOrder/PurchaseItem 真相源字段已声明 @writes"""
        written = loaded_registry.all_written_fields()
        assert "PurchaseItem.quantity_l1" in written
        assert "PurchaseItem.unit_price_l1" in written
        assert "PurchaseOrder.total_price_l1" in written
        assert "PurchaseOrder.purchase_date_l1" in written

    def test_发票writes声明(self, loaded_registry):
        """Invoice 销项税真相源字段已声明 @writes（项目记忆：销项税真相源=发票）"""
        written = loaded_registry.all_written_fields()
        assert "Invoice.tax_amount_l1" in written, "Invoice.tax_amount_l1 (销项税真相源) 缺少 @writes"
        assert "Invoice.amount_without_tax_l1" in written
        assert "Invoice.amount_with_tax_l1" in written
        assert "Invoice.issue_date_l1" in written

    def test_现金流量表writes声明(self, loaded_registry):
        """CashFlowTransaction L2 真相源字段已声明 @writes"""
        written = loaded_registry.all_written_fields()
        assert "CashFlowTransaction.amount_l2" in written
        assert "CashFlowTransaction.flow_category_l2" in written

    def test_费用收付款writes声明(self, loaded_registry):
        """Expense/Payment/Receipt L1 字段已声明 @writes"""
        written = loaded_registry.all_written_fields()
        assert "Expense.amount_l1" in written
        assert "Payment.amount_l1" in written
        assert "Receipt.amount_l1" in written

    def test_reverse_journal_writes声明(self, loaded_registry):
        """finance_integration.reverse_journal 已声明 @writes（与 JournalEngine.post 同字段）"""
        written = loaded_registry.all_written_fields()
        # reverse_journal 应复用 JournalEngine.post 的字段集
        assert "AccountMove.date_l1" in written
        # 同字段多 writer 应在同类（ finance_integration 模块函数 vs JournalEngine.post method）
        # TS01 仅校验 L2 跨类双 writer，L1 不受 TS01 约束

    def test_报表函数已声明reads(self, loaded_registry):
        """关键报表函数都注册了 @reads"""
        read_fields = loaded_registry.all_read_fields()

        # 资产负债表应读 AccountMoveLine（L2 真相源）
        assert "AccountMoveLine.debit_l2" in read_fields or \
               "AccountMoveLine.credit_l2" in read_fields

        # 利润表应读 AccountMoveLine
        assert "AccountMoveLine.debit_l2" in read_fields or \
               "AccountMoveLine.credit_l2" in read_fields

    def test_派生关系已声明derives(self, loaded_registry):
        """L4 派生字段的计算来源已声明"""
        # LedgerAccountBalance.balance_l4 应由 @derives 声明
        derives_writes = [
            w for w in loaded_registry.writes
            if w.is_derived and w.field.path == "LedgerAccountBalance.balance_l4"
        ]
        assert len(derives_writes) > 0, \
            "LedgerAccountBalance.balance_l4 应有 @derives 声明"

        # Inventory.quantity_l4 应由 @derives 声明
        derives_inv = [
            w for w in loaded_registry.writes
            if w.is_derived and w.field.path == "Inventory.quantity_l4"
        ]
        assert len(derives_inv) > 0, \
            "Inventory.quantity_l4 应有 @derives 声明"


class TestL3Coverage:
    """L3 政策配置字段已标注"""

    def test_L3政策字段已声明writes(self, loaded_registry):
        """关键 L3 policy 写入方已注册"""
        written = loaded_registry.all_written_fields()
        assert "Product.track_inventory_l3" in written
        assert "Account.taxpayer_type_l3" in written
        assert "FixedAsset.salvage_rate_l3" in written
        assert "Invoice.certification_status_l3" in written

    def test_L3政策字段被读取(self, loaded_registry):
        """关键 L3 字段被引擎/报表读取"""
        read = loaded_registry.all_read_fields()
        assert "Account.taxpayer_type_l3" in read
        assert "Product.track_inventory_l3" in read


class TestTierSuffixConsistency:
    """TS05: 字段后缀与声明 tier 一致性"""

    def test_writes_tier_matches_suffix(self, loaded_registry):
        """所有 @writes 声明的 tier 应与字段名后缀一致"""
        from lineage import FieldRef
        mismatches = []
        for w in loaded_registry.writes:
            suffix_tier = w.field.tier_from_suffix
            if suffix_tier and suffix_tier != w.tier:
                mismatches.append(
                    f"{w.field.path}: 后缀={suffix_tier}, 声明={w.tier} ({w.func_qualname})"
                )
        assert not mismatches, \
            "@writes tier 与后缀不一致:\n" + "\n".join(mismatches)

    def test_reads_tier_matches_suffix(self, loaded_registry):
        """所有 @reads 声明的 tier 应与字段名后缀一致"""
        from lineage import FieldRef
        mismatches = []
        for r in loaded_registry.reads:
            suffix_tier = r.field.tier_from_suffix
            if suffix_tier and suffix_tier != r.tier:
                mismatches.append(
                    f"{r.field.path}: 后缀={suffix_tier}, 声明={r.tier} ({r.func_qualname})"
                )
        assert not mismatches, \
            "@reads tier 与后缀不一致:\n" + "\n".join(mismatches)


class TestNoDualAlgorithm:
    """TS01: 同一字段不能由不同类写入（双算法风险）"""

    def test_L2真相源无跨类双writer(self, loaded_registry):
        from lineage import TIER_L2, validate_invariants
        violations = [v for v in validate_invariants()
                      if v.code == "TS01"]
        error_msgs = [v.message for v in violations]
        assert not violations, \
            "存在双算法违规:\n" + "\n".join(error_msgs)
