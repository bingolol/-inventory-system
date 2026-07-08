# CONTEXT.md - 进销存管理系统

## Agent 语言规则

**始终使用中文回复。** 所有分析、解释、建议、代码注释、报告均使用简体中文。

## 项目概述

面向中小企业的全栈业务管理平台，涵盖库存管理、采购/销售、项目归集、财务报表及个人账单等核心模块。

## Agent 快速导航

| 场景 | 手册 |
|------|------|
| **记账操作**（查/录/改业务数据） | [docs/INDEX.md → 记账 Agent 技能](docs/INDEX.md) |
| **开发代码**（改/增/修功能） | [docs/开发规范.md](docs/开发规范.md) |

> 以下为本体文档，记录架构、业务规则、目录结构等底层事实。

## Agent 工作流

### ⚠️ 编码前检查清单

判断任务类型 → 加载对应 Skill → 执行。不可跳过。

| 类型 | 关键词 | Skill |
|------|--------|-------|
| 新功能 | 添加/实现/创建/写一个/新增 | `skill(name="tdd")` |
| 调试 | 报错/修复/bug/问题/失败/不工作 | `skill(name="diagnose")` |
| 需求讨论 | 怎么做/方案/设计/思路/规划 | `skill(name="grill-me")` |
| 代码理解 | 这是什么/解释/看看/了解 | `skill(name="zoom-out")` |
| 重构 | 优化/重构/整理/改进 | `skill(name="improve-codebase-architecture")` |
| 精简沟通 | 用户要求精简/连续对话超 10 轮 | `skill(name="caveman")` |
| 创建 PRD/Issue | 创建 PRD/创建 Issue | `skill(name="to-prd")` / `skill(name="to-issues")` |

加载失败**必须**停止并告知用户。

### 8 条规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | **Read docs first** | 先读文档再写代码 |
| 2 | **Docs before code** | 新模块/重构先创建设计文档 |
| 3 | **Plan before execute** | 呈现计划，等批准后执行 |
| 4 | **Self-review** | 完成后自检，同步文档 |
| 5 | **Tests first** | 核心业务逻辑用 TDD |
| 6 | **禁止破坏性操作** | `git clean`/`reset --hard`/`checkout -- .`/`push --force` 等不可逆操作必须获明确授权 |
| 7 | **动码前先问** | 新建/编辑/删除文件前必须呈现计划并等批准 |
| 8 | **Task Agent 禁越权** | 委托 task agent 时明确列出禁止做的事，否则会注入无关代码 |

### 开发流程

1. 确定问题 → 复述并等用户确认
2. 列出方案（改动清单+原因）→ 等批准
3. 实施 → 遇新问题立即汇报等批准
4. 汇报+自检 → `git status` / 测试 / diff

### 自检规范（L1–L5 分层断言）

> 功能能用不代表正常，正常不代表数字正确，数字正确不代表计算过程正确，计算过程正确不代表聚合计算正确。

每次 candidate 完成后强制执行 L1–L2（30 秒内）。L3–L5 按影响的子系统选择执行。

| 层级 | 检查项 | 命令/方法 | 触发条件 |
|------|--------|----------|---------|
| **L1** 编译 | 182 路由无报错 | `python -c "from main import app"` | 强制 |
| **L2** 响应 | 所有列表端点 200 | Smoke sweep（17 个 GET） | 强制 |
| **L3** 数值 | 关键字段期望值断言 | `pytest tests/unit/ tests/invariants/` | 改 model/schema/计算逻辑 |
| **L4** 分录 | 单笔业务金额闭合（借方=贷方，库存=成本） | `pytest tests/unit/ tests/integration/` | 改 engine/command/journal/crud |
| **L5** 聚合 | 借贷全局平衡 + 会计方程式 + BS/IS 对账 | `pytest tests/invariants/ tests/integration/` | 改 engine_finance/engine_inventory/reports |

### L3–L5 变更-断言映射表

不泛泛跑全量，按"改了哪个子系统"选对应的断言。

| 改动层 | 文件/模块 | L3 断言 | L4 断言 | L5 断言 |
|--------|----------|---------|---------|---------|
| **Schema** | `schemas/*.py` | roundtrip: JSON→model→JSON 值不变；非法输入被拦截 | — | — |
| **Model** | `models*.py` | 新增字段可读写、默认值正确 | — | — |
| **Router** | `routers/*.py` | Pagination 分页返回正确条数；DateRange end_of_day 生效；get_or_404 抛错而非静默 | — | — |
| **CRUD** | `crud/*.py` | get_xxx 不返回 None；list_xxx 排序/分页正确 | — | — |
| **Command** | `commands/*.py` | 创建后 entity 字段与输入一致 | dispatch 后 StockMove 数量/金额与 entity 一致；AccountMove debit==credit | — |
| **Engine: inventory** | `engine_inventory.py` | StockMove.unit_cost = total_cost / quantity | StockMove.total_cost = Σ(AccountMove lines for this move) | Inventory.value = Ledger 1405.balance |
| **Engine: finance** | `engine_finance.py` | source 中 total_with_tax - tax_amount = total_without_tax | 采购分录: dr 1405 + dr 222102 = cr 2202；销售分录: dr 6401 = Σitem.unit_cost × qty | 全局借贷平衡 |
| **Engine: journal** | `engine_journal.py` | 每条 AccountMove Σdebit == Σcredit | source_model+source_id 幂等（重复 post 不重复创建） | 所有 posted 凭证 Σdebit == Σcredit |
| **Engine: tax** | `engine_tax.py` | 一般纳税人: output_tax = revenue × rate；小规模: 季度≤30万时普票免税 | 计提分录: dr 6403 = cr 222104 | tax_payable BS = Ledger 2221.balance |
| **Reports** | `reports/`, `crud/finance/*.py` | BS 单科目余额 = Ledger balance | IS net_profit = revenue - cogs - expenses | A = L + E；BS diff = 0 |

**每次 candidate 后跑对应列的全部断言。** 例如改了 `engine_finance.py` → 必须跑 L3+L4+L5 三列中"Engine: finance"行的全部断言。

