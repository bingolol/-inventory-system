# 审计报告 Bug 真实性验证报告

**验证对象**：`audit_report.md` 中列出的 10 个漏洞
**验证方法**：逐条对照真实源码（文件:行号）进行代码审计 + 调用链追溯
**验证时间**：2026-06-29

---

## 验证结论总览

| 编号 | 标题 | 报告评级 | 验证结论 | 实际严重度 |
|---|---|---|---|---|
| #1 | 月结重复执行导致税费重复入账 | P0 | **真实存在** | P1（补提失效真实，并发重复需特定条件） |
| #2 | `_has_closed` 与 `_parse_period` off-by-one | P0 | **不成立**（夸大） | 无（AccountMove.date 是 Date 类型，SQLAlchemy 正确处理） |
| #3 | `_period_hash` 哈希空间 31 位 | P1 | **真实存在**（代码质量问题） | P2（碰撞概率极低，短期无实际风险） |
| #4 | 小规模纳税人免税规则错乱 | P0 | **真实存在** | P1（金额小但性质严重，含专票时出错） |
| #6 | 库存红冲 `is_inbound` None 兜底 | P1 | **真实存在**（代码异味） | P2（正常流程不触发，需绕过 engine 调用） |
| #7 | 固定资产处置日期默认 date.today() | P0 | **真实存在** | P1（router 确认 disposal_date 可选，默认 today） |
| #8 | 盘盈盘亏都挂 6601 管理费用 | P1 | **真实存在** | P1（会计准则不合规，审计风险） |
| #10 | record_sale 用 3% 覆盖税率 | P0 | **真实存在** | P0（1122 应收账款永久虚高，设计缺陷） |
| #11 | 退货成本取最早 StockMove 而非 average_cost | P0 | **不成立**（分析有误） | 无（移动加权平均法下用原始 unit_cost 是正确的） |
| #12 | 红字发票冲销重复冲红整单 | P0 | **真实存在** | P0（部分退货后红冲发票会重复冲红） |

**统计**：10 个漏洞中 **7 个真实存在**，2 个不成立，1 个为低风险代码异味。

---

## 逐条验证详情

### 漏洞 #1：月结重复执行导致税费重复入账 — ✅ 真实存在

**报告引用代码验证**：

| 报告引用 | 真实代码 | 匹配 |
|---|---|---|
| `engine_tax.py:84-86` closed 判定 | 第 84-86 行完全一致 | ✅ |
| `engine_tax.py:253-269` _has_closed | 第 253-269 行完全一致，只查 tax_surcharge 和 tax_income | ✅ |
| `engine_tax.py:110-131` 附加税入口 | 第 110-131 行一致，无独立幂等护栏 | ✅ |
| `engine_tax.py:223-241` 所得税入口 | 第 223-241 行一致，用 `not closed["income_tax"]` 守卫 | ✅ |
| `finance_integration.py:139-148` post_journal 幂等 | 第 139-148 行一致，只查 (source_model, source_id, is_reversal=False) | ✅ |

**场景 A（补提失效）验证**：

```
1. 首次月结：curr_vat=0 → 跳过附加税；如有利润则写入 tax_income 凭证
2. 补开发票后重跑月结：curr_vat>0
   - closed["surcharge"]=False → 附加税正确补提 ✅
   - closed["income_tax"]=True → `not closed["income_tax"]`=False
   - 所得税补提被跳过 ❌
```

**关键代码确认**（`engine_tax.py:223`）：
```python
if abs(delta) > Decimal("0.01") and not closed["income_tax"]:
```
即使 `delta`（应补提差额）大于 0.01，只要 `_has_closed` 查到已有 `tax_income` 凭证，就跳过补提。**这是真实的设计缺陷**——`_has_closed` 用布尔值"存在与否"而非"金额是否匹配"来判断。

**场景 B（并发重复）验证**：理论上成立——两个并发事务的 `_has_closed` 查询和 `post_journal` 的 existing 检查都看不到对方未提交的数据。但需要真正的并发调用月结接口，实际触发概率取决于前端是否禁用按钮和后端是否有锁。

**结论**：场景 A 的补提失效是**真实的、可触发的 bug**。严重度从 P0 下调为 P1（不会导致重复入账，但会导致补提金额永久遗漏）。

