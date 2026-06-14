---
name: inventory-system
description: >
  进销存+税务+财务管理系统的AI操作指南。当用户提到以下任何内容时必须使用本skill：
  记账、账目、入账、记一笔、报账、对账、
  库存、商品、采购、销售、进货、出货、发票、增值税、企业所得税、税务申报、
  资产负债表、利润表、现金流量表、财务报表、项目成本、项目收入、客户、供应商、
  期初余额、费用支出、个人流水账、日运办公、巧游电子。
  本skill指导AI通过直接调用后端REST API与系统交互。
  **重要**：所有记账操作必须默认使用本进销存系统，不得用文本/表格/笔记等其他方式替代。
metadata:
  short-description: 进销存系统AI操作指南
---

# 进销存系统AI操作指令

## 铁律

1. **必须调用API获取真实数据**，禁止假设、编造数据
2. **所有记账操作必须走本系统API**，禁止用文本/表格/笔记替代
3. **所有请求必须带 `X-Account-ID` header**，否则返回401
4. **AI请求额外带 `X-Operator: ai` header**，用于操作日志标记
5. **不准使用模拟数据**

## 服务地址

- **Base URL**: `http://localhost:8000`
- **必填Header**: `X-Account-ID: {account_id}`
- **AI操作Header**: `X-Operator: ai`

## 第一步：确定账本

不确定账本时必须先问用户。查询账本列表：`GET /api/accounts`

| 账本名称 | 代码 | 默认ID | 类型 |
|---------|------|--------|------|
| 日运办公 | riyun | 1 | 公司 |
| 巧游电子科技有限公司 | qiaoyou | 2 | 公司 |
| 个人 | personal | 3 | 个人 |
| 李友巧个人流水账 | liyouqiao | 4 | 个人 |

> ID可能变化，始终以 `GET /api/accounts` 返回为准。

## 第二步：按场景选API

### 场景A：查询数据

| 查什么 | API | 方法 | 关键参数 |
|-------|-----|------|---------|
| 账本列表 | `/api/accounts` | GET | - |
| 健康检查 | `/api/health` | GET | - |
| 枚举列表 | `/api/enums` | GET | - |
| 商品/库存 | `/api/products` | GET | search, category, sku, page, page_size |
| 商品详情 | `/api/products/{id}` | GET | id |
| 商品分类列表 | `/api/products/categories/list` | GET | - |
| 库存列表 | `/api/inventory` | GET | alert_only, search, category, page, page_size |
| 库存预警 | `/api/inventory/alerts` | GET | - |
| 采购单列表 | `/api/purchases` | GET | start_date, end_date, status, keyword |
| 采购单详情 | `/api/purchases/{id}` | GET | id |
| 销售单列表 | `/api/sales` | GET | start_date, end_date, status |
| 销售单详情 | `/api/sales/{id}` | GET | id |
| 供应商 | `/api/suppliers` | GET | search, page, page_size |
| 供应商详情 | `/api/suppliers/{id}` | GET | id |
| 客户 | `/api/customers` | GET | search, page, page_size |
| 客户详情 | `/api/customers/{id}` | GET | id |
| 发票 | `/api/invoices` | GET | direction, invoice_type, year, quarter, certification_status |
| 发票PDF | `/api/invoices/{id}/pdf` | GET | id |
| 费用 | `/api/expenses` | GET | category, year, skip, limit |
| 项目列表(聚合) | `/api/projects` | GET | - |
| 项目列表(管理) | `/api/projects/list` | GET | - |
| 项目详情 | `/api/projects/{id}/cost-income` | GET | id |
| 项目按名称查询 | `/api/projects/{name}/details` | GET | name |
| 项目成本列表 | `/api/costs` | GET | project_id, skip, limit |
| 项目收入列表 | `/api/costs/incomes` | GET | project_id, skip, limit |
| 个人流水 | `/api/personal` | GET | type, start_date, end_date, page, page_size |
| 个人汇总 | `/api/personal/summary` | GET | - |
| 操作日志 | `/api/logs` | GET | entity_type, operation, start_date, end_date, page, page_size |
| 进销存总览 | `/api/reports/overview` | GET | - |
| 利润报表 | `/api/reports/profit` | GET | - |
| 项目报表 | `/api/reports/project` | GET | - |
| 采购报表 | `/api/reports/purchase` | GET | - |
| 销售报表 | `/api/reports/sale` | GET | - |
| 税务报表 | `/api/reports/tax-report` | GET | - |
| 趋势报表 | `/api/reports/trend` | GET | - |
| 增值税季度报表 | `/api/tax-report` | GET | year, quarter |
| 增值税月度报表 | `/api/tax-report/monthly` | GET | year, month |
| 企业所得税 | `/api/income-tax-report` | GET | year |
| 资产负债表 | `/api/financial-reports/balance-sheet` | GET | date |
| 利润表 | `/api/financial-reports/income-statement` | GET | start_date, end_date |
| 财务汇总 | `/api/financial-reports/financial-summary` | GET | - |
| 现金流量表 | `/api/cash-flows/statement` | GET | start_date, end_date |
| 期初余额 | `/api/opening-balances` | GET | - |
| 期初余额详情 | `/api/opening-balances/{id}` | GET | id |
| 最新期初余额 | `/api/opening-balances/latest` | GET | date |
| 不变量验证 | `/api/projects/verify-invariants` | POST | - |
| 对账修复 | `/api/projects/reconcile` | POST | - |
| 对账汇总 | `/api/reconciliations/` | GET | party_type, start_date, end_date |
| 对账明细 | `/api/reconciliations/detail` | GET | party_type, partner_id, start_date, end_date |

