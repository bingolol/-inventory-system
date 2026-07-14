"""ReportReconciliation — 声明式双路径对账

从 Field DSL Source 声明派生一条独立 SQL 路径，
与 ReportEngine 的正常 resolve 路径对比，发现 bug。

设计原则：
- 独立 SQL 路径不复用 snapshot.trace_* 方法（避免继承同一 bug）
- 直接用 SQLAlchemy ORM 查 AccountMoveLine/Invoice/StockMove 等表
- 应用相同的 bucket 过滤（PNL_EXCLUDED/BUSINESS_ONLY/INTERNAL_ONLY）
- 应用相同的 cutoff（period_start/period_end 或 bs_cutoff）
- ESCAPE_HATCH / OPENING / CLASSIFIED_SUM 跳过（无法独立验证）

输出：ReconciliationResult，包含每个字段的 engine_value / sql_value / diff / matched
"""
from dataclasses import dataclass, field as dc_field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from .dsl import Field, Source, Formula, Bucket, Part


# ═══════════════════════════════════════════════════════════════
# 结果数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class FieldReconciliation:
    """单个字段的对账结果"""
    key: str
    label: str
    engine_value: Decimal
    sql_value: Optional[Decimal]   # None 表示跳过（ESCAPE_HATCH/OPENING 等）
    diff: Decimal
    matched: bool
    skipped: bool = False           # True 表示该字段无法独立验证
    skip_reason: str = ""
    note: str = ""                  # 附加说明（如 DualSource 切换口径）


@dataclass
class ReconciliationResult:
    """整张报表的对账结果"""
    report_type: str
    fields: List[FieldReconciliation] = dc_field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.fields)

    @property
    def skipped_count(self) -> int:
        return sum(1 for f in self.fields if f.skipped)

    @property
    def verified_count(self) -> int:
        return self.total_count - self.skipped_count

    @property
    def matched_count(self) -> int:
        return sum(1 for f in self.fields if f.matched and not f.skipped)

    @property
    def mismatched_count(self) -> int:
        return self.verified_count - self.matched_count

    @property
    def all_matched(self) -> bool:
        return self.mismatched_count == 0

    def mismatches(self) -> List[FieldReconciliation]:
        return [f for f in self.fields if not f.matched and not f.skipped]

    def to_dict(self) -> dict:
        return {
            "report_type": self.report_type,
            "summary": {
                "total": self.total_count,
                "verified": self.verified_count,
                "matched": self.matched_count,
                "mismatched": self.mismatched_count,
                "skipped": self.skipped_count,
                "all_matched": self.all_matched,
            },
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "engine_value": float(f.engine_value),
                    "sql_value": float(f.sql_value) if f.sql_value is not None else None,
                    "diff": float(f.diff),
                    "matched": f.matched,
                    "skipped": f.skipped,
                    "skip_reason": f.skip_reason,
                    "note": f.note,
                }
                for f in self.fields
            ],
        }


# ═══════════════════════════════════════════════════════════════
# 独立 SQL 查询路径
# ═══════════════════════════════════════════════════════════════

# Bucket → 排除的 source_model 集合
_BUCKET_EXCLUDE = {
    Bucket.PNL_EXCLUDED: frozenset({"period_close", "year_close"}),
    Bucket.BUSINESS_ONLY: frozenset({
        "vat_transfer_out", "tax_surcharge", "tax_income",
        "tax_income_reversal", "vat_exemption",
        "period_close", "year_close",
    }),
    Bucket.INTERNAL_ONLY: None,  # 特殊处理：include 而非 exclude
    Bucket.ALL: frozenset(),
}

_INTERNAL_TRANSFER_MODELS = frozenset({
    "vat_transfer_out", "tax_surcharge", "tax_income",
    "tax_income_reversal", "vat_exemption",
    "period_close", "year_close",
})


