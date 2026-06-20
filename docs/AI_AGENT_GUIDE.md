# AI Agent 记账操作手册

> 本手册供 AI Agent 加载为 skill，快速执行进销存系统记账操作。

---

## 1. 操作铁律

| # | 规则 | 说明 |
|---|------|------|
| R1 | **必须调用 API** | 所有记账走本系统 API，禁止用文本/表格/笔记替代 |
| R2 | **先查后写** | 操作前先查询确认数据存在（商品、供应商、客户），避免重复创建 |
| R3 | **带齐 Header** | 所有请求必须带 `X-Account-ID`；写操作加 `X-Operator: ai` |
| R4 | **发票用 quick** | 发票录入优先用 `POST /api/invoices/quick`，只需传价税合计+税率，系统自动算税 |
| R5 | **更新付款状态** | 采购单/销售单创建后，付款/收款时更新 `payment_status` |
| R6 | **禁止假设数据** | 必须调用 API 获取真实数据，禁止编造 ID、金额、数量 |
| R7 | **接口清单以发现接口为准** | 写接口（POST/PUT/DELETE/PATCH）清单以 `GET /api/_ai/capabilities` 为唯一真相源；调用清单外写接口会被 **403 硬拦截**。新能力作为现有规范端点的可选字段，而非新增并行端点 |

---

## 2. 必填请求头

```
X-Account-ID: 1          # 账本 ID（缺失返回 401）
X-Operator: ai           # AI 请求标识（写入操作日志）
Content-Type: application/json
```

**获取账本 ID**：`GET /api/accounts` → 返回所有账本，取目标账本的 `id`。

---

## 2.1 白名单机制（核心约束）

> **AI 只能调用白名单内的写接口。**

| 接口类型 | 规则 |
|----------|------|
| **GET 查询** | 全部放行，无需列举 |
| **POST/PUT/DELETE/PATCH 写操作** | 仅限 `GET /api/_ai/capabilities` 返回的 `write_endpoints` 列表 |

**调用白名单外写接口** → 返回 `403 ENDPOINT_NOT_ALLOWED_FOR_AI`，响应包含：
- `ai_instruction`: 应改用的规范端点
- `suggested_endpoint`: 推荐端点路径

**收到 403 后 STOP_RETRYING**，按建议改用规范接口，不要重试原端点。

**获取当前白名单**：
```bash
curl http://localhost:8000/api/_ai/capabilities -H "X-Account-ID: 1"
# 返回 { "write_endpoints": [...], "note": "..." }
```

---

## 3. API 速查表

### 3.1 查询类

| 模块 | 端点 | 说明 |
|------|------|------|
| 商品 | `GET /api/products?page=1&search=关键词&category=分类` | 商品列表 |
| 库存 | `GET /api/inventory` | 库存列表 |
| 库存预警 | `GET /api/inventory/alerts` | 库存预警列表 |
| 供应商 | `GET /api/suppliers?search=关键词` | 供应商列表 |
| 客户 | `GET /api/customers?search=关键词` | 客户列表 |
| 采购单 | `GET /api/purchases?status=completed&start_date=...&end_date=...` | 采购列表 |
| 销售单 | `GET /api/sales?status=completed&start_date=...&end_date=...` | 销售列表 |
| 发票 | `GET /api/invoices?direction=out&year=2026&quarter=2` | 发票列表 |
| 费用 | `GET /api/expenses?category=房租&year=2026` | 费用列表 |
| 期初余额 | `GET /api/opening-balances` | 期初余额 |
| 现金流水 | `GET /api/cash-flows/transactions?flow_category=operating` | 现金流 |
| 个人流水 | `GET /api/personal?type=expense&category=餐饮` | 个人流水 |
| 对账 | `GET /api/reconciliations?party_type=supplier` | 对账汇总 |
| 日志 | `GET /api/logs?entity_type=product&start_date=...` | 操作日志 |
| 枚举 | `GET /api/enums` | 所有枚举值 |

### 3.2 报表类

| 报表 | 端点 |
|------|------|
| 资产负债表 | `GET /api/financial-reports/balance-sheet?date=2026-06-19` |
| 利润表 | `GET /api/financial-reports/income-statement?start_date=...&end_date=...` |
| 财务汇总 | `GET /api/financial-reports/financial-summary?date=2026-06-19` |
| 增值税 | `GET /api/tax-report?year=2026&quarter=2` |
| 企业所得税 | `GET /api/income-tax-report?year=2026&quarter=2` |
| 现金流量表 | `GET /api/cash-flows/statement?start_date=...&end_date=...` |

