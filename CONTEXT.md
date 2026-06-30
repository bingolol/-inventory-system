# CONTEXT.md - 进销存管理系统

## 项目概述

面向中小企业的全栈业务管理平台，涵盖库存管理、采购/销售、项目归集、财务报表及个人账单等核心模块。

## Agent 快速导航

| 场景 | 手册 |
|------|------|
| **记账操作**（查/录/改业务数据） | [docs/财务Agent手册.md](docs/财务Agent手册.md) |
| **开发代码**（改/增/修功能） | [docs/开发Agent手册.md](docs/开发Agent手册.md) |

> 以下为本体文档，记录架构、业务规则、目录结构等底层事实。

## Agent 工作流

### 📚 知识库入口

| 文档 | 内容 |
|------|------|
| [docs/INDEX.md](docs/INDEX.md) | 完整文档索引 |
| [docs/开发速查表.md](docs/开发速查表.md) | 开发规范 + 反模式红线（**修改代码前必读**） |
| [docs/架构参考.md](docs/架构参考.md) | 完整架构手册 |
| [docs/文件索引.md](docs/文件索引.md) | 全仓库文件清单 |
| [docs/会计实务.md](docs/会计实务.md) | 会计实践逻辑与系统实现映射 |
| [代码调用逻辑图.md](代码调用逻辑图.md) | 函数级调用链：Router→Command→Engine→ORM 全链路 |

### ⚠️ 强制执行：编码前检查清单

**每次收到编码任务时，必须按顺序执行以下检查，不可跳过：**

#### 第 1 步：识别任务类型
判断用户请求属于哪种类型：

| 类型 | 关键词 |
|------|--------|
| 新功能 | "添加"、"实现"、"创建"、"写一个"、"新增" |
| 调试 | "报错"、"修复"、"bug"、"问题"、"失败"、"不工作" |
| 需求讨论 | "怎么做"、"方案"、"设计"、"思路"、"规划" |
| 代码理解 | "这是什么"、"解释"、"看看"、"了解" |
| 重构 | "优化"、"重构"、"整理"、"改进" |
| 精简沟通 | 用户明确要求精简、或连续对话超过 10 轮 |

#### 第 2 步：加载对应 Skill（必须）
根据任务类型，**必须**使用 `skill` 工具加载对应 skill：

```
任务类型 → 加载 Skill
─────────────────────────────────
新功能开发 → skill(name="tdd")
调试修复   → skill(name="diagnose")
需求对齐   → skill(name="grill-me")
代码理解   → skill(name="zoom-out")
重构优化   → skill(name="improve-codebase-architecture")
创建 PRD  → skill(name="to-prd")
创建 Issue → skill(name="to-issues")
精简输出   → skill(name="caveman")
创建 Skill → skill(name="write-a-skill")
问题分类   → skill(name="triage")
```

#### 第 3 步：验证加载
加载后，确认 skill 内容已注入当前上下文。如果加载失败，**必须**告知用户并停止执行。

---

### 必须遵守的 5 条规则

| # | 规则 | 说明 |
|---|------|------|
| 1 | **Read docs first** | 先读文档再写代码，理解上下文 |
| 2 | **Docs before code** | 新模块/重构时先创建设计文档 |
| 3 | **Plan before execute** | 呈现计划，等待批准后再执行 |
| 4 | **Self-review** | 完成后自检，确保文档同步更新 |
| 5 | **Tests first** | 核心业务逻辑使用 TDD |

### 开发流程

```
1. 理解任务
   │
   ├─→ 读取 CONTEXT.md (项目上下文)
   ├─→ 读取相关模块文档
   └─→ 如有疑问，先问用户
   │
2. 制定计划
   │
   ├─→ 列出要修改的文件
   ├─→ 说明修改原因
   └─→ 呈现给用户批准
   │
3. 执行开发
   │
   ├─→ 遵循开发速查表中的规范
   ├─→ 遵循反模式红线 (AP-1~AP-14)
   └─→ 核心逻辑先写测试
   │
4. 自检完成
   │
   ├─→ 运行测试: pytest
   ├─→ 检查代码风格
   └─→ 更新相关文档
```