### L5 快速验证（无需跑全量集成测试）

```python
from rules.runtime_checks import check_global_balance, check_accounting_equation
from models_finance import Ledger

ledger = db.query(Ledger).filter(Ledger.code == account.code).first()
v1 = check_global_balance(db, {"ledger_id": ledger.id})                                  # Σdebit == Σcredit
v2 = check_accounting_equation(db, {"ledger_id": ledger.id, "report_date": datetime.now().date()})  # A == L + E + (R - X)
assert len(v1) == 0 and len(v2) == 0
```

**Golden Tests（独立会计师验证）** 见 [docs/测试规范.md § Golden Tests](docs/测试规范.md)。6 张表覆盖全业务闭环，每行期望值标注《小企业会计准则》条文。

**新增 candidate 自检 checklist**：
1. 标施工中 → L1 + L2
2. 实施 → L1
3. 自检 → L1 + L2 + 按变更断言映射表跑 L3/L4/L5
4. 标已自检

### 技能使用规范

- Skills 在 `.opencode/skills/` + `~/.claude/skills/` 中按名查找（如 `skill(name="tdd")`）
- 使用后静默 Review；发现问题先问用户再改 SKILL.md
- 完整技能清单见 `docs/agent_skills.md`

---

## 架构核心约束（改代码前必背）

| 层级 | 职责 | 关键文件 |
|------|------|---------|
| **Routers** | 读→CRUD，写→Commands | `backend/routers/` |
| **Commands** | 封装**所有写操作**，显式编排库存/财务联动 | `backend/commands/*.py` |
| **CRUD** | 仅查询+报表，**写操作已下沉** | `backend/crud/*.py` |
| **Domain** | 业务规则验证（库存/采购/销售单） | `backend/domain/*.py` |
| **Engines** | 会计核算子系统，直连 ORM | `backend/engine_*.py` |
| **EventBus** | 日志+汇总重算，解耦副作用 | `backend/events.py` |

**五大红线**：
- ❌ 读 `has_invoice` 做分支 → ✅ 查 `Invoice` 表（BR-1）
- ❌ 读 `Product.purchase_price` 算成本 → ✅ 读 `SaleItem.unit_cost`（BR-7）
- ❌ 直接 UPDATE `StockMove`/`AccountMove` → ✅ 只 INSERT 反向记录（BR-8）
- ❌ 增值税进费用 → ✅ 仅进负债 2221（BR-5）
- ❌ 绕过 API 直连 DB/脚本 → ✅ 全走 API（BR-17）
- ❌ 凭证科目/方向用错 → ✅ `enforce_journal_rules`（JR-01）校验科目结构
- ❌ 引擎内推导税额 → ✅ 税额是实体字段，命令层写入，引擎只读（BR-27）

---

## 常用诊断/重构工具链

| 场景 | 推荐工具/入口 |
|------|-------------|
| **报表不平/日期过滤失效/库存跨期污染** | `bs-diag` → `scripts/bs_diag.py` |
| **报表读错字段（如读 purchase_price 不读 unit_cost）** | `audit-truth-source` → `scripts/audit_truth_source.py` |
| **疑难 Bug/性能回退** | `diagnose` → 建 2s 确定性复现环 → 二分/假设-埋点 |
| **架构深化/模块合并/接口重设计** | `improve-codebase-architecture` → 生成 HTML 报告 → Grilling |
| **新功能/修 Bug** | `tdd` → 先写 1 个集成测 → 再写最小实现 |

---

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端框架 | Vue.js 3 + Vite + Element Plus UI |
| 状态管理 | Pinia |
| 路由 | Vue Router 4 |
| HTTP 客户端 | Axios |
| 后端框架 | FastAPI (Python 3.x) |
| ORM | SQLAlchemy 2.x |
| 数据库 | SQLite |

## 架构分层

### 业务操作层 (业务联动)

```
Routers → Commands → CRUD / Domain → Events → EventBus
```

### 会计核算层 (财务引擎)

```
Routers → (Commands / 直接调用) → FinanceEngines → ORM
```

### 核心模块

- **Routers**: API 路由层，处理 HTTP 请求。读操作直接调用 CRUD，写操作通过 Commands
- **Commands**: 命令模式，封装全部写操作。伙伴管理已合并为通用 Partner 命令
- **CRUD**: 数据访问层。写操作已迁移至 Commands，本层仅保留查询和报表
- **Domain**: 领域模型，业务规则验证
- **Events**: 领域事件
- **EventBus**: 事件总线，负责日志和汇总重算
- **FinanceEngines**: 会计核算引擎子系统，含总账引擎、凭证引擎、往来账引擎、库存引擎、成本引擎(`cost_engine.py`)、财务引擎(`engine_finance.py`)、税务引擎(`engine_tax.py`)、税务核对引擎(`engine_tax_check.py`)、银行对账引擎(`engine_bank_reconcile.py`)、固定资产引擎(`engine_fixed_asset.py`)，独立于 Commands 层面直接操作 ORM。银行手续费/利息统一通过 `finance_integration.py` 的 `post_bank_fee_journal()` seam 生成凭证

### 数据层级 (L1–L4)

所有数据字段按"数字源原则"分为四层，字段名末尾标注层级（`_l1`/`_l2`/`_l3`/`_l4`）。

#### L1 — 外部输入（API 边界写入，引擎层只读）

用户/发票/银行流水等外部来源的原始数据，命令层接收后写入。

