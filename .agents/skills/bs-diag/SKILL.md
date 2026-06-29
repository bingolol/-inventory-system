---
name: bs-diag
description: 资产负债表/利润表不平衡的故障诊断经验手册。适用于报表不平、日期过滤失效、库存跨期污染、Decimal 精度崩溃等场景。遇到 BS/IS 报表问题时必须加载。
---

# BS/IS 故障诊断经验手册

> 最后更新: 2026-06-28 | 来源: 两次大规模 BS 不平衡排查实战

## 诊断流程

### Phase 1 — 隔离旧数据（最重要）

```
旧数据经过多次代码版本 → 字段残缺 / 值不一致 / 约束违反
→ 排查难度指数级上升
→ 第一步永远是建新账本
```

**操作：**
```python
r = requests.post('/api/accounts', {'name':'诊断','taxpayer_type':'general'})
aid = r.json()['id']
```

然后只在新账本上跑最小数据集（1 采购 + 1 销售 + 1 收款 + 1 付款 + 1 费用），不要一步登天跑全量。

### Phase 2 — 让 BS 输出诊断信息

不要在 BS 不平衡时抛异常——改成返回全字段 + `balanced` 标记：

```python
diff = total_assets - (total_liabilities + total_equity)
balanced = abs(diff) <= Decimal('0.01')
return {
    "balanced": balanced,
    "diff": float(diff.quantize(Q2)),
    "monetary_funds": ...,
    "accounts_receivable": ...,
    "inventory": ...,
    "accounts_payable": ...,
    "tax_payable": ...,
    "paid_in_capital": ...,
    "retained_earnings": ...,
    "period_revenue": ...,    # ← 利润拆解字段
    "period_cogs": ...,
    "period_expenses": ...,
    "period_profit": ...,
}
```

这样就能逐项比对，不需要猜。

### Phase 3 — 独立验算每一项

对 BS 每个项目分别从业务表查询，跟 BS 返回值交叉核对：

| BS 项目 | 验算 SQL/公式 | 常见问题 |
|---------|--------------|---------|
| monetary_funds | `opening_cash - sum(Payment) + sum(Receipt)` | 无 BankAccount 时写死期初值，收付款不反映 |
| inventory | `sum(inbound_cost) - sum(outbound_cost)` 从 StockMove 按 `move_date` 过滤 | 读 Inventory 快照表会被跨期污染 |
| AR | `sum(SaleOrder) WHERE unpaid` | — |
| AP | `sum(PurchaseOrder) WHERE unpaid + sum(Expense) WHERE unpaid` | 固定资产应付单独处理 |
| tax_payable | `max(output_tax - input_tax, 0)` | 进项发票需 certified+special 才计入 |
| paid_in_capital | OpeningBalance.paid_in_capital | — |
| retained_earnings | `opening_re + period_profit` | 利润必须从 IS 口径算 |

### Phase 4 — 如果还不平，看利润拆解

BS 的 `period_profit` 应与 IS 的 `net_profit` 一致。如果不一致，说明 BS 和 IS 用了不同的收入/成本/费用查询口径。

常见原因：一般纳税人的 BS 用 `SaleItem.total_price / (1+tax_rate)`，小规模用 `SaleOrder.total_price`。两个分支不能混。

---

## 已知陷阱清单

### T1: `sum([])` 返回 `int 0`

```python
# ❌ 当 bs_items 为空时 sum 返回 int 0
period_revenue = sum(_d(it.total_price) / ... for it in bs_items)
period_revenue.quantize(Q2)  # → 'int' object has no attribute 'quantize'

# ✅ 始终用 _d() 包裹
period_revenue = _d(sum(_d(it.total_price) / ... for it in bs_items))
period_revenue.quantize(Q2)  # → OK, Decimal('0.00')
```

**扫描命令：** `grep -n "= sum(" *.py | grep -v "_d(sum("`

### T2: SQLite + DateTime + 跨类型比较

```python
# ❌ query_date 是 date 对象
query_date = datetime.strptime(date, "%Y-%m-%d").date()
Expense.expense_date <= query_date
# SQLite 存 "2026-05-31 10:30:00"，比较 "<= 2026-05-31"
# 字母序: "2026-05-31 10:30:00" > "2026-05-31" → FALSE
# 当天 00:00 之后的数据全被过滤

# ✅ query_date 保持 datetime，加 query_end
query_date = datetime.strptime(date, "%Y-%m-%d")  # datetime, 不是 date
query_end = query_date + timedelta(days=1) - timedelta(seconds=1)  # 23:59:59
Expense.expense_date <= query_end  # 覆盖全天
```

