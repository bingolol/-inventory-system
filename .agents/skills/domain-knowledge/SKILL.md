---
name: domain-knowledge
description: 进销存系统领域知识 — Engine 决策表、公式卡、事件映射、ErrorCode 参考、文件修改清单。修改会计/库存/财务代码时必须加载。
---

> 最后校验日期: 2026-06-26 | 校验方式: 逐行读取源码确认

## 1. Engine 决策表

| 业务场景 | Engine | 方法 | 源码位置 |
|----------|--------|------|----------|
| 采购入库 | `InventoryEngine` | `inbound(account_id, product_id, quantity, unit_price, source_type, source_id, tax_rate, operator)` | `engine_inventory.py:28` |
| 采购入库（生成凭证） | `FinanceEngine` | `record_purchase(order, calculated_data=None)` | `engine_finance.py:45` |
| 销售出库 | `InventoryEngine` | `outbound(account_id, product_id, quantity, source_type, source_id, operator)` | `engine_inventory.py:112` |
| 销售出库（生成凭证） | `FinanceEngine` | `record_sale(order)` | `engine_finance.py:73` |
| 库存调整入库 | `InventoryEngine` | `inbound(...)` — 同上，`source_type='adjustment'` | `engine_inventory.py:28` |
| 库存调整出库 | `InventoryEngine` | `outbound(...)` — 同上，`source_type='adjustment'` | `engine_inventory.py:112` |
| 取消采购单（红冲库存） | `InventoryEngine` | `reverse(account_id, product_id, quantity, unit_cost, source_type, source_id, operator)` | `engine_inventory.py:186` |
| 取消采购单（红冲凭证） | `FinanceEngine` | `reverse_purchase(order_id)` | `engine_finance.py:104` |
| 取消销售单（红冲库存） | `InventoryEngine` | `reverse(...)` | `engine_inventory.py:186` |
| 取消销售单（红冲凭证） | `FinanceEngine` | `reverse_sale(order_id)` | `engine_finance.py:108` |
| 强制出库（跳过幂等） | `InventoryEngine` | `force_outbound(account_id, product_id, quantity, source_type, source_id, operator)` | `engine_inventory.py:179` |
| 计提单个资产折旧 | `FixedAssetEngine` | `record_depreciation(asset_id, period)` → 返回 `Optional[FixedAssetDepreciation]` | `engine_fixed_asset.py:43` |
| 批量计提折旧 | `FixedAssetEngine` | `batch_depreciate(period)` → 返回 `List[FixedAssetDepreciation]` | `engine_fixed_asset.py:115` |
| 固定资产处置 | `FixedAssetEngine` | `record_disposal(asset_id, disposal_price=Decimal("0"))` | `engine_fixed_asset.py:130` |
| 计算月折旧额 | `FixedAssetEngine` | `calculate_monthly(asset)` → 返回 `Decimal` | `engine_fixed_asset.py:22` |
| 银行余额变更 | `BankEngine(db, account_id)` | `update_balance(bank_account_id, amount, transaction_type)` → 返回 `BankAccount` | `engine_bank.py:16` |
| 凭证过账 | `finance_integration.py` | `post_journal(db, account_id, move_type, source)` → 返回 `AccountMove` | `finance_integration.py:61` |
| 凭证冲红 | `finance_integration.py` | `reverse_journal(db, account_id, source_model, source_id, reversal_date=None)` → 返回 `Optional[AccountMove]` | `finance_integration.py:95` |
| 获取 ledger_id | `finance_integration.py` | `get_ledger_id(db, account_id)` → 返回 `int` | `finance_integration.py:27` |
| 发票金额计算 | `AccountingEngine` | `calculate_invoice_amounts(amount_with_tax, tax_rate)` → 返回 `InvoiceAmounts` | `accounting_engine.py:177` |
| 发票金额校验 | `AccountingEngine` | `validate_invoice_amounts(amount_without_tax, tax_amount, amount_with_tax)` | `accounting_engine.py:205` |
| 年限平均法折旧 | `AccountingEngine` | `calculate_depreciation_straight_line(original_value, salvage_rate, useful_life, months_used)` → 返回 `DepreciationResult` | `accounting_engine.py:238` |
| 双倍余额递减法折旧 | `AccountingEngine` | `calculate_depreciation_double_declining(original_value, useful_life, months_used)` → 返回 `DepreciationResult` | `accounting_engine.py:295` |
| 年数总和法折旧 | `AccountingEngine` | `calculate_depreciation_sum_of_years(original_value, salvage_rate, useful_life, months_used)` → 返回 `DepreciationResult` | `accounting_engine.py:350` |
| 无形资产摊销 | `AccountingEngine` | `calculate_intangible_amortization(original_value, useful_life, months_used)` → 返回 `AmortizationResult` | `accounting_engine.py:430` |
| 增值税计算 | `AccountingEngine` | `calculate_vat(total_revenue, taxpayer_type, input_tax=Decimal('0'))` → 返回 `VATResult` | `accounting_engine.py:487` |
| 企业所得税 | `AccountingEngine` | `calculate_income_tax(profit, taxpayer_type)` → 返回 `IncomeTaxResult` | `accounting_engine.py:612` |
| 科目余额更新 | `LedgerEngine(db)` | `update_balance(line: AccountMoveLine)` | `engine_ledger.py:55` |
| 科目余额查询 | `LedgerEngine(db)` | `get_balance(ledger_account_id, date=None)` → 返回 `Decimal` | `engine_ledger.py:81` |
| 试算平衡表 | `LedgerEngine(db)` | `get_trial_balance(ledger_id, date)` → 返回 `dict` | `engine_ledger.py:133` |
| 凭证模板过账 | `JournalEngine(db)` | `post(ledger_id, move_type, source)` → 返回 `AccountMove` | `engine_journal.py:20` |
| 往来核销 | `ReceivableEngine(db)` | `reconcile(ledger_id, debit_line_id, credit_line_id, amount)` | `engine_receivable.py:18` |
| 往来余额查询 | `ReceivableEngine(db)` | `get_partner_balance(partner_id, partner_type, account_type=None, as_of=None)` → 返回 `Decimal` | `engine_receivable.py:49` |
| 账龄分析 | `ReceivableEngine(db)` | `get_aging_report(partner_id, partner_type, as_of_date, account_type='asset_receivable')` → 返回 `dict`（4 桶） | `engine_receivable.py:74` |
| 银行对账 | `BankReconcileEngine` | `reconcile(bank_statement_id)` → 返回 `ReconcileResult` | `engine_bank_reconcile.py` |
| 对账单导入 | `BankReconcileEngine` | `import_statement(account_id, transactions)` → 返回 `BankStatement` | `engine_bank_reconcile.py` |
| 增值税计算 | `TaxEngine` | `calculate_vat(period, account_id)` → 返回 `VATReturn` | `engine_tax.py` |
| 所得税计算 | `TaxEngine` | `calculate_income_tax(period, account_id)` → 返回 `IncomeTaxReturn` | `engine_tax.py` |
| 进销项匹配 | `TaxCheckEngine` | `check_invoice_matching(period, account_id)` → 返回 `CheckResult` | `engine_tax_check.py` |
| 从 items 算税额 | `finance_integration.py` | `_calc_tax_from_items(total_with_tax, items)` → 返回 `dict`（内部函数，非公开 API） | `finance_integration.py:44` |