| 分类 | 字段 |
|------|------|
| **税率 / 税额** | `Invoice.tax_rate_l1`, `Invoice.tax_amount_l1`, `PurchaseItem.tax_rate_l1`, `SaleItem.tax_rate_l1`, `PurchaseOrder.tax_amount_l1`, `SaleOrder.tax_amount_l1` |
| **金额 / 数量** | `Invoice.amount_with_tax_l1`, `Invoice.amount_without_tax_l1`, `PurchaseOrder.total_price_l1`, `SaleOrder.total_price_l1`, `PurchaseItem.unit_price_l1`, `PurchaseItem.quantity_l1`, `SaleItem.unit_price_l1`, `SaleItem.quantity_l1`, `Expense.amount_l1`, `Receipt.amount_l1`, `Payment.amount_l1` |
| **日期** | `Invoice.issue_date_l1`, `PurchaseOrder.purchase_date_l1`, `SaleOrder.sale_date_l1`, `Expense.expense_date_l1`, `Payment.payment_date_l1`, `StockMove.move_date_l1`(取源单据日期) |
| **数量方向** | `StockMove.quantity_l1`（正=入/负=出，值来自源单据） |

#### L2 — 引擎计算（内部真相源，Writer 唯一）

引擎层从 L1 数据计算出的不可变事实。

| 分类 | 字段 | 写入者 |
|------|------|--------|
| **库存成本** | `StockMove.unit_cost_l2`, `StockMove.total_cost_l2` | `InventoryEngine.inbound/outbound/reverse` |
| **加权平均** | `CostEngine.weighted_average()`（纯函数，无表字段） | `InventoryEngine.inbound/reverse` 调用 |
| **出库锁定** | `SaleItem.unit_cost_l2`（出库时冻结的加权平均） | `InventoryEngine.outbound() → item.set_calculated_cost()` |
| **凭证分录** | `AccountMoveLine.debit_l2`, `AccountMoveLine.credit_l2`, `AccountMove.amount_total_l2`, `AccountMove.amount_untaxed_l2`, `AccountMove.amount_tax_l2` | `JournalEngine.post()` |
| **折旧 / 摊销** | `FixedAssetDepreciation.amount_l2`, `IntangibleAssetAmortization.amount_l2` | `FixedAssetEngine` / `IntangibleAssetEngine` |
| **现金流分类** | `BankTransaction.flow_category_l2`, `BankTransaction.cash_flow_item_code_l2` | `BankEngine` |

#### L3 — 政策配置（创建时配置，引擎做分支判断）

主数据、税率类型、库存策略等政策选择，不是计算产出。

| 分类 | 字段 |
|------|------|
| **纳税人类型** | `Account.taxpayer_type_l3`（general / small_scale） |
| **商品属性** | `Product.track_inventory_l3`（是否追踪库存）, `Product.purchase_price_l3`, `Product.sale_price_l3`, `Product.min_stock_l3` |
| **固定资产参数** | `FixedAsset.depreciation_method_l3`, `FixedAsset.useful_life_l3`, `FixedAsset.salvage_rate_l3` |
| **发票认证** | `Invoice.certification_status_l3` |

#### L4 — 派生汇总（性能缓存，仅供报表/API 查询）

从 L2 自动派生的缓存值，禁止作为计算输入。

| 分类 | 字段 |
|------|------|
| **库存缓存** | `Inventory.quantity_l4`, `Inventory.average_cost_l4`, `Inventory.total_value_l4` |
| **科目余额** | `LedgerAccountBalance.balance_l4`, `LedgerAccountBalance.debit_total_l4`, `LedgerAccountBalance.credit_total_l4` |
| **银行余额** | `BankAccount.balance_l4` |
| **累计折旧** | `FixedAsset.accumulated_depreciation_l4` |
| **已偿还垫付** | `PersonalAdvance.paid_amount_l4` |

#### 四条铁律（`backend/lineage/registry.py` 强制校验）

| # | 规则 | 说明 |
|---|------|------|
| 1 | 层级单调不降 | L1→L2→L3 合法；L4→L2 禁止（缓存不得作为计算输入） |
| 2 | Writer 唯一 | 每个 L2 字段只能有一个写入函数（避免双算法不一致） |
| 3 | 禁止跳层 | L1 直写 L4 跳过 L2 计算环节属违规（期初余额例外） |
| 4 | L4 不作为下游真相源 | L4 字段被 `@reads` 装饰器引用即违规 |

#### 本系统的追溯链

```
L1 发票 (Invoice/PurchaseOrder)
  → L2 原始凭证 (StockMove)
  → L2 内部计算 (CostEngine.weighted_average)
  → L4 缓存 (Inventory) + 凭证 COGS (AccountMove)
```

## 关键特性

- 多账本隔离（X-Account-ID）
- 命令模式写操作
- 显式编排（Command Handler 直接调用库存和收入联动）
- 领域模型业务规则验证（含 `domain/product_kind.py` 商品类型判定：实体/服务、科目映射）
- 金额精度（Decimal + round(2)）
- 价税分离工具（`utils/price.py` — `split`/`combine`/`quantize` 统一计算）
- 危险操作拦截（readonly_middleware 403 + confirm_middleware 202）
- 数据库自动迁移（启动时自动检测并 ALTER TABLE 新增列，`database.py` `_auto_migrate_columns`）

## 目录结构

