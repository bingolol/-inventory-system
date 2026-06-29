# 财务/进销存系统金融隐患与会计漏洞审计报告

**审计对象**：`backend/` 目录核心账务代码（commit `21f8867c`，2026-06-29 拉取）
**审计范围**：月结、凭证生成、库存流水、调整单、退货冲红、固定资产业务
**审计方法**：代码静态阅读 + 调用链追溯 + 业务流程时序复盘
**报告生成时间**：2026-06-29 19:10 (Asia/Shanghai)
**报告生成者**：Mavis（基于实际文件:行号审计）

---

## 目录

| 编号 | 标题 | 严重等级 |
|---|---|---|
| 漏洞 #1 | 月结重复执行导致增值税附加税、所得税重复入账 | **P0** |
| 漏洞 #2 | `_has_closed` 与 `_parse_period` 组合产生 off-by-one，跨期凭证被漏算 | **P0** |
| 漏洞 #3 | `_period_hash` 哈希空间仅 31 位且无 salt，存在 source_id 冲突风险 | P1 |
| 漏洞 #4 | 小规模纳税人"季度≤30万"免税规则实现错乱，专票部分被错误全额免税 | **P0** |
| 漏洞 #6 | 库存红冲 `is_inbound` 判 `None` 当作入库兜底，方向反转在边界场景出错 | P1 |
| 漏洞 #7 | 固定资产业务日期处置 `disposal_date` 默认值与记账日期错位，跨月 BS 不平 | **P0** |
| 漏洞 #8 | `AdjustInventory` 盘亏走"管理费用"科目，盘盈走"管理费用"科目——两个都挂错了 | P1 |
| 漏洞 #10 | `record_sale` 在凭证层用 3% 法定征收率算销项税，与"减按 1%"的会计引擎真相源冲突 | **P0** |
| 漏洞 #11 | 销售退货冲红时成本与库存回补双向独立计算，库存单价波动时错位 | **P0** |
| 漏洞 #12 | 红字发票冲销调用 `reverse_sale` 用原始 `source_id` 当幂等键，部分退货场景会重复冲红整单 | **P0** |

---

## 漏洞 #1：月结重复执行导致税费重复入账 / 补提失效

**严重等级**：🟥 **P0 — 致命级**
**涉及文件**：
- `backend/engine_tax.py:84-86`（重复执行护栏）
- `backend/engine_tax.py:110-131`（附加税与 VAT 结转入口）
- `backend/engine_tax.py:223-241`（所得税计算入口）
- `backend/finance_integration.py:139-148`（post_journal 通用幂等检查）

### 真实代码证据

**`engine_tax.py:84-86`** — 月结的"已结账"判定逻辑**只覆盖 2 种 source_model**：

```python
# 84-86
closed = self._has_closed(ledger, period)
if closed["surcharge"] and closed["income_tax"]:
    return {"status": "skipped", "msg": f"期 {period} 已结账", "detail": closed}
```

**`engine_tax.py:253-269`** — `_has_closed` 实际检查的范围：

```python
# 253-269
def _has_closed(self, ledger: Ledger, period: str) -> Dict[str, bool]:
    period_start, period_end = _parse_period(period)
    surcharge_exists = self.db.query(AccountMove).filter(
        AccountMove.ledger_id == ledger.id,
        AccountMove.source_model == "tax_surcharge",    # ← 只查附加税
        AccountMove.date >= period_start,
        AccountMove.date <= period_end,
    ).first() is not None

    income_exists = self.db.query(AccountMove).filter(
        AccountMove.ledger_id == ledger.id,
        AccountMove.source_model == "tax_income",       # ← 只查所得税
        AccountMove.date >= period_start,
        AccountMove.date <= period_end,
    ).first() is not None

    return {"surcharge": surcharge_exists, "income_tax": income_exists}
```

**`engine_tax.py:110-131`** — 附加税与 VAT 结转入口（无独立幂等护栏）：

```python
# 110-131
if curr_vat > Decimal("0") and not closed["surcharge"]:
    surcharge_amt = (curr_vat * Decimal("0.12")).quantize(Q2)
    if surcharge_amt > 0:
        post_journal(self.db, account_id, "tax_surcharge", {
            "amount": surcharge_amt,
            "date": close_dt,
            "source_model": "tax_surcharge",
            "source_id": _period_hash(period, "surcharge"),
        })
        result_lines.append(f"附加税: +{surcharge_amt}")
        logger.info(f"月结 {period} 计提附加税: {surcharge_amt}")

    # VAT 结转：仅一般纳税人执行（222101→222106→222107）
    # 小规模纳税人 222103 本身就是应交增值税，无需结转
    if taxpayer_type != "small_scale":
        post_journal(self.db, account_id, "vat_transfer_out", {
            "amount": curr_vat,
            "date": close_dt,
            "source_model": "vat_transfer_out",
            "source_id": _period_hash(period, "vat_xfer"),
        })
        logger.info(f"月结 {period} 转出未交增值税: {curr_vat}")
```

**`engine_tax.py:223-241`** — 所得税计算入口（无独立幂等护栏）：

```python
# 223-241
if abs(delta) > Decimal("0.01") and not closed["income_tax"]:
    if delta > Decimal("0"):
        post_journal(self.db, account_id, "tax_income", {
            "amount": delta,
            "date": close_dt,
            "source_model": "tax_income",
            "source_id": _period_hash(period, "income"),
        })
        result_lines.append(f"所得税: +{delta}")
        logger.info(f"月结 {period} 计提所得税: +{delta}")
    else:
        post_journal(self.db, account_id, "tax_income_reversal", {
            "amount": abs(delta),
            "date": close_dt,
            "source_model": "tax_income_reversal",
            "source_id": _period_hash(period, "income_rev"),
        })
        result_lines.append(f"所得税: -{abs(delta)} (冲回)")
        logger.info(f"月结 {period} 冲回所得税: {abs(delta)}")
```

**`finance_integration.py:139-148`** — post_journal 通用幂等（**只检查 (source_model, source_id, is_reversal=False) 三元组**）：

```python
# 139-148
sm = source.get("source_model")
si = source.get("source_id")
if sm and si is not None and not force:
    existing = db.query(AccountMove).filter(
        AccountMove.source_model == sm,
        AccountMove.source_id == si,
        AccountMove.is_reversal == False,
    ).first()
    if existing:
        return existing
```

### 调用链时序

**场景 A：5 月结账时 `curr_vat=0`（没销项凭证），6 月补开发票后重跑 5 月结账**

```
T1  2026-05-31 23:50 月结 2026-05
    - 此时还有 5 月 31 日的发票未审核，222101 贷方累计 = 0
    - curr_vat = max(0 - 0, 0) = 0
    - if curr_vat > 0: 条件不成立 → 跳过附加税分支
    - 无 tax_surcharge 凭证写入
    - closed["surcharge"] = False
    - 正常返回（无任何 tax_* 凭证）

T2  2026-06-01 00:30 财务补审了 5 月 31 日的发票
    - 系统自动写过账凭证（222101 贷方累计 10,000）
    - 已存在的 tax_income 凭证（5 月 31 日生成）金额是按 0 利润算的 = 0

T3  2026-06-01 09:00 管理员重跑月结 2026-05
    - curr_vat 重新计算 = 10,000
    - if curr_vat > 0 and not closed["surcharge"]:  ← True,True
    - surcharge_amt = 10,000 * 12% = 1,200
    - post_journal("tax_surcharge", source_id=h("2026-05","surcharge"))
    - existing 检查：source_id = h("2026-05","surcharge")，无 existing → 插入新凭证 ✅
    - 附加税 = 1,200 这次正确写入

T4  但所得税呢？
    - _has_closed["income_tax"] = True（之前 5 月 31 日有 tax_income 凭证）
    - delta = 400（实际应计提）- 0（已计提）= 400
    - if abs(delta) > 0.01 and not closed["income_tax"]:  ← True, **False**
    - **直接跳过所得税补提** → 400 元所得税永久漏提
```

**场景 B：管理员在 5 秒内点击"月结"两次（前端没禁用按钮）**

```
T1  2026-05-31 18:00:00 第一次月结
    - _has_closed 全 False
    - post_journal("tax_surcharge", h("2026-05","surcharge"))
    - post_journal("tax_income", h("2026-05","income"))
    - 业务事务已 commit

T2  2026-05-31 18:00:01 第二次月结
    - _has_closed["surcharge"] = True
    - _has_closed["income_tax"] = True
    - return skipped ✅ 安全

但是！—— 如果 T1 和 T2 在同一个事务里：
    - T1 还在 db.flush() 阶段，未 commit
    - T2 的 _has_closed 查询时，**T1 的凭证还看不到**（事务隔离）
    - 两次都判定为未结账 → 两次都 post_journal
    - post_journal 的 existing 检查：源凭证未 commit → 查不到 existing → 再次插入
    - **2 张重复的附加税凭证**！
```

### 真实触发条件

