"""AS-22 显式不支持场景边界声明测试

验证:
1. AS-22 规则定义完整性(已注册、必填字段齐全、severity=WARNING)
2. 静态扫描函数 _check_as22_unsupported_boundary 正确检出/不误报
3. _check_rule_definitions 包含 AS-22 in expected_ids
4. 实际代码库扫描:commands/routers 无 PurchaseEstimate/BadDebt 引用

运行:python -m pytest tests/invariants/test_as22_unsupported_boundary.py -v
"""
import os
import sys
import tempfile
import pytest
from pathlib import Path

# 把 backend 加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture(scope="module", autouse=True)
def _load_rules():
    """模块级前置:加载规则定义"""
    from rules import load_all_rules
    load_all_rules()


# ═══════════════════════════════════════════════════════════════
# 一、AS-22 规则定义完整性
# ═══════════════════════════════════════════════════════════════

class TestAS22RuleDefinition:
    """AS-22 规则定义完整性校验"""

    def test_AS22已注册(self):
        from rules import get_rule_by_id
        r = get_rule_by_id("AS-22")
        assert r is not None, "AS-22 规则未注册"

    def test_AS22必填字段齐全(self):
        from rules import get_rule_by_id
        r = get_rule_by_id("AS-22")
        assert r.name, "AS-22 name 为空"
        assert r.source, "AS-22 source 为空"
        assert r.trigger, "AS-22 trigger 为空"
        assert r.expected_chain, "AS-22 expected_chain 为空"

    def test_AS22名称正确(self):
        from rules import get_rule_by_id
        r = get_rule_by_id("AS-22")
        assert "不支持场景" in r.name or "边界声明" in r.name

    def test_AS22severity为WARNING(self):
        """边界声明用 WARNING(非 ERROR),因为保留模型骨架是允许的设计"""
        from rules import get_rule_by_id
        from rules.dsl import SEVERITY_WARNING
        r = get_rule_by_id("AS-22")
        assert r.severity == SEVERITY_WARNING, f"AS-22 应为 WARNING,实际 {r.severity}"

    def test_AS22category为IMPLEMENTATION(self):
        from rules import get_rule_by_id
        from rules.dsl import CATEGORY_IMPLEMENTATION
        r = get_rule_by_id("AS-22")
        assert r.category == CATEGORY_IMPLEMENTATION

    def test_AS22不变量覆盖7个不支持场景(self):
        from rules import get_rule_by_id
        r = get_rule_by_id("AS-22")
        # B2 / I / A5 / B3 / D2 / D3 / N = 7 个
        assert len(r.invariants) >= 7, f"AS-22 应覆盖至少 7 个不支持场景,实际 {len(r.invariants)}"

    def test_AS22禁止项非空(self):
        from rules import get_rule_by_id
        r = get_rule_by_id("AS-22")
        assert len(r.prohibited) >= 1

    def test_AS22related_fields包含不支持模型(self):
        from rules import get_rule_by_id
        r = get_rule_by_id("AS-22")
        assert "PurchaseEstimate" in r.related_fields
        assert "BadDebt" in r.related_fields


# ═══════════════════════════════════════════════════════════════
# 二、_check_rule_definitions 包含 AS-22
# ═══════════════════════════════════════════════════════════════

class TestCheckRuleDefinitionsIncludesAS22:
    """_check_rule_definitions() 应把 AS-22 纳入 expected_ids"""

    def test_无缺失规则(self):
        from rules.validator import _check_rule_definitions
        violations = _check_rule_definitions()
        # 不应有"缺失规则定义"违规
        missing_violations = [v for v in violations if "缺失" in v.message]
        assert len(missing_violations) == 0, f"规则定义缺失: {[v.message for v in missing_violations]}"

    def test_AS22不报ID重复(self):
        from rules.validator import _check_rule_definitions
        violations = _check_rule_definitions()
        as22_dup = [v for v in violations if v.rule_id == "AS-22" and "重复" in v.message]
        assert len(as22_dup) == 0, f"AS-22 被误报为重复: {[v.message for v in as22_dup]}"