### 场景B：录入数据

**B1：添加商品** `POST /api/products`
```json
{ "name": "商品名", "sku": "唯一编码", "category": "分类", "unit": "个",
  "purchase_price": 20, "sale_price": 25, "min_stock": 5, "initial_stock": 100 }
```

**B2：采购入库** `POST /api/purchases`
```json
{ "supplier_id": 1, "project_id": 1, "has_invoice": false,
  "payment_method": "company", "notes": "备注",
  "items": [{"product_id": 1, "quantity": 10, "unit_price": 25.5, "tax_rate": 0.13}] }
```
> product_id是数字ID，需先 `GET /api/products?search=商品名` 查询获取。project_id 关联项目（推荐），后端自动反查填充 project_name。

**B3：销售出库** `POST /api/sales`
```json
{ "customer_id": 1, "project_id": 1, "deduct_inventory": false, "has_invoice": false,
  "payment_status": "unpaid", "total_price": null, "notes": "备注",
  "items": [{"product_id": 1, "quantity": 5, "unit_price": 30, "tax_rate": 0.01}] }
```
> **project_id** 关联项目（推荐），后端自动反查填充 project_name。
> **deduct_inventory**：是否由销售单直接扣库存。
> - **项目专属销售单**：由项目创建，deduct_inventory=true，扣库存逻辑与零售一致。项目销售单只能通过项目创建，零售单禁止设置 project_id。
> - **零售销售**：project_id 为空，deduct_inventory=true，销售单在 completed 状态下会按 items 扣减库存；取消/删除会回补库存。
> **total_price**（可选）：自定义订单总额。不传或传null时自动按明细合计计算。传值时与明细合计的差额会自动分配到各行单价（支持整单打折、抹零、含税包价等场景）。
> - 单价为0的行优先分配（按数量加权）
> - 所有行都有单价时按金额比例分配（整体打折/加价）
> - 尾差归入最后一行，保证各行合计精确等于自定义总额
> **销售单价**：选择商品后不再自动带指导价(sale_price)，用户需自行填写实际销售单价。
> **同一商品不可重复**：同一订单内同一product_id只能出现一次（后端校验+数据库唯一约束），重复时返回400错误，请合并到一行修改数量。

**B4：记录发票** `POST /api/invoices/quick`（推荐，自动算税）
```json
{ "invoice_no": "发票号", "direction": "in", "invoice_type": "ordinary",
  "amount_with_tax": 113, "tax_rate": 0.13, "counterparty_name": "对方名",
  "issue_date": "2024-01-15", "project_name": "项目名(可选)", "notes": "备注" }
```
- **direction**: in=进项(别人开给我) / out=销项(我开给别人)
- **invoice_type**: ordinary=普票 / special=专票

**B5：认证发票** `POST /api/invoices/{id}/certify` — 仅进项专票，不可逆