## 2. 公式卡

### 2.1 发票金额
```
不含税金额 = 含税金额 / (1 + 税率)
税额 = 含税金额 - 不含税金额
校验：不含税 + 税额 == 价税合计（容差 ±0.01）
```
- Engine: `AccountingEngine.calculate_invoice_amounts()` / `validate_invoice_amounts()`
- ErrorCode: `INVOICE_AMOUNTS_NOT_BALANCED`
- 法规: 《小企业会计准则》第十五条

### 2.2 年限平均法（直线法）
```
月折旧额 = 原值 × (1 - 残值率) / 使用寿命(月)
累计折旧 = 月折旧额 × min(已用月数, 使用寿命)
净值 = 原值 - 累计折旧
```
- Engine: `AccountingEngine.calculate_depreciation_straight_line()` (line 238)
- 校验: 原值>0, 残值率[0,1], 使用寿命>0
- ErrorCode: `DEPRECIATION_ORIGINAL_VALUE_INVALID`, `DEPRECIATION_SALVAGE_RATE_INVALID`, `DEPRECIATION_USEFUL_LIFE_ZERO`

### 2.3 双倍余额递减法
```
月折旧率 = 2 / 使用寿命(月)
月折旧额 = 期初净值 × 月折旧率
净值不能低于 0
```
- Engine: `AccountingEngine.calculate_depreciation_double_declining()` (line 295)
- ⚠️ 简化实现：未实现"最后 2 年改直线法"逻辑
- 校验: 原值>0, 使用寿命>0
- ErrorCode: `DEPRECIATION_ORIGINAL_VALUE_INVALID`, `DEPRECIATION_USEFUL_LIFE_ZERO`

