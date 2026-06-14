# AI Agent 记账助手使用指南

> 本文档供 AI Agent（如 Claude、GPT 等）理解并操作本进销存管理系统的后端 API，帮助用户完成日常记账。

---

## 1. 系统概览

- **后端地址**: `http://localhost:8000`
- **API 前缀**: `/api`
- **认证方式**: 无 Token，通过 `X-Account-ID` 请求头区分账本
- **操作者标识**: `X-Operator` 请求头（AI 请求传 `ai`）

### 必须携带的请求头

```
X-Account-ID: 1        # 账本ID，通常为 1
X-Operator: ai         # 标识操作来源为 AI
Content-Type: application/json
```

---

## 2. 核心业务流程

### 2.1 采购流程

```
创建商品 → 创建供应商 → 创建采购单（自动增加库存）
```

### 2.2 销售流程

```
创建客户 → 创建销售单（可选自动扣减库存）
```

### 2.3 项目记账流程

```
创建项目 → 关联采购单/销售单到项目 → 或手动添加项目成本/收入
```

### 2.4 发票记账流程

```
创建发票（进项/销项） → 进项专票认证 → 季度税务统计
```

---

## 3. API 详细参考

### 3.1 商品管理 `/api/products`

#### 创建商品
```
POST /api/products
```
```json
{
  "name": "钢材",
  "sku": "STL-001",
  "category": "材料",
  "unit": "吨",
  "purchase_price": 3500.00,
  "sale_price": 4200.00,
  "min_stock": 10,
  "description": "Q235B钢材",
  "initial_stock": 100
}
```

#### 查询商品列表
```
GET /api/products?page=1&page_size=20&search=钢材&category=材料
```

#### 获取单个商品
```
GET /api/products/{product_id}
```

#### 更新商品
```
PUT /api/products/{product_id}
```
```json
{
  "name": "钢材（新）",
  "sale_price": 4500.00
}
```

#### 删除商品
```
DELETE /api/products/{product_id}
```

#### 获取分类列表
```
GET /api/products/categories/list
```

---

### 3.2 供应商管理 `/api/suppliers`

#### 创建供应商
```
POST /api/suppliers
```
```json
{
  "name": "XX钢铁公司",
  "contact": "张三",
  "phone": "13800138000",
  "address": "XX市XX路",
  "notes": ""
}
```

#### 查询供应商列表
```
GET /api/suppliers?page=1&page_size=20&search=钢铁
```

#### 获取单个供应商
```
GET /api/suppliers/{supplier_id}
```

#### 更新供应商
```
PUT /api/suppliers/{supplier_id}
```

#### 删除供应商
```
DELETE /api/suppliers/{supplier_id}
```

---

### 3.3 客户管理 `/api/customers`

#### 创建客户
```
POST /api/customers
```
```json
{
  "name": "XX装修公司",
  "contact": "李四",
  "phone": "13900139000",
  "address": "XX市XX街",
  "notes": ""
}
```

#### 查询客户列表
```
GET /api/customers?page=1&page_size=20&search=装修
```

#### 获取/更新/删除客户
```
GET    /api/customers/{customer_id}
PUT    /api/customers/{customer_id}
DELETE /api/customers/{customer_id}
```

---

### 3.4 采购管理 `/api/purchases`