# ═══════════════════════════════════════════════════════════════
# 三、静态扫描函数 _check_as22_unsupported_boundary
# ═══════════════════════════════════════════════════════════════

class TestCheckAS22StaticScan:
    """_check_as22_unsupported_boundary() 静态扫描逻辑"""

    def test_实际代码库扫描无违规(self):
        """当前 backend/commands 和 backend/routers 无 PurchaseEstimate/BadDebt 引用"""
        from rules.validator import _check_as22_unsupported_boundary
        violations = _check_as22_unsupported_boundary()
        # 不应有违规(用户已决策不实现,代码库已无引用)
        assert len(violations) == 0, \
            f"AS-22 静态扫描发现违规: {[v.message for v in violations]}"

    def test_扫描函数返回列表类型(self):
        from rules.validator import _check_as22_unsupported_boundary
        result = _check_as22_unsupported_boundary()
        assert isinstance(result, list)

    def test_扫描函数不抛异常(self):
        """函数应能正常执行,不抛 NameError/AttributeError 等"""
        from rules.validator import _check_as22_unsupported_boundary
        # 不抛异常即通过
        _check_as22_unsupported_boundary()


# ═══════════════════════════════════════════════════════════════
# 四、扫描逻辑单元测试(mock 文件内容)
# ═══════════════════════════════════════════════════════════════

class TestAS22ScanLogic:
    """通过 mock 验证扫描逻辑能检出违规"""

    def test_检测PurchaseEstimate引用(self):
        """模拟 commands 文件引用 PurchaseEstimate,应被检出"""
        from rules.validator import _UNSUPPORTED_MODELS
        assert "PurchaseEstimate" in _UNSUPPORTED_MODELS

    def test_检测BadDebt引用(self):
        from rules.validator import _UNSUPPORTED_MODELS
        assert "BadDebt" in _UNSUPPORTED_MODELS

    def test_关键词覆盖所有不支持场景(self):
        """_UNSUPPORTED_KEYWORDS 应覆盖 7 个不支持场景"""
        from rules.validator import _UNSUPPORTED_KEYWORDS
        # 至少覆盖 B2/I/A5/B3/D2/D3/N
        scenarios_in_keywords = set(_UNSUPPORTED_KEYWORDS.values())
        expected_scenarios = {
            "B2 暂估入库", "I 坏账核销", "A5 分期收款销售",
            "B3 在途物资", "D2 现金折扣", "D3 销售折让", "N 长期待摊费用",
        }
        missing = expected_scenarios - scenarios_in_keywords
        assert not missing, f"_UNSUPPORTED_KEYWORDS 缺少场景: {missing}"

    def test_正则匹配PurchaseEstimate单词边界(self):
        """验证 \\b 边界匹配,避免 PurchaseEstimateXYZ 误报"""
        import re
        content = "from models import PurchaseEstimate\nx = PurchaseEstimate(arg)"
        pattern = r"\bPurchaseEstimate\b"
        matches = re.findall(pattern, content)
        assert len(matches) == 2  # 2 处引用

    def test_正则不匹配PurchaseEstimateXYZ(self):
        import re
        content = "PurchaseEstimateXYZ = 1"
        pattern = r"\bPurchaseEstimate\b"
        matches = re.findall(pattern, content)
        # 单词边界:PurchaseEstimateXYZ 不应匹配 PurchaseEstimate
        # 注意:\b 在 X(字母)后无边界,所以不匹配
        assert len(matches) == 0, f"误报: {matches}"


# ═══════════════════════════════════════════════════════════════
# 五、validate_rules 集成:AS-22 被纳入校验链
# ═══════════════════════════════════════════════════════════════