**检查清单：**
- [ ] `strptime` 后没调 `.date()` → 保持 datetime
- [ ] Date 列（如 `FixedAsset.start_date`）比较 datetime 时用 `.date()` 避免 TypeError
- [ ] 所有 `<= end_date` 比较用 `end_of_day(23:59:59)` 而不是 `00:00:00`

### T3: Inventory 快照表跨期污染

```python
# ❌ 读 Inventory 表—永远是当前快照
for inv in db.query(Inventory).filter(...).all():
    inventory_value += quantity * average_cost
# 4月 BS 读到的是 4月+5月 的库存 → 40,500 变成 57,400

# ✅ 从 StockMove 按业务日期过滤
as_of_moves = _stock_moves_as_of(db, account_id, query_end)
# StockMove 需要 move_date 字段（业务日期，非 created_at）
```

**修复前提：** StockMove 必须有 `move_date` 字段（`DateTime`），由 `InventoryEngine._get_move_date()` 从源单据自动填充。

### T4: StockMove 日期 = 当前时间，不是业务日期

```python
# ❌ InventoryEngine 创建 StockMove 时：
move = StockMove(
    ...
    # created_at 默认 datetime.now()
)
# 所有 StockMove 都是当前时间，无法按业务日期过滤

# ✅ 修复后：
move = StockMove(
    ...
    move_date=self._get_move_date(source_type, source_id),
)
# _get_move_date 从 PurchaseOrder/SaleOrder 取日期
```

### T5: 旧数据污染 — 命中任何一项就应建新账本

| 污染类型 | 症状 |
|---------|------|
| StockMove 无 `move_date` | 历史库存无法按日期过滤 |
| 科目表编码不一致 | 引擎引用不存在的科目编码 |
| OpeningBalance 不过账 | LedgerAccountBalance 为 0，付款崩 INSUFFICIENT_BALANCE |
| 旧 BS 抛异常 | 无法获取分项数据诊断 |
| Expenses 的 `functional_category` 值不匹配 | 利润表费用为 0 |

**诊断命令：**
```bash
# 查 StockMove 日期
python -c "print([(sm.source_type, sm.created_at.date()) for sm in db.query(StockMove).filter(StockMove.account_id==N).all()])"
# 查 OpeningBalance 过账情况
python -c "from models_finance import LedgerAccountBalance; print([lb.balance for lb in db.query(LedgerAccountBalance).join(LedgerAccount).filter(LedgerAccount.code=='1001').all()])"
```

### T6: 期初余额不过账

OpeningBalance 只是业务表记录，不影响 LedgerAccountBalance。
付款/收款 `post_journal` 时 `engine_ledger.py` 检查 1001 科目余额：

```python
if account.code == "1001" and balance_row.balance + delta < 0:
    raise AccountingError(INSUFFICIENT_BALANCE)
```

如果 OpeningBalance 没有对应的 journal entry，1001 余额为 0 → 任何付款都崩。

**修复：** `CreateOpeningBalanceHandler` 调 `post_journal(db, account_id, "opening_balance", {"lines": [...]})`。

---

## Python/Decimal 精度规则

| 规则 | 说明 |
|------|------|
| `Decimal('0.01')` 定义 `Q2` | 全局统一精度 |
| `_d(v)` 包裹所有数值 | `_d(None)` → `0`，`_d(str)` → `Decimal` |
| `_d(sum(...))` 防 `int 0` | `sum([])` 返回 `int 0`，必须转 Decimal |
| `quantize(Q2)` 只在 Decimal 上调 | 不要在 `int` 或 `float` 上调用 |

## 快速检查脚本

创建新账本跑最小测试：

```python
r = post('/api/accounts', {'name':'诊断','taxpayer_type':'general'})
aid = r['id']
post('/api/opening-balances', {'date':'2024-01-01','cash_balance':10000,'paid_in_capital':10000})
# ... 创建商品/供应商/客户/采购/销售/收款/付款/费用 ...
bs = get(f'/api/financial-reports/balance-sheet?date=2024-01-31', aid)
assert bs['balanced'] == True, f"BS不平衡: diff={bs['diff']}"
```

如果 `balanced == True`，问题在旧数据。如果 `balanced == False`，用分项字段逐项排查。