### 3.3 会计预检查类(写操作前先校验,避免返工)

> **何时用**:录发票/建固定资产/算税前,先调对应预检查接口验证金额/参数是否符合会计准则。
> 返回 `valid:true` → 可继续写操作;`valid:false` → 按 `ai_instruction` 修正后重试。
> 若触发 `AccountingError`(如税率非法),返回 422 + `error.code/accounting_rule/calculation_detail`,STOP_RETRYING 并按引导修正。

| 预检查 | 端点 | 必填参数 |
|--------|------|----------|
| 发票金额三件套 | `GET /api/accounting/invoice-amounts` | `amount_with_tax`, `tax_rate` |
| 固定资产折旧 | `GET /api/accounting/depreciation` | `method`(直线法/双倍余额递减法/年数总和法), `original_value`, `useful_life`, `months_used` |
| 增值税 | `GET /api/accounting/vat` | `total_revenue`, `taxpayer_type`(small_scale/general) |
| 企业所得税 | `GET /api/accounting/income-tax` | `profit`, `taxpayer_type`(small_micro/general) |
| 资产负债表平衡 | `GET /api/accounting/balance-sheet` | `date` |
| 利润表等式 | `GET /api/accounting/income-statement` | `start_date`, `end_date` |
| 现金流量表等式 | `GET /api/accounting/cash-flow` | `start_date`, `end_date` |

### 3.4 写操作类（白名单接口 + 参数）

> 以下为 AI 白名单内的全部规范写端点（共 33 个）。实际清单以 `GET /api/_ai/capabilities` 返回为准。

#### 商品 / 合作伙伴

| 操作 | 端点 | 方法 | 必填参数 | 可选参数 |
|------|------|------|----------|----------|
| 创建商品 | `/api/products` | POST | `name` | `sku`, `unit`, `category`, `purchase_price`, `sale_price`, `min_stock`, `initial_stock` |
| 更新商品 | `/api/products/{id}` | PUT | — | `name`, `sku`, `unit`, `category`, `purchase_price`, `sale_price`, `min_stock` |
| 删除商品 | `/api/products/{id}` | DELETE | — | — |
| 创建供应商 | `/api/suppliers` | POST | `name` | `contact`, `phone`, `address`, `notes` |
| 更新供应商 | `/api/suppliers/{id}` | PUT | — | `name`, `contact`, `phone`, `address`, `notes` |
| 删除供应商 | `/api/suppliers/{id}` | DELETE | — | — |
| 创建客户 | `/api/customers` | POST | `name` | `contact`, `phone`, `address`, `notes` |
| 更新客户 | `/api/customers/{id}` | PUT | — | `name`, `contact`, `phone`, `address`, `notes` |
| 删除客户 | `/api/customers/{id}` | DELETE | — | — |

#### 采购 / 销售

| 操作 | 端点 | 方法 | 必填参数 | 可选参数 |
|------|------|------|----------|----------|
| 创建采购单 | `/api/purchases` | POST | `items[]{product_id, quantity, unit_price}` | `supplier_id`, `has_invoice`, `payment_method`, `notes`, `tax_rate` |
| 更新采购单 | `/api/purchases/{id}` | PUT | — | `payment_status`, `status`, `notes` |
| 删除采购单 | `/api/purchases/{id}` | DELETE | — | — |
| 创建销售单 | `/api/sales` | POST | `items[]{product_id, quantity, unit_price}`, `sale_date` | `customer_id`, `deduct_inventory`, `has_invoice`, `payment_status`, `total_price`, `notes`, `tax_rate` |
| 更新销售单 | `/api/sales/{id}` | PUT | — | `payment_status`, `status`, `notes` |
| 删除销售单 | `/api/sales/{id}` | DELETE | — | — |

#### 发票

| 操作 | 端点 | 方法 | 必填参数 | 可选参数 |
|------|------|------|----------|----------|
| AI 快捷录发票 | `/api/invoices/quick` | POST | `invoice_no`, `direction`, `invoice_type`, `amount_with_tax`, `tax_rate`, `counterparty_name`, `issue_date` | `notes`, `image_url`, `fixed_asset{asset_code, asset_name, useful_life, start_date, ...}` |
| 更新发票 | `/api/invoices/{id}` | PUT | — | `invoice_no`, `direction`, `invoice_type`, `tax_rate`, `amount_with_tax`, `counterparty_name`, `issue_date`, `notes` |
| 删除发票 | `/api/invoices/{id}` | DELETE | — | — |
| 认证进项专票 | `/api/invoices/{id}/certify` | POST | — | — |