def _sql_ledger_query(db, ledger, codes: List[str], bucket: Bucket,
                      start=None, end=None, bs_cutoff=None,
                      source_mode: str = "include") -> Tuple[Decimal, Decimal]:
    """独立 SQL 查询：返回 (sum_debit, sum_credit)

    不复用 snapshot.trace_* 方法，直接 ORM 查询。
    source_mode:
    - "include": 只包含 _INTERNAL_TRANSFER_MODELS 中的 source_model
    - "exclude": 排除 bucket 对应的 source_model
    - "all": 不做 source_model 过滤
    """
    from models_finance import AccountMove, AccountMoveLine, LedgerAccount
    from sqlalchemy import func

    q = db.query(
        func.coalesce(func.sum(AccountMoveLine.debit_l2), 0).label("d"),
        func.coalesce(func.sum(AccountMoveLine.credit_l2), 0).label("c"),
    ).select_from(LedgerAccount
    ).join(AccountMoveLine, AccountMoveLine.ledger_account_id == LedgerAccount.id
    ).join(AccountMove, AccountMoveLine.move_id == AccountMove.id
    ).filter(
        LedgerAccount.ledger_id == ledger.id,
        LedgerAccount.code.in_(codes),
        AccountMove.state == "posted",
    )

    # 日期过滤
    if start is not None and end is not None:
        q = q.filter(AccountMove.date_l1 >= start, AccountMove.date_l1 <= end)
    elif bs_cutoff is not None:
        q = q.filter(AccountMove.date_l1 <= bs_cutoff)

    # source_model 过滤
    if source_mode == "include":
        q = q.filter(AccountMove.source_model.in_(_INTERNAL_TRANSFER_MODELS))
    elif source_mode == "exclude":
        exclude_set = _BUCKET_EXCLUDE.get(bucket, frozenset())
        if exclude_set:
            q = q.filter(~AccountMove.source_model.in_(exclude_set))
    # "all" 不过滤

    row = q.one()
    return Decimal(str(row.d)), Decimal(str(row.c))


def _sql_invoice_tax_net(db, account_id: int, bs_cutoff=None) -> Decimal:
    """独立 SQL：发票表销项税 - 进项税（已认证专票）"""
    from models import Invoice
    from sqlalchemy import func
    from enums import InvoiceDirection, InvoiceType, CertificationStatus

    q_out = db.query(func.coalesce(func.sum(Invoice.tax_amount_l1), 0)).filter(
        Invoice.account_id == account_id,
        Invoice.direction == InvoiceDirection.OUT,
    )
    q_in = db.query(func.coalesce(func.sum(Invoice.tax_amount_l1), 0)).filter(
        Invoice.account_id == account_id,
        Invoice.direction == InvoiceDirection.IN,
        Invoice.invoice_type == InvoiceType.SPECIAL,
        Invoice.certification_status_l3 == CertificationStatus.CERTIFIED,
    )
    if bs_cutoff is not None:
        q_out = q_out.filter(Invoice.issue_date_l1 <= bs_cutoff)
        q_in = q_in.filter(Invoice.issue_date_l1 <= bs_cutoff)

    out_tax = Decimal(str(q_out.scalar()))
    in_tax = Decimal(str(q_in.scalar()))
    return out_tax - in_tax


def _sql_stock_moves_value(db, account_id: int, bs_cutoff=None) -> Decimal:
    """独立 SQL：库存流水聚合（与 _resolve_stock_moves 同口径）

    按产品聚合 quantity_l1 与 total_cost_l2，正库存余额累加成本。
    """
    from models import StockMove
    from sqlalchemy import func

    q = db.query(
        StockMove.product_id,
        StockMove.quantity_l1,
        StockMove.total_cost_l2,
    ).filter(StockMove.account_id == account_id)
    if bs_cutoff is not None:
        q = q.filter(StockMove.move_date_l1 <= bs_cutoff)

    rows = q.all()
    agg: Dict[int, Dict[str, Decimal]] = {}
    for r in rows:
        pid = r.product_id
        if pid not in agg:
            agg[pid] = {"qty": Decimal("0"), "value": Decimal("0")}
        qty = Decimal(str(r.quantity_l1 or 0))
        cost = Decimal(str(r.total_cost_l2 or 0))
        vd = abs(cost) * (Decimal("1") if qty > 0 else Decimal("-1"))
        agg[pid]["qty"] += qty
        agg[pid]["value"] += vd

    value = Decimal("0")
    for a in agg.values():
        if a["qty"] > 0:
            value += a["value"]
    return value


def _sql_bank_txns_value(db, account_id: int, bs_cutoff=None) -> Decimal:
    """独立 SQL：银行流水期末余额"""
    from models import BankTransaction
    from sqlalchemy import func, case

    q = db.query(
        func.coalesce(func.sum(
            case(
                (BankTransaction.transaction_type == 'inflow', BankTransaction.amount_l2),
                else_=-BankTransaction.amount_l2,
            )
        ), 0)
    ).filter(BankTransaction.account_id == account_id)
    if bs_cutoff is not None:
        q = q.filter(BankTransaction.transaction_date_l1 <= bs_cutoff)
    return Decimal(str(q.scalar()))