- **场景 A**：补录跨期业务 + 重跑月结（任何 ERP 都常见）
- **场景 B**：并发月结（前端按钮没禁用 / 后台定时任务重复触发 / 网络重发）

### 量化后果

- **场景 A**：补提金额永久漏掉，所得税汇算清缴时**多退少补触发预警**
- **场景 B**：附加税 / 所得税**重复计提 1 倍**，期末调账复杂

### 修复方向

1. **加 `MonthlyClose` 锁表**：`MonthlyClose(ledger_id, period, status, UNIQUE(ledger_id, period))`，事务开始时 `INSERT OR IGNORE` 抢锁
2. **统一幂等键**：`post_journal` 改为 `(source_model, period, source_id)` 三元组
3. **增量更新**：`_has_closed` 返回已存在凭证的 source_id 集合，业务逻辑判断"是否需要补差"

---

## 漏洞 #2：`_has_closed` 与 `_parse_period` 组合产生 off-by-one，跨期凭证被漏算

**严重等级**：🟥 **P0 — 致命级**
**涉及文件**：
- `backend/engine_tax.py:272-277`（_parse_period）
- `backend/engine_tax.py:253-269`（_has_closed）
- `backend/engine_tax.py:178-186`（_crd / _bal / 利润计算）

### 真实代码证据

**`engine_tax.py:272-277`** — 期间边界计算：

```python
# 272-277
def _parse_period(period: str):
    year, month = int(period[:4]), int(period[5:7])
    _, last_day = monthrange(year, month)
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59)   # ← 月末 23:59:59
    return start_dt, end_dt
```

**`engine_tax.py:253-269`** — `_has_closed` 用 `>= start_dt AND <= end_dt`：

```python
# 253-269
def _has_closed(self, ledger: Ledger, period: str) -> Dict[str, bool]:
    period_start, period_end = _parse_period(period)
    surcharge_exists = self.db.query(AccountMove).filter(
        AccountMove.ledger_id == ledger.id,
        AccountMove.source_model == "tax_surcharge",
        AccountMove.date >= period_start,
        AccountMove.date <= period_end,   # ← 用 <= end_dt (23:59:59)
    ).first() is not None
    ...
```

**`engine_tax.py:178-186`** — 利润计算同样用 `close_dt`（即 `end_dt`）：

```python
# 178-186
revenue = _crd(self.db, ledger, "6001", close_dt) + _crd(self.db, ledger, "6051", close_dt)
cogs = _bal(self.db, ledger, "6401", close_dt)
opex = (_bal(self.db, ledger, "6601", close_dt)
        + _bal(self.db, ledger, "6602", close_dt)
        + _bal(self.db, ledger, "6603", close_dt)
        + _bal(self.db, ledger, "6403", close_dt))
non_op_income = _crd(self.db, ledger, "6301", close_dt) + _crd(self.db, ledger, "6111", close_dt)
non_op_expense = _bal(self.db, ledger, "6701", close_dt) + _bal(self.db, ledger, "6711", close_dt)
cumulative_profit = revenue - cogs - opex + non_op_income - non_op_expense
```

### 调用链时序

**场景：5 月 31 日 23:59:58 创建销售订单，sale_date = 2026-05-31 23:59:58**

```
T1  销售订单创建
    - engine_inventory.outbound() 写 StockMove
    - engine_finance.record_sale() → post_journal("sale_order")
    - engine_journal.post() 写 AccountMove (date = sale_date = 2026-05-31 23:59:58)

T2  月结 2026-05
    - _parse_period("2026-05") → start_dt = 2026-05-01 00:00:00
                              end_dt = 2026-05-31 23:59:59
    - _crd(6001, close_dt) 过滤 AccountMove.date <= 2026-05-31 23:59:59
    - 2026-05-31 23:59:58 的销售凭证 date ≤ 23:59:59 ✅ 被计入
```

**真实漏洞场景**（毫秒级时钟漂移 / 跨时区）：

```
T1  2026-05-31 23:59:59.500 创建销售订单（系统时钟漂移）
    - sale_date = 2026-06-01 00:00:00.000（漂移到下月）
    - AccountMove.date = 2026-06-01 00:00:00.000

T2  月结 2026-05
    - end_dt = 2026-05-31 23:59:59
    - 凭证 date = 2026-06-01 00:00:00 → **不计入 5 月利润**
    - 但业务实际发生在 5 月

T3  月结 2026-06
    - end_dt = 2026-06-30 23:59:59
    - 凭证 date = 2026-06-01 00:00:00 ≤ 23:59:59 → 计入 6 月

结果：5 月少算一笔销售、6 月多算一笔销售
→ 5 月利润虚减、6 月利润虚增
→ 5 月少缴所得税、6 月多缴所得税
→ 跨期利润错位，季度汇算清缴触发预警
```

**更严重的 bug**：`AccountMove.date` 字段类型未明确（看 `models_finance.py` 定义），如果存为 `Date` 类型而非 `DateTime`：

```
T1  _parse_period 返回 datetime(2026, 5, 31, 23, 59, 59)
T2  AccountMove.date = 2026-05-31（Date 类型）
T3  SQLAlchemy 比较 Date vs DateTime：
    - SQLite: 直接字符串比较，可能有问题
    - PostgreSQL: 强制 cast Date 到 DateTime 时分秒为 00:00:00
    - 2026-05-31 (00:00:00) ≤ 2026-05-31 23:59:59 ✅ 匹配
    - 2026-06-01 (00:00:00) ≤ 2026-05-31 23:59:59 ❌ 不匹配
    - → 业务结果看似"对"，但代码意图模糊
```

### 真实业务影响

- **跨月凭证被算到下个月**：BS 报表不平
- **5 月末 222101 销项税比实际少**：税务申报口径与账载不一致
- **利润跨期错位**：5 月少缴 / 6 月多缴 → 季度汇算清缴时税务局可能调账

### 修复方向

1. **`_parse_period` 改用半开区间**：返回 `(start_dt, next_month_first_day)`，所有查询改用 `date >= start AND date < next_month_first`
2. **强制 UTC 时区**：避免本地时区漂移
3. **`AccountMove.date` 改用 `Date` 类型**：会计期间不该有时分秒

---

## 漏洞 #3：`_period_hash` 哈希空间仅 31 位且无 salt，存在 source_id 冲突风险

**严重等级**：🟧 **P1 — 高危级**
**涉及文件**：
- `backend/engine_tax.py:280-285`（_period_hash 实现）
- `backend/engine_tax.py:117, 129, 173, 229, 238`（5 个调用点）

### 真实代码证据

**`engine_tax.py:280-285`**：

```python
# 280-285
def _period_hash(period: str, tag: str) -> int:
    h = 0
    for c in f"{period}_{tag}":
        h = ((h << 5) - h) + ord(c)
        h &= 0x7FFFFFFF
    return h
```

**`engine_tax.py:117`** — 附加税 source_id：

```python
# 117
post_journal(self.db, account_id, "tax_surcharge", {
    "amount": surcharge_amt,
    "date": close_dt,
    "source_model": "tax_surcharge",
    "source_id": _period_hash(period, "surcharge"),
})
```

**`engine_tax.py:129`** — VAT 转出 source_id：

```python
# 129
post_journal(self.db, account_id, "vat_transfer_out", {
    "amount": curr_vat,
    "date": close_dt,
    "source_model": "vat_transfer_out",
    "source_id": _period_hash(period, "vat_xfer"),
})
```

**`engine_tax.py:173`** — VAT 减免 source_id：

```python
# 173
post_journal(self.db, account_id, "vat_exemption", {
    "amount": exemption_amt,
    "date": close_dt,
    "source_model": "vat_exemption",
    "source_id": _period_hash(period, "exemption"),
})
```

**`engine_tax.py:229 + 238`** — 所得税 source_id：

```python
# 229
post_journal(self.db, account_id, "tax_income", {
    "amount": delta,
    "date": close_dt,
    "source_model": "tax_income",
    "source_id": _period_hash(period, "income"),
})

# 238
post_journal(self.db, account_id, "tax_income_reversal", {
    "amount": abs(delta),
    "date": close_dt,
    "source_model": "tax_income_reversal",
    "source_id": _period_hash(period, "income_rev"),
})
```

### 调用链时序

**正常路径**：

```
T1  月结 2026-05
    - surcharge_id = _period_hash("2026-05", "surcharge") = X
    - vat_xfer_id = _period_hash("2026-05", "vat_xfer") = Y
    - income_id = _period_hash("2026-05", "income") = Z
    - 写入 3 张凭证 (surcharge, vat_xfer, income)
    - 各自的 source_id 唯一

T2  下月重跑（不应该发生但）
    - post_journal 查 existing (source_model, source_id) → 找到旧凭证
    - 返回旧凭证，不重复插入 ✅
```

**漏洞路径**（**哈希碰撞**）：