**B5.1：上传发票文件** `POST /api/invoices/upload`
> 与quick接口参数相同（通过Form字段提交），额外支持附加PDF文件上传（file字段）。
> Content-Type: multipart/form-data
> 必填字段：file(PDF文件), invoice_no, direction, invoice_type, amount_with_tax, tax_rate, counterparty_name, issue_date
> 可选字段：project_name, notes
> 自动计算不含税金额和税额，创建发票记录并关联PDF文件。

**B5.2：下载发票PDF** `GET /api/invoices/{id}/pdf` — 返回PDF文件流

**B6：记录费用** `POST /api/expenses`
```json
{ "category": "房租", "amount": 5000, "expense_date": "2024-01-15",
  "has_invoice": false, "payment_method": "company", "description": "描述",
  "image_url": "附件(可选)" }
```
- **category只能填**: 房租/水电/工资/材料/办公用品/运费/维修/其他（中文，由 `/api/enums` 管理）

**B7：添加项目成本** `POST /api/costs`
```json
{ "project_id": 1, "cost_type": "材料", "amount": 5000, "product_id": 1, "quantity": 10,
  "payment_method": "company", "invoice_status": "未开", "supplier_name": "供应商(可选)",
  "notes": "备注", "cost_date": "2024-01-15" }
```
- **cost_type只能填**: 材料/人工/差旅/外包/设备/其他（中文）
- **材料类联动**：cost_type="材料"时必填 product_id 和 quantity，创建时自动扣减库存，删除时自动回补，更新时自动调整库存差值
- **非材料类**：product_id 和 quantity 不填，不影响库存

**B8：添加项目收入** `POST /api/costs/incomes`
```json
{ "project_id": 1, "amount": 10000, "payment_status": "pending",
  "received_amount": 0, "invoice_status": "未开", "notes": "备注",
  "income_date": "2024-01-15", "received_date": "2024-01-20" }
```
> **source_type/source_id**：手动录入时可不填（默认 manual），销售单自动生成的收入 source_type='sale_order'、source_id=销售单ID。同一销售单不会重复生成收入（UNIQUE约束保证）。

**B9：记录个人流水** `POST /api/personal`
```json
{ "type": "expense", "amount": 100, "category": "餐饮", "description": "午餐",
  "date": "2024-01-15", "image_url": "附件(可选)" }
```
- 支出category: 餐饮/日用/交通/娱乐/医疗/烟酒/其他
- 收入category: 工资/兼职/理财/其他

**B10：创建项目** `POST /api/projects`
```json
{ "name": "项目名", "customer_id": 1, "status": "ongoing", "start_date": "2024-01-15", "notes": "备注" }
```

**B10.1：项目下直接添加成本** `POST /api/projects/project-costs/`
> 参数同B7，project_id为必填

**B10.2：项目下直接添加收入** `POST /api/projects/project-incomes/`
> 参数同B8，project_id为必填

**B11：创建供应商/客户** `POST /api/suppliers` 或 `POST /api/customers`
```json
{ "name": "名称", "contact": "联系人", "phone": "电话", "address": "地址", "notes": "备注" }
```

**B12：创建期初余额** `POST /api/opening-balances`
```json
{ "date": "2024-01-01", "cash_balance": 10000, "bank_balance": 50000,
  "accounts_receivable": 0, "inventory_value": 0, "accounts_payable": 0,
  "tax_payable": 0, "retained_earnings": 0 }
```

**B13：记录现金流** `POST /api/cash-flows/transactions`
```json
{ "type": "inflow", "amount": 1000, "flow_category": "operating",
  "description": "描述", "transaction_date": "2024-01-15" }
```

**B14：上传图片** `POST /api/upload/image`
> 上传附件图片（JPG/PNG/GIF/WEBP，最大5MB），返回 `image_url` 用于关联到费用/流水等记录。
> 参数：file(文件)、business_type(expense/personal/project_cost等)、record_id(关联记录ID)

**B15：替换图片** `PUT /api/upload/image`
> 上传新图 + 自动删除旧图。额外参数：old_image_url(旧图URL)

**B16：删除图片** `DELETE /api/upload/image?image_url=xxx`
> 仅删除文件，不修改关联记录