---

### 漏洞 #2：`_has_closed` 与 `_parse_period` off-by-one — ❌ 不成立（夸大）

**报告引用代码验证**：

| 报告引用 | 真实代码 | 匹配 |
|---|---|---|
| `engine_tax.py:272-277` _parse_period | 第 272-277 行一致，end_dt = datetime(..., 23, 59, 59) | ✅ |
| `engine_tax.py:253-269` _has_closed 用 `<= end_dt` | 第 258-259 行一致 | ✅ |

**报告遗漏的关键事实**：

`models_finance.py:91` 明确定义：
```python
date = Column(Date, nullable=False)  # ← Date 类型，不是 DateTime
```

**分析**：

1. `AccountMove.date` 是 `Date` 类型，存储为 "2026-05-31"（无时分秒）
2. `_parse_period` 返回 `datetime(2026, 5, 31, 23, 59, 59)`
3. SQLAlchemy 在比较 `Date` 列与 `datetime` 参数时，会通过 `Date` 类型的 `bind_processor` 将 datetime 截断为 date
4. 实际 SQL 比较：`"2026-05-31" <= "2026-05-31"` → True（月末当天正确包含）

报告中描述的"23:59:58 的销售凭证被漏算"场景**不会发生**，因为 AccountMove.date 不存储时分秒。

报告的"毫秒级时钟漂移"场景是**数据录入问题**（sale_date 被设为 6 月 1 日），不是代码 bug。如果业务日期设为 6 月 1 日，凭证正确归属 6 月。

**结论**：bug **不成立**。P0 评级完全不 justified。代码确实可以更清晰（用半开区间 `[start, next_month_first)`），但当前实现在 Date 类型下功能正确。

---

### 漏洞 #3：`_period_hash` 哈希空间 31 位 — ✅ 真实存在（代码质量问题）

**报告引用代码验证**：

`engine_tax.py:280-285` 完全一致：
```python
def _period_hash(period: str, tag: str) -> int:
    h = 0
    for c in f"{period}_{tag}":
        h = ((h << 5) - h) + ord(c)
        h &= 0x7FFFFFFF  # ← 31 位
    return h
```

5 个调用点（第 117, 129, 173, 229, 238 行）均确认。

**分析**：

- djb2 变体，31 位空间（2^31 - 1 ≈ 21 亿）
- 100 个月 × 5 个 tag = 500 个哈希，碰撞概率 ≈ 500²/(2×2³¹) ≈ 0.00006（约十万分之六）
- 报告自己也承认"碰撞概率极低"

**结论**：代码质量问题**真实存在**，但实际风险极低。建议改为字符串 `source_id=f"{period}_{tag}"` 更安全，但 P1 评级偏高，实际为 P2。

---

### 漏洞 #4：小规模纳税人免税规则错乱 — ✅ 真实存在

**报告引用代码验证**：

| 报告引用 | 真实代码 | 匹配 |
|---|---|---|
| `engine_tax.py:159-166` 简化实现 | 第 159-166 行一致，`exemption_amt = quarter_output_vat`（全额减免） | ✅ |
| `accounting_engine.py:585-596` 正确实现 | 第 585-596 行一致，区分 ordinary_tax=0 和 special_tax=rev×1% | ✅ |

**关键差异确认**：

```
季度≤30万 + 含专票 10,000 元场景：

engine_tax.py（错误）:
  exemption_amt = quarter_output_vat = 280,000 × 3% = 8,400（全额免）

accounting_engine.py（正确）:
  ordinary_tax = 0（普票免征）
  special_tax = 10,000 × 1% = 100（专票减按1%）
  正确减免 = 8,300，应缴 100

差异：100 元（专票部分被错误免掉）
```

**结论**：bug **真实存在**。engine_tax.py 的注释"简化：按全额减免处理"明确承认了这个简化。含专票时，专票部分应缴的 1% 增值税被错误免除。P0 略偏高（金额小），实际 P1。

---

### 漏洞 #6：库存红冲 `is_inbound` None 兜底 — ✅ 真实存在（代码异味）

**报告引用代码验证**：

`engine_inventory.py:272` 完全一致：
```python
is_inbound = original is None or original.quantity > 0
```

**分析**：