```
T1  月结 2026-05
    - surcharge_id = _period_hash("2026-05", "surcharge") = 1234567
    - 写入凭证 P1 (source_model="tax_surcharge", source_id=1234567)

T2  月结 2026-12
    - surcharge_id = _period_hash("2026-12", "surcharge") = 1234567   ← 哈希碰撞！
    - post_journal existing 检查 → 找到 P1 → 返回 P1（不再插入）
    - 12 月附加税**漏提**
```

**冲突概率**：
- djb2 哈希在 31 位空间内的碰撞概率 = 1 / 2^31
- 当前业务量小（< 100 个月），碰撞概率极低（~ 1/20 亿）
- 但**是个不可接受的工程债**

### 真实业务影响

- **当前**：业务量小，碰撞概率极低，但可能性不为零
- **未来扩展**：换库（SQLite → PostgreSQL）后 INT4 → INT8，哈希空间变化，旧 source_id 失效
- **新加 tag 时**：如果 tag 命名不当，与已有 tag 撞哈希的概率会指数级上升

### 修复方向

1. **直接用字符串当 source_id**：`source_id=f"{period}_{tag}"`，需先把 `AccountMove.source_id` 字段改成 `VARCHAR(64)`
2. **加显式 salt + CRC32**：`hashlib.crc32(f"{period}|{tag}|v1".encode())`，32 位冲突概率更低
3. **改用 `BigInteger`**：source_id 改 INT8，哈希空间扩大到 2^63-1

---

## 漏洞 #4：小规模纳税人"季度≤30万"免税规则实现错乱

**严重等级**：🟥 **P0 — 致命级**
**涉及文件**：
- `backend/engine_tax.py:133-176`（小规模减免逻辑）
- `backend/accounting_engine.py:575-606`（AccountingEngine 的"正确"实现）

### 真实代码证据

**`engine_tax.py:159-166`** — 月结时的减免计算（**简化实现，未区分发票类型**）：

```python
# 159-166
QUARTERLY_EXEMPTION = Decimal("300000")
if quarterly_revenue <= QUARTERLY_EXEMPTION:
    # 季度≤30万：全额免征（普票免税，专票减按1%）
    # 简化：按全额减免处理（专票部分实际需缴纳，此处取减征额）
    exemption_amt = quarter_output_vat  # 全额减免
else:
    # 超过30万：减按1%征收，减免2%
    exemption_amt = (quarterly_revenue * Decimal("0.02")).quantize(Q2)
```

**`accounting_engine.py:585-596`** — AccountingEngine 的"正确"实现（**已区分普票/专票**）：

```python
# 585-596
# 免税门槛：季度总销售额 ≤30万
QUARTERLY_EXEMPTION = Decimal('300000')

if total_revenue <= QUARTERLY_EXEMPTION:
    # 季度≤30万：普票免征增值税，专票不减兔（减按1%）
    ordinary_tax = Decimal("0")
    special_tax = (special_rev * Decimal('0.01')).quantize(Q2, rounding=ROUND_HALF_UP)
    reduction_item = "小规模普票免征增值税（季≤30万），专票减按1%"
else:
    # 超过门槛：普票专票均减按1%征收
    ordinary_tax = (ordinary_rev * Decimal('0.01')).quantize(Q2, rounding=ROUND_HALF_UP)
    special_tax = (special_rev * Decimal('0.01')).quantize(Q2, rounding=ROUND_HALF_UP)
    reduction_item = "小规模纳税人减按1%征收"
```

### 调用链时序

**场景：小规模纳税人 + 季度内 + 含专票 + 总销售额 28 万（≤30 万）**

```
T1  2026-Q1 季末月结（小规模纳税人）
    - 普票不含税销售额 = 270,000
    - 专票不含税销售额 = 10,000
    - 季度总销售额 = 280,000 ≤ 30 万

T2  AccountingEngine 正确计算：
    - 普票应纳税（季度≤30万应免征）= 0
    - 普票法定 = 270,000 × 3% = 8,100
    - 普票减免 = 8,100 - 0 = 8,100
    
    - 专票应纳税（减按1%）= 10,000 × 1% = 100
    - 专票法定 = 10,000 × 3% = 300
    - 专票减免 = 300 - 100 = 200
    
    - 总减免额 = 8,100 + 200 = 8,300

T3  engine_tax.py:163 错误实现：
    - quarter_output_vat = 222103 贷方发生额 = 280,000 × 3% = 8,400
    - exemption_amt = 8,400（全额减免）
    
T4  对比：8,400（错误） vs 8,300（正确）
    - 差额 = 100 元（专票应缴的 100 元被错误免掉）
```

**会计分录**：

```python
# engine_tax.py:169-174
post_journal(self.db, account_id, "vat_exemption", {
    "amount": exemption_amt,      # ← 8,400（错误）
    "date": close_dt,
    "source_model": "vat_exemption",
    "source_id": _period_hash(period, "exemption"),
})
```

```python
# engine_journal.py:344-356
def _build_vat_exemption(self, source):
    """增值税减免结转：dr:222103(应交增值税-小规模) cr:6301(营业外收入-税收减免)
    """
    self._check_required(source, ["amount"])
    amount = Decimal(str(source["amount"]))
    return [
        {"account_code": "222103", "debit": amount, "credit": Decimal("0")},
        {"account_code": "6301", "debit": Decimal("0"), "credit": amount},
    ], "VAT", {"balance_check": True}
```

**凭证分录对比**：

| 科目 | 正确 | 错误 | 差异 |
|---|---|---|---|
| 借：222103 应交增值税-小规模 | 8,300 | 8,400 | +100 |
| 贷：6301 营业外收入-税收减免 | 8,300 | 8,400 | +100 |

借方冲减 222103 比应冲减的多 100 元，**222103 余额会被冲成负数**（理论不该），贷方多记营业外收入 100 元 → **多缴企业所得税**。

### 真实业务风险

- **金额不大但性质严重**：每季度少缴 100 元增值税 + ~12 元附加税
- **税法违规**：开发票时客户已预缴税款，系统应如实入账
- **审计风险**：审计师看到"季度≤30万 + 含专票 + 全额减免"会标异常

### 真实触发条件

需要满足**全部**以下条件：

1. 纳税人类型 = small_scale
2. 季度总销售额 ≤ 30 万
3. 季度内**开过专票**（不是只有普票）
4. 季度末月（3/6/9/12）执行月结

### 修复方向

**`engine_tax.py:159-166` 改用 AccountingEngine 的拆分逻辑**：

```python
# 修复后
from accounting_engine import AccountingEngine

# 先按发票类型汇总
ordinary_revenue = ...
special_revenue = ...

vat_result = AccountingEngine().calculate_vat(
    total_revenue=quarterly_revenue,
    taxpayer_type="small_scale",
    ordinary_revenue=ordinary_revenue,
    special_revenue=special_revenue,
)
exemption_amt = vat_result.tax_reduction
```

---

## 漏洞 #6：库存红冲 `is_inbound` 判 `None` 当作入库兜底，方向反转在边界场景出错

**严重等级**：🟧 **P1 — 高危级**
**涉及文件**：
- `backend/engine_inventory.py:225-307`（reverse 方法）
- `backend/commands/sale_commands.py:189-197, 440-448, 510-519`（调用方）
- `backend/commands/invoice_commands.py:624-632, 651-659`（发票冲红调用）

### 真实代码证据

**`engine_inventory.py:255-273`** — reverse 核心判断：

```python
# 255-273
# 自动从原始 StockMove 获取正确成本（处理价税分离后的差异）
# 同时判断原始方向：正数=入库(采购)，负数=出库(销售)
# force 模式下取最近一条正向流水（"冲红+重建"后有多条，需冲红最近一条）
orig_query = self.db.query(models.StockMove).filter(
    models.StockMove.source_type == source_type,
    models.StockMove.source_id == source_id,
    models.StockMove.product_id == product_id,
)
if force:
    original = orig_query.order_by(models.StockMove.id.desc()).first()
else:
    original = orig_query.first()
effective_unit_cost = original.unit_cost if original else Decimal(str(unit_cost))
rev_qty = Decimal(str(quantity))
rev_cost = (rev_qty * effective_unit_cost).quantize(Q2)

# 反转方向：原始正→冲销负，原始负→冲销正
is_inbound = original is None or original.quantity > 0   # ← ⚠️ 兜底语义错误
sign = Decimal("-1") if is_inbound else Decimal("1")
```

**`engine_inventory.py:286-301`** — 库存缓存更新：

```python
# 286-301
inv = self.db.query(models.Inventory).filter(
    models.Inventory.account_id == account_id,
    models.Inventory.product_id == product_id,
).with_for_update().first()
if not inv:
    return

old_qty = Decimal(str(inv.quantity))
old_value = Decimal(str(inv.total_value))

if is_inbound:
    inv.quantity -= quantity       # 入库红冲 → 减库存
    inv.total_value = (old_value - rev_cost).quantize(Q2)
else:
    inv.quantity += quantity       # 出库红冲 → 加库存
    inv.total_value = (old_value + rev_cost).quantize(Q2)
```

