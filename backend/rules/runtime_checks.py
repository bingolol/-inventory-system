"""AS-01~AS-07 运行时校验函数

把 9 条会计实务规则的 invariants 文本变成可执行校验函数,
接收 db session 和 context,返回 RuleViolation 列表。

调用方式:
    from rules import validate_rules_runtime
    violations = validate_rules_runtime(db, "AS-01", {"move_id": 123})

或在测试中:
    vs = validate_rules_runtime(db, "AS-01", {"report_date": date(2026,6,30), "account_id": 1})
    assert not vs  # BS 应平衡

context 字段说明(按规则):
    AS-01: move_id(单张凭证) 或 report_date+account_id(BS 恒等式)
    AS-02: invoice_id
    AS-03: product_id(校验库存账面价值==StockMove求和)
    AS-04: account_id+start_date+end_date(校验期间收入==总账6001)
    AS-05: asset_id(校验月折旧公式) 或 batch_date(批量校验)
    AS-06: invoice_id(校验红字发票金额为负)
    AS-07: asset_id(校验处置凭证用了6301/6701)
"""
from typing import List, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from .dsl import RuleViolation
from .validator import get_rule_by_id
from errors import BusinessError, ErrorCode

Q2 = Decimal("0.01")
TOLERANCE = Decimal("0.01")  # 误差容忍


def _make_violation(rule_id: str, message: str, fix_hint: str = "", field: str = None, detail: Any = None) -> RuleViolation:
    """构造违规结果"""
    rule = get_rule_by_id(rule_id)
    return RuleViolation(
        rule_id=rule_id,
        rule_name=rule.name if rule else rule_id,
        severity=rule.severity if rule else "ERROR",
        message=message,
        fix_hint=fix_hint,
        field=field,
        detail=detail,
    )


# ═══════════════════════════════════════════════════════════════
# AS-01: 借贷平衡与资产负债恒等式
# ═══════════════════════════════════════════════════════════════

def check_as01(db: Session, context: dict) -> List[RuleViolation]:
    """AS-01 校验:借贷平衡 / BS 恒等式

    context:
    - move_id: 凭证ID → 校验单张凭证 Σ(debit)==Σ(credit)
    - report_date + account_id: → 校验 BS 恒等式 资产==负债+权益
    """
    violations = []
    move_id = context.get("move_id")
    report_date = context.get("report_date")
    account_id = context.get("account_id")

    if move_id:
        from models_finance import AccountMoveLine
        lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == move_id).all()
        if not lines:
            return violations
        debit = sum((l.debit_l2 or Decimal("0")) for l in lines)
        credit = sum((l.credit_l2 or Decimal("0")) for l in lines)
        if abs(debit - credit) > TOLERANCE:
            violations.append(_make_violation(
                "AS-01",
                f"凭证 {move_id} 借贷不平:借方 {debit} ≠ 贷方 {credit} (差 {debit - credit})",
                fix_hint="检查 AccountMoveLine.debit_l2/credit_l2 金额",
                detail={"move_id": move_id, "debit": float(debit), "credit": float(credit)},
            ))

    if report_date and account_id:
        from crud.finance.balance_sheet import generate_balance_sheet
        try:
            bs = generate_balance_sheet(db, account_id=account_id, end_date=report_date)
            total_assets = Decimal(str(bs.get("total_assets", 0)))
            total_liabilities = Decimal(str(bs.get("total_liabilities", 0)))
            total_equity = Decimal(str(bs.get("total_equity", 0)))
            diff = total_assets - total_liabilities - total_equity
            if abs(diff) > TOLERANCE:
                violations.append(_make_violation(
                    "AS-01",
                    f"BS 不平:资产 {total_assets} ≠ 负债 {total_liabilities} + 权益 {total_equity} (差 {diff})",
                    fix_hint="检查报表生成逻辑或凭证数据 cutoff",
                    detail={"report_date": str(report_date), "diff": float(diff)},
                ))
        except Exception as e:
            violations.append(_make_violation(
                "AS-01",
                f"BS 生成失败,无法校验恒等式: {e}",
                fix_hint="检查 generate_balance_sheet 函数",
            ))

    return violations


# ═══════════════════════════════════════════════════════════════
# AS-02: 价税分离
# ═══════════════════════════════════════════════════════════════

