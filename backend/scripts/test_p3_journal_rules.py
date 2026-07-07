"""P3 JournalRuleRegistry 凭证结构校验测试脚本

验证 JournalRuleRegistry 对所有 posted 凭证的科目结构校验功能。
遍历数据库中所有 state='posted' 的 AccountMove，调用 check_journal_rule，
统计合规/违规情况；发现违规时打印明细并分析是否为规则误报或真实 bug。

用法:
    cd backend/scripts
    python test_p3_journal_rules.py
"""
import sys
from pathlib import Path
from collections import defaultdict

# 把 backend/ 加入 sys.path，使脚本可独立运行
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
import models  # noqa: F401  确保模型表注册
from models_finance import AccountMove, AccountMoveLine, LedgerAccount
from rules import check_journal_rule, all_journal_rules, get_journal_rule


def _print_registered_rules():
    """打印所有已注册的 JournalRule（move_type/name/patterns 数量）"""
    rules = all_journal_rules()
    print(f"已注册 JournalRule 数量: {len(rules)}")
    print(f"  {'move_type':<32} {'name':<16} {'patterns':>8}")
    print(f"  {'-'*32} {'-'*16} {'-'*8}")
    for mt, rule in sorted(rules.items()):
        print(f"  {mt:<32} {rule.name:<16} {len(rule.patterns):>8}")


def _get_debit_credit_codes(db, move_id):
    """获取凭证的借方/贷方科目代码列表（与 check_journal_rule 内部逻辑一致）"""
    lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == move_id).all()
    if not lines:
        return [], []
    la_ids = {l.ledger_account_id for l in lines}
    las = db.query(LedgerAccount).filter(LedgerAccount.id.in_(la_ids)).all()
    code_map = {la.id: la.code for la in las}
    debit_codes = [code_map.get(l.ledger_account_id, "?")
                   for l in lines if (l.debit_l2 or 0) > 0]
    credit_codes = [code_map.get(l.ledger_account_id, "?")
                    for l in lines if (l.credit_l2 or 0) > 0]
    return debit_codes, credit_codes


def main():
    db = SessionLocal()
    try:
        print("=" * 90)
        print(" P3 JournalRuleRegistry 凭证结构校验测试")
        print("=" * 90)
        print()

        # ── 1. 打印所有已注册的 JournalRule ──
        _print_registered_rules()
        print()

        registered = all_journal_rules()

        # ── 2. 遍历所有 posted 凭证 ──
        moves = db.query(AccountMove).filter(AccountMove.state == "posted").all()
        total = len(moves)
        with_rule = 0       # 有规则的凭证数
        without_rule = 0    # 无规则的凭证数（跳过）
        compliant = 0       # 合规凭证数（无 violation）
        violated = 0        # 违规凭证数（有 violation）
        violations_by_type = defaultdict(list)  # move_type -> [(move, violations)]

        for move in moves:
            rule = get_journal_rule(move.move_type)
            if rule is None:
                without_rule += 1
                continue
            with_rule += 1

            vs = check_journal_rule(db, move.id)
            if not vs:
                compliant += 1
            else:
                violated += 1
                violations_by_type[move.move_type].append((move, vs))

        # ── 3. 统计汇总 ──
        print("=" * 90)
        print(" 统计汇总")
        print("=" * 90)
        print(f"  总凭证数 (posted):           {total}")
        print(f"  有规则的凭证数:               {with_rule}")
        print(f"  无规则的凭证数 (跳过):        {without_rule}")
        print(f"  合规凭证数 (无 violation):    {compliant}")
        print(f"  违规凭证数 (有 violation):    {violated}")
        print()

        # ── 4. 违规明细 ──
        if violated == 0:
            print("  违规明细: (none)")
        else:
            print("=" * 90)
            print(f" 违规明细 ({violated} 张)")
            print("=" * 90)
            idx = 0
            for mt, items in sorted(violations_by_type.items()):
                for move, vs in items:
                    idx += 1
                    debit_codes, credit_codes = _get_debit_credit_codes(db, move.id)
                    print()
                    print(f"  [{idx}] move_id={move.id}, move_type='{mt}', "
                          f"move_name='{move.name}', date={move.date_l1}")
                    print(f"      借方科目: {debit_codes}")
                    print(f"      贷方科目: {credit_codes}")
                    for v in vs:
                        print(f"      violation: [{v.rule_id}] {v.rule_name} ({v.severity})")
                        print(f"                 message: {v.message}")
                        if v.fix_hint:
                            print(f"                 fix_hint: {v.fix_hint}")
        print()

        # ── 5. 最终结论 ──
        print("=" * 90)
        if violated == 0:
            print(" PASS: 所有有规则凭证均合规")
        else:
            print(f" FAIL: 共 {violated} 张凭证违规，明细见上")
        print("=" * 90)

    finally:
        db.close()


if __name__ == "__main__":
    main()