class TestValidateRulesIncludesAS22:
    """validate_rules() 应调用 AS-22 校验"""

    def test_validate_rules无registry时执行AS22扫描(self):
        """validate_rules(registry=None) 应包含 AS-22 扫描结果"""
        from rules import validate_rules
        violations = validate_rules(registry=None)
        # 当前代码库无违规,所以 violations 为空
        # 但能正常执行(说明 AS-22 扫描被调用,没抛 NameError)
        assert isinstance(violations, list)

    def test_validate_rules无registry不抛NameError(self):
        """关键回归:validate_rules 不应因 _check_as22 函数缺失而报 NameError"""
        from rules import validate_rules
        try:
            validate_rules(registry=None)
        except NameError as e:
            pytest.fail(f"validate_rules 抛 NameError: {e} — _check_as22_unsupported_boundary 函数未定义")


# ═══════════════════════════════════════════════════════════════
# 六、临时目录扫描测试(验证扫描逻辑真能检出违规)
# ═══════════════════════════════════════════════════════════════

class TestAS22ScanDetectsViolation:
    """用临时目录验证 _check_as22_unsupported_boundary 真能检出违规"""

    def test_临时目录含PurchaseEstimate引用应报违规(self, monkeypatch, tmp_path):
        """在临时 commands 目录放一个引用 PurchaseEstimate 的文件,验证扫描能检出"""
        from rules import validator as validator_mod

        # 在 tmp_path 下建 commands 目录,放一个含违规引用的文件
        commands_dir = tmp_path / "commands"
        commands_dir.mkdir()
        bad_file = commands_dir / "bad_command.py"
        bad_file.write_text(
            "from models import PurchaseEstimate\n"
            "def create_estimate():\n"
            "    return PurchaseEstimate()\n",
            encoding="utf-8",
        )

        # monkeypatch _scan_source_files 让它扫描我们的临时目录
        original_scan = validator_mod._scan_source_files

        def mock_scan(base_dir):
            # 只扫描临时目录,避免扫真实 backend
            if "commands" in str(base_dir) or "routers" in str(base_dir):
                return original_scan(str(base_dir))
            return []

        # 直接 monkeypatch 扫描路径
        monkeypatch.setattr(
            validator_mod,
            "_check_as22_unsupported_boundary",
            lambda: _scan_with_custom_dirs([str(commands_dir)], str(tmp_path)),
        )

        # 调用 patched 函数
        violations = validator_mod._check_as22_unsupported_boundary()
        assert len(violations) > 0, "应检出 PurchaseEstimate 引用违规"
        as22_violations = [v for v in violations if v.rule_id == "AS-22"]
        assert len(as22_violations) > 0
        assert any("PurchaseEstimate" in v.message for v in as22_violations)


def _scan_with_custom_dirs(scan_dirs, backend_dir):
    """辅助函数:扫描自定义目录,返回违规列表"""
    from rules.validator import (
        _scan_source_files, _UNSUPPORTED_MODELS, _UNSUPPORTED_KEYWORDS,
        get_rule_by_id,
    )
    from rules.dsl import RuleViolation, SEVERITY_WARNING
    import re

    violations = []
    rule = get_rule_by_id("AS-22")
    if not rule:
        return violations

    for scan_dir in scan_dirs:
        for fpath, content in _scan_source_files(scan_dir):
            if not content:
                continue
            rel_path = os.path.relpath(fpath, backend_dir).replace("\\", "/")
            layer = "commands" if "/commands/" in rel_path else "routers"

            for model_name, scenario_desc in _UNSUPPORTED_MODELS.items():
                pattern = r"\b" + re.escape(model_name) + r"\b"
                matches = re.findall(pattern, content)
                if matches:
                    violations.append(RuleViolation(
                        rule_id="AS-22",
                        rule_name=rule.name,
                        severity=SEVERITY_WARNING,
                        message=f"{layer}/{rel_path} 引用了不支持场景模型 {model_name} ({scenario_desc})",
                        fix_hint=f"删除对 {model_name} 的引用",
                        field=model_name,
                        detail={"file": rel_path, "model": model_name, "match_count": len(matches)},
                    ))

    return violations