### 场景C：更新数据

| 操作 | API | 方法 |
|------|-----|------|
| 更新商品 | `/api/products/{id}` | PUT |
| 更新供应商 | `/api/suppliers/{id}` | PUT |
| 更新客户 | `/api/customers/{id}` | PUT |
| 更新发票 | `/api/invoices/{id}` | PUT |
| 更新费用 | `/api/expenses/{id}` | PUT |
| 更新项目 | `/api/projects/manage/{id}` | PUT |
| 更新项目成本 | `/api/costs/{id}` | PUT |
| 更新项目收入 | `/api/costs/incomes/{id}` | PUT |
| 更新采购单 | `/api/purchases/{id}` | PUT |
| 更新销售单 | `/api/sales/{id}` | PUT |
| 更新个人流水 | `/api/personal/{id}` | PUT |
| 更新期初余额 | `/api/opening-balances/{id}` | PUT |
| 调整库存 | `/api/inventory/{product_id}` | PUT |

### 场景D：删除数据

| 操作 | API | 方法 |
|------|-----|------|
| 删除商品 | `/api/products/{id}` | DELETE |
| 删除供应商 | `/api/suppliers/{id}` | DELETE |
| 删除客户 | `/api/customers/{id}` | DELETE |
| 删除发票 | `/api/invoices/{id}` | DELETE |
| 删除费用 | `/api/expenses/{id}` | DELETE |
| 删除项目 | `/api/projects/manage/{id}` | DELETE |
| 删除项目成本 | `/api/costs/{id}` | DELETE |
| 删除项目收入 | `/api/costs/incomes/{id}` | DELETE |
| 删除采购单 | `/api/purchases/{id}` | DELETE |
| 删除销售单 | `/api/sales/{id}` | DELETE |
| 删除个人流水 | `/api/personal/{id}` | DELETE |
| 删除期初余额 | `/api/opening-balances/{id}` | DELETE |

> 有关联记录的实体删除会失败，需告知用户原因。

### 场景E：数据导出

> **所有导出请求必须带 `X-Account-ID` header**，否则返回401。

| 导出什么 | API | 方法 | 格式 | 关键参数 |
|---------|-----|------|------|----------|
| 商品导出 | `/api/export/products` | GET | xlsx/csv | `search`, `category` |
| 库存导出 | `/api/export/inventory` | GET | xlsx/csv | `alert_only` |
| 采购导出 | `/api/export/purchases` | GET | xlsx/csv | `start_date`, `end_date` |
| 销售导出 | `/api/export/sales` | GET | xlsx/csv | `start_date`, `end_date` |
| 利润导出 | `/api/export/profit` | GET | xlsx/csv | `start_date`, `end_date` |
| 批量商品导出 | `/api/export/products-batch` | GET | xlsx/csv | `product_ids`（逗号分隔ID，必填） |

### 场景F：热备份

| 操作 | API | 方法 | 说明 |
|------|-----|------|------|
| 执行热备份 | `/api/backup/hot` | POST | SQLite在线备份+图片+PDF→zip，保留最近12份 |
| 备份列表 | `/api/backup/list` | GET | 按时间倒序列出所有备份文件 |
| 下载备份 | `/api/backup/download/{filename}` | GET | 下载指定zip备份文件 |

### 场景G：联动验证与对账

**G1：不变量验证** `POST /api/projects/verify-invariants`
> 验证三大不变量，返回违规项列表。日常巡检使用。
> - 不变量I（库存）：检查是否存在负库存
> - 不变量II（收入）：检查同一销售单是否生成重复收入
> - 不变量III（汇总）：检查项目汇总是否与明细重算一致

**G2：对账修复** `POST /api/projects/reconcile`
> 重算所有项目汇总，修复汇总不变量(III)违规。数据异常时使用。
> 返回修复的项目列表（修复前/后对比）。

**G3：对账管理** `GET /api/reconciliations/`
> 按供应商/客户维度实时计算对账汇总（期初欠款、本期发生、已收/已付、期末欠款、发票金额），按期末欠款降序排列。
> - party_type：supplier（供应商）/ customer（客户），必填
> - start_date / end_date：筛选期间