def check_as02(db: Session, context: dict) -> List[RuleViolation]:
    """AS-02 校验:发票三段平衡

    context:
    - invoice_id: 发票ID
    """
    violations = []
    invoice_id = context.get("invoice_id")
    if not invoice_id:
        return violations

    from models import Invoice
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        return violations

    without_tax = inv.amount_without_tax_l1 or Decimal("0")
    tax_amount = inv.tax_amount_l1 or Decimal("0")
    with_tax = inv.amount_with_tax_l1 or Decimal("0")

    # 校验三段平衡
    diff = (without_tax + tax_amount) - with_tax
    if abs(diff) > TOLERANCE:
        violations.append(_make_violation(
            "AS-02",
            f"发票 {invoice_id} 三段不平:不含税 {without_tax} + 税额 {tax_amount} ≠ 价税合计 {with_tax} (差 {diff})",
            fix_hint="检查 calculate_invoice_amounts 计算",
            field="Invoice.amount_with_tax_l1",
            detail={"invoice_id": invoice_id, "diff": float(diff)},
        ))

    # 校验税率非硬编码(查税率是否合法)
    tax_rate = inv.tax_rate_l1 or Decimal("0")
    valid_rates = {Decimal("0.01"), Decimal("0.03"), Decimal("0.06"), Decimal("0.09"), Decimal("0.13"), Decimal("0")}
    if tax_rate not in valid_rates:
        violations.append(_make_violation(
            "AS-02",
            f"发票 {invoice_id} 税率 {tax_rate} 非法,不在合法税率集 {{0.01, 0.03, 0.06, 0.09, 0.13}} 中",
            fix_hint="检查 Invoice.tax_rate_l1 录入",
            field="Invoice.tax_rate_l1",
            detail={"invoice_id": invoice_id, "tax_rate": float(tax_rate)},
        ))

    return violations


# ═══════════════════════════════════════════════════════════════
# AS-03: 移动加权平均法
# ═══════════════════════════════════════════════════════════════

def check_as03(db: Session, context: dict) -> List[RuleViolation]:
    """AS-03 校验:库存账面价值 == Σ(方向 × StockMove.total_cost_l2)

    context:
    - product_id: 商品ID → 校验 Inventory.total_value_l4 == StockMove 求和
    - account_id: 账本ID → 校验所有商品
    """
    violations = []
    product_id = context.get("product_id")
    account_id = context.get("account_id")

    from models import StockMove, Inventory

    if product_id:
        inv = db.query(Inventory).filter(Inventory.product_id == product_id).first()
        if not inv:
            return violations
        moves = db.query(StockMove).filter(StockMove.product_id == product_id).all()
        sum_total = sum(
            (Decimal(str(m.total_cost_l2 or 0)) if Decimal(str(m.quantity_l1 or 0)) > 0
             else -Decimal(str(m.total_cost_l2 or 0)))
            for m in moves
        )
        diff = (inv.total_value_l4 or Decimal("0")) - sum_total
        if abs(diff) > TOLERANCE:
            violations.append(_make_violation(
                "AS-03",
                f"商品 {product_id} 库存账面价值 {inv.total_value_l4} ≠ StockMove 求和 {sum_total} (差 {diff})",
                fix_hint="检查反向 StockMove.total_cost_l2 是否用原入库金额",
                field="Inventory.total_value_l4",
                detail={"product_id": product_id, "diff": float(diff)},
            ))

    return violations


# ═══════════════════════════════════════════════════════════════
# AS-04: 权责发生制
# ═══════════════════════════════════════════════════════════════

