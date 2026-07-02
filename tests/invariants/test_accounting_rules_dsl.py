"""DSL 规则校验测试

验证 16 条会计准则规则的:
1. 定义完整性(16 条都注册、ID 不重复、必填字段齐全)
2. 校验引擎能检出违规(AS-08/09/10/14 交叉校验)

运行:python -m pytest tests/invariants/test_accounting_rules_dsl.py -v
"""
import sys
import pytest
from pathlib import Path

# 把 backend 加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="module", autouse=True)
def _load_rules():
    """模块级前置:加载 16 条规则定义(触发 Rule 实例化注册)"""
    from rules import load_all_rules
    load_all_rules()


class TestRuleDefinitions:
    """规则定义完整性校验"""

    def test_16条规则全部注册(self):
        from rules import RULES
        assert len(RULES) == 16, f"应注册 16 条规则,实际 {len(RULES)}"

    def test_规则ID从AS01到AS15加AS22(self):
        from rules import RULES
        ids = sorted(r.id for r in RULES)
        expected = [f"AS-{i:02d}" for i in range(1, 16)] + ["AS-22"]
        assert ids == expected, f"规则ID不匹配:期望 {expected},实际 {ids}"

    def test_规则ID不重复(self):
        from rules import RULES
        ids = [r.id for r in RULES]
        assert len(ids) == len(set(ids)), f"规则ID重复:{ids}"

    def test_每条规则必填字段齐全(self):
        from rules import RULES
        for r in RULES:
            assert r.name, f"{r.id} name 为空"
            assert r.source, f"{r.id} source 为空"
            assert r.trigger, f"{r.id} trigger 为空"
            assert r.expected_chain, f"{r.id} expected_chain 为空"

    def test_会计实务基石7条(self):
        from rules import RULES, CATEGORY_ACCOUNTING
        accounting = [r for r in RULES if r.category == CATEGORY_ACCOUNTING]
        assert len(accounting) == 7, f"会计实务基石应 7 条,实际 {len(accounting)}"

    def test_系统实现约定9条(self):
        from rules import RULES, CATEGORY_IMPLEMENTATION
        impl = [r for r in RULES if r.category == CATEGORY_IMPLEMENTATION]
        assert len(impl) == 9, f"系统实现约定应 9 条(AS-08~AS-15 + AS-22),实际 {len(impl)}"

    def test_每条规则至少1个不变量(self):
        from rules import RULES
        for r in RULES:
            assert len(r.invariants) >= 1, f"{r.id} 无不变量"

    def test_每条规则至少1个禁止项(self):
        from rules import RULES
        for r in RULES:
            assert len(r.prohibited) >= 1, f"{r.id} 无禁止项"

    def test_get_rule_by_id(self):
        from rules import get_rule_by_id
        r = get_rule_by_id("AS-01")
        assert r is not None
        assert "借贷平衡" in r.name

    def test_get_rule_by_id不存在返回None(self):
        from rules import get_rule_by_id
        assert get_rule_by_id("AS-99") is None


class TestAS08TierMonotonic:
    """AS-08 字段层级单调校验"""

    def test_无L4读取时无违规(self):
        from rules.validator import _check_as08_tier_monotonic

        class MockRegistry:
            reads = []
            writes = []

        violations = _check_as08_tier_monotonic(MockRegistry())
        assert len(violations) == 0

    def test_有L4读取时报违规(self):
        from rules.validator import _check_as08_tier_monotonic

        class MockRead:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            reads = [
                MockRead("Inventory.quantity_l4", "L4", "list_inventory"),
                MockRead("BankAccount.balance_l4", "L4", "generate_balance_sheet"),
            ]
            writes = []

        violations = _check_as08_tier_monotonic(MockRegistry())
        assert len(violations) == 2
        assert all(v.rule_id == "AS-08" for v in violations)

    def test_L2L1读取无违规(self):
        from rules.validator import _check_as08_tier_monotonic

        class MockRead:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            reads = [
                MockRead("StockMove.quantity_l1", "L1", "list_inventory"),
                MockRead("AccountMoveLine.debit_l2", "L2", "generate_balance_sheet"),
            ]
            writes = []

        violations = _check_as08_tier_monotonic(MockRegistry())
        assert len(violations) == 0