### 2.4 年数总和法
```
年数总和 = n × (n + 1) / 2
月折旧额 = (原值 - 残值) × (剩余年限 / 年数总和) / 12
净值不能低于残值
```
- Engine: `AccountingEngine.calculate_depreciation_sum_of_years()` (line 350)
- 校验: 原值>0, 残值率[0,1], 使用寿命>0
- ErrorCode: `DEPRECIATION_ORIGINAL_VALUE_INVALID`, `DEPRECIATION_SALVAGE_RATE_INVALID`, `DEPRECIATION_USEFUL_LIFE_ZERO`

### 2.5 无形资产摊销
```
月摊销额 = 原值 / 使用寿命(月)
累计摊销 = 月摊销额 × min(已用月数, 使用寿命)
净值 = 原值 - 累计摊销
```
- Engine: `AccountingEngine.calculate_intangible_amortization()` (line 430)
- 校验: 原值>0, 使用寿命>0，累计摊销不超过原值（自动封顶）
- ErrorCode: `AMORTIZATION_ORIGINAL_VALUE_INVALID`, `AMORTIZATION_USEFUL_LIFE_ZERO`

### 2.6 增值税

#### 小规模纳税人
```
征收率：3%（2023-2027 优惠减按 1%）
不含税销售额 = 含税销售额 / (1 + 1%)
应纳增值税 = 不含税销售额 × 1%
附加税（减半）：
  城建税 = 增值税 × 7% × 50%
  教育费附加 = 增值税 × 3% × 50%
  地方教育附加 = 增值税 × 2% × 50%
```
- ⚠️ 当前引擎未实现"季度销售额≤30万免征"条件判断，免税判定在 `routers/tax.py` 调用方处理

#### 一般纳税人
```
税率：13%（货物）/ 9%（运输、建筑）/ 6%（服务）
应纳增值税 = 销项税额 - 进项税额
销项税额 = 不含税销售额 × 税率
进项税额 = 已认证专票税额
附加税（无减半）：
  城建税 = 增值税 × 7%
  教育费附加 = 增值税 × 3%
  地方教育附加 = 增值税 × 2%
```
- Engine: `AccountingEngine.calculate_vat()` (line 487)
- 校验: taxpayer_type 必须为 small_scale/general, revenue >= 0, input_tax >= 0
- ErrorCode: `VAT_TAXPAYER_TYPE_INVALID`, `VAT_REVENUE_NEGATIVE`, `VAT_INPUT_TAX_NEGATIVE`, `VAT_CALCULATION_INVALID`

### 2.7 企业所得税
```
【小微企业】（利润≤300万，人数≤300，资产≤5000万）
应纳税额 = 利润总额 × 25% × 20% = 利润总额 × 5%

【一般企业】
应纳税额 = 利润总额 × 25%
```
- Engine: `AccountingEngine.calculate_income_tax()` (line 612)
- ⚠️ 仅支持 small_micro 和一般企业，不支持高新技术企业
- 校验: profit >= 0（亏损返回 0）
- ErrorCode: `INCOME_TAX_PROFIT_NEGATIVE`, `INCOME_TAX_CALCULATION_INVALID`