#### 创建采购单
```
POST /api/purchases
```
```json
{
  "supplier_id": 1,
  "project_id": null,
  "project_name": "",
  "order_type": "retail",
  "has_invoice": true,
  "payment_method": "company",
  "notes": "采购钢材",
  "items": [
    {
      "product_id": 1,
      "quantity": 50,
      "unit_price": 3500.00,
      "tax_rate": 0.13,
      "notes": ""
    }
  ]
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `supplier_id` | int | 否 | 供应商ID，不填则为散客 |
| `project_id` | int | 否 | 关联项目ID |
| `order_type` | str | 否 | `retail`(零售) / `project`(项目型) / `purchase_labor`(人力采购)，默认 `retail` |
| `has_invoice` | bool | 否 | 是否有发票 |
| `payment_method` | str | 否 | `company`(公司) / `private_advance`(个人垫付) |
| `items` | array | 是 | 采购商品明细，至少1项 |
| `items[].product_id` | int | 是 | 商品ID |
| `items[].quantity` | int | 是 | 数量 |
| `items[].unit_price` | number | 是 | 单价 |
| `items[].tax_rate` | number | 否 | 税率（如 0.13 表示13%） |

> **自动行为**: 创建采购单后自动增加库存（按 `quantity` 增加）。

#### 查询采购单列表
```
GET /api/purchases?page=1&page_size=20&start_date=2026-01-01&end_date=2026-12-31&status=completed&order_type=retail
```

#### 获取单个采购单
```
GET /api/purchases/{purchase_id}
```

#### 更新采购单（全量替换明细）
```
PUT /api/purchases/{purchase_id}
```
```json
{
  "items": [
    {"product_id": 1, "quantity": 60, "unit_price": 3400.00}
  ],
  "total_price": 204000.00,
  "supplier_id": 1,
  "has_invoice": true,
  "payment_method": "company",
  "notes": "修改后的备注"
}
```

> **注意**: 传 `items` 会全量替换原明细，同时自动调整库存差额。

#### 取消采购单
```
PUT /api/purchases/{purchase_id}
```
```json
{
  "status": "cancelled"
}
```
> **自动行为**: 取消时自动回退库存。

#### 删除采购单
```
DELETE /api/purchases/{purchase_id}
```
> **自动行为**: 删除时自动回退库存。

#### 更新采购单字段（不改明细）
```
PUT /api/purchases/{purchase_id}
```
```json
{
  "payment_status": "paid",
  "notes": "已付款"
}
```

---

### 3.5 销售管理 `/api/sales`

#### 创建销售单
```
POST /api/sales
```
```json
{
  "customer_id": 1,
  "project_id": null,
  "project_name": "",
  "order_type": "retail",
  "deduct_inventory": true,
  "has_invoice": false,
  "payment_status": "unpaid",
  "notes": "销售钢材",
  "total_price": 210000.00,
  "items": [
    {
      "product_id": 1,
      "quantity": 50,
      "unit_price": 4200.00,
      "tax_rate": 0.13,
      "notes": ""
    }
  ]
}
```

**字段说明**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `customer_id` | int | 否 | 客户ID，不填则为散客 |
| `project_id` | int | 否 | 关联项目ID |
| `deduct_inventory` | bool | 否 | 是否扣减库存，零售单和项目专属销售单必须为 `true` |
| `payment_status` | str | 否 | `unpaid` / `partial` / `paid`，默认 `unpaid` |
| `total_price` | number | 否 | 销售总价，不传则按明细自动合计；传值时差额分配到各行单价（支持打折/抹零/包价） |
| `items` | array | 是 | 销售商品明细 |

> **自动行为**: 当 `deduct_inventory=true` 时，创建后自动扣减库存；零售单和项目专属销售单均必须设为 `true`。

#### 查询销售单列表
```
GET /api/sales?page=1&page_size=20&start_date=2026-01-01&end_date=2026-12-31&status=completed
```

#### 获取/更新/取消/删除销售单
```
GET    /api/sales/{sale_id}
PUT    /api/sales/{sale_id}     # 支持更新明细、取消、改字段
DELETE /api/sales/{sale_id}
```

> 销售单取消使用 `"status": "cancelled"`，恢复使用 `"status": "completed"`。

---

### 3.6 库存管理 `/api/inventory`

#### 查询库存列表
```
GET /api/inventory?page=1&page_size=20&search=钢材&alert_only=false&category=材料
```

#### 获取库存预警
```
GET /api/inventory/alerts
```
> 返回库存低于 `min_stock` 的商品列表。

#### 手动调整库存
```
PUT /api/inventory/{product_id}
```
```json
{
  "quantity": 150
}
```
> **注意**: 这是设置绝对数量，不是增减。设置为 150 表示将库存调整为 150。

---

### 3.7 项目管理 `/api/projects`

#### 创建项目
```
POST /api/projects
```
```json
{
  "name": "XX工程",
  "customer_id": 1,
  "status": "ongoing",
  "start_date": "2026-05-01",
  "contract_amount": 500000.00,
  "notes": ""
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | str | `ongoing`(进行中) / `completed`(已完成) / `cancelled`(已取消) |
| `contract_amount` | number | 合同金额 |

#### 查询项目列表
```
GET /api/projects
```
> 返回每个项目的成本合计、收入合计、利润、关联订单数。

#### 获取项目详情（成本+收入+采购单）
```
GET /api/projects/{project_id}/cost-income
```

#### 更新项目
```
PUT /api/projects/manage/{project_id}
```
```json
{
  "status": "completed",
  "notes": "项目已完成"
}
```

#### 删除项目
```
DELETE /api/projects/manage/{project_id}
```

#### 验证三大不变量
```
POST /api/projects/verify-invariants
```

#### 对账修复
```
POST /api/projects/reconcile
```

---

### 3.8 项目成本管理 `/api/costs`

#### 添加项目成本
```
POST /api/costs
```
```json
{
  "project_id": 1,
  "cost_type": "材料",
  "amount": 15000.00,
  "payment_method": "company",
  "invoice_status": "已开",
  "supplier_name": "XX钢铁公司",
  "notes": "采购钢材",
  "cost_date": "2026-05-01",
  "product_id": 1,
  "quantity": 50
}
```

**`cost_type` 合法值**: `材料`、`人工`、`差旅`、`外包`、`设备`、`其他`

#### 查询项目成本
```
GET /api/costs?project_id=1
```

#### 更新项目成本
```
PUT /api/costs/{cost_id}
```

#### 删除项目成本
```
DELETE /api/costs/{cost_id}
```

---

### 3.9 项目收入管理 `/api/costs/incomes`

#### 添加项目收入
```
POST /api/costs/incomes
```
```json
{
  "project_id": 1,
  "amount": 50000.00,
  "income_date": "2026-05-15",
  "notes": "首期收款"
}
```

#### 查询项目收入
```
GET /api/costs/incomes?project_id=1
```

#### 更新项目收入
```
PUT /api/costs/incomes/{income_id}
```
```json
{
  "amount": 50000.00,
  "payment_status": "paid",
  "received_amount": 50000.00,
  "invoice_status": "已开",
  "income_date": "2026-05-15",
  "received_date": "2026-05-20",
  "notes": "已全额收到"
}
```

#### 删除项目收入
```
DELETE /api/costs/incomes/{income_id}
```

---

### 3.10 发票管理 `/api/invoices`

#### 创建发票（完整版）
```
POST /api/invoices
```
```json
{
  "invoice_no": "12345678",
  "direction": "out",
  "invoice_type": "special",
  "tax_rate": 0.13,
  "amount_without_tax": 100000.00,
  "tax_amount": 13000.00,
  "amount_with_tax": 113000.00,
  "counterparty_name": "XX装修公司",
  "issue_date": "2026-05-01",
  "certification_status": "n_a",
  "project_name": "XX工程",
  "notes": ""
}
```

#### AI 快捷录入发票（推荐）
```
POST /api/invoices/quick
```
```json
{
  "invoice_no": "12345679",
  "direction": "out",
  "invoice_type": "ordinary",
  "tax_rate": 0.01,
  "amount_with_tax": 10100.00,
  "counterparty_name": "XX客户",
  "issue_date": "2026-05-01",
  "project_name": "",
  "notes": ""
}
```
> **优势**: 只需传 `amount_with_tax` 和 `tax_rate`，系统自动计算 `amount_without_tax` 和 `tax_amount`。

**字段说明**:
| 字段 | 说明 |
|------|------|
| `direction` | `in`(进项/收到的发票) / `out`(销项/开出的发票) |
| `invoice_type` | `ordinary`(普通发票) / `special`(专用发票) |
| `tax_rate` | 税率：`0.01`(1%)、`0.03`(3%)、`0.06`(6%)、`0.09`(9%)、`0.13`(13%) |
| `certification_status` | `n_a`(无需认证) / `pending`(待认证) / `certified`(已认证) |

#### 查询发票列表
```
GET /api/invoices?direction=out&invoice_type=special&year=2026&quarter=2&certification_status=pending
```

#### 认证进项专票
```
POST /api/invoices/{invoice_id}/certify
```
> 只有 `direction=in` 且 `invoice_type=special` 的发票才需要认证。

#### 更新/删除发票
```
PUT    /api/invoices/{invoice_id}
DELETE /api/invoices/{invoice_id}
```

---

### 3.11 税务报表

#### 增值税季度报表
```
GET /api/tax-report?year=2026&quarter=2
```
> 返回：销项税额、进项税额、应纳税额、发票明细。

#### 增值税月度报表
```
GET /api/tax-report/monthly?year=2026&month=5
```

#### 企业所得税报表
```
GET /api/income-tax-report?year=2026&quarter=2
```
> 返回：总收入、总成本、费用、毛利润、应纳税所得额、应纳所得税。

---

### 3.12 费用管理 `/api/expenses`

#### 创建费用
```
POST /api/expenses
```
```json
{
  "project_name": "",
  "category": "房租",
  "amount": 5000.00,
  "expense_date": "2026-05-01",
  "has_invoice": true,
  "payment_method": "company",
  "description": "5月房租"
}
```

**`category` 合法值**: `房租`、`水电`、`工资`、`材料`、`办公用品`、`运费`、`维修`、`其他`

#### 查询费用列表
```
GET /api/expenses?category=房租&year=2026
```

#### 更新/删除费用
```
PUT    /api/expenses/{expense_id}
DELETE /api/expenses/{expense_id}
```

---

### 3.13 对账管理 `/api/reconciliations`

#### 供应商对账汇总
```
GET /api/reconciliations?party_type=supplier&start_date=2026-05-01&end_date=2026-05-31
```

#### 客户对账汇总
```
GET /api/reconciliations?party_type=customer&start_date=2026-05-01&end_date=2026-05-31
```

#### 单个合作伙伴对账明细
```
GET /api/reconciliations/detail?party_type=supplier&partner_id=1&start_date=2026-05-01&end_date=2026-05-31
```

---

### 3.14 财务报表 `/api/financial-reports`

#### 资产负债表
```
GET /api/financial-reports/balance-sheet?date=2026-05-31
```

#### 利润表
```
GET /api/financial-reports/income-statement?start_date=2026-01-01&end_date=2026-05-31
```

#### 财务汇总
```
GET /api/financial-reports/financial-summary?date=2026-05-31
```

---

### 3.15 期初余额 `/api/opening-balances`

#### 创建期初余额
```
POST /api/opening-balances
```
```json
{
  "date": "2026-01-01",
  "cash_balance": 50000.00,
  "bank_balance": 200000.00,
  "accounts_receivable": 80000.00,
  "inventory_value": 150000.00,
  "accounts_payable": 60000.00,
  "tax_payable": 15000.00,
  "retained_earnings": 300000.00
}
```

#### 查询期初余额
```
GET /api/opening-balances
GET /api/opening-balances/latest?date=2026-05-01
```

---

### 3.16 现金流量 `/api/cash-flows`

#### 创建现金流水
```
POST /api/cash-flows/transactions
```
```json
{
  "type": "inflow",
  "amount": 50000.00,
  "flow_category": "operating",
  "description": "收到客户货款",
  "transaction_date": "2026-05-15"
}
```

**`type`**: `inflow`(流入) / `outflow`(流出)
**`flow_category`**: `operating`(经营活动) / `investing`(投资活动) / `financing`(筹资活动)

#### 查询现金流水
```
GET /api/cash-flows/transactions?start_date=2026-05-01&end_date=2026-05-31&flow_category=operating
```

#### 现金流量表
```
GET /api/cash-flows/statement?start_date=2026-01-01&end_date=2026-05-31
```

---

### 3.17 个人流水 `/api/personal`

#### 创建个人记录
```
POST /api/personal
```
```json
{
  "type": "expense",
  "amount": 50.00,
  "category": "餐饮",
  "description": "午餐",
  "date": "2026-05-01"
}
```

**收入 category**: `工资`、`兼职`、`理财`、`其他`
**支出 category**: `餐饮`、`日用`、`交通`、`娱乐`、`医疗`、`烟酒`、`其他`

#### 查询个人流水
```
GET /api/personal?page=1&type=expense&category=餐饮&start_date=2026-05-01&end_date=2026-05-31
```

#### 个人汇总
```
GET /api/personal/summary
GET /api/personal/monthly_summary?type=expense&months=6
GET /api/personal/category_summary?type=expense&start_date=2026-01-01&end_date=2026-12-31
```

---

### 3.18 枚举值查询 `/api/enums`

```
GET /api/enums
```
> 返回所有枚举值定义，包括 `expense_categories`、`cost_types`、`payment_status`、`invoice_direction` 等。

---

### 3.19 账本管理 `/api/accounts`

#### 查询账本列表
```
GET /api/accounts
```
> 返回所有账本，无需 X-Account-ID 请求头。

#### 创建账本
```
POST /api/accounts
```
```json
{
  "name": "新公司账本",
  "type": "company",
  "code": "new_company",
  "taxpayer_type": "small_scale"
}
```

**`type`**: `company`(公司) / `personal`(个人)
**`taxpayer_type`**: `small_scale`(小规模纳税人) / `general`(一般纳税人)

#### 更新账本名称
```
PUT /api/accounts/{account_id}
```
```json
{
  "name": "新名称"
}
```

---

### 3.20 备份管理 `/api/backup`

#### 执行热备份
```
POST /api/backup/hot
```
> 立即创建数据库备份（SQLite 热备 + ZIP 压缩）。

#### 查询备份列表
```
GET /api/backup/list
```

#### 下载备份文件
```
GET /api/backup/download/{filename}
```

---

### 3.21 操作日志 `/api/logs`

```
GET /api/logs?page=1&page_size=50&start_date=2026-05-01&end_date=2026-05-31
```
> 返回系统中所有操作的审计日志。

---

### 3.22 数据导出 `/api/export`

```
GET /api/export/products?format=excel
GET /api/export/products-batch?product_ids=1,2,3&format=excel
GET /api/export/purchases?format=excel
GET /api/export/sales?format=excel
GET /api/export/invoices?format=excel
GET /api/export/expenses?format=excel
```
> 支持 `excel` 和 `csv` 格式。部分导出需要 `X-Account-ID` 请求头。

---

### 3.23 图片上传 `/api/upload/image`

#### 上传图片
```
POST /api/upload/image
Content-Type: multipart/form-data
file: <图片文件>
business_type: expense
record_id: 1
```
> 支持 JPG/PNG/GIF/WEBP，最大 5MB。

#### 替换图片
```
PUT /api/upload/image
Content-Type: multipart/form-data
file: <新图片>
old_image_url: /uploads/images/expense_1_xxx.jpg
```

#### 删除图片
```
DELETE /api/upload/image?image_url=/uploads/images/expense_1_xxx.jpg
```

---

### 3.24 健康检查 `/api/health`

```
GET /api/health
```
> 返回 `{"status": "ok"}`，用于确认服务是否运行。

---

## 4. 常用记账场景示例

### 场景1：记录一笔采购

```bash
# 1. 创建供应商（如果不存在）
curl -X POST http://localhost:8000/api/suppliers \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"name": "XX钢铁公司", "phone": "13800138000"}'

# 2. 创建商品（如果不存在）
curl -X POST http://localhost:8000/api/products \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"name": "钢材", "sku": "STL-001", "unit": "吨", "purchase_price": 3500, "sale_price": 4200}'

# 3. 创建采购单（自动增加库存）
curl -X POST http://localhost:8000/api/purchases \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{
    "supplier_id": 1,
    "has_invoice": true,
    "payment_method": "company",
    "items": [{"product_id": 1, "quantity": 50, "unit_price": 3500, "tax_rate": 0.13}]
  }'
```

### 场景2：记录一笔销售

```bash
# 创建销售单（自动扣减库存）
curl -X POST http://localhost:8000/api/sales \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "deduct_inventory": true,
    "payment_status": "unpaid",
    "total_price": 210000,
    "items": [{"product_id": 1, "quantity": 50, "unit_price": 4200, "tax_rate": 0.13}]
  }'
```

### 场景3：记录发票

```bash
# AI 快捷录入（推荐）
curl -X POST http://localhost:8000/api/invoices/quick \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{
    "invoice_no": "12345678",
    "direction": "out",
    "invoice_type": "ordinary",
    "tax_rate": 0.01,
    "amount_with_tax": 10100,
    "counterparty_name": "XX客户",
    "issue_date": "2026-05-01"
  }'
```

### 场景4：查看本月税务

```bash
# 当前季度增值税报表
curl "http://localhost:8000/api/tax-report?year=2026&quarter=2" \
  -H "X-Account-ID: 1"

# 企业所得税
curl "http://localhost:8000/api/income-tax-report?year=2026&quarter=2" \
  -H "X-Account-ID: 1"
```

### 场景5：项目记账

```bash
# 1. 创建项目
curl -X POST http://localhost:8000/api/projects \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"name": "XX工程", "customer_id": 1, "contract_amount": 500000}'

# 2. 添加项目成本
curl -X POST http://localhost:8000/api/costs \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"project_id": 1, "cost_type": "材料", "amount": 15000, "cost_date": "2026-05-01"}'

# 3. 添加项目收入
curl -X POST http://localhost:8000/api/costs/incomes \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"project_id": 1, "amount": 50000, "income_date": "2026-05-15", "notes": "首期款"}'

# 4. 查看项目利润
curl "http://localhost:8000/api/projects/1/cost-income" -H "X-Account-ID: 1"
```

### 场景6：标记采购单已付款

```bash
curl -X PUT http://localhost:8000/api/purchases/1 \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"payment_status": "paid"}'
```

---

## 5. 重要业务规则

### 5.1 库存联动
- **采购单创建** → 库存自动增加
- **采购单取消/删除** → 库存自动回退
- **销售单创建（`deduct_inventory=true`）** → 库存自动扣减
- **销售单取消/删除** → 库存自动回退

### 5.2 项目汇总联动
- 采购单关联项目 → 项目成本自动更新
- 销售单关联项目 → 项目收入自动更新
- 手动添加项目成本/收入 → 项目利润自动重算

### 5.3 三大不变量
系统维护三个数据一致性不变量：
1. **库存一致性**: 采购/销售/手动调整的库存变动必须一致
2. **项目收入一致性**: 项目收入来源（销售单/手动）必须一致
3. **项目汇总一致性**: 项目总成本/总收入/利润必须等于各明细之和

### 5.4 状态流转
| 实体 | 状态值 | 说明 |
|------|--------|------|
| 采购单 | `pending` → `completed` → `cancelled` | 新建→完成→取消 |
| 销售单 | `pending` → `completed` → `cancelled` | 可从cancelled恢复到completed |
| 项目 | `ongoing` → `completed` / `cancelled` | 进行中→已完成/已取消 |
| 支付 | `unpaid` → `partial` → `paid` | 未付→部分付→已付 |

---

## 6. 错误处理

| HTTP 状态码 | 含义 | 常见原因 |
|-------------|------|----------|
| 400 | 请求错误 | 业务逻辑校验失败（如删除被引用的数据） |
| 401 | 未授权 | 缺少 `X-Account-ID` 请求头 |
| 404 | 不存在 | ID 无效或不属于当前账本 |
| 409 | 数据冲突 | 唯一约束冲突（如商品编码重复） |
| 422 | 参数校验失败 | 枚举值不合法（响应中会提示合法值列表） |
| 500 | 服务器错误 | 未预期的异常 |

---

## 7. AI Agent 必须遵守

1. **先查后写**: 操作前先查询确认数据是否存在（如商品、供应商、客户）
2. **幂等创建**: 创建商品/供应商/客户时先用 `search` 参数查询，避免重复创建
3. **使用 quick 接口**: 发票录入优先用 `POST /api/invoices/quick`，自动计算税额
4. **关联项目**: 采购单/销售单尽量关联 `project_id`，方便项目利润统计
5. **标记付款状态**: 采购单/销售单创建后，付款/收款时更新 `payment_status`
6. **定期查税**: 每季度用 `GET /api/tax-report` 查看增值税，用 `GET /api/income-tax-report` 查看所得税
7. **对账检查**: 定期用 `GET /api/reconciliations` 检查供应商/客户往来账