#### 库存

| 操作 | 端点 | 方法 | 必填参数 | 可选参数 |
|------|------|------|----------|----------|
| 调整库存 | `/api/inventory/{product_id}` | PUT | `quantity` | — |

#### 费用 / 财务

| 操作 | 端点 | 方法 | 必填参数 | 可选参数 |
|------|------|------|----------|----------|
| 创建费用 | `/api/expenses` | POST | `category`, `amount`, `expense_date` | `functional_category`, `has_invoice`, `payment_method`, `description`, `image_url` |
| 更新费用 | `/api/expenses/{id}` | PUT | — | `category`, `amount`, `expense_date`, `has_invoice`, `payment_method`, `description` |
| 删除费用 | `/api/expenses/{id}` | DELETE | — | — |
| 创建期初余额 | `/api/opening-balances` | POST | `date` | `cash_balance`, `bank_balance`, `accounts_receivable`, `inventory_value`, `fixed_assets_original`, `accumulated_depreciation`, `accounts_payable`, `tax_payable`, `paid_in_capital`, `retained_earnings` |
| 创建现金流水 | `/api/cash-flows/transactions` | POST | `type`, `amount`, `transaction_date` | `flow_category`, `description`, `related_entity_type`, `related_entity_id` |
| 创建固定资产 | `/api/fixed-assets` | POST | `asset_code`, `name`, `original_value`, `useful_life`, `start_date` | `category`, `salvage_rate`, `depreciation_method`, `accumulated_depreciation`, `status` |
| 更新固定资产 | `/api/fixed-assets/{id}` | PUT | — | `asset_code`, `name`, `category`, `original_value`, `salvage_rate`, `useful_life`, `depreciation_method`, `start_date`, `status` |

#### 个人流水

| 操作 | 端点 | 方法 | 必填参数 | 可选参数 |
|------|------|------|----------|----------|
| 创建个人流水记录 | `/api/personal` | POST | `type`, `amount` | `category`, `description`, `image_url`, `date` |
| 更新个人流水记录 | `/api/personal/{tx_id}` | PUT | — | `type`, `amount`, `category`, `description`, `image_url`, `date` |
| 删除个人流水记录 | `/api/personal/{tx_id}` | DELETE | — | — |

#### 付款 / 收款

| 操作 | 端点 | 方法 | 必填参数 | 可选参数 |
|------|------|------|----------|----------|
| 创建付款 | `/api/payments` | POST | `payment_type`, `related_entity_type`, `related_entity_id`, `amount`, `payment_date` | `payment_method`, `bank_account_id`, `description` |
| 创建收款 | `/api/receipts` | POST | `receipt_type`, `related_entity_type`, `related_entity_id`, `amount`, `receipt_date` | `receipt_method`, `bank_account_id`, `description` |

#### 备份

| 操作 | 端点 | 方法 | 必填参数 | 可选参数 |
|------|------|------|----------|----------|
| 热备份 | `/api/backup/hot` | POST | — | — |

---

## 4. 场景模板

### 场景 A：记录采购

```bash
# 1. 查/建供应商
curl -H "X-Account-ID: 1" "http://localhost:8000/api/suppliers?search=钢铁"
# 不存在则创建
curl -X POST http://localhost:8000/api/suppliers \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"name":"XX钢铁公司","phone":"13800138000"}'

# 2. 查/建商品
curl -H "X-Account-ID: 1" "http://localhost:8000/api/products?search=钢材"
# 不存在则创建
curl -X POST http://localhost:8000/api/products \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"name":"钢材","sku":"STL-001","unit":"吨","purchase_price":3500,"sale_price":4200}'

# 3. 创建采购单（自动增加库存）
curl -X POST http://localhost:8000/api/purchases \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"supplier_id":1,"has_invoice":true,"payment_method":"company",
       "items":[{"product_id":1,"quantity":50,"unit_price":3500,"tax_rate":0.13}]}'
```

### 场景 B：记录销售

```bash
# 创建销售单（自动扣减库存）
curl -X POST http://localhost:8000/api/sales \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"customer_id":1,"deduct_inventory":true,"payment_status":"unpaid",
       "total_price":210000,
       "items":[{"product_id":1,"quantity":50,"unit_price":4200,"tax_rate":0.13}]}'
```