## 3. 事件映射

> handlers.py 加载时自动注册（通过 `@on` 装饰器）
> v7 重构后：handlers 只保留日志 handler，库存/收入联动已移至 Command Handler 显式调用

| 事件名 | Handler | 职责 |
|--------|---------|------|
| `sale_order.created` | `_log_sale_created` (priority=10) | 记录操作日志 |
| `sale_order.cancelled` | `_log_sale_cancelled` (priority=10) | 记录操作日志 |
| `sale_order.deleted` | `_log_sale_deleted` (priority=10) | 记录操作日志 |
| `sale_order.restored` | `_log_sale_restored` (priority=10) | 记录操作日志 |
| `sale_order.items_updated` | `_log_sale_items_updated` (priority=10) | 记录操作日志 |
| `purchase_order.created` | `_log_purchase_created` (priority=10) | 记录操作日志 |
| `purchase_order.updated` | `_log_purchase_updated` (priority=10) | 记录操作日志 |
| `purchase_order.deleted` | `_log_purchase_deleted` (priority=10) | 记录操作日志 |

跨层调用路径（以采购入库为例）:
```
Router → dispatch(CreatePurchaseCommand) → CommandHandler.handle()
  ├── InventoryEngine.inbound()    ← 显式调用库存引擎
  ├── FinanceEngine.record_purchase()  ← 显式调用财务引擎
  ├── emit("purchase_order.created")    ← 触发事件（仅日志）
  └── unit_of_work 自动 commit
```

### 2.8 移动加权平均成本（InventoryEngine）
```
入库后平均成本 = (旧库存总价值 + 入库成本) / (旧库存数量 + 入库数量)
出库时 unit_cost = 当前 average_cost（锁定到 SaleItem）
```
- Engine: `InventoryEngine.inbound()` (line 83), `outbound()` (line 148)
- 精度: unit_cost 存 N(12,6), 总价值存 N(12,2)
- BR-7: StockMove 是库存真相源，Inventory 仅为缓存

### 2.9 季度日期范围
```
Q1: [year-01-01, year-04-01)
Q2: [year-04-01, year-07-01)
Q3: [year-07-01, year-10-01)
Q4: [year-10-01, year+1-01-01)
```
- 工具函数: `utils.get_quarter_date_range(year, quarter)` → `(datetime, datetime)`
- 模式: 半开区间 `[start, end)`，便于 SQL 比较；闭区间调用方用 `end - timedelta(days=1)`
- 已替换 8 处硬编码

## 4. ErrorCode 参考

三种错误体系并存，不要混用：

### 4.1 `AccountingErrorCode`（accounting_engine.py:18）
纯会计数学计算使用，抛出 `AccountingError`。在 `main.py:84` 有独立异常处理器。
| ErrorCode | 触发场景 |
|-----------|----------|
| `INVOICE_AMOUNTS_NOT_BALANCED` | 发票金额等式不平 |
| `VAT_TAXPAYER_TYPE_INVALID` | 纳税人类型非法 |
| `VAT_REVENUE_NEGATIVE` | 收入为负 |
| `VAT_INPUT_TAX_NEGATIVE` | 进项税额为负 |
| `VAT_CALCULATION_INVALID` | 增值税计算结果校验失败 |
| `INCOME_TAX_PROFIT_NEGATIVE` | 利润为负（不缴税） |
| `INCOME_TAX_CALCULATION_INVALID` | 所得税计算结果校验失败 |
| `DEPRECIATION_ORIGINAL_VALUE_INVALID` | 折旧原值<=0 |
| `DEPRECIATION_SALVAGE_RATE_INVALID` | 折旧残值率不在[0,1] |
| `DEPRECIATION_USEFUL_LIFE_ZERO` | 折旧使用寿命为0 |
| `AMORTIZATION_ORIGINAL_VALUE_INVALID` | 摊销原值<=0 |
| `AMORTIZATION_USEFUL_LIFE_ZERO` | 摊销使用寿命为0 |
| `ACCOUNT_NOT_FOUND` | 科目不存在 |
| `NON_LEAF_ACCOUNT` | 非叶子科目不允许有余额 |
| `INSUFFICIENT_BALANCE` | 现金科目余额不足 |
| `UNKNOWN_MOVE_TYPE` | 不支持的凭证类型 |
| `AMOUNT_MISMATCH` | 金额不一致 |
| `BALANCE_NOT_EQUAL` | 借贷不平 |
| `FIELD_REQUIRED` | 必填字段缺失 |
| `LINE_NOT_FOUND` | 核销行不存在 |

