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
- **FinanceEngines**: 会计核算引擎子系统，含总账引擎、凭证引擎、往来账引擎、库存引擎、财务引擎，独立于 Commands 层面直接操作 ORM

## 关键特性

- 多账本隔离（X-Account-ID）
- 命令模式写操作
- 显式编排（Command Handler 直接调用库存和收入联动）
- 领域模型业务规则验证
- 金额精度（Decimal + round(2)）

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
- 原记录保留,审计痕迹完整
- 冲销后自动重置订单 payment_status 为 unpaid

依据: 《会计基础工作规范》第五十一条 — 错误更正使用红字冲销法
系统实现: `crud/reversal.py`

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
- 系统实现: `backend/engine_inventory.py`

### BR-8:会计凭证/折旧流水同样是真相源

`FixedAssetDepreciation` 和 `AccountMove` 与 `StockMove` 同等保护：
- 三张表均加 `before_update` 事件监听器，任何 UPDATE 操作抛出 `BusinessError`
- `SaleItem.unit_cost` 使用 `@property` + `set_calculated_cost()` 模式，禁止直接赋值

| 表 | 防护方式 | 代码位置 |
|----|----------|----------|
| `StockMove` | `before_update` 全拦 | `models.py` |
| `FixedAssetDepreciation` | `before_update` 全拦 | `models.py` |
| `AccountMove` | `before_update` 全拦 | `models_finance.py` |
| `SaleItem.unit_cost` | `@property` 只读 + `set_calculated_cost()` | `models.py` |

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
> 3. **税务速算需 2 趟请求**：增值税月报 + 所得税季报分开调用。远期建议合并为 `GET /tax-report/dashboard-summary`。

老板不关心复杂的勾稽关系，只关心四个问题。所有报表设计围绕核心问题展开：

| 老板问 | 对应报表 | 数据来源 |
|--------|----------|----------|
| **这月赚了多少？** | 月度损益速览 | 利润表+ 本期收入/成本/费用汇总 |
| **仓库压了多少钱？** | 库存资金占用 | StockMove 加权平均成本 × 当前库存量 |
| **客户欠我多少钱？** | 应收汇总 | 往来账龄 + 未收销售单 |
| **这个月该交多少税？** | 税务速算 | 增值税 + 企业所得税 + 附加税 |

税务报表输出格式与税务局电子申报系统一致，数字可直接照抄填写，无需二次计算。
