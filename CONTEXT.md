# CONTEXT.md - 进销存管理系统

## 项目概述

面向中小企业的全栈业务管理平台，涵盖库存管理、采购/销售、项目归集、财务报表及个人账单等核心模块。

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

```
Routers → Commands → CRUD / Domain → Events → EventBus
```

### 核心模块

- **Routers**: API 路由层，处理 HTTP 请求。读操作直接调用 CRUD，写操作通过 Commands
- **Commands**: 命令模式，封装全部写操作。伙伴管理已合并为通用 Partner 命令
- **CRUD**: 数据访问层。写操作已迁移至 Commands，本层仅保留查询和报表
- **Domain**: 领域模型，业务规则验证
- **Events**: 领域事件
- **EventBus**: 事件总线，负责日志和汇总重算

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
│   │   └── personal_commands.py
│   ├── crud/           # 数据访问（仅查询 + 报表）
│   │   ├── base.py            # 公共函数（_log, _generate_order_no）
│   │   ├── products.py        # 商品 + 库存查询
│   │   ├── partners.py        # 伙伴查询（只读）
│   │   ├── orders.py          # 订单查询（只读）
│   │   ├── invoices.py        # 发票查询 + 税务报表
│   │   ├── finance.py         # 财务查询 + 报表生成
│   │   ├── personal.py        # 个人流水查询 + 统计
│   │   ├── inventory_ops.py   # 库存操作（扣减/恢复）
│   │   ├── reports.py         # 统计报表
│   │   └── logs.py            # 操作日志查询
│   ├── domain/         # 领域模型
│   │   ├── base.py            # 基类
│   │   ├── inventory.py       # 库存业务规则
│   │   ├── money.py           # 金额值对象
│   │   ├── purchase_order.py  # 采购单业务规则
│   │   └── sale_order.py      # 销售单业务规则
│   ├── models.py       # ORM 模型
│   ├── schemas/        # Pydantic 模式
│   └── enums.py        # 枚举定义
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

### BR-2:经营口径与税务口径

| 口径 | 取数源 | 用途 |
|------|--------|------|
| 经营口径 | **订单金额**(SaleOrder.total_price,含税) | 利润表、内部经营分析 |
| 税务口径 | **发票金额**(Invoice.amount_without_tax,不含税) | 增值税报表、企业所得税申报 |

- 利润表(经营口径)= 无票收入 + 有票收入,两者均取**订单金额**。录入销售单时 `has_invoice` 必填(真=已开票 / 假=无票),用于利润表分两行列示。
- 经营口径与税务口径金额天然不同(含税 vs 不含税),**不视为 bug**。利润表应单列"其中:已开票收入(含税)"便于与税务报表对账。
- **禁止**把两个口径混用或强求一致。

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