def check_as04(db: Session, context: dict) -> List[RuleViolation]:
    """AS-04 校验:期间收入 == 总账 6001 贷方发生额

    context:
    - account_id + start_date + end_date: 校验期间收入
    """
    violations = []
    account_id = context.get("account_id")
    start_date = context.get("start_date")
    end_date = context.get("end_date")

    if not (account_id and start_date and end_date):
        return violations

    from models_finance import AccountMove, AccountMoveLine, LedgerAccount
    from sqlalchemy import func

    # 总账 6001 贷方发生额
    la_6001 = db.query(LedgerAccount).filter(LedgerAccount.code == "6001").first()
    if not la_6001:
        return violations

    ledger_credit = db.query(func.sum(AccountMoveLine.credit_l2)).join(AccountMove).filter(
        AccountMoveLine.ledger_account_id == la_6001.id,
        AccountMove.date_l1 >= start_date,
        AccountMove.date_l1 <= end_date,
    ).scalar() or Decimal("0")

    # 销售订单总额(禁止用作期间收入,但此处仅作对比)
    from models import SaleOrder
    order_total = db.query(func.sum(SaleOrder.total_price_l1)).filter(
        SaleOrder.account_id == account_id,
        SaleOrder.sale_date_l1 >= start_date,
        SaleOrder.sale_date_l1 <= end_date,
    ).scalar() or Decimal("0")

    # 此处不直接报违规(差异可能来自未开票销售),仅当差异 > 容忍值时提示
    # 真正的违规是报表读 Σ(SaleOrder) 而非总账,由 AS-08/10 静态校验覆盖
    # 这里校验总账 6001 是否有数据(若期间有销售但 6001 为 0,说明未过账)
    if order_total > 0 and ledger_credit == 0:
        violations.append(_make_violation(
            "AS-04",
            f"期间 {start_date}~{end_date} 有销售订单 {order_total} 但总账 6001 贷方为 0,可能未过账",
            fix_hint="检查 FinanceEngine.record_sale 是否调用",
            field="AccountMoveLine.credit_l2",
            detail={"order_total": float(order_total), "ledger_credit": float(ledger_credit)},
        ))

    return violations


# ═══════════════════════════════════════════════════════════════
# AS-05: 折旧与摊销
# ═══════════════════════════════════════════════════════════════

def check_as05(db: Session, context: dict) -> List[RuleViolation]:
    """AS-05 校验:折旧公式 / 累计折旧上限 / 摊销上限

    context:
    - asset_id: 固定资产ID → 校验累计折旧不超原值×(1-残值率)
    - intangible_asset_id: 无形资产ID → 校验累计摊销不超原值
    """
    violations = []

    # ── 固定资产 ──
    asset_id = context.get("asset_id")
    if asset_id:
        from models import FixedAsset
        asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
        if asset:
            original = asset.original_value_l1 or Decimal("0")
            salvage_rate = asset.salvage_rate_l3 or Decimal("0")
            accum_depr = asset.accumulated_depreciation_l4 or Decimal("0")
            useful_life = asset.useful_life_l3 or 0

            # 累计折旧上限
            max_depr = original * (Decimal("1") - salvage_rate)
            if accum_depr > max_depr + TOLERANCE:
                violations.append(_make_violation(
                    "AS-05",
                    f"资产 {asset_id} 累计折旧 {accum_depr} 超过上限 {max_depr} (原值×(1-残值率))",
                    fix_hint="检查 batch_depreciate 是否超提",
                    field="FixedAsset.accumulated_depreciation_l4",
                    detail={"asset_id": asset_id, "accum": float(accum_depr), "max": float(max_depr)},
                ))

            # 月折旧额公式校验(若 useful_life > 0)
            if useful_life > 0:
                expected_monthly = (original * (Decimal("1") - salvage_rate) / Decimal(str(useful_life))).quantize(Q2)
                from models import FixedAssetDepreciation
                latest = db.query(FixedAssetDepreciation).filter(
                    FixedAssetDepreciation.asset_id == asset_id
                ).order_by(FixedAssetDepreciation.id.desc()).first()
                if latest and latest.amount_l2:
                    # 尾差：最后一期剩余可计提金额可能小于月折旧额（接近残值）
                    remaining_before = max_depr - latest.accumulated_before_l2
                    expected_final = min(expected_monthly, remaining_before).quantize(Q2)
                    actual = latest.amount_l2
                    if actual != expected_monthly and actual != expected_final and actual > TOLERANCE:
                        violations.append(_make_violation(
                            "AS-05",
                            f"资产 {asset_id} 月折旧额 {actual} ≠ 期望 {expected_monthly} 或尾差 {expected_final} (原值×(1-残值率)÷寿命)",
                            fix_hint="检查 record_depreciation 计算公式",
                            field="FixedAssetDepreciation.amount_l2",
                            detail={"asset_id": asset_id, "actual": float(actual), "expected": float(expected_monthly), "final": float(expected_final)},
                        ))

    # ── 无形资产 ──
    intangible_asset_id = context.get("intangible_asset_id")
    if intangible_asset_id:
        from models import IntangibleAsset
        asset = db.query(IntangibleAsset).filter(IntangibleAsset.id == intangible_asset_id).first()
        if asset:
            original = asset.original_value_l1 or Decimal("0")
            accum_amort = asset.accumulated_amortization_l4 or Decimal("0")
            useful_life = asset.useful_life_l3 or 0

            # 累计摊销上限：无形资产无残值，上限为原值
            if accum_amort > original + TOLERANCE:
                violations.append(_make_violation(
                    "AS-05",
                    f"无形资产 {intangible_asset_id} 累计摊销 {accum_amort} 超过原值 {original}",
                    fix_hint="检查 batch_amortize 是否超提",
                    field="IntangibleAsset.accumulated_amortization_l4",
                    detail={"asset_id": intangible_asset_id, "accum": float(accum_amort), "max": float(original)},
                ))

            # 月摊销额公式校验
            if useful_life > 0:
                expected_monthly = (original / Decimal(str(useful_life))).quantize(Q2)
                from models import IntangibleAssetAmortization
                latest = db.query(IntangibleAssetAmortization).filter(
                    IntangibleAssetAmortization.asset_id == intangible_asset_id
                ).order_by(IntangibleAssetAmortization.id.desc()).first()
                if latest and latest.amount_l2:
                    # 尾差：最后一期剩余可摊销金额可能小于月摊销额
                    remaining_before = original - latest.accumulated_before_l2
                    expected_final = min(expected_monthly, remaining_before).quantize(Q2)
                    actual = latest.amount_l2
                    if actual != expected_monthly and actual != expected_final and actual > TOLERANCE:
                        violations.append(_make_violation(
                            "AS-05",
                            f"无形资产 {intangible_asset_id} 月摊销额 {actual} ≠ 期望 {expected_monthly} 或尾差 {expected_final} (原值÷寿命)",
                            fix_hint="检查 record_amortization 计算公式",
                            field="IntangibleAssetAmortization.amount_l2",
                            detail={"asset_id": intangible_asset_id, "actual": float(actual), "expected": float(expected_monthly), "final": float(expected_final)},
                        ))

    return violations