### 4.2 `ErrorCode`（errors.py:20）
通用业务错误，抛出 `BusinessError`。
| 分组 | ErrorCode |
|------|-----------|
| 库存(1xxx) | `INVENTORY_INSUFFICIENT`, `INVENTORY_NEGATIVE_AMOUNT` |
| 订单(2xxx) | `ORDER_NOT_FOUND`, `ORDER_INVALID_STATE`, `ORDER_EMPTY_ITEMS`, `ORDER_DUPLICATE_PRODUCT` |
| 发票(3xxx) | `INVOICE_NOT_FOUND`, `INVOICE_DUPLICATE_NUMBER`, `INVOICE_INVALID_DATE` |
| 财务(4xxx) | `BALANCE_ALREADY_EXISTS`, `BALANCE_SHEET_UNBALANCED`, `INCOME_STATEMENT_INVALID`, `CASH_FLOW_STATEMENT_INVALID` |
| 商品(5xxx) | `PRODUCT_NOT_FOUND`, `PRODUCT_HAS_TRANSACTIONS` |
| 合作伙伴(6xxx) | `SUPPLIER_HAS_ORDERS`, `CUSTOMER_HAS_ORDERS`, `CUSTOMER_NOT_FOUND` |
| 固定资产(8.5xxx) | `FIXED_ASSET_NOT_FOUND`, `FIXED_ASSET_DISPOSAL_REQUIRED` |
| 银行账户(9xxx) | `BANK_ACCOUNT_NOT_FOUND` |
| 通用(9xxx) | `VALIDATION_ERROR`, `DUPLICATE_ENTRY`, `DATA_INTEGRITY_ERROR`, `READONLY_DATA`, `SECURITY_VIOLATION`, `INTERNAL_ERROR`, `ENDPOINT_NOT_ALLOWED_FOR_AI` |

**ErrorCode → HTTP 状态码映射**（在 `ERROR_REGISTRY` 中配置）:
- 4xx: `VALIDATION_ERROR`(422), `ORDER_NOT_FOUND`(404), `PRODUCT_NOT_FOUND`(404), `INVENTORY_INSUFFICIENT`(409), `DUPLICATE_ENTRY`(409)
- 5xx: `INTERNAL_ERROR`(500)

### 4.3 `AccountingError`（accounting_engine.py:17）
引擎内部使用，已统一为 `AccountingErrorCode` 枚举。通过 `finance_integration.py` 的 `post_journal()`/`reverse_journal()` 转为 `BusinessError`。
| ErrorCode | 触发引擎 | 说明 |
|----------|----------|------|
| `ACCOUNT_NOT_FOUND` | engine_ledger, engine_journal | 科目不存在 |
| `NON_LEAF_ACCOUNT` | engine_ledger | 非叶子科目不允许有余额 |
| `INSUFFICIENT_BALANCE` | engine_ledger | 现金科目余额不足 |
| `UNKNOWN_MOVE_TYPE` | engine_journal | 不支持的凭证类型 |
| `AMOUNT_MISMATCH` | engine_journal | 金额不一致 |
| `BALANCE_NOT_EQUAL` | engine_journal | 借贷不平 |
| `FIELD_REQUIRED` | engine_journal | 必填字段缺失 |
| `LINE_NOT_FOUND` | engine_receivable | 核销行不存在 |