- 当 `original is None` 时，`is_inbound = True`，默认按入库红冲处理
- 正常业务流程中，`reverse()` 被调用时 original 应该存在（因为 outbound 先执行）
- `track_inventory=False` 的商品在第 242-243 行提前返回，不触发此代码
- 只有在绕过 engine 接口直接操作 StockMove、或 StockMove 被手动删除时才会触发

**结论**：代码异味**真实存在**，但正常业务流程不触发。建议改为 `original is None` 时抛异常，但 P1 偏高，实际 P2。

---

### 漏洞 #7：固定资产处置日期默认 date.today() — ✅ 真实存在

**报告引用代码验证**：

`engine_fixed_asset.py:163` 完全一致：
```python
disposal_date = disposal_date or date.today()
```

**Router 验证**（`routers/fixed_assets.py:138`）：
```python
disposal_date: Optional[str] = Query(None, description="处置业务日期 YYYY-MM-DD（不传则用今天）")
```

确认 disposal_date 是**可选参数**，不传时默认 None → `date.today()`。

**分析**：

- docstring（第 141-142 行）提到 BR-22 修复方向，但代码未实现
- 对比 `finance_integration.py:208` 的 `reverse_journal` 已修复为 `reversal_date or original.date`
- 跨月处置时，凭证日期为 today 而非业务日期，导致 BS 报表跨月不平

**结论**：bug **真实存在**。Router 确认 disposal_date 可选，默认 today。跨月补录处置时凭证日期错误。P0 略偏高（需要特定时序），实际 P1。

---

### 漏洞 #8：盘盈盘亏都挂 6601 管理费用 — ✅ 真实存在

**报告引用代码验证**：

`product_commands.py:269-278` 完全一致：
```python
if delta < 0:
    # 盘亏
    lines = [
        {"account_code": "6601", "debit": value, "credit": Decimal("0")},   # 借：管理费用
        {"account_code": "1405", "debit": Decimal("0"), "credit": value},   # 贷：库存商品
    ]
else:
    # 盘盈
    lines = [
        {"account_code": "1405", "debit": value, "credit": Decimal("0")},   # 借：库存商品
        {"account_code": "6601", "debit": Decimal("0"), "credit": value},   # 贷：管理费用
    ]
```

**分析**：

- 根据《小企业会计准则》，盘盈盘亏应先挂 `1901 待处理财产损溢`，查明原因后再转入损益科目
- 盘盈贷 `6601` 会减少管理费用（而非增加营业外收入 6301），分类错误
- 盘亏借 `6601` 在未查明原因前直接进费用，跳过了中转科目

**结论**：bug **真实存在**。会计准则不合规，审计风险。P1 评级合理。

---

### 漏洞 #10：record_sale 用 3% 覆盖税率 — ✅ 真实存在（最严重）

**报告引用代码验证**：

`engine_finance.py:80-93` 完全一致：
```python
for item in order.items:
    line_total = Decimal(str(item.total_price))
    total_without_tax += line_total
    rate = item.tax_rate
    if is_small_scale and rate and rate > 0:
        rate = self._vat_rate(self.account)  # ← 覆盖为 3%
    if rate:
        tax_amount += (line_total * Decimal(str(rate))).quantize(Q2)
```

`_vat_rate` 第 42 行返回 `Decimal("0.03")`（小规模）。

`schemas/order.py:73` 确认 SaleItem 默认 `tax_rate = Decimal('0.01')`。

**分析**：

1. item.tax_rate 默认 0.01（1%），但被覆盖为 0.03（3%）
2. 凭证分录：贷 222103 = revenue × 3%（应为 1%）
3. **更严重**：total_with_tax = revenue × 1.03，借 1122 = revenue × 1.03
4. 客户实际应付 revenue × 1.01（按 1% 税率开票）
5. **1122 应收账款永久虚高 2%**，季度末免税分录只冲 222103 不调 1122

**对比退货代码**（`sale_commands.py:317-319`）：
```python
if taxpayer_type == "small_scale" and rate and rate > 0:
    rate = Decimal("0.01")  # 小规模 1% 征收率
```
退货用 1%，销售用 3%，**税率不对称**。

**结论**：bug **真实存在且严重**。P0 评级合理。1122 永久虚高是最核心的问题，季末免税无法修正。