class TestAS09WriterUnique:
    """AS-09 Writer 唯一校验"""

    def test_单writer无违规(self):
        from rules.validator import _check_as09_writer_unique

        class MockWrite:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            writes = [
                MockWrite("StockMove.unit_cost_l2", "L2", "InventoryEngine.inbound"),
            ]
            reads = []

        violations = _check_as09_writer_unique(MockRegistry())
        assert len(violations) == 0

    def test_同类多方法不算违规(self):
        """同类多个方法写同字段合法(如 inbound/outbound/reverse 都写 StockMove)"""
        from rules.validator import _check_as09_writer_unique

        class MockWrite:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            writes = [
                MockWrite("StockMove.unit_cost_l2", "L2", "InventoryEngine.inbound"),
                MockWrite("StockMove.unit_cost_l2", "L2", "InventoryEngine.outbound"),
                MockWrite("StockMove.unit_cost_l2", "L2", "InventoryEngine.reverse"),
            ]
            reads = []

        violations = _check_as09_writer_unique(MockRegistry())
        assert len(violations) == 0

    def test_跨类多writer报违规(self):
        from rules.validator import _check_as09_writer_unique

        class MockWrite:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            writes = [
                MockWrite("StockMove.unit_cost_l2", "L2", "InventoryEngine.inbound"),
                MockWrite("StockMove.unit_cost_l2", "L2", "FinanceEngine.calc"),
            ]
            reads = []

        violations = _check_as09_writer_unique(MockRegistry())
        assert len(violations) == 1
        assert "双算法" in violations[0].message


class TestAS10L4NoRead:
    """AS-10 L4 字段报表禁读校验"""

    def test_读L4字段报违规(self):
        from rules.validator import _check_as10_l4_no_read

        class MockRead:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            reads = [
                MockRead("Inventory.quantity_l4", "L4", "list_inventory"),
                MockRead("BankAccount.balance_l4", "L4", "generate_balance_sheet"),
            ]
            writes = []

        violations = _check_as10_l4_no_read(MockRegistry())
        assert len(violations) == 2
        assert all(v.rule_id == "AS-10" for v in violations)

    def test_读L2无违规(self):
        from rules.validator import _check_as10_l4_no_read

        class MockRead:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            reads = [
                MockRead("StockMove.quantity_l1", "L1", "list_inventory"),
                MockRead("AccountMoveLine.debit_l2", "L2", "generate_balance_sheet"),
            ]
            writes = []

        violations = _check_as10_l4_no_read(MockRegistry())
        assert len(violations) == 0


class TestAS14ServiceProduct:
    """AS-14 服务产品不扣库存校验"""

    def test_track_inventory未被reads报违规(self):
        from rules.validator import _check_as14_service_product

        class MockRegistry:
            reads = []
            writes = []

        violations = _check_as14_service_product(MockRegistry())
        assert len(violations) == 1
        assert "track_inventory_l3" in violations[0].message

    def test_track_inventory已被reads无违规(self):
        from rules.validator import _check_as14_service_product

        class MockRead:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            reads = [
                MockRead("Product.track_inventory_l3", "L3", "InventoryEngine.inbound"),
            ]
            writes = []

        violations = _check_as14_service_product(MockRegistry())
        assert len(violations) == 0


class TestValidateRulesIntegration:
    """validate_rules 集成校验"""

    def test_无registry时仅校验定义完整性(self):
        from rules import validate_rules
        violations = validate_rules(registry=None)
        # 16 条定义完整 + AS-22 静态扫描无违规(commands/routers 无 PurchaseEstimate/BadDebt 引用)
        assert len(violations) == 0

    def test_有registry时做交叉校验(self):
        from rules import validate_rules

        class MockRead:
            def __init__(self, field_path, tier, func):
                self.field = type("F", (), {"path": field_path})()
                self.tier = tier
                self.func_qualname = func

        class MockRegistry:
            reads = [
                MockRead("Inventory.quantity_l4", "L4", "list_inventory"),
            ]
            writes = []

        violations = validate_rules(MockRegistry())
        # AS-08 和 AS-10 都应报违规
        rule_ids = [v.rule_id for v in violations]
        assert "AS-08" in rule_ids
        assert "AS-10" in rule_ids