### 场景 C：录入发票

```bash
# AI 快捷录入（自动算税）
curl -X POST http://localhost:8000/api/invoices/quick \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"invoice_no":"12345678","direction":"out","invoice_type":"ordinary",
       "tax_rate":0.01,"amount_with_tax":10100,
       "counterparty_name":"XX客户","issue_date":"2026-06-19"}'
```

**带固定资产入账**（购入设备等，发票与资产在同一事务原子创建并自动关联）：

```bash
curl -X POST http://localhost:8000/api/invoices/quick \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"invoice_no":"87654321","direction":"in","invoice_type":"special",
       "tax_rate":0.13,"amount_with_tax":11300,
       "counterparty_name":"XX设备商","issue_date":"2026-06-19",
       "fixed_asset":{"asset_code":"FA-001","asset_name":"数控机床",
         "category":"电子设备","salvage_rate":0.05,"useful_life":60,
         "depreciation_method":"年限平均法","start_date":"2026-06-01",
         "accumulated_depreciation":0,"asset_status":"在用"}}'
# 响应 data.related_order_type=="fixed_asset"，data.fixed_asset.id 为关联资产 ID
```

### 场景 D：查看税务

```bash
curl "http://localhost:8000/api/tax-report?year=2026&quarter=2" -H "X-Account-ID: 1"
curl "http://localhost:8000/api/income-tax-report?year=2026&quarter=2" -H "X-Account-ID: 1"
```

### 场景 E：标记已付款

```bash
curl -X PUT http://localhost:8000/api/purchases/1 \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"payment_status":"paid"}'
```

### 场景 F：个人记账

```bash
curl -X POST http://localhost:8000/api/personal \
  -H "X-Account-ID: 1" -H "X-Operator: ai" -H "Content-Type: application/json" \
  -d '{"type":"expense","amount":50,"category":"餐饮","description":"午餐","date":"2026-06-19"}'
```

---

## 5. 关键字段速查

### 发票

| 字段 | 合法值 |
|------|--------|
| `direction` | `in`(进项) / `out`(销项) |
| `invoice_type` | `ordinary`(普票) / `special`(专票) |
| `tax_rate` | `0.01` / `0.03` / `0.06` / `0.09` / `0.13` |
| `certification_status` | `n_a` / `pending` / `certified` |

### 订单

| 字段 | 合法值 |
|------|--------|
| `status` | `pending` / `completed` / `cancelled` |
| `payment_status` | `unpaid` / `partial` / `paid` |
| `payment_method` | `company` / `private_advance` |

### 费用

| 字段 | 合法值 |
|------|--------|
| `category` | `房租`/`水电`/`工资`/`材料`/`办公用品`/`运费`/`维修`/`其他` |
| `cost_type` | `材料`/`人工`/`差旅`/`外包`/`设备`/`其他` |

### 个人流水

| 字段 | 合法值 |
|------|--------|
| 收入分类 | `工资`/`兼职`/`理财`/`其他` |
| 支出分类 | `餐饮`/`日用`/`交通`/`娱乐`/`医疗`/`烟酒`/`其他` |

---

## 6. 自动联动行为

| 操作 | 系统自动执行 |
|------|-------------|
| 创建采购单 | 库存 +quantity |
| 取消/删除采购单 | 库存 -quantity（回补） |
| 创建销售单 (deduct_inventory=true) | 库存 -quantity |
| 取消/删除销售单 | 库存 +quantity（恢复） |

---

## 7. 错误码

| HTTP | 含义 | 处理 |
|------|------|------|
| 400 | 业务校验失败 | 检查响应 message，修正数据 |
| 401 | 缺少 X-Account-ID | 补充请求头 |
| 403 | AI 调用了非规范写接口 | **STOP_RETRYING**，按 `ai_instruction` / `suggested_endpoint` 改用规范接口（见 R7） |
| 404 | 不存在 | 检查 ID 是否正确、是否属于当前账本 |
| 409 | 数据冲突 | 唯一约束冲突（如商品编码重复） |
| 422 | 参数校验失败 / 会计计算错误 | 响应中会提示合法值列表；会计错误另含 `accounting_rule`(法规依据) + `calculation_detail`(数值明细),按 `ai_instruction` 修正 |

---

## 8. 完整参考

健康检查：`GET /api/health` → `{"status":"ok"}`

---

*AI Agent 操作手册 v2.0 | 2026-06-20 — 新增白名单机制 + 完整参数说明*
