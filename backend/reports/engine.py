"""ReportEngine — 声明式报表统一执行引擎

接收字段定义列表 + LedgerSnapshot，按拓扑顺序 resolve 每个字段，
返回结果字典。trace 模式下附带 contributions。
"""

from collections import deque
from decimal import Decimal
from typing import Any, Dict, List, Set

from .dsl import Field, Source, Formula, Bucket


class ReportEngine:

    def __init__(self):
        self._classified_cache = None

    def execute(self, fields: List[Field], snapshot, trace: bool = False,
                source_mode: str = "invoice") -> Dict[str, Any]:
        """执行报表定义

        source_mode: "invoice" (默认, 走 DualSource.primary)
                     "ledger"  (走 DualSource.secondary)
                     "both"    (primary 为主，额外输出 verification)
        """
        # ── 预扫描：如定义中有 CLASSIFIED_SUM，填充分类缓存 ──
        has_classified = any(
            f.source.formula == Formula.CLASSIFIED_SUM
            or (f.source.formula == Formula.DUAL_SOURCE
                and f.source.primary and f.source.primary.formula == Formula.CLASSIFIED_SUM)
            for f in fields
        )
        if has_classified:
            bank = snapshot.trace_bank_txns_classified()
            cash = snapshot.trace_cash_txns_classified()
            self._classified_cache = self._merge_classified(bank, cash)
        else:
            self._classified_cache = {}

        self._source_mode = source_mode

        ordered = self._topo_sort(fields)
        ctx: Dict[str, Any] = {}  # {key: (value, [ids_or_tuples])}

        for field in ordered:
            value, ids = self._resolve(field.source, snapshot, ctx)
            if field.transform:
                value, ids = self._apply_transform(field.transform, value, ids, snapshot, ctx)
            ctx[field.key] = (value, ids)

        # 组装结果
        if trace:
            result = {}
            for field in ordered:
                value, ids = ctx[field.key]
                entry = {"value": float(value), "contributions": self._format_contributions(ids, snapshot)}
                if self._source_mode == "both":
                    self._attach_verification(field, entry, snapshot, ctx)
                result[field.key] = entry
            return result
        else:
            if self._source_mode == "both":
                result = {}
                for field in ordered:
                    value, _ids = ctx[field.key]
                    entry = {"value": float(value)}
                    self._attach_verification(field, entry, snapshot, ctx)
                    result[field.key] = entry
                return result
            return {field.key: float(ctx[field.key][0]) for field in ordered}

    def _attach_verification(self, field: Field, entry: dict, snapshot, ctx):
        """source_mode=both 时，为 DualSource 字段附加总账对账"""
        s = field.source
        if s.formula == Formula.DUAL_SOURCE and s.secondary:
            sec_val, sec_ids = self._resolve(s.secondary, snapshot, ctx)
            prim_val = ctx.get(field.key, (Decimal("0"), []))[0]
            entry["verification"] = {
                "ledger_value": float(sec_val),
                "diff": round(float(prim_val - sec_val), 2),
                "matched": abs(prim_val - sec_val) < Decimal("0.02"),
            }

    def _merge_classified(self, bank: dict, cash: dict) -> dict:
        """合并银行和现金分类结果 → {cf_code: (amount, [(source_type, id), ...])}"""
        merged = {}
        for src, data in [("bank_txn", bank), ("cash_txn", cash)]:
            for code, (amount, ids) in data.items():
                if code not in merged:
                    merged[code] = (Decimal("0"), [])
                prev_amount, prev_ids = merged[code]
                merged[code] = (prev_amount + amount, prev_ids + [(src, i) for _, i in ids])
        return merged

    def _format_contributions(self, ids: list, snapshot) -> list:
        """统一格式化 contributions：支持 aml_id 和 (source_type, txn_id) 两种格式"""
        if not ids:
            return []
        result = []
        aml_set = set()
        txn_items = []
        for item in ids:
            if isinstance(item, tuple):
                txn_items.append({"source_type": item[0], "source_id": item[1]})
            elif isinstance(item, int):
                aml_set.add(item)
        if aml_set:
            meta = snapshot.get_move_meta(aml_set)
            for aid in sorted(aml_set):
                m = meta.get(aid, {})
                result.append({
                    "aml_id": aid,
                    "move_name": m.get("move_name", ""),
                    "move_date": str(m.get("move_date", "")),
                    "source_model": m.get("source_model", ""),
                    "source_id": m.get("source_id", 0),
                })
        result.extend(txn_items)
        return result

    # ── 拓扑排序 ──

    def _topo_sort(self, fields: List[Field]) -> List[Field]:
        """按依赖顺序排列：deps 引用的字段必须先 resolve"""
        key_map = {f.key: f for f in fields}
        in_degree: Dict[str, int] = {f.key: 0 for f in fields}
        children: Dict[str, List[str]] = {f.key: [] for f in fields}

        for f in fields:
            deps = self._collect_deps(f.source) or []
            for dep in deps:
                if dep in key_map and dep != f.key:
                    children.setdefault(dep, []).append(f.key)
                    in_degree[f.key] = in_degree.get(f.key, 0) + 1

        queue = deque([k for k, d in in_degree.items() if d == 0])
        sorted_keys: List[str] = []

        while queue:
            k = queue.popleft()
            sorted_keys.append(k)
            for child in children.get(k, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(sorted_keys) != len(fields):
            missing = set(f.key for f in fields) - set(sorted_keys)
            raise ValueError(f"循环依赖或缺失依赖: {missing}")

        return [key_map[k] for k in sorted_keys]

    def _collect_deps(self, source: Source) -> List[str]:
        if source.formula == Formula.SUM_FIELDS:
            return list(source.deps)
        if source.formula == Formula.DUAL_SOURCE:
            deps = []
            if source.primary:
                deps.extend(self._collect_deps(source.primary))
            if source.secondary:
                deps.extend(self._collect_deps(source.secondary))
            return deps
        if source.formula == Formula.POSITIVE_PART or source.formula == Formula.NEGATIVE_PART:
            return list(source.deps)
        return []

    # ── 字段 resolve ──

    def _resolve(self, source: Source, snapshot, ctx: dict) -> tuple:
        start = snapshot._period_start
        end = snapshot._period_end

        if source.formula == Formula.DUAL_SOURCE:
            if self._source_mode == "ledger" and source.secondary:
                s = source.secondary
            elif self._source_mode == "both":
                s = source.primary
            else:
                s = source.primary
            return self._resolve(s, snapshot, ctx)
        elif source.formula == Formula.CUM_BALANCE:
            return self._resolve_cum(source, snapshot, "bal")
        elif source.formula == Formula.CUM_CREDIT:
            return self._resolve_cum(source, snapshot, "crd")
        elif source.formula == Formula.PERIOD_NET:
            return self._resolve_cum(source, snapshot, "period")
        elif source.formula == Formula.COMPOSITE:
            return self._resolve_composite(source, snapshot, start, end)
        elif source.formula == Formula.SUM_FIELDS:
            return self._resolve_sum(source, ctx)
        elif source.formula == Formula.ESCAPE_HATCH:
            return source.resolver(snapshot)
        elif source.formula == Formula.OPENING:
            ob = snapshot.opening_balance
            val = getattr(ob, source.key, Decimal("0")) if ob else Decimal("0")
            return _d(val), []
        elif source.formula == Formula.INVOICE_TAX_NET:
            return self._resolve_invoice_tax_net(snapshot)
        elif source.formula == Formula.STOCK_MOVES:
            return self._resolve_stock_moves(snapshot)
        elif source.formula == Formula.BANK_TXNS:
            return self._resolve_bank_txns(snapshot)
        elif source.formula == Formula.CASH_TXNS:
            return self._resolve_cash_txns(snapshot)
        elif source.formula == Formula.CLASSIFIED_SUM:
            return self._resolve_classified_sum(source)
        else:
            import logging
            logging.getLogger("inventory").warning(
                f"ReportEngine._resolve: unknown formula {source.formula}, returning 0"
            )
            return Decimal("0"), []
            return Decimal("0"), []

    def _resolve_cum(self, source: Source, snapshot, mode: str) -> tuple:
        """按 Bucket 选择 trace_biz_dc / trace_pnl_dc （期间模式） 或 trace_bal / trace_crd"""
        bucket = source.bucket
        start = snapshot._period_start
        end = snapshot._period_end

        d_total = Decimal("0")
        c_total = Decimal("0")
        all_ids: List[int] = []

        for code in source.codes:
            # 期间模式：PERIOD_NET 用 trace_pnl_dc
            # 累计模式：CUM_BALANCE/CUM_CREDIT 用 trace_bal/trace_crd（bs_cutoff 已在 snapshot 内）
            if mode == "period":
                if bucket == Bucket.PNL_EXCLUDED:
                    d, c, ids = snapshot.trace_pnl_dc(code, start, end)
                elif bucket == Bucket.BUSINESS_ONLY:
                    d, c, ids = snapshot.trace_biz_dc(code, start, end)
                elif bucket == Bucket.INTERNAL_ONLY:
                    d, c, ids = snapshot.trace_intl_dc(code, start, end)
                else:
                    d, c, ids = snapshot.trace_per_dc(code, start, end)
                d_total += d
                c_total += c
            else:
                if bucket == Bucket.PNL_EXCLUDED:
                    d, c, ids = snapshot.trace_cum_dc(code)
                else:
                    # 简化：非期间模式直接用 cum_dc
                    d, c, ids = snapshot.trace_cum_dc(code)
                d_total += d
                c_total += c
            all_ids.extend(ids)

        if mode == "crd":
            return c_total - d_total, all_ids
        elif mode == "period":
            return d_total - c_total, all_ids
        else:  # bal
            return d_total - c_total, all_ids

    def _resolve_composite(self, source: Source, snapshot, start, end) -> tuple:
        """多科目多方向组合"""
        value = Decimal("0")
        all_ids: List[int] = []

        has_period = start is not None and end is not None

        for part in source.parts:
            for code in part.codes:
                if has_period:
                    if source.bucket == Bucket.PNL_EXCLUDED:
                        d, c, ids = snapshot.trace_pnl_dc(code, start, end)
                    elif source.bucket == Bucket.BUSINESS_ONLY:
                        d, c, ids = snapshot.trace_biz_dc(code, start, end)
                    else:
                        d, c, ids = snapshot.trace_per_dc(code, start, end)
                else:
                    d, c, ids = snapshot.trace_cum_dc(code)

                if part.side == "debit":
                    value += d * part.sign
                elif part.side == "credit":
                    value += c * part.sign
                else:
                    value += (d - c) * part.sign
                all_ids.extend(ids)

        return value, all_ids

    def _resolve_sum(self, source: Source, ctx: dict) -> tuple:
        """SUM_FIELDS：汇总子字段的 value，合并 contributions，支持 sign"""
        value = Decimal("0")
        all_ids: List[int] = []
        signs = source.signs or {}
        for dep in source.deps:
            if dep in ctx:
                v, ids = ctx[dep]
                value += v * signs.get(dep, 1)
                all_ids.extend(ids)
        return value, all_ids

    def _apply_transform(self, transform: Source, value, aml_ids, snapshot, ctx: dict):
        if transform.formula == Formula.POSITIVE_PART:
            v = max(value, Decimal("0"))
            return v, aml_ids
        elif transform.formula == Formula.NEGATIVE_PART:
            return max(-value, Decimal("0")), aml_ids
        elif transform.formula == Formula.OPENING_FALLBACK:
            if value == Decimal("0") and snapshot.opening_balance:
                ob = snapshot.opening_balance
                fallback = getattr(ob, transform.opening_key, Decimal("0"))
                return _d(fallback), aml_ids
            return value, aml_ids
        elif transform.formula == Formula.SUBACCOUNT_FALLBACK:
            if value == Decimal("0") and transform.subaccount_codes:
                sub_value = Decimal("0")
                sub_ids = []
                start = snapshot._period_start
                end = snapshot._period_end
                for sub_code in transform.subaccount_codes:
                    d, c, ids = snapshot.trace_pnl_dc(sub_code, start, end)
                    sub_value += d - c
                    sub_ids.extend(ids)
                return sub_value, sub_ids
            return value, aml_ids
        elif transform.formula == Formula.NEGATE:
            return -value, aml_ids
        return value, aml_ids

    # ── 非总账数据源 ──

    def _resolve_invoice_tax_net(self, snapshot) -> tuple:
        """发票表：销项税额 - 进项税额。返回 (value, [invoice_ids])"""
        from enums import InvoiceDirection, InvoiceType, CertificationStatus

        output_tax = Decimal("0")
        input_tax = Decimal("0")
        invoice_ids = []

        for inv in snapshot.invoices():
            if inv.direction == InvoiceDirection.OUT:
                output_tax += _d(inv.tax_amount_l1)
                invoice_ids.append(inv.id)
            elif (inv.direction == InvoiceDirection.IN
                  and inv.invoice_type == InvoiceType.SPECIAL
                  and inv.certification_status_l3 == CertificationStatus.CERTIFIED):
                input_tax += _d(inv.tax_amount_l1)
                invoice_ids.append(inv.id)

        return output_tax - input_tax, invoice_ids

    def _resolve_stock_moves(self, snapshot) -> tuple:
        """库存流水聚合：按产品汇总，正库存余额 * 加权平均成本"""
        from utils import _d as ud

        moves = snapshot.stock_moves()
        inv_agg = {}
        move_ids = []
        for m in moves:
            pid = m.product_id
            if pid not in inv_agg:
                inv_agg[pid] = {"qty": Decimal("0"), "value": Decimal("0")}
            qty = ud(m.quantity_l1)
            cost = ud(m.total_cost_l2)
            vd = abs(cost) * (Decimal("1") if qty > 0 else Decimal("-1"))
            inv_agg[pid]["qty"] += qty
            inv_agg[pid]["value"] += vd
            move_ids.append(m.id)

        value = Decimal("0")
        for agg in inv_agg.values():
            if agg["qty"] > 0:
                value += agg["value"]

        return value, move_ids

    def _resolve_bank_txns(self, snapshot) -> tuple:
        txns = snapshot.bank_transactions()
        value = Decimal("0")
        ids = []
        for t in txns:
            if t.transaction_type == 'inflow':
                value += _d(t.amount_l2)
            else:
                value -= _d(t.amount_l2)
            ids.append(t.id)
        return value, ids

    def _resolve_cash_txns(self, snapshot) -> tuple:
        txns = snapshot.cash_flow_transactions()
        value = Decimal("0")
        ids = []
        for t in txns:
            if t.transaction_type == 'inflow':
                value += _d(t.amount_l2)
            else:
                value -= _d(t.amount_l2)
            ids.append(t.id)
        return value, ids

    def _resolve_classified_sum(self, source: Source) -> tuple:
        """从 _classified_cache 按 cf_code 取数求和"""
        cache = self._classified_cache or {}
        value = Decimal("0")
        ids = []
        for code in source.codes:
            if code in cache:
                amount, code_ids = cache[code]
                value += amount
                ids.extend(code_ids)
        return value, ids


def _d(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))