### 何时询问 vs 何时直接执行

| 询问用户 | 直接执行 |
|----------|----------|
| 不确定业务规则时 | 明确的 Bug 修复 |
| 涉及数据库结构变更时 | 文档更新 |
| 涉及多个模块的重构时 | 单一文件的小改动 |
| 可能影响现有功能时 | 测试补充 |

### Agent 技能

技能是规则的落地工具。`docs/agent_skills.md` 按 5 类场景说明 19 个技能的用途。

| 规则 | 对应技能 |
|------|----------|
| Tests first | `tdd` |
| Self-review | `review`、`neat-freak` |
| Read docs first | `zoom-out` |
| Plan before execute | `grill-me`、`grill-with-docs` |

| 场景 | 技能 |
|------|------|
| **开发核心**（高频） | `tdd`、`diagnose`、`review`、`zoom-out` |
| **计划设计**（中频） | `to-issues`、`to-prd`、`triage`、`grill-me`、`grill-with-docs`、`prototype`、`improve-codebase-architecture` |
| **会话交接**（低频） | `handoff`、`neat-freak`、`teach`、`write-a-skill` |
| **通信模式** | `caveman` |
| **不适用** | `migrate-to-shoehorn`、`scaffold-exercises`、`setup-pre-commit`、`git-guardrails-claude-code`、`setup-matt-pocock-skills` |

### 文档检查清单

Agent 完成任务后检查：

- [ ] 代码测试通过
- [ ] 相关文档已更新
- [ ] 没有引入新的反模式
- [ ] 遵循命名约定
- [ ] 错误处理使用 BusinessError

---

## 技能使用规范

- 每次使用技能（Skill 工具）完成任务后，静默执行 Review。
- 一切顺利 → 无需任何操作。
- 发现问题或绕路方案 → 先询问用户是否同意更新技能文档，用户确认后再修改对应的 SKILL.md。

## Skills 说明