```
inventory-system/
├── backend/
│   ├── routers/        # API 路由（读操作直接调用 CRUD）
│   ├── commands/       # 命令模式（全部写操作）
│   │   ├── base.py            # Command + Handler 基类 + dispatch
│   │   ├── partner_commands.py # 通用 Partner 命令
│   │   ├── product_commands.py
│   │   ├── finance_commands.py
│   │   ├── personal_commands.py
│   │   ├── personal_advance_commands.py # 个人垫付命令
│   │   ├── account_commands.py
│   │   ├── bank_commands.py            # 银行账户/流水命令
│   │   ├── bank_reconcile.py           # 银行对账命令
│   │   ├── cash_commands.py            # 现金流命令（费用/付款/收款）
│   │   ├── tax_declaration_commands.py # 税务申报命令
│   │   ├── fixed_asset_commands.py     # 固定资产命令
│   │   ├── month_end.py                # 月结命令
│   │   ├── reversal_ops.py             # 冲销操作
│   │   └── orders/                     # 订单子包（重构自旧 purchase/sale/invoice 命令）
│   │       ├── __init__.py
│   │       ├── _order.py               # 参数化订单命令
│   │       ├── _purchase.py            # 采购领域规则
│   │       ├── _sale.py                # 销售领域规则
│   │       ├── _invoice.py             # 发票命令
│   │       ├── _lifecycle.py           # 订单生命周期编排
│   │       └── _cascade.py             # 冲红级联策略
│   ├── crud/           # 数据访问（仅查询 + 报表）
│   │   ├── base.py
│   │   ├── products.py
│   │   ├── partners.py
│   │   ├── orders.py
│   │   ├── invoices.py
│   │   ├── invoice_linkage.py
│   │   ├── finance.py
│   │   ├── personal.py
│   │   ├── inventory_ops.py   # 已废弃
│   │   ├── reports.py
│   │   └── logs.py
│   ├── domain/         # 领域模型
│   │   ├── base.py
│   │   ├── inventory.py
│   │   ├── money.py
│   │   ├── purchase_order.py
│   │   ├── sale_order.py
│   │   └── product_kind.py
│   ├── models.py           # ORM 模型（业务表）
│   ├── models_finance.py   # ORM 模型（会计核算表）
│   ├── models_bank.py      # ORM 模型（银行对账表）
│   ├── account_dep.py      # 账本依赖注入
│   ├── accounting_engine.py# 会计核算引擎编排
│   ├── engine_bank.py      # 银行引擎
│   ├── engine_bank_reconcile.py# 银行对账引擎
│   ├── engine_finance.py   # 财务引擎（采购/销售凭证生成）
│   ├── engine_fixed_asset.py# 固定资产引擎
│   ├── engine_intangible_asset.py# 无形资产引擎
│   ├── engine_inventory.py # 库存引擎（StockMove 流水）
│   ├── engine_journal.py   # 凭证引擎
│   ├── engine_ledger.py    # 总账/明细账引擎
│   ├── engine_period_close.py# 期间结转引擎
│   ├── engine_receivable.py# 往来账龄引擎
│   ├── engine_tax.py       # 税务引擎
│   ├── engine_tax_check.py # 税务核对引擎
│   ├── cost_engine.py      # 成本引擎（加权平均 L2 计算真相源）
│   ├── finance_integration.py # 财务集成层
│   ├── operation_result.py # 操作结果类型
│   ├── events.py           # 事件总线
│   ├── handlers.py         # 事件处理器
│   ├── uow.py              # Unit of Work 事务边界
│   ├── ai_gateway.py       # AI 网关
│   ├── errors.py           # 错误定义
│   ├── image_utils.py      # 图片工具
│   ├── utils/              # 工具包
│   │   ├── audit.py
│   │   ├── period.py
│   │   ├── price.py
│   │   └── process_guard.py
│   ├── middleware/         # 中间件包
│   │   ├── readonly_middleware.py
│   │   └── confirm_middleware.py
│   ├── journal/            # 凭证分录构建
│   │   ├── _cash.py / _fixed_asset.py / _misc.py / _purchase.py
│   │   ├── _reverse.py / _sale.py / _tax.py
│   ├── reports/            # 报表引擎
│   │   ├── dsl.py / engine.py / reconcile.py
│   │   └── definitions/
│   ├── policy/             # 税务政策
│   │   ├── entity_profile.py / policy_engine.py / vat_facts.py
│   │   ├── declaration_mapper.py / income_tax_facts.py
│   ├── rules/              # 运行时校验
│   │   ├── dsl.py / journal_rules.py / rules_definition.py
│   │   ├── runtime_checks.py / validator.py
│   ├── lineage/            # 数据血缘（L1-L4 层级校验）
│   │   └── registry.py
│   ├── accounting_guide/   # 会计规则指引
│   ├── schemas/            # Pydantic 模式
│   └── enums.py            # 枚举定义
├── frontend/
│   ├── src/
│   │   ├── views/      # 页面视图（36+ 文件，含 Dashboard、SupplyChain、FinancialOverview 等）
│   │   ├── components/ # 组件（24 个，含 Layout、OrderFormDialog、BalanceSheet 等）
│   │   ├── composables/# 组合式逻辑（8 个）
│   │   ├── stores/     # Pinia 状态（account / auth / enums）
│   │   └── api/        # API 请求（22 个文件）
│   └── ...
└── docs/               # 文档

## 业务规则(已确认决策)

> 本节记录已与业务方确认的规则。Agent 修改相关逻辑前必读,不得"修复"此处标记为"故意设计"的行为。
> 新规则追加到本节末尾,不要改动已确认条目。

### BR-1:单一真相源原则

"某记录是否有发票"这个事实,**唯一真相**是发票表是否存在指向该记录的关联(Invoice.related_order_id + related_order_type)。
订单/采购/费用表上的 `has_invoice` 布尔字段是历史遗留副本。
新增逻辑不得依赖 `has_invoice` 字段做业务分支,应查询发票表。

### BR-3:开票与销售单的关系

- 开发票与创建销售单**同步进行**:开票时同步添加销售单,`has_invoice=True` 即代表"已开票"的既成事实。
- **不存在**"标了 has_invoice=True 但还没开发票"的时间差状态(此场景按业务方确认不会发生)。
- 因此 `has_invoice` 语义为"已开票事实",非"开票意图",无需区分意图/事实两层状态。

### BR-4:无票收入不强制计提销项税

- 小规模纳税人无票收入,实务中税务局不主动稽查,**系统不强制计提无票销项税**。
- 增值税报表只统计发票表数据,无票销售单不进入增值税销项。
- **这是业务方确认的故意设计**,不是 bug。禁止把"无票收入未计提销项"当作缺口修复。
- 无票销售在利润表计入经营收入,在现金流量表通过银行流水体现(如有收款)。

### BR-5:税费支出分类

月末交税走费用支出(Expense),按税种分类:

| 税种 | 是否走费用支出 | category | functional_category | 说明 | 法律依据 |
|------|---------------|----------|---------------------|------|---------|
| 企业所得税 | ✅ 是费用 | `所得税` | `税金及附加` | 月末计提:借所得税费用,贷应交税费;缴纳:借应交税费,贷银行存款 | 企业所得税法第五条 |
| 附加税(城建/教育/地方教育) | ✅ 是费用 | `税金及附加` | `税金及附加` | 跟随增值税,属税金及附加科目 | 城市维护建设税法第四条 |
| 增值税 | ❌ 不是费用 | 不走费用 | 不走费用 | 属负债(代收代付),缴纳只是清负债,不计入费用。若入费用会虚增费用、少计利润 | 增值税暂行条例 |

- **禁止**把增值税塞进费用支出。
- 分录依据: [小企业会计准则.md §六/6.6 缴纳税金](docs/小企业会计准则.md#66-缴纳)

### BR-6:冲销生成反向分录（非删除）

冲销收款/付款时,系统生成反向分录(红字冲销法),而非直接删除原记录:
- 冲销收款: 生成反向 Receipt + 反向 BankTransaction + 回滚银行余额
- 冲销付款: 生成反向 Payment + 反向 BankTransaction + 回滚银行余额
- 冲销银行交易: 生成反向 BankTransaction + 反向凭证（先冲红原凭证，未找到则走 post_journal 补反向分录）
- 原记录保留,审计痕迹完整
- 冲销后自动重置订单 payment_status 为 unpaid（涉及订单时）

依据: 《会计基础工作规范》第五十一条 — 错误更正使用红字冲销法
系统实现: `commands/reversal_ops.py`（含 `reverse_receipts`、`reverse_payments`、`reverse_single_receipt`、`reverse_single_payment`、`reverse_bank_transaction`）

**已知不对称**: 批量冲销（取消整单时级联触发）不逐笔冲红收款/付款凭证（`call_reverse_journal=False`），
因上层调用方（`reversal_ops.py`）集中通过 `FinanceEngine.reverse_sale/reverse_purchase` 冲红销售/采购凭证，
收款/付款凭证的冲红在整体订单凭证冲红中间接体现。单笔红冲（API 直接调用）会独立冲红对应凭证（`call_reverse_journal=True`）。

### BR-7:库存真相源是 StockMove 流水

库存数据的**唯一真相源**是 `StockMove` 流水表，`Inventory` 表仅为性能缓存：

| 来源 | 写入 StockMove | 更新 Inventory | 说明 |
|------|---------------|---------------|------|
| 采购入库 | `InventoryEngine.inbound()` | 增加 quantity + 移动加权平均 | |
| 销售出库 | `InventoryEngine.outbound()` | 减少 quantity | 锁定 unit_cost 到 SaleItem |
| 库存调整单 | `InventoryEngine.inbound/outbound()` | ± quantity | 记录 InventoryAdjustment 原因 |
| 取消订单 | `InventoryEngine.reverse()` | 回退 quantity | source_type = `xxx_reversal` |

- StockMove 一旦生成**严禁修改或删除**，错误修正通过红冲调整单实现
- 创建商品时不再创建 Inventory 记录（不再接受 `initial_stock`），库存必须通过采购单/期初余额/调整单创建
- **COGS 真相源**: 所有涉及销售成本的查询/报表必须读 `SaleItem.unit_cost`（出库时锁定的移动加权平均成本），禁止读 `Product.purchase_price`。见 [docs/单一真相源原则.md](docs/单一真相源原则.md)
- 系统实现: `backend/engine_inventory.py`（写入 StockMove），`backend/cost_engine.py`（加权平均 L2 计算真相源）

### BR-8:会计凭证/折旧流水同样是真相源

`FixedAssetDepreciation` 和 `AccountMove` 与 `StockMove` 同等保护，双层防护：
- **ORM 层**: `before_update` 事件监听器拦截 ORM UPDATE（`db.query().update()` 或修改对象后 commit）
- **数据库层**: SQLite `BEFORE UPDATE` 触发器拦截原始 SQL UPDATE（`db.execute(text("UPDATE ..."))`）
- `SaleItem.unit_cost` 使用 `@property` + `set_calculated_cost()` 模式，禁止直接赋值

| 表 | ORM 防护 | DB 触发器 | 代码位置 |
|----|----------|----------|----------|
| `StockMove` | `before_update` 全拦 | `trg_immutable_stock_moves` | `models.py` + `database.py` |
| `FixedAssetDepreciation` | `before_update` 全拦 | `trg_immutable_depreciations` | `models.py` + `database.py` |
| `AccountMove` | `before_update` 全拦 | `trg_immutable_account_moves` | `models_finance.py` + `database.py` |
| `SaleItem.unit_cost` | `@property` 只读 + `set_calculated_cost()` | — | `models.py` |

触发器在 `init_db()` 中自动创建（`_create_immutable_triggers`），幂等可重复执行。系统内部冲红/反向操作均通过 INSERT 新记录实现，不 UPDATE 既有记录。

### BR-9: 收款/付款默认关联银行账户（故意设计）

创建收款/付款时如果不传 `bank_account_id`，系统自动绑定该账本第一个银行账户。这不是遗漏检测的 bug，而是便利性设计——实务中绝大多数收款/付款都走银行。如果业务需要走现金（1001），仍可显式传 `bank_account_id=null`。

### BR-10: 银行调节表确认前置（故意设计）

`POST /api/bank/reconciliation/{id}/confirm` 发现未处理的费用/利息项时拒绝确认，要求先调 `generate-entry`。这不是 bug——会计实务中调节表确认是最后一步，确认前必须有财务人员审核每一笔入账分录。

### BR-11: 增值税结转遵循财会〔2016〕22号

月末销项>进项时，系统自动生成 `dr 222106(转出未交增值税) cr 222107(未交增值税)`。留抵不作专门分录，自然体现在应交增值税科目借方余额中。附加税以当期`curr_vat`为基数计提（12%），不是等到次月实缴才计提。

### BR-12: 月结完整流程

`POST /api/finance/month-close` 按固定顺序执行：折旧计提（`FixedAssetEngine.batch_depreciate`）→ 无形资产摊销 → 增值税计算 → 附加税计提 → 所得税计提 → **损益结转**（`PeriodCloseEngine` 将收入/费用科目余额结转到 4103 本年利润，12 月追加 4103→4104 年结）。折旧和摊销计入费用从而影响所得税。月结返回含 `depreciation_count`、`amortization_count`、`period_close_count` 字段。

### BR-13: 银行手续费/利息统一走 post_journal

`POST /api/bank/entry`（直录）和 `POST /api/bank/reconciliation/{id}/generate-entry`（对账补录）均通过 `post_journal` → `JournalEngine.post()` → `engine_journal._build_bank_fee_entry` 生成凭证，保证幂等检查（`source_model + source_id`）和借贷平衡校验。

两种方式对应不同记账时机（见 [docs/会计实务.md §1](./docs/会计实务.md#一银行记账实务)）：
- **直录** — 平时实时记账，同时生成 BankTransaction + 会计凭证
- **对账流程** — 期末对账时补录，只生成会计凭证（银行流水已在银行对账单上）

### BR-14: 小规模增值税普票/专票分开计算

小规模纳税人增值税计算区分普票/专票，季度总销售额≤30万时普票免征：

```
季度总销售额（普票+专票合计）≤ 30万：
  普票收入 → 免征增值税（tax = 0）
  专票收入 → 减按1%征收（tax = special_revenue × 1%）