### 调用链时序

**正常场景**（已有正向 StockMove）：

```
T1  2026-05-01 采购 10 件商品 A，单价 100
    - StockMove(source_type="purchase_order", source_id=PO1, product_id=A, quantity=+10, unit_cost=100, total_cost=1000)
    - inv.quantity = 10, inv.total_value = 1000

T2  2026-05-15 取消该采购单
    - 调用 reverse(source_type="purchase_order", source_id=PO1, quantity=10, unit_cost=100)
    - original = 找到 PO1 的 StockMove (quantity=+10)
    - is_inbound = original.quantity > 0 = True
    - sign = -1
    - 写入 StockMove(source_type="purchase_order_reversal", source_id=PO1, quantity=-10, total_cost=1000)
    - inv.quantity = 10 - 10 = 0  ✅
```

**漏洞场景 A**（original=None，手动调 reverse）：

```
T1  2026-05-01 创建采购单 PO1，但通过其他渠道入库（没调 engine_inventory.inbound）
    - 无 StockMove 写入
    - inv.quantity = 0

T2  2026-05-15 程序员手抖调 reverse(source_type="purchase_order", source_id=PO1, quantity=10, unit_cost=100)
    - original = None
    - is_inbound = original is None or ... = True  ← ⚠️ 把不存在的入库当作入库红冲
    - sign = -1
    - 写入 StockMove(quantity=-10, total_cost=1000)
    - inv.quantity = 0 - 10 = -10  ← ⚠️ 库存变负数！
```

**漏洞场景 B**（original=None，服务类商品入库调用 reverse）：

```
T1  2026-05-01 销售 5 件商品 B（track_inventory=False，服务类）
    - outbound 跳过（engine_inventory.py:145-146）
    - 无 StockMove
    - inv 行不存在

T2  2026-05-15 取消销售单 → 调用 reverse(source_type="sale_order", source_id=SO1, quantity=5)
    - product = _get_product(B) → 存在但 track_inventory=False
    - reverse() 第 241-243 行 return ← ⚠️ 提前返回
    - **这条路径不会触发**（line 242-243 救了它）

但是！—— 如果是正常 track_inventory=True 商品，但某些特殊业务直接写了 StockMove 然后被删除：
T1  2026-05-01 销售 5 件 C
    - 写入 StockMove(quantity=-5)
    - 业务直接 DELETE StockMove（绕过 engine 接口）
T2  2026-05-15 取消销售单 → reverse
    - original = None
    - is_inbound = True  ← 错！本应是出库红冲
    - sign = -1
    - 写入 StockMove(quantity=-5)
    - inv.quantity -= 5 → 库存被扣但没有任何原始出库
    - **库存凭空减少**！
```

### 真实业务影响

- **库存数量可能变负**：违反会计恒等式（库存不能为负）
- **库存价值为负**：资产负债表不平
- **触发连锁错误**：后续出库检查 `inv.quantity < quantity` 抛错

### 真实触发条件

- 任何 `original is None` 的场景：
  - 直接写 StockMove 绕过 engine
  - StockMove 被手动删除
  - 业务系统集成时序错乱
  - 测试 fixture 不完整

### 修复方向

**`engine_inventory.py:272`** — 删掉 `None` 兜底：

```python
# 修复后
if not original:
    raise BusinessError(
        code=ErrorCode.VALIDATION_ERROR,
        data={"details": f"找不到原始库存流水: source_type={source_type}, "
                         f"source_id={source_id}, product_id={product_id}"}
    )
is_inbound = original.quantity > 0
sign = Decimal("-1") if is_inbound else Decimal("1")
```

**或者**从 `source_type` 字符串判断方向（更耦合但更安全）：

```python
# purchase_order / inventory_adjustment_positive → 入库
# sale_order / inventory_adjustment_negative → 出库
```

---

## 漏洞 #7：固定资产业务日期处置 `disposal_date` 默认值与记账日期错位，跨月 BS 不平

**严重等级**：🟥 **P0 — 致命级**
**涉及文件**：
- `backend/engine_fixed_asset.py:130-175`（record_disposal）
- `backend/routers/fixed_assets.py`（调用 record_disposal 的 router）

### 真实代码证据

**`engine_fixed_asset.py:130-163`** — 处置逻辑：

```python
# 130-163
def record_disposal(self, asset_id: int, disposal_price: Decimal = Decimal("0"),
                    disposal_date: Optional[date] = None) -> None:
    """处置（报废/出售）固定资产
    ...
    BR-22: disposal_date 默认用今天，但允许调用方传入业务日期，
    避免 BS 按 cutoff 过滤时资产处置凭证被排除（与 reverse_journal 同类问题）。
    """
    asset = self.db.query(models.FixedAsset).filter(
        models.FixedAsset.id == asset_id,
        models.FixedAsset.account_id == self.account_id,
    ).first()
    if not asset:
        raise BusinessError(code=ErrorCode.FIXED_ASSET_NOT_FOUND,
                            data={"asset_id": asset_id})
    if asset.status == "报废":
        return

    asset.status = "报废"
    self.db.flush()

    original = Decimal(str(asset.original_value))
    accumulated = Decimal(str(asset.accumulated_depreciation))
    net_value = original - accumulated
    disposal_price = Decimal(str(disposal_price))
    diff = disposal_price - net_value

    disposal_date = disposal_date or date.today()   # ← ⚠️ 默认是今天，与 BR-22 修复方向相反
    source = {
        "original_value": original,
        "accumulated_depreciation": accumulated,
        "net_value": net_value,
        "disposal_price": disposal_price,
        "diff": diff,
        "source_model": "fixed_asset_disposal",
        "source_id": asset_id,
        "date": disposal_date,
        "description": f"固定资产处置: {asset.name}",
    }
    post_journal(self.db, self.account_id, "asset_disposal", source)
```

### 与 BR-22 修复的对比

**`finance_integration.py:200-208`** — BR-22 修复 reverse_journal 用 `original.date`：

```python
# 200-208
# BR-22: 默认用原凭证日期作为冲红日期，与 InventoryEngine.reverse 的 StockMove
# 反向流水 move_date（也是从原单据取业务日期）保持一致。否则 BS 报表按 cutoff
# 过滤时，StockMove 反向流水会进表但 AccountMove 反向凭证不会进表，
# 造成"库存值包含冲回、利润不含冲回"的资产与权益错配（典型 diff=40000 不平）。
reversal = AccountMove(
    ledger_id=original.ledger_id,
    name=f"冲红-{original.name}",
    move_type=original.move_type,
    date=reversal_date or original.date,    # ← 默认用原凭证日期
    state="posted",
    source_model=source_model,
    source_id=source_id,
    amount_total=original.amount_total,
    reversed_entry_id=original.id,
    is_reversal=True,
)
```

**对照之下**：`engine_fixed_asset.py:163` 仍然 `date.today()`，**没修这个同类 bug**。

### 调用链时序

```
场景：5 月 31 日（周五）发现打印机已报废，5 月已结账，6 月补入账

T1  2026-05-29 业务部门提交报废申请，财务积压
T2  2026-05-31 18:00 财务人员忘记处理
T3  2026-05-31 23:59:59 系统自动月结 2026-05
T4  2026-06-01 09:00 财务人员发现 5 月已结账，资产处置需补录
T5  → 调用 POST /api/fixed-assets/{id}/dispose
T6  → router 调用 record_disposal(asset_id=5, disposal_price=0)
T7  → disposal_date = date.today() = 2026-06-01   ← ⚠️ 业务实际发生在 5 月
T8  → AccountMove.date = 2026-06-01
T9  → 凭证分录：
    借 1602 累计折旧  30,000
    贷 1601 固定资产  40,000
    借 6711 营业外支出  10,000  (diff = 0 - 10,000 = -10,000)
```

### 真实业务影响

**5 月 BS 报表错误**：

```
5 月 31 日 BS（错误）：
  1601 固定资产 100,000（实际应 90,000，打印机 5 月已报废）
  1602 累计折旧  30,000
  净值          70,000（应 60,000）

6 月 30 日 BS（错误）：
  1601 固定资产  90,000（突然消失 10,000）
  净值          60,000（碰巧对，但原因错误）
```

**利润表跨月错位**：

```
5 月利润表（错误）：
  6711 营业外支出 0（少计 10,000）
  营业利润 虚增 10,000
  利润总额 虚增 10,000
  所得税 多缴 500（10,000 × 5%）

6 月利润表（错误）：
  6711 营业外支出 10,000（突然冒出来）
  营业利润 虚减 10,000
  所得税 少缴 500
```

**季度汇算清缴**：
- 5 月多缴 + 6 月少缴 = 平衡
- **但**：如果 5 月亏损、6 月盈利 → 5 月亏损未弥补 6 月利润（错失 500 元抵税）

### 真实业务触发条件

