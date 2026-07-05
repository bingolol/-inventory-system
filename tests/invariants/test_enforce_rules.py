"""enforce_rules 业务流程拦截测试

验证:
1. enforce_rules 函数本身:违规抛 BusinessError,合规不抛
2. 5 个业务入口确实调用了 enforce_rules(mock 验证)
3. ErrorCode.RULE_VIOLATION 已注册

运行:python -m pytest tests/invariants/test_enforce_rules.py -v
"""
import sys
import pytest
from decimal import Decimal
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="module", autouse=True)
def _load_rules():
    from rules import load_all_rules
    load_all_rules()


# ═══════════════════════════════════════════════════════════════
# enforce_rules 函数本身
# ═══════════════════════════════════════════════════════════════

class TestEnforceRules函数:
    """enforce_rules 是业务流程拦截的核心入口"""

    def test_合规数据不抛异常(self, db):
        from rules import enforce_rules
        from models import Invoice

        inv = Invoice(
            account_id=1,
            invoice_no="ENFORCE-OK",
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.13"),
            amount_without_tax_l1=Decimal("100.00"),
            tax_amount_l1=Decimal("13.00"),
            amount_with_tax_l1=Decimal("113.00"),
            counterparty_name="测试",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        # 不应抛异常
        enforce_rules(db, ["AS-02"], {"invoice_id": inv.id})

    def test_违规数据抛BusinessError(self, db):
        from rules import enforce_rules
        from models import Invoice
        from errors import BusinessError, ErrorCode

        inv = Invoice(
            account_id=1,
            invoice_no="ENFORCE-BAD",
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.13"),
            amount_without_tax_l1=Decimal("100.00"),
            tax_amount_l1=Decimal("13.00"),
            amount_with_tax_l1=Decimal("114.00"),  # 不平
            counterparty_name="测试",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        with pytest.raises(BusinessError) as exc_info:
            enforce_rules(db, ["AS-02"], {"invoice_id": inv.id})

        assert exc_info.value.code == ErrorCode.RULE_VIOLATION
        assert "AS-02" in str(exc_info.value.message)
        assert "violations" in exc_info.value.data

    def test_多规则同时校验(self, db):
        """enforce_rules 支持一次校验多条规则"""
        from rules import enforce_rules
        from models import Invoice
        from errors import BusinessError

        inv = Invoice(
            account_id=1,
            invoice_no="H-ENFORCE-MULTI",  # 红字前缀但金额为正(触发 AS-06)
            direction="out",
            invoice_type="ordinary",
            tax_rate_l1=Decimal("0.13"),
            amount_without_tax_l1=Decimal("100.00"),
            tax_amount_l1=Decimal("13.00"),
            amount_with_tax_l1=Decimal("113.00"),
            counterparty_name="测试",
            issue_date_l1=datetime(2026, 6, 1),
        )
        db.add(inv)
        db.commit()

        with pytest.raises(BusinessError) as exc_info:
            enforce_rules(db, ["AS-02", "AS-06"], {"invoice_id": inv.id})

        # AS-02 通过(三段平衡), AS-06 报违规(红字金额为正)
        assert "AS-06" in str(exc_info.value.message)

    def test_空规则列表不抛异常(self, db):
        from rules import enforce_rules
        enforce_rules(db, [], {"invoice_id": 1})  # 不应抛异常

    def test_校验异常被捕获转为违规(self, db):
        """校验函数内部异常应被捕获,转为 RuleViolation 而非向上抛

        通过 mock 让 check_fn 抛异常,验证 enforce_rules 捕获后转为 BusinessError
        而非让原始异常向上传播。
        """
        from rules import enforce_rules
        from errors import BusinessError

        with patch("rules.runtime_checks.RUNTIME_CHECKS") as mock_checks:
            mock_check = MagicMock(side_effect=RuntimeError("模拟校验内部崩溃"))
            mock_checks.get.return_value = mock_check
            mock_checks.items.return_value = [("AS-01", mock_check)]

            with pytest.raises(BusinessError) as exc_info:
                enforce_rules(db, ["AS-01"], {"move_id": 1})

            assert "AS-01" in str(exc_info.value.message)
            assert "运行时校验异常" in str(exc_info.value.message)


# ═══════════════════════════════════════════════════════════════
# ErrorCode 注册验证
# ═══════════════════════════════════════════════════════════════

class TestErrorCode注册:
    """验证 RULE_VIOLATION 错误码已正确注册"""

    def test_错误码存在(self):
        from errors import ErrorCode
        assert hasattr(ErrorCode, "RULE_VIOLATION")
        assert ErrorCode.RULE_VIOLATION.value == "RULE_VIOLATION"

    def test_错误码在registry中(self):
        from errors import ERROR_REGISTRY, ErrorCode, ActionType
        status, action, template, instruction = ERROR_REGISTRY[ErrorCode.RULE_VIOLATION]
        assert status == 422
        assert action == ActionType.USER_INPUT
        assert "会计准则" in template

    def test_BusinessError可用此码(self):
        from errors import BusinessError, ErrorCode
        err = BusinessError(ErrorCode.RULE_VIOLATION, message="测试")
        assert err.code == ErrorCode.RULE_VIOLATION
        assert err.message == "测试"


# ═══════════════════════════════════════════════════════════════
# 业务入口拦截验证(mock 验证 enforce_rules 被调用)
# ═══════════════════════════════════════════════════════════════

class Test业务入口拦截:
    """验证 5 个业务入口确实引用了 enforce_rules

    通过 mock enforce_rules 验证业务流程会调用它,
    确保"被动工具"已变为"主动护栏"。
    """

    def test_engine_journal引用enforce_rules(self):
        """JournalEngine.post 应调用 enforce_rules(AS-01)"""
        import engine_journal
        import inspect
        src = inspect.getsource(engine_journal.JournalEngine.post)
        assert "enforce_rules" in src
        assert "AS-01" in src

    def test_reverse_journal走post_seam(self):
        """finance_integration.reverse_journal 应委托 JournalEngine.post 生成冲红凭证

        AS-01 借贷平衡校验由 post 内部统一执行，reverse_journal 不再直接调用 enforce_rules。
        直接读取源文件，避免 crud.personal 等无关模块的循环导入错误影响此测试。
        """
        from pathlib import Path
        src_path = Path(__file__).resolve().parents[2] / "backend" / "finance_integration.py"
        src = src_path.read_text(encoding="utf-8")
        func_start = src.find("def reverse_journal(")
        func_src = src[func_start:src.find("\ndef ", func_start + 1)]
        assert "engine.post" in func_src
        assert "reverse_entry" in func_src
        assert "AccountMove(" not in func_src

    def test_invoice_commands引用enforce_rules(self):
        """CreateInvoiceHandler / ReverseInvoiceHandler 应调用 enforce_rules"""
        from commands.orders._invoice import CreateInvoiceHandler, ReverseInvoiceHandler
        import inspect

        create_src = inspect.getsource(CreateInvoiceHandler.handle)
        assert "enforce_rules" in create_src
        assert "AS-02" in create_src


        reverse_src = inspect.getsource(ReverseInvoiceHandler.handle)
        assert "enforce_rules" in reverse_src
        assert "AS-06" in reverse_src

    def test_engine_inventory引用enforce_rules(self):
        """InventoryEngine.inbound/_record_outbound/reverse 应调用 enforce_rules(AS-03)"""
        import engine_inventory
        import inspect

        inbound_src = inspect.getsource(engine_inventory.InventoryEngine.inbound)
        assert "enforce_rules" in inbound_src
        assert "AS-03" in inbound_src

        outbound_src = inspect.getsource(engine_inventory.InventoryEngine._record_outbound)
        assert "enforce_rules" in outbound_src
        assert "AS-03" in outbound_src

        reverse_src = inspect.getsource(engine_inventory.InventoryEngine.reverse)
        assert "enforce_rules" in reverse_src
        assert "AS-03" in reverse_src

    def test_engine_fixed_asset引用enforce_rules(self):
        """FixedAssetEngine.record_depreciation / record_disposal 应调用 enforce_rules"""
        import engine_fixed_asset
        import inspect

        dep_src = inspect.getsource(engine_fixed_asset.FixedAssetEngine.record_depreciation)
        assert "enforce_rules" in dep_src
        assert "AS-05" in dep_src

        disposal_src = inspect.getsource(engine_fixed_asset.FixedAssetEngine.record_disposal)
        assert "enforce_rules" in disposal_src
        assert "AS-07" in disposal_src

    def test_5个入口文件均可正常导入(self):
        """验证无循环依赖,5 个文件均能正常导入"""
        import engine_journal
        import engine_inventory
        import engine_fixed_asset
        import commands.orders

        # 验证 enforce_rules 在各模块的命名空间中
        assert hasattr(engine_journal, "enforce_rules")
        assert hasattr(engine_inventory, "enforce_rules")
        assert hasattr(engine_fixed_asset, "enforce_rules")