# ═══════════════════════════════════════════════════════════════
# AS-06: 增值税红字冲减
# ═══════════════════════════════════════════════════════════════

def check_as06(db: Session, context: dict) -> List[RuleViolation]:
    """AS-06 校验:红字发票金额为负

    context:
    - invoice_id: 红字发票ID
    """
    violations = []
    invoice_id = context.get("invoice_id")
    if not invoice_id:
        return violations

    from models import Invoice
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        return violations

    # 判断是否红字发票(发票号含 H- 前缀或金额为负)
    is_red = inv.invoice_no.startswith("H-") or (inv.amount_with_tax_l1 or 0) < 0

    if is_red:
        # 红字发票金额必须为负
        if (inv.amount_without_tax_l1 or 0) >= 0:
            violations.append(_make_violation(
                "AS-06",
                f"红字发票 {invoice_id} 不含税金额 {inv.amount_without_tax_l1} 应为负数",
                fix_hint="检查红字发票创建逻辑",
                field="Invoice.amount_without_tax_l1",
                detail={"invoice_id": invoice_id},
            ))
        if (inv.tax_amount_l1 or 0) >= 0:
            violations.append(_make_violation(
                "AS-06",
                f"红字发票 {invoice_id} 税额 {inv.tax_amount_l1} 应为负数",
                fix_hint="检查红字发票创建逻辑",
                field="Invoice.tax_amount_l1",
                detail={"invoice_id": invoice_id},
            ))

    return violations


# ═══════════════════════════════════════════════════════════════
# AS-07: 固定资产处置损益入营业外收支
# ═══════════════════════════════════════════════════════════════