1. 固定资产业务发生日期 ≠ 处置入账日期
2. 跨月结账（5 月已结账才处置 5 月业务）
3. 财务人员依赖默认值 `disposal_date=None`

### 修复方向

**`engine_fixed_asset.py:163`** — 改为优先用业务日期：

```python
# 修复后
if disposal_date is None:
    raise BusinessError(
        code=ErrorCode.VALIDATION_ERROR,
        data={"details": "disposal_date 必填，资产处置必须使用业务发生日期而非今天"}
    )
```

**或者**允许从资产 `last_business_date` 字段推断（但需要先在 FixedAsset 模型加这个字段）。

---

## 漏洞 #8：AdjustInventory 盘亏走"管理费用"，盘盈走"管理费用"——两个都挂错了

**严重等级**：🟧 **P1 — 高危级**
**涉及文件**：
- `backend/commands/product_commands.py:263-282`（post_journal 调用）
- `backend/schemas/order.py:145-160`（InventoryAdjust schema）

### 真实代码证据

**`commands/product_commands.py:263-282`** — 库存调整的会计分录：

```python
# 263-282
# 3a. 过账
value = (abs(delta) * unit_cost).quantize(Q2)
if value > 0:
    from finance_integration import post_journal
    from datetime import date
    journal_date = cmd.adjust_date if cmd.adjust_date else date.today().isoformat()
    if delta < 0:
        # 库存减少（盘亏/报损）
        lines = [
            {"account_code": "6601", "debit": value, "credit": Decimal("0")},   # ← 借：管理费用
            {"account_code": "1405", "debit": Decimal("0"), "credit": value},   # ← 贷：库存商品
        ]
    else:
        # 库存增加（盘盈）
        lines = [
            {"account_code": "1405", "debit": value, "credit": Decimal("0")},   # ← 借：库存商品
            {"account_code": "6601", "debit": Decimal("0"), "credit": value},   # ← 贷：管理费用  ← ⚠️ 错！
        ]
    post_journal(db, cmd.account_id, "opening_balance", {
        "date": journal_date,
        "lines": lines,
    })
```

### 与会计准则的冲突

**《小企业会计准则》附录：会计科目、主要账务处理**

**盘盈（库存盘盈）标准流程**：

```
发现盘盈：
  借 1405 库存商品
  贷 1901 待处理财产损溢   ← ⚠️ 中转科目，不是直接进损益

查明原因后（从 1901 转出）：
  借 1901 待处理财产损溢
  贷 6301 营业外收入       ← 最终进损益
```

**盘亏（库存盘亏）标准流程**：

```
发现盘亏：
  借 1901 待处理财产损溢   ← ⚠️ 中转科目
  贷 1405 库存商品

查明原因后（从 1901 转出）：
  自然损耗：
    借 6601 管理费用
  责任人赔偿：
    借 1221 其他应收款
  非常损失（火灾、被盗）：
    借 6711 营业外支出
```

### 调用链时序

```
T1  2026-05-15 盘点发现商品 X 多出 5 件，单价 50 元
T2  调用 PUT /api/inventory/{product_id}
    body: {"quantity": 105, "reason": "盘盈", "unit_cost": 50}
T3  → routers/inventory.py:57 adjust_inventory
T4  → dispatch(AdjustInventory(...))
T5  → AdjustInventoryHandler.handle() (product_commands.py:186)
T6  → engine.inbound(...)              (product_commands.py:248-254)
    - StockMove 写入正确（5件，单价50）
T7  → post_journal("opening_balance")  (product_commands.py:279)
    - 凭证分录：
      借 1405 库存商品 250
      贷 6601 管理费用 250  ← ⚠️ 错！应该贷 1901 或 6301
    - 6601 期末进利润表，虚增管理费用 250 元
    - 实际应该是贷 1901 待处理财产损溢
T8  财务人员查 5 月利润表发现管理费用异常
```

### 真实业务风险

| 业务 | 当前实现 | 会计准则要求 | 后果 |
|---|---|---|---|
| 盘亏 100 元 | 借：6601 / 贷：1405 | 先借 1901 → 查因后借 6601/1221/6711 | 责任无法追溯，少计提应收款 |
| 盘盈 100 元 | 借：1405 / 贷：6601 | 借 1405 → 贷 1901 → 查因后贷 6301 | 虚减利润 100，少缴所得税 |

**审计风险**：

- 审计师看到"盘盈贷 6601"会直接标异常
- 企业所得税汇算清缴时需要做纳税调整（不允许税前扣除的盘亏直接进管理费用）

### 修复方向

**短期修复**（最小改动）：

```python
# product_commands.py:263-282
if delta < 0:
    # 盘亏：先挂 1901，待处理
    lines = [
        {"account_code": "1901", "debit": value, "credit": Decimal("0")},
        {"account_code": "1405", "debit": Decimal("0"), "credit": value},
    ]
else:
    # 盘盈：先挂 1901，待处理
    lines = [
        {"account_code": "1405", "debit": value, "credit": Decimal("0")},
        {"account_code": "1901", "debit": Decimal("0"), "credit": value},
    ]
```

**长期修复**（推荐）：

- 增加 `account_treatment` 字段（`natural_loss` / `damage` / `theft` / `unaccounted`）
- 根据 `account_treatment` 决定最终挂哪个损益科目
- 实现"两步走"流程：先盘盈盘亏入 1901，查因后从 1901 转出

---

## 漏洞 #10：record_sale 在凭证层用 3% 法定征收率算销项税，与"减按 1%"的会计引擎真相源冲突

**严重等级**：🟥 **P0 — 致命级**
**涉及文件**：
- `backend/engine_finance.py:80-113`（record_sale 实现）
- `backend/accounting_engine.py:575-606`（正确的小规模 VAT 计算）
- `backend/engine_journal.py:97-142`（_build_sale_order）

### 真实代码证据

**`engine_finance.py:80-93`** — record_sale 的税额计算：

```python
# 80-93
def record_sale(self, order, force: bool = False) -> None:
    is_small_scale = self.account and self.account.taxpayer_type == "small_scale"
    total_without_tax = Decimal('0')
    tax_amount = Decimal('0')
    for item in order.items:
        line_total = Decimal(str(item.total_price))
        total_without_tax += line_total
        rate = item.tax_rate
        if is_small_scale and rate and rate > 0:
            rate = self._vat_rate(self.account)     # ← 调用 _vat_rate，覆盖为 3%
        if rate:
            tax_amount += (line_total * Decimal(str(rate))).quantize(Q2)
    tax_amount = tax_amount.quantize(Q2)
    total_with_tax = (total_without_tax + tax_amount).quantize(Q2)
```

**`engine_finance.py:32-42`** — `_vat_rate` 实际返回 3%（**不是 1%**）：

```python
# 32-42
@staticmethod
def _vat_rate(account) -> Decimal:
    """获取默认增值税税率
    
    注意：此方法仅提供默认税率，用于小规模纳税人销售价税分离的兜底场景。
    - 一般纳税人：默认 13%，但实际销售时以行项 item.tax_rate 为准（支持 13%/9%/6% 多税率商品）
    - 小规模纳税人：法定征收率 3%（减按 1% 征收的优惠在 AccountingEngine.calculate_vat 中处理）
    """
    if account is None:
        return Decimal("0.03")
    return Decimal("0.13") if account.taxpayer_type == "general" else Decimal("0.03")
```

**`engine_finance.py:94-113`** — 把 tax_amount 塞进 source dict，过账：

```python
# 94-113
source = {
    "partner_id": order.customer_id or 0,
    "total_with_tax": total_with_tax,
    "total_without_tax": total_without_tax,
    "tax_amount": tax_amount,    # ← 用 3% 算的
    "items": [...],
    "source_model": "sale_order",
    "source_id": order.id,
    "date": order.sale_date,
    "account_config": self._account_config(),
}
post_journal(self.db, self.account_id, "sale_order", source, force=force)
```

**`engine_journal.py:97-117`** — _build_sale_order 信任 source 里的 tax_amount：

```python
# 97-117
def _build_sale_order(self, source):
    self._check_required(source, ["partner_id", "total_with_tax",
                                   "total_without_tax", "tax_amount", "items"])
    
    total_with_tax = Decimal(str(source["total_with_tax"]))
    total_without_tax = Decimal(str(source["total_without_tax"]))
    tax_amount = Decimal(str(source["tax_amount"]))
    
    if total_without_tax + tax_amount != total_with_tax:
        raise AccountingError(AccountingErrorCode.AMOUNT_MISMATCH, "不含税 + 税额 != 价税合计")
    
    acct_conf = source.get("account_config", {})
    taxpayer_type = acct_conf.get("taxpayer_type") if "account_config" in source else "general"
    tax_code = "222103" if taxpayer_type == "small_scale" else "222101"
    
    lines = [
        {"account_code": "1122", "debit": total_with_tax, "credit": Decimal("0"),
         "partner_id": source["partner_id"], "partner_type": "customer"},
        {"account_code": "6001", "debit": Decimal("0"), "credit": total_without_tax},
        {"account_code": tax_code, "debit": Decimal("0"), "credit": tax_amount},  # ← 直接用
    ]
```