def _sql_cash_txns_value(db, account_id: int, bs_cutoff=None) -> Decimal:
    """独立 SQL：现金流水期末余额"""
    from models import CashFlowTransaction
    from sqlalchemy import func, case

    q = db.query(
        func.coalesce(func.sum(
            case(
                (CashFlowTransaction.transaction_type == 'inflow', CashFlowTransaction.amount_l2),
                else_=-CashFlowTransaction.amount_l2,
            )
        ), 0)
    ).filter(CashFlowTransaction.account_id == account_id)
    if bs_cutoff is not None:
        q = q.filter(CashFlowTransaction.transaction_date_l1 <= bs_cutoff)
    return Decimal(str(q.scalar()))


# ═══════════════════════════════════════════════════════════════
# ReportReconciliation 主类
# ═══════════════════════════════════════════════════════════════

class ReportReconciliation:
    """报表对账引擎：从 DSL Source 派生独立 SQL，与 ReportEngine 对比"""

    def __init__(self, db, snapshot, report_type: str = "unknown"):
        self.db = db
        self.snapshot = snapshot
        self.report_type = report_type
        self._ledger = snapshot._ledger
        self._account_id = snapshot._account_id
        self._bs_cutoff = snapshot._bs_cutoff
        self._period_start = snapshot._period_start
        self._period_end = snapshot._period_end

    def reconcile(self, fields: List[Field], engine_values: Dict[str, Decimal],
                  source_mode: str = "invoice") -> ReconciliationResult:
        """对账主入口

        Args:
            fields: 报表字段定义
            engine_values: ReportEngine.execute() 的结果 {key: value}
            source_mode: "invoice"/"ledger"/"both"，影响 DualSource 取哪一侧

        Returns:
            ReconciliationResult
        """
        result = ReconciliationResult(report_type=self.report_type)

        for f in fields:
            # label=None 的字段是内部辅助字段（如 _vat_net），跳过对账
            if f.label is None:
                continue
            eng_val = Decimal(str(engine_values.get(f.key, 0)))
            sql_val, note, skipped, skip_reason = self._reconcile_field(f, source_mode)

            if skipped:
                result.fields.append(FieldReconciliation(
                    key=f.key, label=f.label,
                    engine_value=eng_val, sql_value=None,
                    diff=Decimal("0"), matched=True,
                    skipped=True, skip_reason=skip_reason, note=note,
                ))
            else:
                diff = eng_val - sql_val
                # 容忍 0.02 误差（精度边界）
                matched = abs(diff) < Decimal("0.02")
                result.fields.append(FieldReconciliation(
                    key=f.key, label=f.label,
                    engine_value=eng_val, sql_value=sql_val,
                    diff=diff, matched=matched, note=note,
                ))

        return result

    def _reconcile_field(self, f: Field, source_mode: str) -> Tuple[Optional[Decimal], str, bool, str]:
        """对单个字段派生独立 SQL，并应用 transform（与 ReportEngine 一致）

        返回 (sql_value, note, skipped, skip_reason)
        """
        sql_val, note, skipped, skip_reason = self._reconcile_source(f.source, source_mode)
        if skipped or sql_val is None:
            return sql_val, note, skipped, skip_reason

        # 应用 transform（与 ReportEngine._apply_transform 一致）
        if f.transform:
            tf_val = self._apply_transform_sql(f.transform, sql_val)
            if tf_val is not None:
                sql_val = tf_val
                note = (note + " + transform:" + f.transform.formula.name).strip()

        return sql_val, note, False, ""

    def _apply_transform_sql(self, transform: Source, value: Decimal) -> Optional[Decimal]:
        """独立 SQL 路径应用 transform（与 ReportEngine._apply_transform 一致）"""
        formula = transform.formula

        if formula == Formula.POSITIVE_PART:
            return max(value, Decimal("0"))

        if formula == Formula.NEGATIVE_PART:
            v = max(-value, Decimal("0"))
            return abs(v) if transform.abs else v

        if formula == Formula.NEGATE:
            return -value

        if formula == Formula.OPENING_FALLBACK:
            # 值=0 时兜底到期初（与 engine 一致）
            if value == Decimal("0") and self.snapshot.opening_balance:
                return Decimal(str(getattr(self.snapshot.opening_balance, transform.opening_key, 0) or 0))
            return value

        if formula == Formula.SUBACCOUNT_FALLBACK:
            # 主科目=0 时回退到子科目（与 engine 一致）
            if value == Decimal("0") and transform.subaccount_codes:
                sub_value = Decimal("0")
                for sub_code in transform.subaccount_codes:
                    d, c = self._sql_ledger([sub_code], Bucket.PNL_EXCLUDED, mode="period")
                    sub_value += d - c
                return sub_value
            return value

        # 未知 transform，不处理
        return value

    def _reconcile_source(self, source: Source, source_mode: str) -> Tuple[Optional[Decimal], str, bool, str]:
        """根据 Source.formula 派生独立 SQL"""
        formula = source.formula

        # DualSource：按 source_mode 选择 primary 或 secondary
        if formula == Formula.DUAL_SOURCE:
            if source_mode == "ledger" and source.secondary:
                val, note, sk, reason = self._reconcile_source(source.secondary, source_mode)
                return val, f"DualSource.secondary(ledger口径): {note}", sk, reason
            else:
                val, note, sk, reason = self._reconcile_source(source.primary, source_mode)
                return val, f"DualSource.primary(invoice口径): {note}", sk, reason

        # 总账类公式
        if formula == Formula.CUM_BALANCE:
            d, c = self._sql_ledger(source.codes, source.bucket, mode="cum")
            return d - c, "", False, ""

        if formula == Formula.CUM_CREDIT:
            d, c = self._sql_ledger(source.codes, source.bucket, mode="cum")
            return c - d, "", False, ""

        if formula == Formula.PERIOD_NET:
            d, c = self._sql_ledger(source.codes, source.bucket, mode="period")
            return d - c, "", False, ""

        if formula == Formula.COMPOSITE:
            return self._reconcile_composite(source), "", False, ""

        if formula == Formula.INVOICE_TAX_NET:
            return _sql_invoice_tax_net(self.db, self._account_id, self._bs_cutoff), "", False, ""

        if formula == Formula.STOCK_MOVES:
            return _sql_stock_moves_value(self.db, self._account_id, self._bs_cutoff), "", False, ""

        if formula == Formula.BANK_TXNS:
            return _sql_bank_txns_value(self.db, self._account_id, self._bs_cutoff), "", False, ""

        if formula == Formula.CASH_TXNS:
            return _sql_cash_txns_value(self.db, self._account_id, self._bs_cutoff), "", False, ""

        # 不可独立验证的类型
        if formula == Formula.SUM_FIELDS:
            return None, "SUM_FIELDS 依赖子字段，对账在子字段层验证", True, "aggregation"

        if formula == Formula.ESCAPE_HATCH:
            return None, "ESCAPE_HATCH 自定义 resolver，无法独立验证", True, "escape_hatch"

        if formula == Formula.OPENING:
            return None, "OPENING 期初数据，不在 SQL 对账范围", True, "opening"

        if formula == Formula.CLASSIFIED_SUM:
            return None, "CLASSIFIED_SUM 依赖分类器缓存，需独立验证分类器", True, "classifier"

        # Transform 类型（POSITIVE_PART/NEGATIVE_PART/OPENING_FALLBACK/SUBACCOUNT_FALLBACK/NEGATE）
        # 这些是 transform，不应在 source 位置出现；若出现，跳过
        return None, f"未知/Transform formula: {formula}", True, "unknown_formula"

    def _sql_ledger(self, codes: List[str], bucket: Bucket, mode: str) -> Tuple[Decimal, Decimal]:
        """总账查询：与 ReportEngine._resolve_cum 口径对齐

        cum 模式（CUM_BALANCE/CUM_CREDIT）：与 engine 的 trace_cum_dc 一致，不排除 source_model
        period 模式（PERIOD_NET）：按 bucket 排除（与 engine 的 trace_pnl_dc/trace_biz_dc 一致）
        """
        if mode == "cum":
            # cum 模式：engine 用 trace_cum_dc 不排除任何 source_model
            return _sql_ledger_query(
                self.db, self._ledger, codes, bucket,
                bs_cutoff=self._bs_cutoff, source_mode="all",
            )
        else:  # period
            return _sql_ledger_query(
                self.db, self._ledger, codes, bucket,
                start=self._period_start, end=self._period_end,
                source_mode="exclude",
            )

    def _reconcile_composite(self, source: Source) -> Decimal:
        """COMPOSITE 独立 SQL：按 part.side 和 part.sign 聚合

        模式选择与 engine._resolve_composite 对齐：
        - BS（无 period_start/end）→ cum 模式（用 bs_cutoff）
        - IS（有 period_start/end）→ period 模式
        """
        has_period = self._period_start is not None and self._period_end is not None
        mode = "period" if has_period else "cum"
        value = Decimal("0")
        for part in source.parts:
            d, c = self._sql_ledger(part.codes, source.bucket, mode=mode)
            if part.side == "debit":
                value += d * part.sign
            elif part.side == "credit":
                value += c * part.sign
            else:
                value += (d - c) * part.sign
        return value
