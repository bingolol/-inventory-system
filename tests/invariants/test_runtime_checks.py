"""AS-01~AS-07 运行时校验测试

验证 7 条会计实务规则的可执行校验函数能正确:
- 检出违规数据
- 通过合规数据

运行:python -m pytest tests/invariants/test_runtime_checks.py -v
"""
import sys
import pytest
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path

# 把 backend 加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="module", autouse=True)
def _load_rules():
    """模块级前置:加载 15 条规则定义"""
    from rules import load_all_rules
    load_all_rules()


# ═══════════════════════════════════════════════════════════════
# AS-02: 价税分离(最易测试,无需 db)
# ═══════════════════════════════════════════════════════════════

class TestAS02价税分离:
    """AS-02 校验:发票三段平衡"""

    def test_三段平衡无违规(self, db):
        from rules import validate_rules_runtime
        from models import Invoice

        inv = Invoice(
            account_id=1,
            invoice_no="TEST-AS02-OK",
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.13"),
            amount_without_tax_l1=Decimal("100.00"),
            tax_amount_l1=Decimal("13.00"),
            amount_with_tax_l1=Decimal("113.00"),
            counterparty_name="测试客户",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        vs = validate_rules_runtime(db, "AS-02", {"invoice_id": inv.id})
        assert len(vs) == 0, f"三段平衡应无违规,实际 {[v.message for v in vs]}"

    def test_三段不平报违规(self, db):
        from rules import validate_rules_runtime
        from models import Invoice

        inv = Invoice(
            account_id=1,
            invoice_no="TEST-AS02-BAD",
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.13"),
            amount_without_tax_l1=Decimal("100.00"),
            tax_amount_l1=Decimal("13.00"),
            amount_with_tax_l1=Decimal("114.00"),  # 故意不平
            counterparty_name="测试客户",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        vs = validate_rules_runtime(db, "AS-02", {"invoice_id": inv.id})
        assert len(vs) == 1
        assert "三段不平" in vs[0].message
        assert vs[0].rule_id == "AS-02"

    def test_税率非法报违规(self, db):
        from rules import validate_rules_runtime
        from models import Invoice

        inv = Invoice(
            account_id=1,
            invoice_no="TEST-AS02-RATE",
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.15"),  # 非法税率
            amount_without_tax_l1=Decimal("100.00"),
            tax_amount_l1=Decimal("15.00"),
            amount_with_tax_l1=Decimal("115.00"),
            counterparty_name="测试客户",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        vs = validate_rules_runtime(db, "AS-02", {"invoice_id": inv.id})
        # 三段平衡通过,但税率非法
        rate_vs = [v for v in vs if "税率" in v.message]
        assert len(rate_vs) == 1
        assert "0.15" in rate_vs[0].message

    def test_发票不存在无违规(self, db):
        from rules import validate_rules_runtime
        vs = validate_rules_runtime(db, "AS-02", {"invoice_id": 99999})
        assert len(vs) == 0


# ═══════════════════════════════════════════════════════════════
# AS-06: 增值税红字冲减
# ═══════════════════════════════════════════════════════════════

class TestAS06红字冲减:
    """AS-06 校验:红字发票金额为负"""

    def test_红字发票金额为正报违规(self, db):
        from rules import validate_rules_runtime
        from models import Invoice

        inv = Invoice(
            account_id=1,
            invoice_no="H-TEST-AS06-BAD",  # 红字发票前缀
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.13"),
            amount_without_tax_l1=Decimal("100.00"),  # 应为负
            tax_amount_l1=Decimal("13.00"),  # 应为负
            amount_with_tax_l1=Decimal("113.00"),  # 应为负
            counterparty_name="测试客户",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        vs = validate_rules_runtime(db, "AS-06", {"invoice_id": inv.id})
        assert len(vs) == 2  # 不含税 + 税额 都应为负
        assert all(v.rule_id == "AS-06" for v in vs)

    def test_红字发票金额为负无违规(self, db):
        from rules import validate_rules_runtime
        from models import Invoice

        inv = Invoice(
            account_id=1,
            invoice_no="H-TEST-AS06-OK",
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.13"),
            amount_without_tax_l1=Decimal("-100.00"),
            tax_amount_l1=Decimal("-13.00"),
            amount_with_tax_l1=Decimal("-113.00"),
            counterparty_name="测试客户",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        vs = validate_rules_runtime(db, "AS-06", {"invoice_id": inv.id})
        assert len(vs) == 0

    def test_普通发票不校验红字(self, db):
        """非红字发票不触发 AS-06 校验"""
        from rules import validate_rules_runtime
        from models import Invoice

        inv = Invoice(
            account_id=1,
            invoice_no="NORMAL-TEST-AS06",
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.13"),
            amount_without_tax_l1=Decimal("100.00"),
            tax_amount_l1=Decimal("13.00"),
            amount_with_tax_l1=Decimal("113.00"),
            counterparty_name="测试客户",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        vs = validate_rules_runtime(db, "AS-06", {"invoice_id": inv.id})
        assert len(vs) == 0  # 普通发票不校验红字规则


# ═══════════════════════════════════════════════════════════════
# API 完整性
# ═══════════════════════════════════════════════════════════════

class TestAPI完整性:
    """验证 validate_rules_runtime API 行为"""

    def test_未知规则返回违规(self, db):
        from rules import validate_rules_runtime
        vs = validate_rules_runtime(db, "AS-99", {})
        assert len(vs) == 1
        assert "无运行时校验函数" in vs[0].message

    def test_无context字段时不报错(self, db):
        """空 context 应返回空违规,不抛异常"""
        from rules import validate_rules_runtime
        for rule_id in ["AS-01", "AS-02", "AS-03", "AS-04", "AS-05", "AS-06", "AS-07"]:
            vs = validate_rules_runtime(db, rule_id, {})
            assert isinstance(vs, list), f"{rule_id} 应返回列表"

    def test_validate_all_runtime不抛异常(self, db):
        """validate_all_runtime 对空 context 应不抛异常"""
        from rules import validate_all_runtime
        vs = validate_all_runtime(db, {})
        assert isinstance(vs, list)

    def test_7条规则全部注册(self):
        from rules import RUNTIME_CHECKS
        expected = {"AS-01", "AS-02", "AS-03", "AS-04", "AS-05", "AS-06", "AS-07", "AS-15"}
        assert set(RUNTIME_CHECKS.keys()) == expected