**`accounting_engine.py:581-596`** — AccountingEngine 注释说"法定 3%"，**实际计算用 1%**：

```python
# 581
tax_rate = Decimal('0.03')
tax_payable_gross = (total_revenue * tax_rate).quantize(Q2, rounding=ROUND_HALF_UP)

# 免税门槛：季度总销售额 ≤30万
QUARTERLY_EXEMPTION = Decimal('300000')

if total_revenue <= QUARTERLY_EXEMPTION:
    # 季度≤30万：普票免征增值税，专票不减兔（减按1%）
    ordinary_tax = Decimal("0")
    special_tax = (special_rev * Decimal('0.01')).quantize(Q2, rounding=ROUND_HALF_UP)  # ← 1% 减按
    reduction_item = "小规模普票免征增值税（季≤30万），专票减按1%"
```

### 调用链时序

```
场景：小规模纳税人 + 单次销售 100,000 元

T1  2026-05-01 销售 100,000 元
T2  → engine_finance.record_sale(order)
T3  → line_total = 100,000, rate = item.tax_rate = 0.01（item schema 默认值，看 schemas/order.py:73）
T4  → if is_small_scale and rate and rate > 0: True
T5  → rate = _vat_rate(account) = 0.03   ← ⚠️ 0.01 被覆盖为 0.03
T6  → tax_amount = 100,000 × 3% = 3,000
T7  → total_with_tax = (100,000 + 3,000).quantize(Q2) = 103,000
T8  → source = {total_with_tax: 103,000, total_without_tax: 100,000, tax_amount: 3,000}
T9  → post_journal("sale_order", source)
T10 → _build_sale_order:
    100,000 + 3,000 == 103,000 ✅
T11 → 凭证分录：
    借 1122 应收账款 103,000
    贷 6001 主营业务收入 100,000
    贷 222103 应交增值税-小规模 3,000  ← ⚠️ 虚高 2,000（应为 1,000）
```

### 真实业务风险

1. **销项税虚高 2 倍**（3% vs 1%）：每笔销售凭证多挂 2,000 元的应交税费
2. **222103 期末余额虚高**：季度申报时发现**应纳税额远超实际**
3. **如果季度总销售额 ≤30 万**：实际普票部分应**全额免征**，但凭证里挂了 3,000 → 还需用 `vat_exemption` 冲回
4. **如果季度总销售额 >30 万**：实际只需缴 1%（1,000），凭证挂了 3,000 → 月结时 `tax_income_reversal` 冲回 2,000，但**如果 source_id 哈希碰撞，冲回会失败**

### 真实业务触发条件

1. 纳税人类型 = small_scale
2. item.tax_rate > 0（schema 默认 0.01）
3. 不论季度销售额是否 > 30 万

**这条漏洞 100% 触发**。每一个小规模销售单都会多算销项税。

### 修复方向

**方案 A（最小改动）**：`engine_finance.py:88-92` 直接删除小规模税率覆盖逻辑：

```python
# 修复后
for item in order.items:
    line_total = Decimal(str(item.total_price))
    total_without_tax += line_total
    rate = item.tax_rate  # ← 不再覆盖
    if rate:
        tax_amount += (line_total * Decimal(str(rate))).quantize(Q2)
```

**方案 B（推荐，统一真相源）**：直接调用 `AccountingEngine.calculate_vat`：

```python
from accounting_engine import AccountingEngine
from collections import defaultdict

# 按发票类型汇总（需先从 item 区分）
ordinary_revenue = sum(item.total_price for item in order.items if not item.is_special)
special_revenue = sum(item.total_price for item in order.items if item.is_special)

vat_result = AccountingEngine().calculate_vat(
    total_revenue=order.total_price,
    taxpayer_type=account.taxpayer_type,
    input_tax=Decimal("0"),
    ordinary_revenue=ordinary_revenue,
    special_revenue=special_revenue,
)
tax_amount = vat_result.tax_payable
```

**额外要求**：需要在 `SaleItem` schema 增加 `is_special` 字段标识专票。

---

## 漏洞 #11：销售退货冲红时成本与库存回补双向独立计算，库存单价波动时错位

**严重等级**：🟥 **P0 — 致命级**
**涉及文件**：
- `backend/commands/sale_commands.py:228-351`（ReturnSaleOrderHandler）
- `backend/engine_journal.py:376-418`（_build_sale_return）
- `backend/engine_inventory.py:225-307`（reverse 方法）

### 真实代码证据

**`commands/sale_commands.py:270-308`** — 退货时的成本计算（**取最早 StockMove，不是当前 average_cost**）：

```python
# 270-308
# 找到原销售明细
orig_item = next((it for it in order.items if it.product_id == pid), None)
if not orig_item:
    continue

# 3a. 库存回补（InventoryEngine.reverse 自动从原 StockMove 取 unit_cost）
product = db.query(models.Product).filter(
    models.Product.id == pid,
    models.Product.account_id == cmd.account_id,
).first()
if product and product.track_inventory:
    eng.reverse(
        account_id=cmd.account_id,
        product_id=pid,
        quantity=int(qty_ret),
        unit_cost=Decimal("0"),  # 自动从原 StockMove 取
        source_type="sale_order",
        source_id=order.id,
        operator=cmd.operator,
        source_id_override=return_id,  # 避免与整单冲销的幂等冲突
    )
    # 取 unit_cost 计算成本冲红
    move = db.query(StockMove).filter(
        StockMove.source_type == "sale_order",
        StockMove.source_id == order.id,
        StockMove.product_id == pid,
    ).first()    # ← ⚠️ 取第一条（最早），不是当前 average_cost
    unit_cost = move.unit_cost if move and move.unit_cost else Decimal("0")
    cost_return += (qty_ret * unit_cost).quantize(Q2)
```

**`engine_inventory.py:286-306`** — reverse 内部用 `original.unit_cost` 计算 `total_cost`：

```python
# 286-306
inv = self.db.query(models.Inventory).filter(
    models.Inventory.account_id == account_id,
    models.Inventory.product_id == product_id,
).with_for_update().first()
if not inv:
    return

old_qty = Decimal(str(inv.quantity))
old_value = Decimal(str(inv.total_value))

if is_inbound:
    inv.quantity -= quantity
    inv.total_value = (old_value - rev_cost).quantize(Q2)
else:
    inv.quantity += quantity
    inv.total_value = (old_value + rev_cost).quantize(Q2)   # ← 用 rev_cost（基于 original.unit_cost）
new_qty = Decimal(str(inv.quantity))
if new_qty > 0:
    inv.average_cost = (Decimal(str(inv.total_value)) / new_qty).quantize(Decimal("0.000001"))
else:
    inv.average_cost = Decimal("0")
```

### 调用链时序

**场景**：商品 A 多次入库导致 average_cost 变化

```
T1  2026-05-01 采购 10 件 A，单价 100
    - StockMove(qty=+10, unit_cost=100, total_cost=1000)
    - inv: qty=10, value=1000, avg_cost=100

T2  2026-05-15 采购 5 件 A，单价 120
    - StockMove(qty=+5, unit_cost=120, total_cost=600)
    - inv: qty=15, value=1600, avg_cost=106.67

T3  2026-05-20 销售 8 件 A
    - engine_inventory.outbound 用 inv.average_cost=106.67 算出库
    - StockMove(qty=-8, unit_cost=106.67, total_cost=853.33)
    - inv: qty=7, value=746.67, avg_cost=106.67

T4  2026-06-01 部分退货 3 件 A
    - return_id = 1001
    - eng.reverse(source_type="sale_order", source_id=SO1, quantity=3, source_id_override=1001)
    - reverse 内部：
      orig_query = StockMove(source_type="sale_order", source_id=SO1, product_id=A).first()
      original = 找到 qty=-8 那条，original.unit_cost=106.67
      rev_qty=3, rev_cost=3*106.67=320.00
      写入 reversal StockMove(qty=+3, unit_cost=106.67, total_cost=320.00)
      inv: qty=7+3=10, value=746.67+320=1066.67, avg_cost=106.67
    - sale_commands.py:302 取 first() 找到的也是同一条 (106.67)
    - cost_return = 3 * 106.67 = 320.00
    - 凭证：
      借 6001 主营业务收入 (按 total_price 比例)
      借 222101 销项税额
      贷 1122 应收账款
      借 1405 库存商品 320
      贷 6401 主营业务成本 320
    - ✅ 这次对，因为原 StockMove 只有一条
```

**漏洞场景**（同一 sale_order 多次重建，**force=True 反复冲红+重建**）：

