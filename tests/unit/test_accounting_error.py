"""AccountingError 结构化响应单元测试(TDD - 纯逻辑层)

验证 AccountingError 能转成与 BusinessError 一致的结构化响应,
保留 code / accounting_rule / calculation_detail / ai_instruction 四个引导字段。
不依赖 app/TestClient,只测转换逻辑。
"""
import pytest
from decimal import Decimal

from accounting_engine import AccountingError, AccountingErrorCode


@pytest.mark.unit
class TestAccountingErrorToDict:
    """AccountingError.to_dict() → 结构化响应体(缺口1修复的基础)"""

    def _make_unbalanced(self):
        return AccountingError(
            code=AccountingErrorCode.INVOICE_AMOUNTS_NOT_BALANCED,
            message="不含税 100 + 税额 13 ≠ 含税 114",
            ai_instruction="STOP_RETRYING. 发票金额不平衡,请检查不含税=含税/(1+税率)。",
            accounting_rule="《小企业会计准则》第十五条",
            calculation_detail={"amount_without_tax": 100, "tax_amount": 13, "diff": 1},
        )

    def test_has_error_envelope(self):
        """响应体顶层有 error 包络(与 BusinessError.to_dict 一致)"""
        d = self._make_unbalanced().to_dict()
        assert "error" in d

    def test_preserves_code(self):
        """error.code == AccountingErrorCode 字符串值"""
        d = self._make_unbalanced().to_dict()
        assert d["error"]["code"] == "INVOICE_AMOUNTS_NOT_BALANCED"

    def test_preserves_message(self):
        d = self._make_unbalanced().to_dict()
        assert d["error"]["message"] == "不含税 100 + 税额 13 ≠ 含税 114"

    def test_preserves_accounting_rule(self):
        """error.accounting_rule 透传法规依据"""
        d = self._make_unbalanced().to_dict()
        assert d["error"]["accounting_rule"] == "《小企业会计准则》第十五条"

    def test_preserves_calculation_detail(self):
        """error.calculation_detail 透传数值明细,供 AI 诊断"""
        d = self._make_unbalanced().to_dict()
        assert d["error"]["calculation_detail"]["diff"] == 1

    def test_preserves_ai_instruction(self):
        d = self._make_unbalanced().to_dict()
        assert "STOP_RETRYING" in d["error"]["ai_instruction"]


@pytest.mark.unit
class TestAccountingErrorStatusMap:
    """AccountingErrorCode → HTTP status 映射(缺口1:不能一律 500)"""

    @pytest.mark.parametrize("code,status", [
        (AccountingErrorCode.INVOICE_AMOUNTS_NOT_BALANCED, 422),
        (AccountingErrorCode.INVOICE_TAX_RATE_INVALID, 422),
        (AccountingErrorCode.VAT_TAXPAYER_TYPE_INVALID, 422),
        (AccountingErrorCode.VAT_REVENUE_NEGATIVE, 422),
        (AccountingErrorCode.INCOME_TAX_PROFIT_NEGATIVE, 422),
        (AccountingErrorCode.DEPRECIATION_USEFUL_LIFE_ZERO, 422),
        (AccountingErrorCode.DEPRECIATION_METHOD_NOT_IMPLEMENTED, 422),
        (AccountingErrorCode.DEPRECIATION_SALVAGE_RATE_INVALID, 422),
        (AccountingErrorCode.BALANCE_SHEET_UNBALANCED, 422),
        (AccountingErrorCode.INCOME_STATEMENT_INVALID, 422),
    ])
    def test_status_is_4xx(self, code, status):
        """所有 AccountingError 都是输入/校验类,应映射到 4xx 而非 500"""
        exc = AccountingError(code=code, message="x", ai_instruction="STOP_RETRYING.")
        assert exc.http_status == status
        assert 400 <= status < 500