## 5. 文件修改清单

### 新增 API 端点
```
1. backend/enums.py              → 添加枚举（如需要）
2. backend/models.py             → 添加 ORM 模型（如需要）
3. backend/schemas/              → 添加 Pydantic Schema
4. backend/commands/             → 添加 Command + Handler
5. backend/crud/                 → 添加查询函数
6. backend/routers/              → 添加路由端点
7. tests/                        → 添加测试
```

### 新增写操作
```
1. backend/commands/xxx_commands.py  → @dataclass Command + @register Handler
2. backend/commands/__init__.py      → 导出 Command
3. backend/routers/xxx.py            → 路由调用 dispatch()
```

### 新增会计计算
```
1. backend/accounting_engine.py    → 添加计算方法 + 返回 dataclass
2. backend/enums.py 或 accounting_engine.py → 添加 AccountingErrorCode
3. backend/routers/accounting_check.py → 添加预检查端点
4. tests/                          → 单元测试
```

### 新增凭证模板
```
1. backend/engine_journal.py       → 添加 _build_xxx() 方法
2. backend/engine_journal.py       → 在 _build() 的 move_type 分发添加分支
3. backend/finance_integration.py  → 可选：添加高层封装
4. tests/                          → 测试
```

### 新增 Engine
```
1. backend/engine_xxx.py           → Engine 类，与其它 Engine 风格一致
2. 注意：Engine 不应直接抛 HTTPException，应抛 BusinessError / AccountingError
3. 在架构文档中记录新 Engine 职责
```

## 6. 关键架构规则

- **写操作必须走 Command 模式**（`dispatch(Command, db)`），禁止在 Router 中直接写数据库
- **事务边界必须用 `unit_of_work(db)`**，commit/rollback 只在 uow 中，业务代码只做 flush
- **所有查询必须过滤 `account_id`**（多账本隔离）
- **金额计算必须用 `Decimal`**，禁止 float。精度：`Q2 = Decimal('0.01')`
- **所有写操作必须 `_log()`**，保留审计痕迹
- **Engine 之间禁止互相直接调用**，通过 Command Handler 编排
- **返回数据必须用 Pydantic Schema（model_validate）**，禁止直接返回 ORM 对象
- **CRUD 层只读不写**，业务校验在 Command Handler 中完成
- **Engine-owned 字段用 `@property` 防护**，禁止 `model.field = X` 直写
- **真相源表加 `before_update` 事件**，禁止任何 UPDATE 操作
- **`_d()` 做 Decimal 安全转换，`Q2` 做金额精度规范**，定义在 `utils.py`

- **文档观众原则**：每份文档只写给目标读者看。新建或修改文档前先确定读者是谁、ta需要知道什么，不相关的内容一律不放。
## 7. 防护层（ORM 防护模式）

### 7.1 `@property` + `set_*()` 模式（engine-owned 字段）

引擎独占的缓存字段，业务层只能读不能写：

```python
# models.py
_unit_cost = Column("unit_cost", Numeric(12, 6), default=Decimal('0'))

@property
def unit_cost(self):
    return self._unit_cost

def set_calculated_cost(self, value):
    """Only InventoryEngine.outbound() should call this"""
    self._unit_cost = value
```

效果：
- `item.unit_cost = 100` → `AttributeError: can't set attribute`
- `item.set_calculated_cost(100)` → 正常
- 所有读取 `item.unit_cost` 不变