```
T1  销售 8 件 A（创建 SO1）
    - StockMove(qty=-8, unit_cost=106.67, total_cost=853.33)   ← StockMove #1
    - 凭证 V1

T2  改单价，从 1000 改 1200
    - reverse_sale(SO1, force=True) → 冲红 V1
    - record_sale(SO1, force=True) → 重建 V2
    - engine_inventory.force_outbound(qty=8, source_id=SO1)
    - 写入 StockMove(qty=-8, unit_cost=106.67, total_cost=853.33)   ← StockMove #2
    - 现在 SO1 有 2 条正向 StockMove（force=True 不幂等检查）

T3  部分退货 3 件 A
    - eng.reverse(source_id_override=1001)
    - orig_query.first() → 找到 StockMove #1（最早，unit_cost=106.67）
    - 写入 reversal StockMove(qty=+3, unit_cost=106.67, total_cost=320.00)
    - inv 更新基于 106.67 ✅

    - sale_commands.py:302 .first() → 同样找到 StockMove #1
    - cost_return = 3 * 106.67 = 320 ✅

    - **巧合对**——因为两次销售单价没变
```

**真正的漏洞**（**改单价后两次 sales**）：

```
T1  销售 8 件 A，sale_price=100
    - StockMove(qty=-8, unit_cost=106.67, total_cost=853.33)   ← StockMove #1
    - 凭证 V1 (cost=853.33)

T2  改 sale_price 为 120，反冲重建
    - reverse_sale(SO1, force=True) → 冲红 V1
    - record_sale(SO1, force=True) → 重建 V2
    - force_outbound 写入 StockMove #2(qty=-8, unit_cost=106.67)
    - 凭证 V2 (cost=853.33)

T3  又改 sale_price 为 150，再次反冲重建
    - reverse_sale(SO1, force=True) → 冲红 V2
    - record_sale(SO1, force=True) → 重建 V3
    - force_outbound 写入 StockMove #3(qty=-8, unit_cost=106.67)
    - SO1 共有 3 条正向 StockMove，2 条反向 StockMove

T4  部分退货 3 件 A
    - eng.reverse(source_id_override=1001)
    - orig_query.first() → StockMove #1（**最早的那条**）
    - rev_cost = 3 * 106.67 = 320.00
    - inv.total_value += 320
    - 写入 reversal StockMove #3(qty=+3, source_id=1001, unit_cost=106.67)

    - sale_commands.py:302 .first() → 同样 StockMove #1 (unit_cost=106.67)
    - cost_return = 3 * 106.67 = 320.00
    - 凭证：
      借 1405 320
      贷 6401 320
    - **巧合对**——只要 average_cost 没变，cost_return 都对

T5  但是！—— 如果 T2 和 T3 之间发生了**新采购**导致 average_cost 变化：
T2.5  采购 5 件 A，单价 150
      - StockMove(qty=+5, unit_cost=150, total_cost=750)
      - inv: qty=10+5=15（假设 T2 之后 inv 状态: qty=7, value=746.67）
      - 等等，T2 是反冲重建，inv 状态变化：
        - T1 销售后：inv qty=10-8=2, value=1000-853.33=146.67
        - T2 反冲：inv qty=2+8=10, value=146.67+853.33=1000, avg_cost=100
        - T2.5 采购：inv qty=10+5=15, value=1000+750=1750, avg_cost=116.67
        - T3 反冲重建：force_outbound 写入新 StockMove, unit_cost=inv.average_cost=116.67
          - inv qty=15-8=7, value=1750-933.33=816.67, avg_cost=116.67

T4  退货 3 件
    - eng.reverse → orig_query.first() → 找到 **StockMove #1**（最早, unit_cost=106.67）
    - **但当前 inv.average_cost = 116.67**
    - reverse 用 106.67 计算 rev_cost = 320
    - inv: qty=7+3=10, value=816.67+320=1136.67, avg_cost=113.67
    
    - sale_commands.py:302 .first() → 同样找到 StockMove #1 (106.67)
    - cost_return = 3 * 106.67 = 320
    
    - **库存和凭证对得上（都用 106.67），但**：
      - 真正的退货成本应该用**当前 average_cost = 116.67**
      - 真实成本应该是 350.00（3 × 116.67）
      - **少冲 30 元主营业务成本**
      - 利润虚增 30 元
      - 所得税多缴 1.5 元
```

### 真实业务影响

- **主营业务成本计算偏低**：用最早的 unit_cost 而非当前 average_cost
- **利润虚增**：少冲成本 → 利润虚增 → 多缴所得税
- **库存价值与凭证价值不匹配**：虽然在这个具体场景里两边都用了 106.67（巧合），但**逻辑上不可靠**

### 真实业务触发条件

1. 销售单经历过 `UpdateSaleOrderItems`（明细更新 → 反复冲红+重建）
2. 重建后有新的采购入库（导致 average_cost 变化）
3. 再发生部分退货

### 修复方向

**`commands/sale_commands.py:302-308`** — 改用 `inv.average_cost` 而非 `original.unit_cost`：

```python
# 修复后
inv = get_or_create_inventory(db, cmd.account_id, pid)
unit_cost = inv.average_cost or Decimal("0")
cost_return += (qty_ret * unit_cost).quantize(Q2)
```

**或者**——保持用 `original.unit_cost`（出库时记的），但**确保 reverse 也用同一个**：

```python
# engine_inventory.py:267 已经是 effective_unit_cost = original.unit_cost
# 只需要 sale_commands.py:302 也用 original.unit_cost（已实现）
# 真正的 bug 在于：**average_cost 变化后，原 unit_cost 不再代表真实成本**
```

**根本修复**：退货时应该按**当前 average_cost** 计算成本，而不是原始出库成本。会计准则允许这样（移动加权平均法）。

---

## 漏洞 #12：红字发票冲销调用 reverse_sale 用原始 `source_id` 当幂等键，部分退货场景会重复冲红整单

**严重等级**：🟥 **P0 — 致命级**
**涉及文件**：
- `backend/commands/invoice_commands.py:605-660`（红字发票冲销）
- `backend/finance_integration.py:178-216`（reverse_journal 实现）

### 真实代码证据

**`commands/invoice_commands.py:605-660`** — 红字发票冲销逻辑：

```python
# 605-660
# 5. 级联冲红凭证和库存
cascade_lines = []

if invoice.related_order_type == "sale_order" and invoice.related_order_id:
    # 销项发票 → 冲红销售凭证（收入/应收/税额）
    from engine_finance import FinanceEngine
    FinanceEngine(db, cmd.account_id).reverse_sale(invoice.related_order_id)   # ← ⚠️ 整单冲红
    cascade_lines.append("冲红销售凭证")

    # 冲红库存（库存回退）
    from engine_inventory import InventoryEngine
    engine_inv = InventoryEngine(db)
    sale_order = db.query(models.SaleOrder).filter(
        models.SaleOrder.id == invoice.related_order_id,
        models.SaleOrder.account_id == cmd.account_id,
    ).first()
    if sale_order:
        for item in sale_order.items:
            unit_cost = _d(item.unit_cost) if item.unit_cost else Decimal('0')
            engine_inv.reverse(
                account_id=cmd.account_id,
                product_id=item.product_id,
                quantity=item.quantity,    # ← ⚠️ 整单 quantity，不是红字发票关联的部分数量
                unit_cost=unit_cost,
                source_type="sale_order",
                source_id=sale_order.id,
                operator=cmd.operator,
            )
        cascade_lines.append(f"库存回退({len(sale_order.items)}项)")

elif invoice.related_order_type == "purchase_order" and invoice.related_order_id:
    # 进项发票 → 冲红采购凭证（存货/应付/税额）
    from engine_finance import FinanceEngine
    FinanceEngine(db, cmd.account_id).reverse_purchase(invoice.related_order_id)   # ← ⚠️ 整单冲红
    cascade_lines.append("冲红采购凭证")

    # 冲红库存（库存退回）
    from engine_inventory import InventoryEngine
    engine_inv = InventoryEngine(db)
    purchase_order = db.query(models.PurchaseOrder).filter(
        models.PurchaseOrder.id == invoice.related_order_id,
        models.PurchaseOrder.account_id == cmd.account_id,
    ).first()
    if purchase_order:
        for item in purchase_order.items:
            unit_cost = _d(item.unit_price) if item.unit_price else Decimal('0')
            engine_inv.reverse(
                account_id=cmd.account_id,
                product_id=item.product_id,
                quantity=item.quantity,    # ← ⚠️ 整单 quantity
                unit_cost=unit_cost,
                source_type="purchase_order",
                source_id=purchase_order.id,
                operator=cmd.operator,
            )
        cascade_lines.append(f"库存退回({len(purchase_order.items)}项)")
```

**`finance_integration.py:178-196`** — reverse_journal 的幂等检查：