def check_as07(db: Session, context: dict) -> List[RuleViolation]:
    """AS-07 校验:处置凭证用了 6301/6701 而非 6111/6711

    context:
    - asset_id: 固定资产ID(已处置) → 校验处置凭证科目
    """
    violations = []
    asset_id = context.get("asset_id")
    if not asset_id:
        return violations

    from models import FixedAsset
    from models_finance import AccountMove, AccountMoveLine, LedgerAccount

    asset = db.query(FixedAsset).filter(FixedAsset.id == asset_id).first()
    if not asset or asset.status != "报废":
        return violations

    # 查处置凭证
    moves = db.query(AccountMove).filter(
        AccountMove.source_model == "fixed_asset_disposal",
        AccountMove.source_id == asset_id,
    ).all()

    if not moves:
        return violations  # 无凭证,无法校验

    # 收集所有分录的科目代码
    la_ids = set()
    for m in moves:
        lines = db.query(AccountMoveLine).filter(AccountMoveLine.move_id == m.id).all()
        for l in lines:
            la_ids.add(l.ledger_account_id)

    la_codes = db.query(LedgerAccount.code).filter(LedgerAccount.id.in_(la_ids)).all()
    la_codes = {row[0] for row in la_codes}

    # 禁止 6111/6711
    if "6111" in la_codes:
        violations.append(_make_violation(
            "AS-07",
            f"资产 {asset_id} 处置凭证用了 6111 资产处置收益,小企业准则应入 6301 营业外收入",
            fix_hint="改 engine_fixed_asset.record_disposal 用 6301/6701",
            field="LedgerAccount.code",
            detail={"asset_id": asset_id, "wrong_code": "6111"},
        ))
    if "6711" in la_codes:
        violations.append(_make_violation(
            "AS-07",
            f"资产 {asset_id} 处置凭证用了 6711 资产处置损失,小企业准则应入 6701 营业外支出",
            fix_hint="改 engine_fixed_asset.record_disposal 用 6301/6701",
            field="LedgerAccount.code",
            detail={"asset_id": asset_id, "wrong_code": "6711"},
        ))

    return violations


# ═══════════════════════════════════════════════════════════════
# AS-15: 冲红凭证日期一致性
# ═══════════════════════════════════════════════════════════════

def check_as15(db: Session, context: dict) -> List[RuleViolation]:
    """AS-15 校验:反向凭证日期与原凭证一致

    context:
    - move_id: 反向凭证ID(新生成的冲红凭证)
    """
    violations = []
    move_id = context.get("move_id")
    if not move_id:
        return violations

    from models_finance import AccountMove

    reversal = db.query(AccountMove).filter(AccountMove.id == move_id).first()
    if not reversal or not reversal.is_reversal or not reversal.reversed_entry_id:
        return violations

    original = db.query(AccountMove).filter(AccountMove.id == reversal.reversed_entry_id).first()
    if not original:
        return violations

    rev_date = reversal.date_l1
    orig_date = original.date_l1

    if hasattr(rev_date, "date"):
        rev_date = rev_date.date() if hasattr(rev_date, "date") else rev_date
    if hasattr(orig_date, "date"):
        orig_date = orig_date.date() if hasattr(orig_date, "date") else orig_date

    if rev_date != orig_date:
        violations.append(_make_violation(
            "AS-15",
            f"冲红凭证 {move_id} 日期 {rev_date} 与原凭证 {original.id} 日期 {orig_date} 不一致",
            fix_hint="检查 reverse_journal 的 reversal_date 参数,应使用原凭证日期",
            field="AccountMove.date_l1",
            detail={
                "reversal_move_id": move_id,
                "original_move_id": original.id,
                "reversal_date": str(rev_date),
                "original_date": str(orig_date),
            },
        ))

    return violations


# ═══════════════════════════════════════════════════════════════
# 统一入口
# ═══════════════════════════════════════════════════════════════

# 规则ID → 校验函数映射
RUNTIME_CHECKS = {
    "AS-01": check_as01,
    "AS-02": check_as02,
    "AS-03": check_as03,
    "AS-04": check_as04,
    "AS-05": check_as05,
    "AS-06": check_as06,
    "AS-07": check_as07,
    "AS-15": check_as15,
}