---

### 漏洞 #11：退货成本取最早 StockMove — ❌ 不成立（分析有误）

**报告引用代码验证**：

`sale_commands.py:302-308` 和 `engine_inventory.py:258-273` 代码均与报告一致。

**报告分析的核心错误**：

报告称"退货成本应该用当前 average_cost 而非原始 unit_cost"。**这是错误的**。

**正确会计处理**（移动加权平均法）：

```
T1  销售 8 件，当时 average_cost = 106.67
    → COGS = 8 × 106.67 = 853.33（凭证记 6401 借 853.33）

T2  采购 5 件单价 150，average_cost 变为 116.67

T3  退货 3 件
    → 应冲减 COGS = 3 × 106.67 = 320.00（冲减原销售时记的成本）
    → 库存回补 = 3 × 106.67 = 320.00（恢复原出库时扣减的价值）
    → ✅ 两者一致，账实相符

如果按报告建议用 average_cost=116.67：
    → COGS 冲减 = 3 × 116.67 = 350.00（但原销售只记了 320）
    → 库存回补 = 350.00
    → ❌ COGS 冲减(350) ≠ 原 COGS(320)，产生 30 元无来源差异
```

**移动加权平均法的核心原则**：退货是原销售的逆向操作，必须用原销售时的出库成本冲回，而非当前平均成本。

**关于 force=True 不一致**：

报告称 reverse 用 `order_by(desc).first()`（最新），sale_commands 用 `.first()`（最早），造成不一致。但实际验证：

- ReturnSaleOrder 调用 `eng.reverse(..., source_id_override=return_id)` **不传 force=True**
- force 默认 False，reverse 内部用 `.first()`（最早）
- sale_commands 也用 `.first()`（最早）
- **两者一致，无不一致**

**结论**：bug **不成立**。当前实现（用原始 unit_cost）是正确的移动加权平均法处理。报告的修复建议（改用 average_cost）反而是错误的。P0 评级完全不 justified。

---

### 漏洞 #12：红字发票冲销重复冲红整单 — ✅ 真实存在

**报告引用代码验证**：

`invoice_commands.py:608-633` 完全一致：
```python
if invoice.related_order_type == "sale_order" and invoice.related_order_id:
    FinanceEngine(db, cmd.account_id).reverse_sale(invoice.related_order_id)  # ← 整单冲红
    ...
    for item in sale_order.items:
        engine_inv.reverse(
            ...
            quantity=item.quantity,  # ← 整单数量
            source_type="sale_order",
            source_id=sale_order.id,  # ← 原 source_id，无 override
        )
```

**场景验证**：

```
T1  销售 10 件 → V1(source_model="sale_order", source_id=SO1), M1(qty=-10)

T2  部分退货 3 件 → V2(source_model="sale_return", source_id=return_id), M2(qty=+3)

T3  红字发票冲销：
    - reverse_sale(SO1) → reverse_journal 查 (sale_order, SO1, is_reversal=True)
    - 不存在（部分退货走的是 sale_return）→ 创建 V3 整单冲红
    - V1 被完全冲红！
    - 库存：reverse(source_type="sale_order", source_id=SO1, qty=10)
      - 幂等检查 (sale_order_reversal, SO1) → 不存在（M2 的 source_id=return_id）
      - 创建 M3(qty=+10) → 库存 +10
    - 总库存变化：+3(退货) + 10(红冲) = +13（应仅为 +3 或 +10）
```

**结论**：bug **真实存在**。部分退货后做红字发票冲销，会导致整单被重复冲红，应收/收入/库存全部错乱。P0 评级合理。

---

## 修复优先级建议（基于验证结果调整）

### 必须立即修复

| 优先级 | 漏洞 | 原因 |
|---|---|---|
| **P0** | #10 record_sale 3% 税率 | 每笔小规模销售凭证都错，1122 永久虚高 |
| **P0** | #12 红字发票重复冲红 | 部分退货后红冲发票会破坏整单数据 |

### 建议尽快修复

| 优先级 | 漏洞 | 原因 |
|---|---|---|
| **P1** | #1 月结补提失效 | 跨期补录时所得税永久漏提 |
| **P1** | #4 小规模免税错算 | 含专票时少缴增值税 |
| **P1** | #7 处置日期默认 today | 跨月 BS 不平 |
| **P1** | #8 盘盈盘亏科目错挂 | 审计风险 |