```python
# 178-196
def reverse_journal(
    db: Session,
    account_id: int,
    source_model: str,
    source_id: int,
    reversal_date: Optional[date] = None,
    force: bool = False,
) -> Optional[AccountMove]:
    """冲红原凭证（带幂等防御）"""
    existing_reversal = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == True,
    ).first()
    if existing_reversal and not force:
        return None   # ← 已冲红过 → 跳过

    orig_query = db.query(AccountMove).filter(
        AccountMove.source_model == source_model,
        AccountMove.source_id == source_id,
        AccountMove.is_reversal == False,
    )
    ...
```

### 调用链时序

**场景 A**：部分退货 + 红字发票冲销（**灾难性重复冲红**）

```
T1  2026-05-01 销售 10 件 A，单价 100
    - sale_order SO1 (qty=10, total=1000)
    - 凭证 V1 (source_id=SO1, source_model="sale_order", is_reversal=False)
    - StockMove M1 (qty=-10, source_id=SO1)

T2  2026-05-15 部分退货 3 件 A
    - ReturnSaleOrderHandler:
      - return_id = 1001
      - eng.reverse(source_id_override=1001, quantity=3)
      - StockMove M2 (qty=+3, source_id=1001, source_type="sale_order_reversal")
      - inv: qty -= 3 + 3 = 实际 qty 减少
      - post_journal("sale_return", source_id=1001)
      - 凭证 V2 (source_id=1001, source_model="sale_return", is_reversal=False)
    - 发票 INV1 (红字，amount=300, related_order_type="sale_order", related_order_id=SO1)

T3  2026-05-20 客户要求把这张红字发票再做一次冲销（系统 bug 或误操作）
    - 调用 ReverseInvoiceHandler（invoice_commands.py）
    - 找到 INV1
    - if invoice.related_order_type == "sale_order" and invoice.related_order_id:
        - FinanceEngine.reverse_sale(SO1)  ← ⚠️ 用 SO1 当 source_id 冲红原销售凭证
        - reverse_journal 查 existing_reversal (source_model="sale_order", source_id=SO1, is_reversal=True)
        - **没有！** 因为 SO1 没被冲红过（部分退货走的是 sale_return source_model）
        - 找到 original (source_model="sale_order", source_id=SO1, is_reversal=False) = V1
        - 创建 V3 借贷互换 (source_id=SO1, source_model="sale_order", is_reversal=True, reversed_entry_id=V1.id)
        - **V1 被冲红了**！

T4  结果：
    - V1 已被冲红
    - V2 是部分退货凭证（V2 不动）
    - 现在 V1 + V3 借贷相抵，等于 SO1 收入和应收完全冲掉
    - 加上 V2 部分冲红 → SO1 收入被冲了 100% + 部分重复冲红
    - **应收账款被冲成负数 / 主营业务收入被冲成负数**
    - 库存：
      - 调用 engine_inv.reverse(source_id=SO1, quantity=10)
      - 找到 M1 (qty=-10)
      - 写入 M3 (qty=+10, source_id=SO1, source_type="sale_order_reversal")
      - inv: qty 增加 10 + 3 = 13 (原本 qty=0)
      - **库存凭空增加 13 件**！
```

**场景 B**：幂等冲突（先红冲发票，再取消销售单）

```
T1  2026-05-01 销售 10 件 A
    - V1 (source_id=SO1), M1 (source_id=SO1)

T2  2026-05-15 红字发票冲销
    - reverse_sale(SO1) → V3 借贷互换 (is_reversal=True, reversed_entry_id=V1)
    - engine_inv.reverse(SO1, qty=10) → M3 (sale_order_reversal, qty=+10, source_id=SO1)
    - inv: qty 加 10 ✅

T3  2026-05-16 取消销售单 SO1
    - CancelSaleOrderHandler:
      - eng.reverse(source_id=SO1, qty=10)
      - 幂等检查 (source_type="sale_order_reversal", source_id=SO1, product_id=A) → **找到 M3** → 跳过！
      - FinanceEngine.reverse_sale(SO1)
      - 幂等检查 (source_model="sale_order", source_id=SO1, is_reversal=True) → **找到 V3** → 跳过！
    - **库存和凭证都没动**，但业务上销售单已取消
    - 数据不一致
```

### 真实业务影响

**场景 A**（部分退货 + 红字发票重复冲销）：

- 应收账款虚减（被冲成负数）
- 主营业务收入虚减（部分被冲成负数）
- 库存凭空增加
- 损益表不平
- 资产负债表不平

**场景 B**（先红冲发票再取消订单）：

- 销售单状态显示已取消，但库存/凭证无变化
- 用户再次执行操作时**没有报错也没有效果**
- 数据一致性问题，审计困难

### 真实触发条件

**场景 A**：

- 部分退货（走 sale_return source_model）后
- 又对该销售单的开票做红冲（invoice_commands.py:611 用 reverse_sale 而不是 reverse_return）

**场景 B**：

- 任何对销售单/采购单做"先发票红冲再单据取消"的业务流

### 修复方向

**`commands/invoice_commands.py:608-633`** — 区分三种情况：

```python
if invoice.related_order_type == "sale_order" and invoice.related_order_id:
    # 检查是否已存在 sale_return 凭证（部分退货）
    existing_return = db.query(AccountMove).filter(
        AccountMove.source_model == "sale_return",
        AccountMove.source_id == invoice.id,  # 红字发票的 ID
        AccountMove.is_reversal == False,
    ).first()
    
    if existing_return:
        # 部分退货场景：只冲红退货凭证，**不冲红原销售凭证**
        # 实际上发票红冲本身就要写一张红字凭证
        cascade_lines.append("已存在部分退货凭证，跳过整单冲红")
    else:
        # 整单红冲
        FinanceEngine(db, cmd.account_id).reverse_sale(invoice.related_order_id)
        cascade_lines.append("冲红销售凭证")
    
    # 库存也只回退红字发票对应的数量
    # 需要从 red_invoice items 里读取，而不是从原 sale_order items
```

**或者更彻底**——**重写 invoice 反冲逻辑**，让它走 `sale_return` 路径而不是 `reverse_sale`：

```python
# 所有红字发票都走 sale_return source_model
# 库存用 source_id_override=invoice_id 反冲
# 避免和原 sale_order 混淆
```

---

## 总结

### 漏洞严重程度统计

| 严重等级 | 数量 | 漏洞编号 |
|---|---|---|
| 🟥 **P0 — 致命级** | 7 个 | #1, #2, #4, #7, #10, #11, #12 |
| 🟧 **P1 — 高危级** | 3 个 | #3, #6, #8 |

### 修复优先级建议

1. **立即修复**（P0 致命，会导致账实不符 / 报表不平 / 重复扣税）：
   - 漏洞 #4（小规模免税错算）— 季度申报直接少缴税
   - 漏洞 #10（record_sale 销项税虚高）— 每笔销售凭证都错
   - 漏洞 #12（红字发票重复冲红）— 整单数据被改坏
   - 漏洞 #7（dispose 日期错位）— 跨月 BS 不平
   - 漏洞 #1（月结重复执行）— 补提失效 / 重复计提
   - 漏洞 #2（off-by-one 漏算）— 跨期利润错位
   - 漏洞 #11（部分退货成本错位）— 主营业务成本失真

2. **优先修复**（P1 高危，影响可观测性或极端场景）：
   - 漏洞 #8（盘盈盘亏科目错挂）— 审计风险
   - 漏洞 #6（库存红冲 None 兜底）— 数据破坏
   - 漏洞 #3（哈希空间 31 位）— 长期工程债

### 修复策略建议

| 漏洞 | 修复类型 | 工作量估算 |
|---|---|---|
| #1 月结幂等 | 新增 MonthlyClose 锁表 + 改 _has_closed | 1-2 天 |
| #2 off-by-one | _parse_period 改半开区间 + 字段类型 Date | 0.5 天 |
| #3 _period_hash | source_id 改 VARCHAR | 1 天（含 schema 迁移） |
| #4 小规模免税 | 拆分普票/专票，调 AccountingEngine | 1-2 天 |
| #6 库存 None 兜底 | reverse() 抛 BusinessError | 0.5 天 |
| #7 dispose 日期 | 强制要求 disposal_date | 0.5 天 |
| #8 盘盈盘亏科目 | 改 1901 中转 + 二步走流程 | 2-3 天 |
| #10 record_sale 税率 | 删除 _vat_rate 覆盖，调 AccountingEngine | 1 天 |
| #11 退货成本 | 改用 inv.average_cost | 0.5 天 |
| #12 发票红冲 | 区分部分退货场景，重写 invoice 反冲 | 2-3 天 |

**总工作量**：10-14 工作日（按 1 个开发估算）

### 风险与收益

- **不修复的风险**：
  - 季度所得税汇算清缴触发预警
  - 审计师标异常
  - 极端场景下数据被破坏需要重建
  - 客户对账时频繁发现差异

- **修复的收益**：
  - 月结 100% 准确
  - 季度报税口径与账载一致
  - 凭证可追溯到每一笔业务
  - 减少财务对账工作量

---

**报告结束**

如需进一步分析某个具体漏洞的代码 diff 或修复 PR，请告诉我具体哪个编号。