**G4：对账明细** `GET /api/reconciliations/detail`
> 查看单个供应商/客户的对证明细（订单+发票）。
> - party_type + partner_id（必填）：指定对方
> - start_date / end_date：筛选期间

## 第三步：税务逻辑

### 增值税（先确认纳税人身份）

**小规模纳税人**（small_scale）：不可抵扣进项
```
应纳税额 = 销项税额（全额缴纳）
```

**一般纳税人**（general）：可抵扣已认证进项专票
```
应纳税额 = max(销项税额 - 进项专票税额(certified), 0)
```

API：`GET /api/tax-report?year=YYYY&quarter=Q` 或 `GET /api/tax-report/monthly?year=YYYY&month=M`

### 企业所得税
```
收入 = 全年已完成销售总额
成本 = 全年已完成采购总额
费用 = 全年Expense总额
企业所得税 = max(收入 - 成本 - 费用, 0) × 5%
```

API：`GET /api/income-tax-report?year=YYYY`

### 资产负债表 / 利润表 / 现金流量表
分别调用：`/api/financial-reports/balance-sheet`、`/api/financial-reports/income-statement`、`/api/cash-flows/statement`

## 第四步：返回结果

必须包含：操作是否成功 + 具体数据结果 + 计算过程（如有）

## 错误处理

| 状态码 | 含义 | 处理 |
|--------|------|------|
| 400 | 参数错误 | 检查必填参数、日期格式(YYYY-MM-DD) |
| 401 | 缺少X-Account-ID | 先确认账本 |
| 404 | 资源不存在 | 确认ID正确 |
| 409 | 数据冲突 | 告知用户具体原因（SKU重复/供应商有采购记录/客户有销售记录） |
| 422 | 校验失败 | 错误信息会指出哪个字段的哪个值不合法+合法值列表 |
| 500 | 服务器异常 | 提示用户联系管理员 |
| 连接失败 | 后端未启动 | 提示双击桌面"启动进销存系统.bat" |

> **409常见场景**：删除供应商时有关联采购单、删除客户时有关联销售单或项目、SKU重复（当前sku无unique约束，此场景暂不触发）

## 关键字段限制

| 字段 | 合法值 |
|------|--------|
| 税率 | 0.01 / 0.03 / 0.06 / 0.09 / 0.13 |
| 成本类型 | 材料/人工/差旅/外包/设备/其他（中文） |
| 费用类别 | 房租/水电/工资/材料/办公用品/运费/维修/其他（中文） |
| 个人支出类别 | 餐饮/日用/交通/娱乐/医疗/烟酒/其他（中文） |
| 个人收入类别 | 工资/兼职/理财/其他（中文） |
| 支付方式 | company / private_advance |
| 项目状态 | ongoing / completed / cancelled |
| 发票方向 | in(进项) / out(销项) |
| 发票类型 | ordinary(普票) / special(专票) |
| 认证状态 | n_a / certified / pending |
| 现金流方向 | inflow / outflow |
| 现金流类别 | operating / investing / financing |
| 图片业务类型 | expense / personal / project_cost / invoice |
| 收入来源类型 | manual(手动) / sale_order(销售单自动) |
| 销售扣库存开关 | deduct_inventory: true/false（项目专属销售单和零售单必须true；零售单禁止设置project_id） |
| 销售自定义总额 | total_price: 可选float，null=自动计算，传值则差额分配到行单价 |
| 采购单付款状态 | payment_status: paid/unpaid（PurchaseOrderUpdate现已支持修改） |
| 同一商品重复 | 同一订单内同一product_id只能出现一次，重复返回400 |
| 对账类型 | party_type: supplier / customer |
| 图片格式 | JPG/PNG/GIF/WEBP，最大5MB |
| 日期格式 | YYYY-MM-DD |

> 所有分类枚举由 `/api/enums` 统一管理，`backend/enums.py` 为单一真相源。

## 操作反馈（强制执行）

每次录入/修改/删除后必须提供：

```
【操作反馈】
工作内容 — 调用了哪个API、传了什么参数
困难/错误 — 有无报错、怎么解决的
最终结果 — 是否成功、记录摘要（关键数字、ID、状态）
```

## 对抗性检查（录入前必须自问）