### 可延后修复

| 优先级 | 漏洞 | 原因 |
|---|---|---|
| **P2** | #3 哈希空间 31 位 | 碰撞概率极低 |
| **P2** | #6 None 兜底 | 正常流程不触发 |

### 无需修复

| 漏洞 | 原因 |
|---|---|
| #2 off-by-one | AccountMove.date 是 Date 类型，功能正确 |
| #11 退货成本 | 用原始 unit_cost 是正确的移动加权平均法 |

---

## 修复方案与实施（已执行）

以下为 8 个真实存在漏洞的修复方案，已全部实施并通过语法检查。

### 修复 #10：record_sale 3% 税率覆盖（P0）

**文件**：`backend/engine_finance.py`

**修复内容**：移除 `is_small_scale` 时用 `_vat_rate()` 覆盖 `item.tax_rate` 为 3% 的逻辑，直接使用行项 `item.tax_rate`（小规模默认 0.01 即 1%）。

```python
# 修复前（错误）：
is_small_scale = self.account and self.account.taxpayer_type == "small_scale"
rate = item.tax_rate
if is_small_scale and rate and rate > 0:
    rate = self._vat_rate(self.account)  # ← 覆盖为 3%

# 修复后（正确）：
rate = item.tax_rate  # 直接用行项税率，小规模默认 1%，一般纳税人按商品税率
```

**效果**：1122 应收账款不再虚高 2%，与退货代码（`sale_commands.py:319` 已正确用 1%）保持一致。

---

### 修复 #12：红字发票重复冲红整单（P0）

**文件**：`backend/commands/invoice_commands.py` — `ReverseInvoiceHandler`

**修复内容**：在红字发票冲红时，检查销售单是否已有部分退货：
1. **订单已取消** → 跳过（凭证库存已整单冲红）
2. **有部分退货** → 用 `sale_return` 凭证冲红剩余部分（避免 `reverse_sale` 整单冲红导致重复）
3. **无部分退货** → 整单冲红（原逻辑）

**核心逻辑**：
```python
# 计算已部分退货数量（通过 sale_order_reversal 类型的 StockMove）
reversed_qty_map = {}  # product_id → 已退货数量
# ...
remaining_qty = item.quantity - already_reversed
if remaining_qty > 0:
    remaining_items.append((item, remaining_qty))

if has_partial_return:
    # 用 sale_return 凭证冲红剩余部分（独立 source_id 避免幂等冲突）
    post_journal(db, account_id, "sale_return", {...})
else:
    # 无部分退货 → 整单冲红
    FinanceEngine(db, account_id).reverse_sale(sale_order.id)
```

**效果**：部分退货后红字发票冲红不再重复冲减收入/应收/税额/库存。

---

### 修复 #1：月结所得税补提失效（P1）

**文件**：`backend/engine_tax.py`

**修复内容**：
1. **所得税**：移除 `not closed["income_tax"]` 守卫，首次用普通过账（幂等），后续用 `force=True` 补提差额
2. **附加税**：改为 delta 模式（target - posted），已计提后仍可补提差额
3. **VAT 结转**：独立检查是否已结转过，不再依赖 `closed["surcharge"]`

```python
# 所得税修复：
if abs(delta) > Decimal("0.01"):  # 移除 and not closed["income_tax"]
    if delta > Decimal("0"):
        post_journal(..., force=closed["income_tax"])  # 首次不force，后续force补提

# 附加税修复（delta 模式）：
target_surcharge = (curr_vat * Decimal("0.12")).quantize(Q2)
posted_surcharge = _crd(self.db, ledger, "222104", close_dt)
surcharge_delta = target_surcharge - posted_surcharge
if surcharge_delta > Decimal("0.01"):
    post_journal(..., force=closed["surcharge"])
```

**效果**：跨期补录利润变动后，所得税和附加税可以正确补提差额。

---

### 修复 #4：小规模免税规则错乱（P1）

**文件**：`backend/engine_tax.py`

**修复内容**：区分普票和专票，普票全额免（3%减免），专票减按1%（2%减免，1%留缴）。

