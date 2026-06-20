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