- Skills 文件位于 `C:\Users\Administrator\.claude\skills\` 目录
- 加载时使用 skill 名称（如 `tdd`、`diagnose`），不要用文件路径
- 系统会自动从 skills 目录查找对应的 SKILL.md 文件

## 违反后果

如果跳过上述检查清单直接编码，**必须**立即停止，回退到第 1 步重新执行.

---

## 架构核心约束（改代码前必背）

| 层级 | 职责 | 关键文件 |
|------|------|---------|
| **Routers** | 读→CRUD，写→Commands | `backend/routers/` |
| **Commands** | 封装**所有写操作**，显式编排库存/财务联动 | `backend/commands/*.py` |
| **CRUD** | 仅查询+报表，**写操作已下沉** | `backend/crud/*.py` |
| **Domain** | 业务规则验证（库存/采购/销售单） | `backend/domain/*.py` |
| **Engines** | 会计核算子系统，直连 ORM | `backend/engine_*.py` |
| **EventBus** | 日志+汇总重算，解耦副作用 | `backend/middleware/event_bus.py` |

**五大红线**：
- ❌ 读 `has_invoice` 做分支 → ✅ 查 `Invoice` 表（BR-1）
- ❌ 读 `Product.purchase_price` 算成本 → ✅ 读 `SaleItem.unit_cost`（BR-7）
- ❌ 直接 UPDATE `StockMove`/`AccountMove` → ✅ 只 INSERT 反向记录（BR-8）
- ❌ 增值税进费用 → ✅ 仅进负债 2221（BR-5）
- ❌ 绕过 API 直连 DB/脚本 → ✅ 全走 API（BR-17）

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
- **FinanceEngines**: 会计核算引擎子系统，含总账引擎、凭证引擎、往来账引擎、库存引擎、财务引擎、税务引擎(`engine_tax.py`)、税务核对引擎(`engine_tax_check.py`)、银行对账引擎(`engine_bank_reconcile.py`)，独立于 Commands 层面直接操作 ORM

## 关键特性

- 多账本隔离（X-Account-ID）
- 命令模式写操作
- 显式编排（Command Handler 直接调用库存和收入联动）
- 领域模型业务规则验证
- 金额精度（Decimal + round(2)）
- 危险操作拦截（readonly_middleware 403 + confirm_middleware 202）
- 数据库自动迁移（启动时自动检测并 ALTER TABLE 新增列，`database.py` `_auto_migrate_columns`）

## 目录结构

```
inventory-system/
├── backend/
│   ├── routers/        # API 路由（读操作直接调用 CRUD）
│   ├── commands/       # 命令模式（全部写操作）
│   │   ├── base.py            # Command + Handler 基类 + dispatch
│   │   ├── crud_compat.py     # CRUD 桥接层
│   │   ├── partner_commands.py # 通用 Partner 命令（Supplier/Customer 合并）
│   │   ├── product_commands.py
│   │   ├── purchase_commands.py
│   │   ├── sale_commands.py
│   │   ├── invoice_commands.py
│   │   ├── finance_commands.py
│   │   ├── personal_commands.py
│   │   └── account_commands.py
│   ├── crud/           # 数据访问（仅查询 + 报表）
│   │   ├── base.py            # 公共函数（_log, _generate_order_no）
│   │   ├── products.py        # 商品 + 库存查询
│   │   ├── partners.py        # 伙伴查询（只读）
│   │   ├── orders.py          # 订单查询（只读）
│   │   ├── invoices.py        # 发票查询 + 税务报表
│   │   ├── invoice_linkage.py # 发票与业务关联查询
│   │   ├── finance.py         # 财务查询 + 报表生成
│   │   ├── personal.py        # 个人流水查询 + 统计
│   │   ├── inventory_ops.py   # 库存操作（已废弃，改用 engine_inventory.py）
│   │   ├── reports.py         # 统计报表
│   │   └── logs.py            # 操作日志查询
│   ├── domain/         # 领域模型
│   │   ├── base.py            # 基类
│   │   ├── inventory.py       # 库存业务规则
│   │   ├── money.py           # 金额值对象
│   │   ├── purchase_order.py  # 采购单业务规则
│   │   └── sale_order.py      # 销售单业务规则
│   ├── models.py           # ORM 模型（业务表）
│   ├── models_finance.py   # ORM 模型（会计核算表）
│   ├── account_dep.py      # 账本依赖注入
│   ├── accounting_engine.py# 会计核算引擎编排
│   ├── engine_bank.py      # 银行引擎
│   ├── engine_finance.py   # 财务引擎（采购/销售凭证生成）
│   ├── engine_fixed_asset.py# 固定资产引擎（折旧/处置）
│   ├── engine_inventory.py # 库存引擎（StockMove 流水 + 移动加权平均）
│   ├── engine_journal.py   # 凭证引擎
│   ├── engine_ledger.py    # 总账/明细账引擎
│   ├── engine_receivable.py# 往来账龄引擎
│   ├── finance_integration.py # 财务引擎与业务的集成层
│   ├── operation_result.py # 操作结果类型
│   ├── utils/               # 工具包（`_d`/`get_or_404`/日期解析/工厂函数 + `audit.py` 审计日志）
│   ├── middleware/          # 中间件包（只读 + EventBus 中间件）
│   ├── schemas/            # Pydantic 模式
│   └── enums.py            # 枚举定义
├── frontend/
│   ├── src/
│   │   ├── views/      # 页面视图
│   │   │   ├── Dashboard.vue         # 首页仪表盘
│   │   │   ├── Products.vue          # 商品管理
│   │   │   ├── Suppliers.vue         # 供应商管理
│   │   │   ├── Customers.vue         # 客户管理
│   │   │   ├── Purchases.vue         # 采购管理
│   │   │   ├── Sales.vue             # 销售管理
│   │   │   ├── Inventory.vue         # 库存管理
│   │   │   ├── Invoices.vue          # 发票管理
│   │   │   ├── Expenses.vue          # 费用管理
│   │   │   ├── Personal.vue          # 个人流水
│   │   │   ├── FinancialReports.vue  # 财务报表
│   │   │   ├── CashFlow.vue          # 现金流管理
│   │   │   ├── TaxReport.vue         # 税务报表
│   │   │   ├── Reconciliations.vue   # 对账管理
│   │   │   ├── Reports.vue           # 统计报表
│   │   │   ├── Logs.vue              # 操作日志
│   │   │   ├── TrialBalance.vue      # 试算平衡表
│   │   │   ├── JournalMoves.vue      # 凭证管理
│   │   │   ├── AgingReport.vue       # 往来账龄
│   │   │   └── Backup.vue            # 数据备份
│   │   ├── components/ # 组件
│   │   ├── composables/# 组合式逻辑
│   │   ├── stores/     # Pinia 状态
│   │   └── api/        # API 请求
│   └── ...
└── docs/               # 文档

## 业务规则(已确认决策)

> 本节记录已与业务方确认的规则。Agent 修改相关逻辑前必读,不得"修复"此处标记为"故意设计"的行为。
> 新规则追加到本节末尾,不要改动已确认条目。

### BR-1:单一真相源原则

"某记录是否有发票"这个事实,**唯一真相**是发票表是否存在指向该记录的关联(Invoice.related_order_id + related_order_type)。
订单/采购/费用表上的 `has_invoice` 布尔字段是历史遗留副本,目标是删除并改为派生查询(见架构改进方案 1)。
在此之前,新增逻辑不得依赖 `has_invoice` 字段做业务分支,应查询发票表。

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

- 现有 EXPENSE_CATEGORIES 需补充 `税金及附加`、`所得税` 两个类目。
- 现有 EXPENSE_FUNCTIONAL_CATEGORIES 需补充 `税金及附加`(与销售/管理/财务费用并列,利润表单列)。
- **禁止**把增值税塞进费用支出。
- 分录依据: [小企业会计准则.md §六/6.6 缴纳税金](docs/小企业会计准则.md#66-缴纳)
- 计算依据: [小企业会计准则.md §二/2.4 增值税](docs/小企业会计准则.md#24-增值税)

### BR-6:冲销生成反向分录（非删除）

冲销收款/付款时,系统生成反向分录(红字冲销法),而非直接删除原记录:
- 冲销收款: 生成反向 Receipt + 反向 BankTransaction + 回滚银行余额
- 冲销付款: 生成反向 Payment + 反向 BankTransaction + 回滚银行余额
- 冲销银行交易: 生成反向 BankTransaction + 反向凭证（先冲红原凭证，未找到则走 post_journal 补反向分录）
- 原记录保留,审计痕迹完整
- 冲销后自动重置订单 payment_status 为 unpaid（涉及订单时）

依据: 《会计基础工作规范》第五十一条 — 错误更正使用红字冲销法
系统实现: `crud/reversal.py`（含 `reverse_receipts`、`reverse_payments`、`reverse_single_receipt`、`reverse_single_payment`、`reverse_bank_transaction`）

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
- 系统实现: `backend/engine_inventory.py`

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

### BR-12: 月结自动计提折旧

`POST /api/finance/month-close` 在算税之前自动调用 `FixedAssetEngine.batch_depreciate(period)`，折旧计入费用从而影响所得税。月结返回含 `depreciation_count` 字段。

### BR-13: 银行手续费/利息统一走 post_journal

`POST /api/bank/entry`（直录）和 `POST /api/bank/reconciliation/{id}/generate-entry`（对账补录）均通过 `post_journal` → `JournalEngine.post()` → `engine_journal._build_bank_fee_entry` 生成凭证，保证幂等检查（`source_model + source_id`）和借贷平衡校验。

两种方式对应不同记账时机（见 [docs/会计实务.md §1](./docs/会计实务.md#一银行记账实务)）：
- **直录** — 平时实时记账，同时生成 BankTransaction + 会计凭证
- **对账流程** — 期末对账时补录，只生成会计凭证（银行流水已在银行对账单上）

### BR-14: 小规模增值税普票/专票分开计算（2026-06-29 修复）

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

### BR-18: 红字发票冲红（2026-06-29 新增）

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
  4. 操作日志
```

- 红字发票金额为负数是税法要求，`InvoiceOut` schema 不限制 `ge=0`（仅 `InvoiceCreate` 限制）
- 幂等防御：已冲红发票再次冲红报错
- `DELETE /api/invoices/{id}` 被 readonly 中间件 403 拦截，强制走 reverse

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
- 系统实现: `commands/purchase_commands.py` + `commands/sale_commands.py`

### BR-22: BS 应交税费包含小规模纳税人科目（2026-06-29 修复）

资产负债表 `tax_payable` 必须同时读取两种纳税人的应交增值税科目：

| 纳税人类型 | 销项税科目 | 月结结转 | 最终余额科目 |
|-----------|-----------|---------|-------------|
| 一般纳税人 | 222101 | 222101→222106→222107 | 222107 |
| 小规模纳税人 | 222103 | 不走转出未交增值税 | 222103 |

```python
vat_payable = _credit_balance("222107") + _credit_balance("222103")
```

小规模纳税人没有"转出未交增值税"子科目，222103 本身就是负债科目。

### BR-23: 报表科目完整覆盖（2026-06-29 修复）

BS 和利润表必须覆盖科目表中全部损益类科目：

| 科目 | 名称 | BS | 利润表 | 修复说明 |
|------|------|----|--------|---------|
| 6001 | 主营业务收入 | ✓ | ✓ | 已有 |
| 6051 | 其他业务收入 | ✓ | ✓ | 本轮修复（原只读 6001） |
| 6111 | 资产处置收益 | ✓ | ✓ | 本轮修复（原遗漏） |
| 6401 | 主营业务成本 | ✓ | ✓ | 已有 |
| 6403 | 税金及附加 | ✓ | ✓ | 已有 |
| 6601 | 管理费用 | ✓ | ✓ | 已有 |
| 6602 | 销售费用 | ✓ | ✓ | 本轮修复（原 BS 只读 6601，利润表硬编码 0） |
| 6603 | 财务费用 | ✓ | ✓ | 本轮修复（同上） |
| 6301 | 营业外收入-税收减免 | ✓ | ✓ | 本轮修复（BS 原遗漏） |
| 6701 | 营业外支出 | ✓ | ✓ | 本轮修复（BS 原遗漏） |
| 6711 | 资产处置损失 | ✓ | ✓ | 本轮修复（原遗漏） |
| 6801 | 所得税费用 | ✓ | ✓ | 已有 |

BS 利润公式：`收入 - 成本 - 期间费用 - 税金及附加 - 所得税 + 营业外收入 - 营业外支出`

### BR-24: 其他应付款/个人垫付模块（2026-06-30 新增）

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

> **已知局限**（纯前端方案，不依赖后端改动）：
> 1. **应收/应付汇总**：通过前端聚合未结清订单计算，不支持大数据分页。远期需加 `GET /finance/receivable/summary` 后端端点。
> 2. **月度损益不含费用**：`GET /reports/profit` 不返回费用汇总，需额外调 expenses API 前端计算。远期建议 profit 端点内置 expense 字段。
> 3. **税务速算需 2 趚请求**：增值税月报 + 所得税季报分开调用。远期建议合并为 `GET /tax-report/dashboard-summary`。
> 4. **坏账核销端点暂未实现**（2026-06-29 标记暂缓）：[models_finance.py](backend/models_finance.py) 已有 `BadDebt` 模型，但无对应 router 暴露。实现需先确认会计处理方式（直接冲销法 vs 备抵法）、增值税是否转出、是否关联原销售单/发票等设计决策，待后续排期。AI Agent 触发坏账核销场景时应跳过或标记为"未实现"，不要尝试调用 `POST /api/finance/bad-debt`（会 404）。

老板不关心复杂的勾稽关系，只关心四个问题。所有报表设计围绕核心问题展开：

| 老板问 | 对应报表 | 数据来源 |
|--------|----------|----------|
| **这月赚了多少？** | 月度损益速览 | 利润表+ 本期收入/成本/费用汇总 |
| **仓库压了多少钱？** | 库存资金占用 | StockMove 加权平均成本 × 当前库存量 |
| **客户欠我多少钱？** | 应收汇总 | 往来账龄 + 未收销售单 |
| **这个月该交多少税？** | 税务速算 | 增值税 + 企业所得税 + 附加税 |

税务报表输出格式与税务局电子申报系统一致，数字可直接照抄填写，无需二次计算。