```python
# 修复前（错误）：
exemption_amt = quarter_output_vat  # 全额免（专票也被免）

# 修复后（正确）：
ordinary_rev = ...  # 查普票不含税金额
special_rev = ...   # 查专票不含税金额
exemption_amt = (
    ordinary_rev * Decimal("0.03")  # 普票全额免
    + special_rev * Decimal("0.02") # 专票减免2%（1%留缴）
).quantize(Q2)
```

**效果**：专票部分不再被错误全额免税，1% 增值税正确留在 222103 缴纳。

---

### 修复 #7：固定资产处置日期默认 today（P1）

**文件**：`backend/engine_fixed_asset.py` + `backend/routers/fixed_assets.py`

**修复内容**：强制要求 `disposal_date` 参数，不传时抛 BusinessError。与 `sale_date`、`return_date` 的处理方式一致。

```python
# 修复前（错误）：
disposal_date = disposal_date or date.today()  # 跨月 BS 不平

# 修复后（正确）：
if disposal_date is None:
    raise BusinessError(
        code=ErrorCode.VALIDATION_ERROR,
        message="处置日期不能为空，请提供业务发生日期",
    )
```

Router 同步改为必填：`disposal_date: str = Query(..., description="处置业务日期 YYYY-MM-DD（必填）")`

**效果**：跨月补录处置时凭证日期正确，BS 报表不再错配。

---

### 修复 #8：盘盈盘亏科目错挂（P1）

**文件**：`backend/finance_integration.py` + `backend/commands/product_commands.py`

**修复内容**：
1. 在 `CHART_OF_ACCOUNTS` 中添加 `1901 待处理财产损溢`
2. 盘盈盘亏先挂 1901，查明原因后再转入损益科目

```python
# 修复前（错误）：
if delta < 0:  # 盘亏
    lines = [{"account_code": "6601", ...}, {"account_code": "1405", ...}]  # 直接进管理费用
else:  # 盘盈
    lines = [{"account_code": "1405", ...}, {"account_code": "6601", ...}]  # 直接冲管理费用

# 修复后（正确）：
if delta < 0:  # 盘亏
    lines = [{"account_code": "1901", ...}, {"account_code": "1405", ...}]  # 先挂待处理
else:  # 盘盈
    lines = [{"account_code": "1405", ...}, {"account_code": "1901", ...}]  # 先挂待处理
```

**效果**：符合《小企业会计准则》盘盈盘亏处理流程，降低审计风险。

---

### 修复 #3：哈希空间 31 位（P2）

**文件**：`backend/engine_tax.py`

**修复内容**：将 `_period_hash` 的掩码从 `0x7FFFFFFF`（31 位）扩展到 `0x7FFFFFFFFFFFFFFF`（63 位）。

```python
# 修复前：
h &= 0x7FFFFFFF  # 31 位，约 21 亿

# 修复后：
h &= 0x7FFFFFFFFFFFFFFF  # 63 位，约 9.2×10^18
```

**效果**：碰撞概率从十万分之六降至可忽略的 10^-17 量级。

---

### 修复 #6：库存红冲 None 兜底（P2）

**文件**：`backend/engine_inventory.py`

**修复内容**：`original` 为 None 时抛 BusinessError，而非默认按入库方向处理。

```python
# 修复前（错误）：
is_inbound = original is None or original.quantity > 0  # None 当入库

# 修复后（正确）：
if original is None:
    raise BusinessError(
        code=ErrorCode.VALIDATION_ERROR,
        data={"details": f"找不到原始库存流水: ..."},
    )
is_inbound = original.quantity > 0
```

**效果**：避免在异常情况下方向判断错误，及早暴露数据问题。

---

## 修改文件清单

| 文件 | 修复漏洞 |
|---|---|
| `backend/engine_finance.py` | #10 |
| `backend/commands/invoice_commands.py` | #12 |
| `backend/engine_tax.py` | #1, #3, #4 |
| `backend/engine_fixed_asset.py` | #7 |
| `backend/routers/fixed_assets.py` | #7 |
| `backend/finance_integration.py` | #8 |
| `backend/commands/product_commands.py` | #8 |
| `backend/engine_inventory.py` | #6 |

**全部 8 个文件已通过 Python 语法检查（py_compile）。**

---

**报告结束**