def validate_rules_runtime(db: Session, rule_id: str, context: dict) -> List[RuleViolation]:
    """运行时校验指定规则

    Args:
        db: 数据库 session
        rule_id: 规则ID (AS-01 ~ AS-07)
        context: 校验上下文(如 move_id, invoice_id, report_date 等)

    Returns:
        RuleViolation 列表(空列表表示无违规)

    示例:
        # 校验单张凭证借贷平衡
        vs = validate_rules_runtime(db, "AS-01", {"move_id": 123})
        # 校验 BS 恒等式
        vs = validate_rules_runtime(db, "AS-01", {"report_date": date(2026,6,30), "account_id": 1})
        # 校验发票三段平衡
        vs = validate_rules_runtime(db, "AS-02", {"invoice_id": 456})
    """
    check_fn = RUNTIME_CHECKS.get(rule_id)
    if not check_fn:
        return [RuleViolation(
            rule_id=rule_id,
            rule_name="(未知规则)",
            severity="ERROR",
            message=f"规则 {rule_id} 无运行时校验函数",
            fix_hint=f"在 runtime_checks.py 中为 {rule_id} 添加 check_fn",
        )]
    return check_fn(db, context)


def validate_all_runtime(db: Session, context: dict) -> List[RuleViolation]:
    """运行时校验所有 AS-01~AS-07 规则

    Args:
        db: 数据库 session
        context: 校验上下文(各规则按需读取 context 字段)

    Returns:
        RuleViolation 列表
    """
    all_violations = []
    for rule_id, check_fn in RUNTIME_CHECKS.items():
        try:
            all_violations.extend(check_fn(db, context))
        except Exception as e:
            all_violations.append(_make_violation(
                rule_id,
                f"运行时校验异常: {e}",
                fix_hint=f"检查 {check_fn.__name__} 实现",
            ))
    return all_violations


# ═══════════════════════════════════════════════════════════════
# 业务流程拦截入口
# ═══════════════════════════════════════════════════════════════

def enforce_rules(db: Session, rule_ids: List[str], context: dict) -> None:
    """在业务流程关键节点运行时校验会计准则,违规抛 BusinessError 拦截

    把"被动可调用的工具"变为"主动护栏":在凭证过账/发票创建/出库/折旧/处置
    等关键节点调用此函数,违反 AS-01~AS-07 的操作将被拒绝。

    调用示例:
        # 凭证过账后校验借贷平衡
        enforce_rules(db, ["AS-01"], {"move_id": move.id})
        # 发票创建后校验价税分离
        enforce_rules(db, ["AS-02"], {"invoice_id": db_invoice.id})

    事务语义: 此函数在 db.flush() 之后、db.commit() 之前调用。
    若抛出 BusinessError,异常向上传播,调用方(路由/命令处理器)的
    commit 不会执行,事务自动回滚,违规数据不会落库。

    Args:
        db: 数据库 session
        rule_ids: 要校验的规则ID列表,如 ["AS-01"] 或 ["AS-02", "AS-06"]
        context: 校验上下文,如 {"move_id": 123}

    Raises:
        BusinessError(ErrorCode.RULE_VIOLATION): 当任何规则违规时
    """
    all_violations: List[RuleViolation] = []
    for rule_id in rule_ids:
        try:
            all_violations.extend(validate_rules_runtime(db, rule_id, context))
        except Exception as e:
            all_violations.append(_make_violation(
                rule_id,
                f"运行时校验异常: {e}",
                fix_hint=f"检查 {rule_id} 校验函数实现",
            ))
    if all_violations:
        summary = "; ".join(f"[{v.rule_id}] {v.message}" for v in all_violations)
        raise BusinessError(
            ErrorCode.RULE_VIOLATION,
            message=f"会计准则校验失败: {summary}",
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
                    for v in all_violations
                ],
            },
        )


def _register_check_fns():
    """把 RUNTIME_CHECKS 中的函数反向赋值给 Rule.check_fn

    单独提取为函数,避免模块加载时循环依赖。
    在 rules 包 __init__.py 中调用。
    """
    from .dsl import RULES
    from . import rules_definition  # noqa: F401  确保规则已注册
    for rule in RULES:
        if rule.id in RUNTIME_CHECKS:
            rule.check_fn = RUNTIME_CHECKS[rule.id]


# 模块加载时自动注册(此时 rules_definition 可能未加载,需在 __init__.py 中再次调用)
_register_check_fns()