| 字段 | 模型 | 写入方法 | 状态 |
|------|------|----------|------|
| `SaleItem.unit_cost` | `SaleItem` | `set_calculated_cost()` | ✅ 已加 |
| `Inventory.quantity` | `Inventory` | 引擎 `inbound/outbound/reverse` | ❌ 待加 |
| `Inventory.average_cost` | `Inventory` | 同上 | ❌ 待加 |
| `Inventory.total_value` | `Inventory` | 同上 | ❌ 待加 |
| `BankAccount.balance` | `BankAccount` | `BankEngine.update_balance()` | ❌ 待加 |
| `FixedAsset.accumulated_depreciation` | `FixedAsset` | `FixedAssetEngine.record_depreciation()` | ❌ 待加 |
| `StockMove.*` | `StockMove` | `InventoryEngine` 构造时设置 | ❌ 待加 |
| `FixedAssetDepreciation.*` | `FixedAssetDepreciation` | `FixedAssetEngine` 构造时设置 | ❌ 待加 |

### 7.2 `before_update` 事件监听器（不可变真相源）

真相源流水表禁止任何 UPDATE 操作：

```python
from sqlalchemy import event

@event.listens_for(StockMove, 'before_update')
def prevent_stock_move_update(mapper, connection, target):
    raise BusinessError(code=ErrorCode.INVALID_OPERATION, message="StockMove 是真相源，严禁修改")
```

| 表 | 策略 | 状态 |
|----|------|------|
| `StockMove` | 全部拒绝 | ❌ 待加 |
| `FixedAssetDepreciation` | 全部拒绝 | ❌ 待加 |
| `AccountMove` | 全部拒绝 | ❌ 待加 |
| `AccountMoveLine` | 全部拒绝 | ❌ 待加 |

### 7.3 业务守卫（状态变更拦截）

特定字段值变更需要走引擎，禁止直接赋值：

```python
# invoice_commands.py
if cmd.asset_status == "报废":
    raise BusinessError(code=ErrorCode.FIXED_ASSET_DISPOSAL_REQUIRED,
                        data={"asset_id": asset.id})
asset.status = cmd.asset_status
```

| 拦截 | 位置 | 状态 |
|------|------|------|
| `FixedAsset.status = "报废"` 绕过处置引擎 | `invoice_commands.py:560/752` | ✅ 已加 |

## 8. 真相源模型定义

`StockMove` 和 `FixedAssetDepreciation` 在 `models.py` 中尚缺（历史遗留），需补：

### StockMove（库存流水）
```python
class StockMove(Base):
    __tablename__ = "stock_moves"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 6), default=Decimal('0'))
    total_cost = Column(Numeric(12, 2), default=Decimal('0'))
    source_type = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    __table_args__ = (
        UniqueConstraint('source_type', 'source_id', 'product_id', name='uix_stock_move_source'),
    )
```

### FixedAssetDepreciation（折旧流水）
```python
class FixedAssetDepreciation(Base):
    __tablename__ = "fixed_asset_depreciations"
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("fixed_assets.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    period = Column(String(7), nullable=False, comment="YYYY-MM")
    amount = Column(Numeric(12, 2), nullable=False)
    accumulated_before = Column(Numeric(12, 2), default=Decimal('0'))
    accumulated_after = Column(Numeric(12, 2), default=Decimal('0'))
    created_at = Column(DateTime, default=datetime.now)
    __table_args__ = (
        UniqueConstraint('asset_id', 'period', name='uix_depreciation_period'),
    )
```

### Inventory 补充字段
```python
average_cost = Column(Numeric(12, 6), default=Decimal('0'), comment="移动加权平均成本")
total_value = Column(Numeric(12, 2), default=Decimal('0'), comment="库存总价值(成本)")
```

## 9. 工具函数

| 函数 | 位置 | 说明 |
|------|------|------|
| `_d(v)` | `utils.py:10` | 安全转 Decimal：float/int/str → Decimal，None → Decimal('0') |
| `Q2` | `utils.py:10` | `Decimal('0.01')`，金额量化精度 |
| `get_quarter_date_range(year, quarter)` | `utils.py:31` | 返回半开区间 `(start, end)`，Q4 跨年 |
| `_get_product(account_id, product_id)` | `engine_inventory.py:12` | 查 Product + 抛 `PRODUCT_NOT_FOUND`，caller 处理 `track_inventory` |