季度总销售额 > 30万：
  普票收入 → 减按1%征收
  专票收入 → 减按1%征收
```

- 免税门槛看季度总销售额（普票+专票合计），但只有普票享受免税，专票始终按1%缴税
- 附加税只基于实际缴纳的增值税计算，免税部分不计附加税

### BR-15: 亏损不抛异常，返回 0

`calculate_income_tax()` 亏损时返回 `tax_payable=0` + `reduction_item="亏损，不计提所得税"`，不再抛 `INCOME_TAX_PROFIT_NEGATIVE` 异常。与 `engine_tax.py` 月结 `max(cumulative_profit * rate, 0)` 逻辑一致。

### BR-16: 个体工商户不缴企业所得税

`Account.type` 区分企业类型：
- `company` → 正常计算企业所得税（5%/25%）
- `personal` → `calculate_income_tax()` 返回 0（个体户缴个人所得税，系统不处理个税）

三个环节均已覆盖个体户判断：
- 所得税报表 `routers/income_tax.py` → `calculate_income_tax(entity_type)` 返回 0 ✓
- 所得税预缴表 `crud/finance.py` → 同上 ✓
- **月结计提 `engine_tax.py`** → `account.type == "personal"` 时跳过所得税计提 ✓（2026-06-29 修复）

### BR-17: 禁止脚本操作，必须通过 API

本系统所有数据操作**禁止使用脚本**（包括但不限于 Python 脚本、SQL 直连、数据库管理工具）。一切读写必须通过 API 接口完成：
- 脚本绕过 API 会破坏事件总线、审计日志、库存引擎等联动逻辑
- ORM 模型不在 API 层复用可能导致数据不一致
- 调试/运维场景如需批量操作，通过 API 循环调用实现

### BR-26: 运行时校验护栏（纵深防御）

除五大红线和 BR-8 防护外，系统提供两个独立校验工具（`backend/rules/runtime_checks.py`）：

| 函数 | 功能 | 调用场景 |
|------|------|---------|
| `check_global_balance()` | 全局借贷平衡校验：所有 posted 凭证 Σ(debit) == Σ(credit) | 月结/运维兜底，发现 AS-01 漏检或 DB 直写导致的失衡 |
| `check_accounting_equation()` | 会计方程式：资产 == 负债 + 权益 + (收入 - 费用)，纯 SQL，不经 BS 报表 | 与 BS 报表走两条独立路径，互为对账验证 |

- `check_accounting_equation` 按 `LedgerAccount.account_type` 分组求和，`asset_contra` 型科目（累计折旧/摊销）正确作为资产减项
- 损益净额 = 收入 - 费用（年结前直接参与方程式；年结后已转到 4103，收入/费用归零）

### BR-27: 税额为外部输入，禁止引擎推导（2026-07-05 确立）

税额（`tax_amount_l1`）是业务凭证（发票、订单）上的**外部事实**，不是引擎内部的推导值。

- **写入**：税额在命令层（API 边界）写入 `Order.tax_amount_l1` / `Invoice.tax_amount_l1`。如果调用方仅提供含税金额+税率，命令层可调用 `split()`/`combine()` **一次**补全缺失项，此后再不重算。
- **读取**：引擎层（`engine_finance`、`engine_inventory`、`tax_declarations`）只读实体上的 `tax_amount_l1`，严禁调用 `split()`/`combine()`。
- **退货**：退货单的税额按原单税额 ×（退货金额/原单金额）比例计算，不重新推导。
- **禁止**：`split()` 和 `combine()` 不可出现在 `backend/engine_*.py` 或 `backend/crud/finance/*.py` 的 import 中。

### BR-18: 红字发票冲红

发票通过 `POST /api/invoices/{id}/reverse` 冲红，而非物理删除：

```
冲红流程：
  1. 标记原发票 is_reversed=True, reversed_at=now
  2. 创建红字发票（负数金额，方向不变，发票号 H-原号）
  3. 级联冲红：
     ├─ 销项发票（关联销售单）→ reverse_sale 冲红凭证 + InventoryEngine.reverse 库存回退
     ├─ 进项发票（关联采购单）→ reverse_purchase 冲红凭证 + InventoryEngine.reverse 库存退回
     ├─ 费用发票 → 无库存冲红
     ├─ 固定资产发票 → 资产冲红需人工处理
     └─ 独立发票 → 无级联冲红
```

- 红字发票金额负数是税法要求，`InvoiceOut` schema 不限制 `ge=0`
- 幂等防御：已冲红发票再次冲红报错；DELETE 被 403 拦截

系统实现: `commands/invoice_commands.py` `ReverseInvoice` + `routers/invoices.py`

### BR-19: 危险操作拦截 — 已过账数据禁止物理删除（2026-06-29 修复）

`readonly_middleware.py` 拦截以下 DELETE 操作，强制走冲红/取消流程：

| 被拦截的 DELETE | 替代操作 | 理由 |
|----------------|---------|------|
| `/api/invoices/{id}` | `POST /{id}/reverse` | 发票红冲 |
| `/api/fixed-assets/{id}` | `POST /{id}/dispose` | 资产处置 |
| `/api/expenses/{id}` | `POST /{id}/reverse` | 费用冲红（冲红总账凭证+保留审计轨迹） |
| `/api/cash-flows/transactions/{id}` | `POST /transactions/{id}/reverse` | 现金流水冲红 |
| `/api/sales/{id}` | `POST /{id}/cancel` | 销售单取消（保留审计轨迹+冲红凭证库存） |
| `/api/purchases/{id}` | `POST /{id}/cancel` | 采购单取消（同上） |
| `/api/opening-balances/{id}` | 无（期初余额锁定） | 期初余额创建后不可修改 |

新增冲红接口：
- `POST /api/expenses/{id}/reverse` — 冲红总账凭证 + 标记 `is_reversed=True`
- `POST /api/cash-flows/transactions/{id}/reverse` — 冲红总账凭证 + 标记 `is_reversed=True`

所有冲红接口统一遵循：不物理删除、冲红总账凭证、幂等防御、操作日志。

系统实现: `middleware/readonly_middleware.py` + `routers/expenses.py` + `routers/cash_flows.py`

### BR-20: 库存调整必须填写原因（2026-06-29 新增）

库存盘点调整（增加或减少）必须填写 `reason` 字段，前端弹窗二次确认：

```
盘点按钮 → 对话框（填新库存量 + 调整原因）
  ├─ 原因为空或数量未变 → 确认按钮禁用
  └─ 点击确认 → PopConfirm "确认将库存从 X 调整为 Y？"
      └─ 确认 → 调 API（带 reason）→ 完成
```

- 后端校验：`delta != 0` 且 `reason` 为空 → 报错
- 日志记录格式：`库存盘点: 100→95（原因: 盘亏）`
- 系统实现: `commands/product_commands.py` `AdjustInventory` + `frontend/src/views/Inventory.vue`

### BR-21: 采购/销售业务日期必填（2026-06-29 修复）

创建采购单/销售单时业务日期（`purchase_date`/`sale_date`）必填，不允许用 `datetime.now()` 兜底：

- 业务日期级联到凭证日期（`AccountMove.date`）和库存移动日期（`StockMove.move_date`）
- 用当前时间兜底会导致：BS 按日期过滤时凭证被错误排除、利润表期间归属错误
- 系统实现: `commands/orders/_purchase.py` + `commands/orders/_sale.py`

### BR-22: BS 应交税费包含小规模纳税人科目

资产负债表 `tax_payable` 必须同时读取两种纳税人的应交增值税科目：

| 纳税人类型 | 销项税科目 | 月结结转 | 最终余额科目 |
|-----------|-----------|---------|-------------|
| 一般纳税人 | 222101 | 222101→222106→222107 | 222107 |
| 小规模纳税人 | 222103 | 不走转出未交增值税 | 222103 |

```python
vat_payable = _credit_balance("222107") + _credit_balance("222103")
```

小规模纳税人没有"转出未交增值税"子科目，222103 本身就是负债科目。

### BR-23: 报表科目完整覆盖

BS 和利润表必须覆盖科目表中全部损益类科目：

| 科目 | 名称 | BS | 利润表 | 说明 |
|------|------|----|--------|------|
| 6001 | 主营业务收入 | ✓ | ✓ | |
| 6051 | 其他业务收入 | ✓ | ✓ | 原只读 6001 |
| 6111 | 资产处置收益 | ✓ | ✓ | 原遗漏 |
| 6401 | 主营业务成本 | ✓ | ✓ | |
| 6403 | 税金及附加 | ✓ | ✓ | |
| 6601 | 管理费用 | ✓ | ✓ | |
| 6602 | 销售费用 | ✓ | ✓ | 原 BS 只读 6601，利润表硬编码 0 |
| 6603 | 财务费用 | ✓ | ✓ | 同上 |
| 6301 | 营业外收入-税收减免 | ✓ | ✓ | 原遗漏 |
| 6701 | 营业外支出 | ✓ | ✓ | 原遗漏 |
| 6711 | 资产处置损失 | ✓ | ✓ | 原遗漏 |
| 6801 | 所得税费用 | ✓ | ✓ | |

BS 利润公式：`收入 - 成本 - 期间费用 - 税金及附加 - 所得税 + 营业外收入 - 营业外支出`

### BR-25: 附加税减半独立配置（2026-07-05 重构）

附加税减半判定不再跟随 `income_type`（所得税小型微利），而是独立从 `Account.surcharge_halved` 字段读取：

| 判定 | 真相源 | 更新时机 |
|------|--------|---------|
| 附加税减半 | `Account.surcharge_halved` 布尔字段 | 创建账本时配置，**年末评估待实现** |
| 所得税小型微利（`income_type`） | 纳税人类型 + 当年累计利润 ≤ 300万 | 月结时实时计算 |

**待实现**：`POST /api/finance/assess-surcharge` 年末自动评估路由 + `policy/annual_revenue_assessment.py`。当前需手动通过 API 更新 `Account.surcharge_halved`。

**教育费附加/地方教育附加季度免征**（财税〔2016〕12 号）：季度不含税销售额 ≤ 30 万时，教育费附加（3%）和地方教育附加（2%）免征，城建税（7%）照常征收。`policy/vat_facts.py` 定义 `VAT_SMALL_SCALE_QUARTERLY_EXEMPTION` 常量，`policy/policy_engine.py` 的 `calculate_surcharges()` 通过 `vat_facts.small_scale_quarterly_exemption` 读取门槛值并接收 `quarterly_revenue` 参数，月结时由 `engine_tax.py` 计算季度销售额并传入。

### BR-24: 其他应付款/个人垫付模块

老板/员工用个人资金替公司垫付费用（如零星采购、办公费用、固定资产）时，公司形成一笔对个人的负债，挂账"其他应付款"科目（2241）。

**业务流程**：

1. **创建垫付单** `POST /api/personal-advances`：借 debit_account_code（默认 6601 管理费用）贷 2241 其他应付款。
2. **偿还** `POST /api/personal-advances/{id}/repay`：支持部分偿还，多次累计。借 2241 贷 1002 银行存款（或 1001 库存现金）。带 `bank_account_id` 时自动生成 BankTransaction 并扣减银行余额。
3. **红冲垫付单** `POST /api/personal-advances/{id}/reverse`：冲红总账凭证 + 标记 `is_reversed=True`。**前置约束**：必须先红冲所有未冲红的偿还记录。
4. **红冲单笔偿还** `POST /api/personal-advances/{id}/repayments/{rid}/reverse`：冲红总账凭证 + 反向银行流水（如有）+ 累减 paid_amount + 重算 repayment_status。

**关键规则**：

- 借方科目白名单（`enums.PERSONAL_ADVANCE_DEBIT_ACCOUNTS`）：`6601 管理费用` / `6602 销售费用` / `1405 库存商品` / `1601 固定资产` / `1701 无形资产`。由 schemas 层校验。
- 垫付人（债权人）按人名自由填写（`advancer_name`），不维护独立的人员表。
- 垫付单号格式：`PA-YYYY-NNNN`（账本内年度递增），与采购/销售单号格式不同。
- 偿还金额 ≤ `remaining_amount`（amount - paid_amount），禁止超额偿还。
- BS 报表 `total_current_liabilities` 必须包含 `other_payable`（2241 余额），否则资产与权益错配不平。
- 偿还流程的多步原子性（实体写 + 总账 + 银行流水 + 状态更新）由 `unit_of_work(db)` 包裹，与 `expenses` / `payments` 路由模式一致，不走 Command 层。
- AI 网关已对 4 个写接口开放（create/repay/reverse/reverse-repayment），`/reverse` 自动走 ConfirmMiddleware 二次确认。

---

## 产品设计原则

### PR-1: 前端隐藏专业术语

前端不得直接展示会计科目和借贷分录。`FinanceEngine` 在后台生成专业凭证，前端只展示业务语言：

| ❌ 不要 | ✅ 要 |
|---------|-------|
| 借：库存商品 1000 贷：银行存款 1000 | 库存增加了 100 个，银行存款减少了 1000 元 |
| 借：主营业务成本 500 贷：库存商品 500 | 出库了 50 个，成本 500 元 |
| 借方/贷方/科目名称 | 业务描述（钱/货/往来对象） |

会计核算专用页面（凭证管理、科目余额表）可按会计格式展示，但所有业务操作类界面（采购/销售/库存/费用）严禁出现会计科目。

### PR-2: 报表直击痛点（含已知局限）

> **已知局限**：
> 1. **应收/应付汇总**：通过前端聚合未结清订单计算，不支持大数据分页。远期需加 `GET /finance/receivable/summary` 后端端点。
> 2. **月度损益不含费用**：`GET /reports/profit` 不返回费用汇总，需额外调 expenses API 前端计算。远期建议 profit 端点内置 expense 字段。
> 3. **税务速算需 2 请求**：增值税月报 + 所得税季报分开调用。远期建议合并为 `GET /tax-report/dashboard-summary`。
> 4. **坏账核销端点暂未实现**：[models_finance.py](backend/models_finance.py) 已有 `BadDebt`
> 
> **已实现**：
> - 报表端点支持 `trace` 参数返回数据追溯链，`reconcile` 参数启用双路径对账验证
> - `check_global_balance()` 全局借贷平衡校验 + `check_accounting_equation()` 会计方程式独立验证（`backend/rules/runtime_checks.py`），与 BS 报表走两条独立路径互为对账 模型，但无对应 router 暴露。实现需先确认会计处理方式（直接冲销法 vs 备抵法）、增值税是否转出、是否关联原销售单/发票等设计决策，待后续排期。AI Agent 触发坏账核销场景时应跳过或标记为"未实现"，不要尝试调用 `POST /api/finance/bad-debt`（会 404）。

老板不关心复杂的勾稽关系，只关心四个问题。所有报表设计围绕核心问题展开：

| 老板问 | 对应报表 | 数据来源 |
|--------|----------|----------|
| **这月赚了多少？** | 月度损益速览 | 利润表+ 本期收入/成本/费用汇总 |
| **仓库压了多少钱？** | 库存资金占用 | StockMove 加权平均成本 × 当前库存量 |
| **客户欠我多少钱？** | 应收汇总 | 往来账龄 + 未收销售单 |
| **这个月该交多少税？** | 税务速算 | 增值税 + 企业所得税 + 附加税 |

税务报表输出格式与税务局电子申报系统一致，数字可直接照抄填写，无需二次计算。

---

## 部署与安全上下文

### DS-1: 本地单机系统（已确认决策）

本系统设计为**本地单机部署**（localhost / 内网），不面向公网暴露：

| 方面 | 决策 | 理由 |
|------|------|------|
| 部署范围 | 用户个人电脑或公司内网服务器 | 面向中小企业，无 SaaS 化需求 |
| Token 存储 | localStorage（不改成 httpOnly cookie） | 无 XSS 攻击面（浏览器仅加载自家前端），简化架构 |
| 密码安全 | 当前措施已足够 | pbkdf2 哈希 + 盐 + 限流 + timing-safe 比较 |
| 传输加密 | 建议通过反向代理（nginx/caddy）启用 HTTPS | 内网传输非明文即可，非强制 |

**安全决策原则**：系统安全措施与部署环境匹配。本地单机场景下，localStorage token 存储和公网级 CSRF/XSS 纵深防御的投入产出比低，不做额外加固。如需公网部署，应整体评估安全方案（WAF、HTTPS、httpOnly cookie、CSRF token 等）。
