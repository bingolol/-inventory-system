"""JournalRuleRegistry — 凭证结构声明式校验

为每种 move_type 声明预期的科目结构（借方/贷方必须出现的科目前缀），
凭证 post 后自动比对实际凭证 vs 声明规则，发现科目错配。

设计原则：
- 规则只校验"科目结构"（哪些科目前缀应出现），不校验金额（金额由业务逻辑决定）
- 支持条件分支：同一 move_type 可能有多种合法结构（如小规模/一般纳税人）
- 规则与 builder 方法分离，避免循环依赖
- 集成到 engine_journal.post()，违规抛 BusinessError 拦截

与 AS-01（借贷平衡）的关系：
- AS-01 只校验 Σ(debit)==Σ(credit)，不校验科目是否正确
- JournalRule 校验科目结构，补充 AS-01 的盲区
- 例：销售凭证必须用 6001（营业收入），如果误用 5001，AS-01 不报错，但 JournalRule 会报错
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .dsl import RuleViolation


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class AccountPattern:
    """科目模式：描述凭证中应出现的科目前缀

    匹配规则：科目前缀匹配（如 "6001" 匹配 "6001"/"600101"/"60010101"）
    must_have_debit: 借方必须出现的科目前缀（至少一个匹配）
    must_have_credit: 贷方必须出现的科目前缀
    must_not_have: 必须不出现的科目前缀（任何方向都不行）
    condition: 可选，描述此模式的触发条件（仅文档用途，不参与匹配）
    """
    must_have_debit: List[str] = field(default_factory=list)
    must_have_credit: List[str] = field(default_factory=list)
    must_not_have: List[str] = field(default_factory=list)
    condition: str = ""


@dataclass
class JournalRule:
    """凭证规则：声明某种 move_type 的预期结构

    patterns 中的多个模式是 OR 关系：实际凭证匹配任意一个即合规。
    用于支持条件分支（如小规模/一般纳税人不同税金科目）。
    """
    move_type: str
    name: str
    patterns: List[AccountPattern]
    description: str = ""


# ═══════════════════════════════════════════════════════════════
# 注册表
# ═══════════════════════════════════════════════════════════════

_JOURNAL_RULES: Dict[str, JournalRule] = {}


def register_journal_rule(rule: JournalRule) -> JournalRule:
    """注册凭证规则"""
    _JOURNAL_RULES[rule.move_type] = rule
    return rule


def get_journal_rule(move_type: str) -> Optional[JournalRule]:
    """获取 move_type 的规则"""
    return _JOURNAL_RULES.get(move_type)


def all_journal_rules() -> Dict[str, JournalRule]:
    """获取所有规则"""
    return dict(_JOURNAL_RULES)


# ═══════════════════════════════════════════════════════════════
# 校验引擎
# ═══════════════════════════════════════════════════════════════

def _code_matches_prefix(code: str, prefixes: List[str]) -> bool:
    """检查 code 是否匹配任一前缀"""
    return any(code.startswith(p) for p in prefixes)


def check_journal_rule(db, move_id: int) -> List[RuleViolation]:
    """校验单张凭证是否符合其 move_type 的科目结构规则

    Args:
        db: 数据库 session
        move_id: 凭证ID

    Returns:
        RuleViolation 列表（空表示合规）
    """
    from models_finance import AccountMove, AccountMoveLine, LedgerAccount

    move = db.query(AccountMove).filter(AccountMove.id == move_id).first()
    if not move:
        return []

    rule = get_journal_rule(move.move_type)
    if not rule:
        return []  # 无规则，跳过

    # 加载凭证行 + 科目代码
    lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == move_id).all()
    if not lines:
        return []

    # 获取每行对应的科目代码
    code_map = {}
    la_ids = {l.ledger_account_id for l in lines}
    if la_ids:
        las = db.query(LedgerAccount).filter(LedgerAccount.id.in_(la_ids)).all()
        code_map = {la.id: la.code for la in las}

    debit_codes = [code_map.get(l.ledger_account_id, "") for l in lines if (l.debit_l2 or 0) > 0]
    credit_codes = [code_map.get(l.ledger_account_id, "") for l in lines if (l.credit_l2 or 0) > 0]
    all_codes = debit_codes + credit_codes

    violations = []

    # 尝试匹配任一 pattern
    matched_pattern = None
    pattern_failures = []  # 记录每个 pattern 的失败原因

    for idx, pattern in enumerate(rule.patterns):
        failure = _match_pattern(pattern, debit_codes, credit_codes, all_codes, idx)
        if failure is None:
            matched_pattern = pattern
            break
        pattern_failures.append(failure)

    if matched_pattern is None:
        # 所有 pattern 都不匹配，报告违规
        detail = {
            "move_type": move.move_type,
            "move_id": move_id,
            "debit_codes": debit_codes,
            "credit_codes": credit_codes,
            "pattern_failures": pattern_failures,
        }
        violations.append(RuleViolation(
            rule_id="JR-01",
            rule_name=f"凭证结构校验:{rule.name}",
            severity="ERROR",
            message=f"凭证 {move_id} (type={move.move_type}) 科目结构不符合规则。"
                    f"借方:{debit_codes} 贷方:{credit_codes}。"
                    f"预期:{[p.condition or f'pattern#{i}' for i, p in enumerate(rule.patterns)]}",
            fix_hint=f"检查 _build_{move.move_type} builder 方法的科目代码",
            field="AccountMoveLine.ledger_account_id",
            detail=detail,
        ))

    return violations


def _match_pattern(pattern: AccountPattern, debit_codes: List[str],
                   credit_codes: List[str], all_codes: List[str],
                   pattern_idx: int) -> Optional[str]:
    """尝试匹配单个 pattern。返回 None 表示匹配成功，返回字符串表示失败原因

    语义（与 AccountPattern docstring 一致）：
    - must_have_debit: 列表中任一前缀在借方匹配即可（OR 语义）
    - must_have_credit: 列表中任一前缀在贷方匹配即可（OR 语义）
    - must_not_have: 列表中任一前缀在任何方向匹配都算违规
    """
    # 检查 must_have_debit：借方至少有一个科目匹配列表中任一前缀
    if pattern.must_have_debit:
        if not any(any(c.startswith(p) for p in pattern.must_have_debit) for c in debit_codes):
            return f"pattern#{pattern_idx}: 借方缺少科目前缀 {pattern.must_have_debit}（任一即可）"

    # 检查 must_have_credit：贷方至少有一个科目匹配列表中任一前缀
    if pattern.must_have_credit:
        if not any(any(c.startswith(p) for p in pattern.must_have_credit) for c in credit_codes):
            return f"pattern#{pattern_idx}: 贷方缺少科目前缀 {pattern.must_have_credit}（任一即可）"

    # 检查 must_not_have：任何方向都不应出现（任一前缀匹配即违规）
    for prefix in pattern.must_not_have:
        if any(c.startswith(prefix) for c in all_codes):
            return f"pattern#{pattern_idx}: 不应出现科目前缀 {prefix}"

    return None  # 匹配成功


def enforce_journal_rules(db, move_id: int) -> None:
    """在凭证 post 后运行时校验科目结构，违规抛 BusinessError 拦截

    集成点：engine_journal.post() 在 enforce_rules(["AS-01"]) 之后调用

    Args:
        db: 数据库 session
        move_id: 凭证ID

    Raises:
        BusinessError(ErrorCode.RULE_VIOLATION): 当科目结构违规时
    """
    from errors import BusinessError, ErrorCode

    violations = check_journal_rule(db, move_id)
    if violations:
        summary = "; ".join(f"[{v.rule_id}] {v.message}" for v in violations)
        raise BusinessError(
            ErrorCode.RULE_VIOLATION,
            message=f"凭证科目结构校验失败: {summary}",
            data={
                "details": summary,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity,
                        "message": v.message,
                        "fix_hint": v.fix_hint,
                        "field": v.field,
                    }
                    for v in violations
                ],
            },
        )


# ═══════════════════════════════════════════════════════════════
# 规则定义：为核心 move_type 注册科目结构
# ═══════════════════════════════════════════════════════════════

def _register_default_rules():
    """注册默认凭证规则

    覆盖核心业务凭证：销售/采购/收款/付款/费用/折旧/税金结转
    不覆盖：opening_balance/cash_flow/reverse_entry/period_close/year_close
    （这些是基础设施凭证，结构灵活，不适合固定规则）
    """
    from operation_result import EntityType as ET

    # 销售订单：借应收 贷收入+销项税 (+借成本 贷库存)
    register_journal_rule(JournalRule(
        move_type=ET.SALE_ORDER, name="销售订单",
        patterns=[
            AccountPattern(
                must_have_debit=["1122"],  # 应收账款
                must_have_credit=["6001", "6051"],  # 营业收入
                condition="一般纳税人/小规模销售",
            ),
        ],
        description="销售凭证必须借应收(1122)、贷收入(6001/6051)，可选贷销项税(222101/222103)",
    ))

    # 采购订单：借库存+进项税 贷应付；或借费用（服务类商品）+进项税 贷应付
    register_journal_rule(JournalRule(
        move_type=ET.PURCHASE_ORDER, name="采购订单",
        patterns=[
            AccountPattern(
                must_have_debit=["1405"],  # 库存商品
                must_have_credit=["2202", "2241"],  # 应付账款 或 其他应付款（个人垫付）
                condition="采购入库",
            ),
            AccountPattern(
                must_have_debit=["6601"],  # 主体费用（服务类商品直接费用化）
                must_have_credit=["2202", "2241"],
                condition="采购服务",
            ),
        ],
        description="采购凭证必须借库存(1405)或费用(6601)、贷应付(2202)或其他应付款(2241)，可选借进项税(222102)",
    ))

    # 销售退货：反向销售
    register_journal_rule(JournalRule(
        move_type=ET.SALE_RETURN, name="销售退货",
        patterns=[
            AccountPattern(
                must_have_debit=["6001", "6051"],  # 红字收入
                must_have_credit=["1122"],  # 红字应收
                condition="销售退货",
            ),
        ],
        description="销售退货必须借收入(6001/6051)、贷应收(1122)",
    ))

    # 采购退货：反向采购
    register_journal_rule(JournalRule(
        move_type=ET.PURCHASE_RETURN, name="采购退货",
        patterns=[
            AccountPattern(
                must_have_debit=["2202"],  # 红字应付
                must_have_credit=["1405"],  # 红字库存
                condition="采购退货",
            ),
        ],
        description="采购退货必须借应付(2202)、贷库存(1405)",
    ))

    # 收款：借银行/现金 贷应收
    register_journal_rule(JournalRule(
        move_type=ET.RECEIPT, name="收款",
        patterns=[
            AccountPattern(
                must_have_debit=["1001", "1002"],  # 库存现金/银行存款
                must_have_credit=["1122"],  # 应收账款
                condition="客户收款",
            ),
        ],
        description="收款凭证必须借现金/银行(1001/1002)、贷应收(1122)",
    ))

    # 付款：借应付 贷银行/现金 (+贷代扣个税)
    register_journal_rule(JournalRule(
        move_type=ET.PAYMENT, name="付款",
        patterns=[
            AccountPattern(
                must_have_debit=["2202", "2211"],  # 应付账款/应付职工薪酬
                must_have_credit=["1001", "1002"],  # 库存现金/银行存款
                condition="供应商付款/工资发放",
            ),
        ],
        description="付款凭证必须借应付(2202/2211)、贷现金/银行(1001/1002)",
    ))

    # 费用：借费用科目 贷银行/应付/应付职工薪酬/其他应付款
    # _build_expense 贷方按场景：1001/1002(现金/银行)、2202(供应商)、2211(工资)、2241(个人垫付)
    register_journal_rule(JournalRule(
        move_type=ET.EXPENSE, name="费用报销",
        patterns=[
            AccountPattern(
                must_have_debit=["6601", "6602", "6603", "6403"],  # 管理/销售/财务/税金及附加
                must_have_credit=["1001", "1002", "2202", "2211", "2241"],
                condition="费用报销",
            ),
        ],
        description="费用凭证必须借费用类(6601/6602/6603/6403)、贷现金/银行/应付/应付职工薪酬/其他应付款",
    ))

    # 折旧：借管理费用 贷累计折旧/累计摊销
    register_journal_rule(JournalRule(
        move_type=ET.DEPRECIATION, name="折旧摊销",
        patterns=[
            AccountPattern(
                must_have_debit=["6601"],  # 管理费用
                must_have_credit=["1602", "1702"],  # 累计折旧/累计摊销
                condition="月度折旧摊销",
            ),
        ],
        description="折旧凭证必须借管理费用(6601)、贷累计折旧/摊销(1602/1702)",
    ))

    # 固定资产采购：借固定资产 贷银行/应付/其他应付款(个人垫付)
    register_journal_rule(JournalRule(
        move_type=ET.FIXED_ASSET_PURCHASE, name="固定资产采购",
        patterns=[
            AccountPattern(
                must_have_debit=["1601"],  # 固定资产
                must_have_credit=["1001", "1002", "2202"],  # 现金/银行/应付（公司采购）
                condition="固定资产采购-公司付款",
            ),
            AccountPattern(
                must_have_debit=["1601"],  # 固定资产
                must_have_credit=["2241"],  # 其他应付款（个人垫付）
                condition="固定资产采购-个人垫付",
            ),
        ],
        description="固定资产采购必须借固定资产(1601)、贷现金/银行/应付(2202)/其他应付款(2241个人垫付)",
    ))

    # 无形资产采购：借无形资产 贷银行/应付/其他应付款(个人垫付)
    register_journal_rule(JournalRule(
        move_type=ET.INTANGIBLE_ASSET_PURCHASE, name="无形资产采购",
        patterns=[
            AccountPattern(
                must_have_debit=["1701"],  # 无形资产
                must_have_credit=["1001", "1002", "2202"],  # 现金/银行/应付（公司采购）
                condition="无形资产采购-公司付款",
            ),
            AccountPattern(
                must_have_debit=["1701"],  # 无形资产
                must_have_credit=["2241"],  # 其他应付款（个人垫付）
                condition="无形资产采购-个人垫付",
            ),
        ],
        description="无形资产采购必须借无形资产(1701)、贷现金/银行/应付(2202)/其他应付款(2241个人垫付)",
    ))

    # 附加税计提：借税金及附加 贷应交税费
    register_journal_rule(JournalRule(
        move_type=ET.TAX_SURCHARGE, name="附加税计提",
        patterns=[
            AccountPattern(
                must_have_debit=["6403"],  # 税金及附加
                must_have_credit=["222"],  # 应交税费（222110/222111/222112等）
                condition="月度附加税计提",
            ),
        ],
        description="附加税计提必须借税金及附加(6403)、贷应交税费(222xxx)",
    ))

    # 所得税计提：借所得税费用 贷应交所得税
    register_journal_rule(JournalRule(
        move_type=ET.TAX_INCOME, name="所得税计提",
        patterns=[
            AccountPattern(
                must_have_debit=["6801"],  # 所得税费用
                must_have_credit=["222105"],  # 应交所得税
                condition="所得税计提",
            ),
        ],
        description="所得税计提必须借所得税费用(6801)、贷应交所得税(222105)",
    ))

    # 所得税冲回：反向所得税计提
    register_journal_rule(JournalRule(
        move_type=ET.TAX_INCOME_REVERSAL, name="所得税冲回",
        patterns=[
            AccountPattern(
                must_have_debit=["222105"],  # 应交所得税
                must_have_credit=["6801"],  # 所得税费用
                condition="所得税冲回",
            ),
        ],
        description="所得税冲回必须借应交所得税(222105)、贷所得税费用(6801)",
    ))

    # VAT 转出：借转出未交增值税 贷未交增值税（§12.3）
    register_journal_rule(JournalRule(
        move_type=ET.VAT_TRANSFER_OUT, name="VAT转出",
        patterns=[
            AccountPattern(
                must_have_debit=["222106"],  # 转出未交增值税
                must_have_credit=["222107"],  # 未交增值税
                condition="月末VAT转出",
            ),
        ],
        description="VAT转出必须借转出未交增值税(222106)、贷未交增值税(222107)",
    ))

    # VAT 免税：借应交增值税 费营业收入（免税转收入）
    register_journal_rule(JournalRule(
        move_type=ET.VAT_EXEMPTION, name="VAT免税",
        patterns=[
            AccountPattern(
                must_have_debit=["222101", "222103"],  # 应交增值税
                must_have_credit=["6101", "6051", "6001", "6301"],  # 营业外收入/其他业务收入/营业收入/税收减免
                condition="小规模免税",
            ),
        ],
        description="VAT免税必须借应交增值税(222101/222103)、贷收入类(6101/6051/6001)",
    ))

    # 资产处置：贷资产原值 + 借方按场景（折旧/收款/损益）
    # _build_asset_disposal 在 accumulated=0 时 1602 debit=0 不进入借方列表，
    # 因此不能用单一 pattern 强制借方必须有 1602/1702
    register_journal_rule(JournalRule(
        move_type=ET.ASSET_DISPOSAL, name="资产处置",
        patterns=[
            # 完整处置（有折旧）：借累计折旧/摊销
            AccountPattern(
                must_have_debit=["1602", "1702"],
                must_have_credit=["1601", "1701"],
                condition="有折旧处置",
            ),
            # 无折旧亏损（disposal_price=0, diff<0）：借营业外支出
            AccountPattern(
                must_have_debit=["6701"],
                must_have_credit=["1601", "1701"],
                condition="无折旧亏损处置",
            ),
            # 无折旧有收款（disposal_price>0）：借银行存款
            AccountPattern(
                must_have_debit=["1002"],
                must_have_credit=["1601", "1701"],
                condition="无折旧有收款处置",
            ),
        ],
        description="资产处置贷方必须有资产原值(1601/1701)；借方按场景：折旧(1602/1702)/收款(1002)/损益(6701)",
    ))

    # 银行手续费/利息：两种结构（手续费借费用贷银行；利息收入借银行贷费用）
    register_journal_rule(JournalRule(
        move_type=ET.BANK_FEE_ENTRY, name="银行手续费/利息",
        patterns=[
            AccountPattern(
                must_have_debit=["6603", "6601"],  # 财务费用/管理费用
                must_have_credit=["1002"],  # 银行存款
                condition="银行手续费",
            ),
            AccountPattern(
                must_have_debit=["1002"],  # 银行存款
                must_have_credit=["6603", "6601"],  # 财务费用/管理费用（红字或冲减）
                condition="银行利息收入",
            ),
        ],
        description="银行手续费借费用(6603/6601)贷银行(1002)；利息收入借银行(1002)贷费用(6603/6601)",
    ))

    # 个人垫付：借费用/资产/应交税费 贷其他应付款
    # 借方由 debit_account_code 决定用途（与 PERSONAL_ADVANCE_DEBIT_ACCOUNTS 白名单一致）
    register_journal_rule(JournalRule(
        move_type=ET.PERSONAL_ADVANCE, name="个人垫付",
        patterns=[
            AccountPattern(
                must_have_debit=["6601", "6602", "6603", "6403"],  # 费用类
                must_have_credit=["2241"],  # 其他应付款
                condition="个人垫付费用",
            ),
            AccountPattern(
                must_have_debit=["1405", "1601", "1701"],  # 资产类（垫付采购货款/固定资产/无形资产）
                must_have_credit=["2241"],
                condition="个人垫付资产",
            ),
            AccountPattern(
                must_have_debit=["222103", "222105", "222107", "222110"],  # 应交税费（个人垫付代缴税: 小规模增值税/所得税/未交增值税/城建税）
                must_have_credit=["2241"],
                condition="个人垫付代缴税",
            ),
            AccountPattern(
                must_have_debit=["1221"],  # 其他应收款（多缴所得税挂账）
                must_have_credit=["2241"],
                condition="个人垫付-多缴所得税挂账",
            ),
            AccountPattern(
                must_have_debit=["6711"],  # 营业外支出-税收滞纳金
                must_have_credit=["2241"],
                condition="个人垫付-税收滞纳金",
            ),
        ],
        description="个人垫付必须贷其他应付款(2241)；借方按用途：费用(6601/6602/6603/6403/6711)/资产(1405/1601/1701/1221)/应交税费(222103/222105/222110)",
    ))

    # 个人垫付还款：借其他应付款 贷银行/现金
    register_journal_rule(JournalRule(
        move_type=ET.PERSONAL_ADVANCE_REPAYMENT, name="个人垫付还款",
        patterns=[
            AccountPattern(
                must_have_debit=["2241"],  # 其他应付款
                must_have_credit=["1001", "1002"],  # 现金/银行
                condition="个人垫付还款",
            ),
        ],
        description="个人垫付还款必须借其他应付款(2241)、贷现金/银行(1001/1002)",
    ))


# 模块加载时自动注册默认规则
_register_default_rules()