1. **归属验证**：这条记录属于当前账本吗？发票对方名称匹配吗？
2. **数据合理性**：单价/数量/税率是否合理？商品是否存在需先添加？
3. **逻辑一致性**：进项/销项方向对吗？专票/普票选对了吗？product_id是数字ID不是名称？

## 常见误判

| 误区 | 正确做法 |
|------|---------|
| 日运 vs 巧游混淆 | 录入前必须确认账本 |
| 进项/销项方向反 | 进项(in)=别人开给我，销项(out)=我开给别人 |
| 专票/普票选错 | 专票(special)可抵扣，普票(ordinary)不可 |
| 商品名当product_id | 必须先查询获取数字ID |
| 个人垫付vs公司付款 | payment_method不同，影响现金流 |
| 金额≥1000元 | 执行前必须向用户复述关键参数并确认 |

## 联动机制（v2.4改造）

### 核心联动链路

```
采购单(project_id) → 入库（库存增加）
项目专属销售单(project_id) → 扣库存 + 自动生成项目收入
零售销售单(project_id=NULL, deduct_inventory=true) → 扣库存
项目领料(材料类成本) → 出库（库存扣减）+ 项目成本记录
```

### 三大不变量

| # | 不变量 | 含义 | 保障 |
|---|--------|------|------|
| I | 库存不变量 | 销售单扣库存/回补与实际库存变动一致；材料成本变动后库存变化=数量差值；不允许负库存 | 扣减前校验+assert+UNIQUE索引+deduct_inventory统一条件 |
| II | 收入不变量 | 同一销售单最多一条自动收入；已有sale_order收入时禁止手动创建 | 幂等检查+uq_income_source唯一索引+冲突校验 |
| III | 汇总不变量 | 项目total_cost=销售单商品进价×数量；total_income=收入合计；profit=收入-成本 | update_project_summary统一重算 |

### 工作流程

```
项目生命周期：创建项目 → 生成空销售单 → 添加商品(售价+成本价) → 库存随销售单扣减/回补
                 → 销售单完成 → 自动生成项目收入 → 汇总重算
                 → 删除一行成本 → 库存立即回补(逐行精度)

零售生命周期：创建零售单(deduct_inventory=true) → 完成扣库存 → 取消回补库存
                 → 零售单禁止关联project_id

采购生命周期：创建采购单 → 入库(库存增加) → 可关联项目(反查填充project_name)
```

### 联动注意事项

1. **项目专属销售单必须扣库存**：项目创建时自动生成空销售单，后续添加商品时库存随销售单变动（扣减/回补），与零售销售单逻辑一致
   - **零售销售单**：deduct_inventory=true，status=completed 时直接扣库存；取消/删除时回补
   - **项目专属销售单**：由项目创建，deduct_inventory=true，扣库存逻辑与零售一致
   - **零售单禁止关联项目**：普通零售销售单不允许设置 project_id，项目销售单只能由项目创建
2. **材料类成本必填product_id+quantity**：cost_type="材料"时必须关联商品和数量，否则无法联动库存。材料类成本为出库记录/备注，不参与项目total_cost计算
3. **库存不足时报错**：材料领料或销售单扣库存时，超出库存返回400错误，整个事务回滚
4. **删除成本自动回补库存**：删除材料类成本时，库存自动恢复
5. **删除销售单联动删除收入**：删除关联项目的销售单时，自动删除对应的项目收入
6. **项目删除前置校验**：项目下有未取消的销售单/采购单时禁止删除，需先取消或解除关联
7. **日常巡检**：定期调用 `POST /api/projects/verify-invariants` 检查数据一致性
8. **数据异常修复**：汇总不一致时调用 `POST /api/projects/reconcile` 对账修复

### 项目详情效率小技巧（前端已增强）

- 项目收入明细若 `source_type='sale_order'` 且存在 `source_id`，可直接调用 `GET /api/sales/{source_id}` 追溯对应销售单明细（用于核对收入来源）。

## 启动服务

后端未启动时提示用户双击桌面 `启动进销存系统.bat`，或手动启动：
```
cd Desktop\inventory-system\backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---
版本：v6.0.0 | 更新日期：2026-06-02 | 变更：项目专属销售单扣库存逻辑统一、零售单禁止关联项目、total_cost改为销售单商品进价×数量、收入冲突检查
