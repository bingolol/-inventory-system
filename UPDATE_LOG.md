# 进销存管理系统 - 更新日志

> 本文档记录项目的每一次代码变更，确保跨会话可追溯。
> 每次修改经测试通过后必须在此追加记录。

---

## 2026-05-01 销售单支持自定义销售金额

### 变更概述
销售单增加自定义金额功能，支持整单打折、抹零、含税包价等场景。自定义总额与明细合计的差额会自动分配到各行单价。

### 具体修改
- `backend/schemas.py` → `SaleOrderCreate`/`SaleOrderUpdate` 增加 `total_price: Optional[float] = None`
- `backend/crud/orders.py` → 新增 `_distribute_total_price()` 差额分配函数；`create_sale_order`/`update_sale_order` 传了 total_price 时自动将差额分配到各行单价
  - 单价为0的行优先分配（按数量加权）
  - 所有行都有单价时按金额比例分配（整体打折/加价）
  - 尾差归入最后一行，保证各行合计精确等于自定义总额
- `backend/crud/orders.py` → `update_sale_order` 中 `model_dump(exclude_unset=True)` 排除 `total_price`（防止覆盖已正确设置的总额）；只改总额不改明细时也重新分配行单价
- `frontend/src/views/Sales.vue` → 新建/编辑弹窗底部改为"明细合计: ¥xxx → [自定义金额输入框] 订单总额: ¥xxx"
- `frontend/src/views/Sales.vue` → 修复 `total_price` 传递逻辑：`|| null` → `?? undefined`（修复0值丢失bug）；编辑回显 `|| null` → `?? null`（修复0值回显丢失）

### Bug修复
- 前端 `form.value.total_price || null` 当自定义金额为0时 `0||null=null`，传给后端变成未传 → 改为 `?? undefined`
- 后端 `model_dump(exclude_unset=True)` 会将 `total_price: None` 写入 order 导致总额被清空 → 排除 `total_price`
- 编辑回显 `row.total_price || null` 当总额为0时变为 null → 改为 `?? null`

### 测试验证
- 不传 total_price → 自动计算 = 400.0 ✓
- 传 total_price=5000 + 单价全0 → 差额按数量分配，合计=5000.0 ✓
- 传 total_price=5000 + 部分有单价 → 差额分配到单价0的行，合计=5000.0 ✓
- 传 total_price=360 + 全有单价 → 按比例打折，合计=360.0 ✓
- API 测试：total_price=5000 返回正确 ✓
- API 测试：不传 total_price 自动计算 ✓

---

## 2026-05-01 销售单/采购单禁止同一商品重复出库

### 变更概述
修复销售单和采购单允许同一商品出现多行的bug。同一订单内同一商品重复添加会导致：库存逐行扣减中间状态可能库存不足报错；删除/编辑订单时库存回补逻辑虽然总量正确但行级处理碎片化；用户数据录入容易出错。

三层防护：后端CRUD校验→前端选择防重→数据库唯一约束。

### 具体修改
- `backend/crud/orders.py` → `create_sale_order`/`update_sale_order`/`create_purchase_order`/`update_purchase_order` 增加重复 product_id 校验，发现重复时抛出 ValueError "同一商品不可重复添加，请合并到一行"
- `backend/models.py` → `SaleItem`/`PurchaseItem` 添加 `(order_id, product_id)` UniqueConstraint
- `backend/database.py` → 新增 `_migrate_unique_item_constraint` 迁移函数，自动清理已有重复数据（合并数量和金额）并创建唯一索引
- `frontend/src/views/Sales.vue` → `onItemProductChange`/`onEditItemProductChange` 检测已选商品重复，提示用户修改数量并清空当前选择
- `frontend/src/views/Purchases.vue` → 同上，`onItemProductChange`/`onEditItemProductChange` 增加重复检测

### 测试验证
- 后端：重复 product_id 创建销售单/采购单均返回 400 错误
- 后端：不同 product_id 正常创建
- 数据库：`uix_sale_item_order_product`/`uix_purchase_item_order_product` 唯一索引已创建
- 前端：编译通过，无语法错误

---

## 2026-05-01 销售单客户选择支持自定义输入（自动新建客户）

### 变更概述
销售单新建/编辑弹窗的客户选择从纯下拉改为可创建模式（`allow-create`），用户输入的客户名若不在列表中则自动新建客户。留空仍为散客。

### 具体修改
- `frontend/src/views/Sales.vue` → 新建弹窗：客户 `el-select` 添加 `allow-create default-first-option`，`v-model` 从 `customer_id` 改为 `customer_name`（字符串）
- `frontend/src/views/Sales.vue` → 编辑弹窗：同上改造
- `frontend/src/views/Sales.vue` → `form`/`editForm` 初始值：`customer_id: null` → `customer_name: ''`
- `frontend/src/views/Sales.vue` → `showEditDialog`：预填充 `customer_name: row.customer_name`
- `frontend/src/views/Sales.vue` → `handleSave`/`handleEditSave`：提交前按名字在 `customers` 列表查找 → 找到用已有 `customer_id` → 找不到调 `api.createCustomer({name})` 新建后取 `id` → 名字为空则 `customer_id=null`（散客）
- 后端无需改动

### 测试验证
| 测试项 | 结果 |
|--------|------|
| 前端构建 | 通过（✓ built in 7.07s） |
| 后端创建客户API | `POST /api/customers/` 返回 `{id: 5, name: "测试散客A"}` |
| 后端删除客户API | `DELETE /api/customers/5` 返回 `{"message":"已删除"}` |

---

## 2026-05-01 导出功能修复：window.open改为axios blob（解决缺少X-Account-ID请求头）

### 变更概述
4个Vue页面的导出功能使用 `window.open()` 直接打开URL，浏览器原生请求不经过axios拦截器，不携带 `X-Account-ID` 请求头，导致后端返回"缺少 X-Account-ID 请求头，请先选择账本"。统一改为 `api.exportFile()` 通过axios发请求+blob下载，与 `exportProductsBatch` 模式一致。

### 具体修改
- `frontend/src/api/index.js` → 新增通用 `exportFile(type, format, params)` 方法：通过 `api.get()` + `responseType: 'blob'` 发请求（自动携带X-Account-ID），从 Content-Disposition 解析文件名，`URL.createObjectURL` 触发浏览器下载
- `frontend/src/views/Inventory.vue` → `exportData` 改为 async，`window.open(api.getExportUrl(...))` → `await api.exportFile('inventory', format, params)`
- `frontend/src/views/Purchases.vue` → 同上模式，`'purchases'`
- `frontend/src/views/Sales.vue` → 同上模式，`'sales'`
- `frontend/src/views/Reports.vue` → `exportReport` 改为 async，`window.open(api.getExportUrl(...))` → `await api.exportFile(typeMap[activeTab.value]||'profit', format, params)`

### 测试验证
| 测试项 | 结果 |
|--------|------|
| 后端带 X-Account-ID 请求导出 | 200 OK |
| 后端不带 X-Account-ID 请求导出 | 返回 `{"detail":"缺少 X-Account-ID 请求头，请先选择账本"}` |
| 前端构建 | 通过（✓ built in 7.24s） |
| window.open+getExportUrl 残留检查 | 0处，全部替换完成 |

---

## 2026-05-01 销售单价格改为用户自行填写

### 变更概述
销售单选择商品后不再自动带商品指导价（sale_price），允许用户自行填写销售单价。采购单保持原有逻辑不变（选择商品自动带入采购价）。

### 具体修改
- `frontend/src/views/Sales.vue` → `onItemProductChange`（新建销售单）：移除自动填充 `p.sale_price` 的逻辑
- `frontend/src/views/Sales.vue` → `onEditItemProductChange`（编辑销售单）：移除自动填充 `p.sale_price` 的逻辑

### 测试验证
- 前端 vite build 构建成功，无编译错误

---

## 2026-04-30 采购单+销售单行级编辑及体验优化

### 变更概述
1. 采购单支持行级商品编辑（修改数量/单价、删除行自动扣库存、行数归零自动删单）
2. 销售单对称支持行级编辑（与采购单一致的编辑体验，含零售库存回补/扣减、项目收入联动）
3. 采购单付款状态前端展示和编辑（列表显示已付款/未付款标签，新建/编辑弹窗可修改）
4. 编辑采购单支持修改税率（编辑弹窗增加税率下拉，0%/3%/6%/9%/13%）

### 具体修改

**采购单行级编辑**
- `backend/schemas.py` → PurchaseOrderUpdate 扩展：新增 supplier_id, project_id, has_invoice, payment_method, items（全量替换模式）
- `backend/crud/orders.py` → 重写 update_purchase_order：支持 items 全量替换，旧行先扣库存→删除旧行→新建行加库存→重算总价；新 items 为空时自动删除整个采购单
- `frontend/src/views/Purchases.vue` → 操作列增加"编辑"按钮；新增编辑弹窗（支持预填充、行内增删改）；状态操作下拉改为独立入口

**销售单行级编辑**
- `backend/schemas.py` → SaleOrderUpdate 扩展：新增 customer_id, project_id, has_invoice, payment_status, items
- `backend/crud/orders.py` → 重写 update_sale_order：支持 items 全量替换，旧零售库存回补→删旧行→新行扣库存→重新生成项目收入；行数归零自动删单
- `frontend/src/views/Sales.vue` → 操作列增加"编辑"按钮；新增编辑弹窗（支持客户/项目/出库开关/开票/支付状态/备注/图片/商品明细编辑）

**采购单付款状态展示**
- `frontend/src/views/Purchases.vue` → 列表增加"付款状态"列（已付款/未付款标签）；新建/编辑弹窗增加付款状态下拉

**编辑采购单税率**
- `frontend/src/views/Purchases.vue` → 编辑弹窗增加税率选择；showEditDialog 预填充 tax_rate；handleEditSave 提交 tax_rate

### 测试验证
- 后端模块导入验证通过（schemas.py + crud/orders.py）
- 前端 vite build 构建成功，无编译错误

---

## 2026-04-29 采购管理+库存管理页面增加查询按钮

### 变更概述
采购管理和库存管理页面增加搜索框和查询按钮，筛选器不再自动触发查询，改为统一由查询按钮触发，风格与商品管理页面一致。

### 具体修改
- `backend/crud/orders.py` → list_purchase_orders 新增 keyword 参数，支持按单号/项目名/供应商名模糊搜索
- `backend/routers/purchases.py` → list_purchases 路由新增 keyword 查询参数
- `backend/crud/products.py` → list_inventory 新增 search+category 参数，统一先 join Product 再按条件过滤
- `backend/routers/inventory.py` → list_inventory 路由新增 search+category 查询参数
- `frontend/src/views/Purchases.vue` → 新增 keyword 搜索框+查询按钮，移除 @change 自动查询，loadData/exportData 传 keyword
- `frontend/src/views/Inventory.vue` → 新增 searchKeyword 搜索框+categoryFilter 分类筛选+查询按钮，预警开关从 header 移到筛选区，loadData/exportData 传 search/category

### 测试验证
- 后端模块导入验证通过（crud.orders, crud.products, routers.purchases, routers.inventory）
- 前端 vite build 构建成功，无编译错误

---

## 2026-04-28 SKILL.md更新：联动改造v2.4同步

### 变更概述
联动改造v2.4全量实施完成后，将SKILL.md同步更新至v5.0.0，补全联动相关API、字段、注意事项。

### 具体修改
- `docs/SKILL.md` → 场景A新增：不变量验证(`POST /api/projects/verify-invariants`)、对账修复(`POST /api/projects/reconcile`)
- `docs/SKILL.md` → B2采购入库：project_name改为project_id，说明自动反查填充
- `docs/SKILL.md` → B3销售出库：project_name改为project_id，说明不再扣库存+自动生成项目收入
- `docs/SKILL.md` → B7项目成本：新增product_id+quantity字段，说明材料类联动库存机制
- `docs/SKILL.md` → B8项目收入：新增source_type/source_id说明
- `docs/SKILL.md` → 新增场景G：联动验证与对账（verify-invariants + reconcile）
- `docs/SKILL.md` → 新增"联动机制(v2.4改造)"章节：核心链路、三大不变量、8条注意事项
- `docs/SKILL.md` → 关键字段限制新增：收入来源类型(manual/sale_order)
- `docs/SKILL.md` → 版本号：v4.0.0 → v5.0.0

### 测试验证
- 文件内容逐项核对，所有联动API和字段说明与改造方案v2.4一致

---

## 2026-04-28 联动改造v2.4全量实施

### 变更概述
实施联动改造方案v2.4，实现项目成本↔库存联动、销售单↔项目收入联动、统一利润计算三大核心改造。

### 具体修改

**阶段1：数据层**
- `backend/models.py` → SaleOrder/PurchaseOrder 新增 project_id(FK→projects.id)+relationship；ProjectCost 新增 product_id(FK→products.id)+quantity+product relationship；ProjectIncome 新增 source_type/source_id + UniqueConstraint("source_type","source_id")
- `backend/database.py` → 新增 `_migrate_linkage(engine)` 迁移函数：6列DDL+5索引+同名项目消除+uq_projects_account_name唯一索引+旧数据project_id回填+销售单收入回填；init_db()末尾调用
- `backend/schemas.py` → SaleOrderCreate/Out+PurchaseOrderCreate/Out 新增 project_id；ProjectCostCreate 新增 product_id/quantity/unit_price；ProjectCostUpdate 新增 product_id/quantity；ProjectCostOut 新增 product_id/quantity/product_name；ProjectIncomeCreate/Out 新增 source_type/source_id

**阶段2：联动业务层**
- `backend/crud/linkage.py` → 新建，5个联动函数：cost_deduct_inventory(材料扣库存)、cost_restore_inventory(材料回补库存)、cost_update_inventory(更新库存差值)、sale_create_income(销售单生成收入)、sale_delete_income(销售单删除收入)
- `backend/crud/base.py` → `_log` 函数从 db.commit() 改为 db.flush()，保证事务原子性

**阶段3：统一计算**
- `backend/utils.py` → update_project_summary 移除 db.commit()、新增采购成本(PurchaseOrder)计算、round(2)；新增 verify_invariants 三大不变量验证函数

**阶段4：路由层改造**
- `backend/routers/project_costs.py` → 全部6个端点改造：创建/删除/更新成本调用 linkage + update_project_summary，删除所有增量累加；收入端点保护 sale_order 来源不可手动修改/删除；列表返回 product_id/quantity/product_name/source_type/source_id
- `backend/crud/orders.py` → create_sale_order 移除库存扣减+新增 project_id/project_name 赋值+sale_create_income；update_sale_order 移除库存操作+取消/恢复联动收入；delete_sale_order 移除库存回补+sale_delete_income；create/update/delete_purchase_order 新增 project_id 赋值+update_project_summary
- `backend/routers/sales.py` → 新增 operator 传参+project_id 返回
- `backend/routers/purchases.py` → 新增 operator 传参+project_id 返回
- `backend/routers/projects.py` → get_projects 改为 GROUP BY 聚合+project_id关联；get_project_detail 新增采购单tab+商品名批量查询+source_type/source_id；delete_project 新增前置校验+级联回补；新增 verify-invariants + reconcile 端点；移除旧的 create_project_cost/income 端点和聚合详情弹窗

**阶段5：前端改造**
- `frontend/src/views/Sales.vue` → project_name→project_id下拉+数据源切换getProjectList+移除出库提示
- `frontend/src/views/Purchases.vue` → project_name→project_id下拉+数据源切换getProjectList
- `frontend/src/views/Projects.vue` → 订单聚合看板改为项目概览(统一Project表)；成本表新增商品/数量列；收入表新增来源列+sale_order保护；新增采购单tab；移除旧聚合详情弹窗

### 测试验证
- 后端 init_db()+app创建：107条路由，无报错
- 迁移验证：6个新列、5个索引、2个唯一索引均已创建
- 旧数据回填：sale_orders/purchase_orders 的 project_id 回填正常（无匹配的为NULL）
- verify_invariants 执行正常，返回违规项（1个负库存历史数据）
- 所有Python模块导入验证通过

---

## 2026-04-28 联动改造前端补完：成本添加弹窗

### 变更概述
Projects.vue 新增"添加成本"按钮和成本添加弹窗，支持材料类成本选择商品+自动计算金额。

### 具体修改
- `frontend/src/views/Projects.vue` → 成本明细tab新增"添加成本"按钮；新增costAddVisible弹窗（含costTypes枚举、product_id下拉+库存显示、quantity+unit_price自动计算amount、支付方式/发票状态/供应商/备注字段）；新增7个JS函数（onCostTypeChange/onProductSelect/calcMaterialAmount/showCostAddDialog/saveCostAdd）

### 测试验证
- 方法：vite build 前端编译
- 结果：构建成功，无编译错误

### 变更概述
修正5项硬/高风险：导入缺失、SQLite约束说明、销售单双扣、校验未实现、金额口径。

### 具体修改
- `docs/联动改造方案.md` → v2.4：
  - `crud/linkage.py` 代码片段增加 `from typing import Optional`
  - `UniqueConstraint` 注释明确"SQLite旧表靠CREATE UNIQUE INDEX，模型层约束给新库"
  - 销售单库存扣减逻辑移除：库存出库统一走项目领料，销售单只记录客户和金额，不再扣库存
  - `verify_invariants` 删掉未实现的软校验伪代码，保留负库存硬校验+后续增强注释
  - 金额口径明确：amount为唯一真实值，前端辅助计算unit_price不存库，允许手动调整

### 测试验证
- 方法：逐项审查5项修正在方案中的体现
- 结果：5项修正全部落地

---

## 2026-04-28 联动改造方案v2.3拼写+回填策略修正

### 变更概述
修正Vue模板拼写错误；将同名项目回填策略从"warning+随机绑最早"改为"强制消除同名+UNIQUE约束+安全回填"。

### 具体修改
- `docs/联动改造方案.md` → v2.3：
  - 修正 `:value]="p.id"` 为 `:value="p.id"`（Vue模板拼写错误）
  - 回填策略重构：同名项目不再"随机绑最早"，而是先自动重命名（加后缀_2/_3），再建 `UNIQUE(account_id, name)` 索引，最后才安全回填
  - 回填SQL增加 `account_id` 条件，确保跨账号不误绑

### 测试验证
- 方法：审查Vue模板语法和回填SQL逻辑
- 结果：拼写已修正；同名项目场景下不会绑错，而是先消除同名再回填

---

## 2026-04-29 销售单零售扣库存开关（deduct_inventory）

### 变更概述
为销售单新增 `deduct_inventory` 开关：**零售=true 由销售单直接扣/回补库存**；**项目业务保持不扣库存，继续走项目领料/材料成本联动**，避免双扣。

### 具体修改
- `backend/models.py` → `SaleOrder` 新增 `deduct_inventory` 字段（旧数据允许 NULL，逻辑按 false 处理）
- `backend/schemas.py` → `SaleOrderCreate/Update/Out` 新增 `deduct_inventory`；`SaleOrderOut` 输出层归一化 NULL→false
- `backend/database.py` → `_migrate_linkage` 增加 `sale_orders.deduct_inventory` 迁移（默认0）
- `backend/crud/linkage.py` → 新增零售销售单库存联动：`sale_deduct_inventory`/`sale_restore_inventory`（仅在 `deduct_inventory=true && project_id is NULL && status=completed` 生效）
- `backend/crud/orders.py` → 销售单创建/删除/状态切换增加零售扣库存分支；项目单若传 `deduct_inventory=true` 返回400拒绝，防止双扣
- `backend/routers/sales.py` → 销售单响应增加 `deduct_inventory`
- `frontend/src/views/Sales.vue` → 新增“零售出库(直接扣库存)”开关；选择项目时禁用并强制不扣库存；创建销售单提交 `deduct_inventory`
- `docs/销售单零售扣库存开关方案.md` → 新增独立方案文档（v1.1审查修正版）

### 测试验证
- 后端：执行 `init_db()` 迁移无报错；`import backend/main.py` 通过
- 前端：`npm run build` 构建通过

---

## 2026-04-29 项目管理：项目详情页体验与效率优化（Drawer + 筛选 + 追溯）

### 变更概述
优化项目管理前端项目详情页的体验与效率：详情改为抽屉展示、首屏增加KPI与风险提示、成本/收入明细增加筛选与合计，并支持从自动收入一键追溯到来源销售单。

### 具体修改
- `docs/项目管理-项目详情页优化方案.md` → 新增可执行方案文档（体验+效率优先）
- `frontend/src/api/index.js` → 新增 `getSale(id)` 便于收入追溯
- `frontend/src/views/Projects.vue` →
  - 项目详情 `el-dialog` → `el-drawer`，首屏增加KPI（收入/成本/利润/待收/已收/未开票）
  - 成本明细：增加筛选条（类型/支付/发票/日期/关键字）+ 当前筛选合计
  - 收入明细：增加筛选条（来源/收款/发票/日期/关键字）+ 待收/已收汇总
  - 自动收入（sale_order）增加“查看销售单”按钮，调用 `GET /api/sales/{id}` 弹窗展示销售单明细

### 测试验证
- 前端：`npm run build` 构建通过

---

## 2026-04-28 联动改造方案v2.2审查修正

### 变更概述
基于7项审查意见修正方案：空值防护、事务边界、函数职责、查询性能、删除校验、索引补全、回填策略和前端兼容。

### 具体修改
- `docs/联动改造方案.md` → v2.2升级，主要变化：
  - `cost_update_inventory` 签名改为 `Optional[str/int]`，增加 `old_quantity or 0` 空值防护
  - 路由层事务模式增加"失败回滚铁律"：flush→联动→commit，失败必须rollback整个事务
  - `update_project_summary` 移除内部 `db.commit()`，由调用方统一commit（事务编排权归调用方）
  - `get_projects` 从N+1查询改为GROUP BY批量聚合
  - 项目删除增加前置校验（未取消销售单/采购单禁止删除）+ 统一库存联动入口说明
  - `project_incomes.source_id` 增加单独索引
  - 回填策略处理同名项目（检测冲突+按created_at ASC取最早）+ 建议加UNIQUE(account_id,name)
  - 后端自动填充project_name（前端不传，从project_id反查），避免历史查询出现空值

### 测试验证
- 方法：逐项审查7项修正是否在方案中正确体现
- 结果：7项修正全部落地，方案完整

---

## 2026-04-28 联动改造方案v2.0精简重写

### 变更概述
将联动改造方案从v1.1（含重复章节和独立架构优化章节）精简合并为v2.0，架构优化融入代码变更步骤，消除重复。

### 具体修改
- `docs/联动改造方案.md` → 全文重写，主要变化：
  - 删除重复的第一、二章（v1.1合并时产生）
  - 架构优化（联动逻辑下沉crud/linkage.py、旧数据回填、聚合接口改造）从独立第十一章融入第三~六章
  - 迁移函数整合：索引创建+旧数据回填+收入回填统一在`_migrate_linkage`中
  - 路由层直接调用linkage函数，不再先写内联版再写抽取版
  - 进阶优化（SQLAlchemy event监听、前端单tab合并）降级为第十一章"可选"
  - 行数从1457行精简到约700行

### 测试验证
- 方法：逐章审查方案结构，确认无遗漏（6大断裂点→5个实施步骤→进阶优化）
- 结果：方案完整无重复，架构优化已融入各步骤

---

## 2026-04-28 联动改造方案v2.1不变量强化

### 变更概述
基于三大不变量（库存/收入/汇总）审查方案，补充模型层约束、代码层幂等检查、事务模式修正和对账机制。

### 具体修改
- `docs/联动改造方案.md` → v2.1升级，主要变化：
  - 第二章新增"三大不变量"表格
  - 步骤1：ProjectIncome增加`uq_income_source` UNIQUE约束，迁移增加去重+唯一索引
  - 步骤2：`cost_deduct_inventory`加assert断言，`sale_create_income`加幂等检查
  - 步骤3.5新增：`verify_invariants`不变量验证函数 + 对账API
  - 步骤4：所有路由改为单次commit模式（消除汇总不一致窗口）
  - 风险章节：新增三层防护表

### 测试验证
- 方法：逐项审查三大不变量的模型层/代码层/事后校验保障
- 结果：三大不变量均有三层防护（约束→代码→校验），方案完整

> 本文档记录项目的每一次代码变更，确保跨会话可追溯。
> 每次修改经测试通过后必须在此追加记录。

---

## 2026-04-28 个人支出类别新增"烟酒"

### 变更概述
个人流水账支出类别新增"烟酒"选项。

### 具体修改
- `backend/enums.py` → PERSONAL_EXPENSE_CATEGORIES 列表中"医疗"与"其他"之间插入"烟酒"

### 测试验证
- 方法：重启后端后调用 `GET /api/enums`，确认 personal_expense_categories 返回7项，包含"烟酒"
- 结果：API 返回 `["餐饮","日用","交通","娱乐","医疗","烟酒","其他"]`，验证通过

---

## 2026-04-28 架构加固 + crud模块拆分

### 变更概述
评估系统架构健壮性，修复6个架构问题，并将 crud.py 单文件拆分为包目录。

### 1. crud.py 拆分为包目录（零破坏性）
- **原文件**: `backend/crud.py` (1496行单文件) → 已删除
- **新结构**: `backend/crud/` 包目录，通过 `__init__.py` re-export 保持 `crud.xxx` 调用方式不变
- **影响范围**: 所有 router 文件 `import crud` 零改动

| 子模块 | 行数 | 职责 | 关键改进 |
|--------|------|------|----------|
| `base.py` | ~50 | 公共函数：订单号生成、操作日志、库存查询 | 订单号增加HHMMSS时间戳防并发冲突 |
| `products.py` | ~120 | 商品+库存 CRUD | `update_product` 加事务包裹 |
| `partners.py` | ~140 | 供应商+客户 CRUD | 删除前主动查关联记录，有则拒绝 |
| `orders.py` | ~220 | 采购+销售 CRUD | 全部写操作加事务包裹 + 金额 round(2) |
| `invoices.py` | ~170 | 发票+税务 CRUD | 写操作加事务包裹 + 金额 round(2) |
| `projects.py` | ~120 | 项目 CRUD | 写操作加事务包裹 + 金额 round(2) |
| `personal.py` | ~100 | 个人流水 CRUD | 写操作加事务包裹 |
| `finance.py` | ~350 | 期初余额+三大报表+现金流量 | 写操作加事务包裹 |
| `logs.py` | ~20 | 操作日志查询 | 纯读操作无变更 |
| `reports.py` | ~140 | 统计报表 | 纯读操作无变更 |
| `__init__.py` | ~40 | 统一 re-export | 76个导出项，保持接口一致 |

### 2. 事务包裹（无事务 → 全覆盖）
- **问题**: 写操作出错后数据库状态不一致
- **修复**: 所有写操作加 `try/except Exception + db.rollback() + raise`
- **涉及文件**: `crud/orders.py`, `crud/partners.py`, `crud/products.py`, `crud/invoices.py`, `crud/projects.py`, `crud/personal.py`, `crud/finance.py`

### 3. 金额精度（Float → round兜底）
- **问题**: 浮点数累加产生精度偏差
- **修复**: 
  - 行金额: `line_total = round(quantity * unit_price, 2)`
  - 订单总额: `order.total_price = round(total, 2)`
  - 报表金额: `round(sum_value, 2)` 统一兜底
- **涉及文件**: `crud/orders.py`, `crud/invoices.py`, `crud/reports.py`, `crud/personal.py`, `crud/finance.py`

### 4. 订单号并发冲突
- **问题**: 同一天内多用户同时创建订单可能生成相同序号
- **修复**: 订单号格式从 `{前缀}{日期}-{序号}` 改为 `{前缀}{日期}-{时分秒}-{序号}`
  - 旧: `PO20260428-001`
  - 新: `PO20260428-143025-001`
- **涉及文件**: `crud/base.py` 的 `_generate_order_no()`
- **注意**: SQLite VARCHAR 实际不限存储长度，无需 schema 迁移

### 5. 供应商/客户不可随意删除
- **问题**: 有业务关联的供应商/客户可被直接删除，导致数据孤岛
- **修复**:
  - `delete_supplier`: 查 `PurchaseOrder` 关联，有则抛出 `ValueError` 拒绝
  - `delete_customer`: 查 `SaleOrder` + `Project` 双重关联，有则拒绝
- **涉及文件**: `crud/partners.py`

### 6. CORS 安全限制
- **问题**: `allow_origins=["*"]` 全开，生产环境存在跨域安全风险
- **修复**: 改为 localhost 白名单，支持 `CORS_ORIGINS` 环境变量追加
  - 允许: `localhost:5173`, `localhost:4173`, `localhost:8000`, `127.0.0.1` 对应端口
- **涉及文件**: `backend/main.py`

### 7. 前端 API 硬编码消除
- **问题**: `api/index.js` 硬编码 `http://localhost:8000`
- **修复**: 使用 Vite 环境变量
  - 开发环境: 走 Vite proxy (`/api` → `localhost:8000`)，无需设置变量
  - 生产环境: 设置 `VITE_API_BASE_URL=http://localhost:8000`
- **涉及文件**: `frontend/src/api/index.js`, `frontend/.env.development`, `frontend/.env.production`

### 测试验证

#### 基础连通性（12/12 通过）
- 后端启动成功，无导入错误
- 12个API端点全部返回200：商品、供应商、客户、采购、销售、发票、库存、概览、个人流水、日志、项目、费用
- crud包导出76个函数/常量，与原始单文件接口完全一致

#### 专项测试（全部通过）

| 测试项 | 方法 | 结果 | 说明 |
|--------|------|------|------|
| 事务rollback | db.flush→模拟异常→rollback→查数据恢复 | PASS | 核心事务机制正确 |
| 金额精度 | 创建采购单3项*33.33=99.99，验证line_total和total_price | PASS | round(2)精度正确 |
| 订单号格式 | 创建采购单验证返回的order_no | PASS | 格式PO20260428-133006-001含HHMMSS |
| 供应商关联删除拒绝 | DELETE /api/suppliers/3（有1条采购记录） | PASS | 返回409 + "该供应商存在1条采购记录，无法删除" |
| 供应商无关联可删除 | 创建新供应商→立即删除 | PASS | 返回200 |
| 客户关联删除拒绝 | DELETE /api/customers/3（account_id=2，有5条销售记录） | PASS | 返回409 + "该客户存在5条销售记录和0个项目关联，无法删除" |
| 客户无关联可删除 | 创建新客户→立即删除 | PASS | 返回200 |
| CORS白名单 | main.py配置检查 | PASS | localhost白名单+环境变量追加，无通配符 |
| 前端环境变量 | .env文件+api/index.js检查 | PASS | 无硬编码URL，走import.meta.env |

#### 已知问题（原始设计，非本次修复引入）
- **SKU无唯一约束**: `Product.sku` 字段只有 `index=True`，无 `unique=True`，重复SKU不会报错。当前23个SKU无重复，加约束安全。→ **待办：后续添加unique约束+迁移+API层检查**

---

## 2026-04-28 SKILL.md文档同步更新

### 变更概述
将SKILL.md与系统实际API端点完全同步，补全所有缺失端点。

### 具体修改
- 文件: `docs/SKILL.md`
  - 场景A查询数据：新增12个端点（健康检查、商品详情、商品分类、采购/销售详情、供应商/客户详情、发票PDF、项目按名称查询、财务汇总、期初余额详情、6个报表端点）
  - 场景B录入数据：新增B5.1发票文件上传、B5.2发票PDF下载、B10.1/B10.2项目下直接创建成本/收入、B14-B16图片上传/替换/删除
  - 新增场景E数据导出（5个xlsx导出端点）
  - 新增场景F热备份（执行备份、备份列表、下载备份）
  - 关键字段限制：新增个人支出/收入类别、现金流方向/类别、图片业务类型/格式
  - 错误处理：409增加关联删除拒绝说明
  - 版本号：v3.0.0 → v4.0.0

### 测试验证
- 后端实际106个API端点，SKILL.md覆盖所有核心端点
- 所有枚举值与`backend/enums.py`一致
- 图片/备份/导出API均在main.py和对应router中确认存在

---

## 2026-05-01 对账管理功能

### 变更概述
新增对账管理功能，支持按供应商和客户维度实时计算对账数据，点开页面即可查看所有对方的对账汇总。

### 具体修改
- `backend/routers/reconciliations.py` → 新建对账路由，提供2个接口：
  - `GET /api/reconciliations/` — 一键获取所有供应商/客户的对账汇总（期初欠款、本期发生、已收/已付、期末欠款、发票金额），按期末欠款降序排列
  - `GET /api/reconciliations/detail` — 查看单个对方的对证明细（订单+发票）
- `backend/main.py` → 注册对账路由（同时注册 `/api/reconciliations` 和 `/api/reconciliation` 以兼容有无斜杠的请求）
- `frontend/src/api/index.js` → 新增 `getReconciliations()` 和 `getReconciliationDetail()` API方法
- `frontend/src/views/Reconciliations.vue` → 新建对账页面：
  - 手动查询（类型+日期范围+查询按钮）
  - 汇总卡片展示合计数据
  - 表格展示所有对方对账数据，点击行或"明细"按钮打开抽屉查看明细
- `frontend/src/router/index.js` → 注册 `/reconciliations` 路由
- `frontend/src/components/Layout.vue` → 侧边栏新增"对账管理"导航
- `frontend/vite.config.js` → 代理端口从8000改为8001（匹配当前后端服务端口）

### 测试验证
- 后端导入验证通过
- 前端 `npm run build` 构建成功

---

## 2026-05-01 采购单付款状态修复

### 变更概述
修复采购单付款状态无法修改的问题。

### 问题原因
`PurchaseOrderUpdate` Schema 缺少 `payment_status` 字段，导致前端提交修改时该字段被忽略；同时 `PurchaseOrderOut` 和 `_build_purchase_out` 也未返回该字段，前端无法显示当前值。

### 具体修改
- `backend/schemas.py` → `PurchaseOrderUpdate` 新增 `payment_status: Optional[str] = None`
- `backend/schemas.py` → `PurchaseOrderOut` 新增 `payment_status: str`
- `backend/routers/purchases.py` → `_build_purchase_out` 添加 `payment_status=order.payment_status`

### 测试验证
- 后端导入验证通过

---

## 2026-05-01 库存商品批量导出接口

### 变更概述
新增库存商品批量导出后端接口和前端批量选择导出功能，支持按勾选的商品ID列表导出为 Excel 或 CSV 格式。修复了原导出功能因未携带 `X-Account-ID` 请求头导致"没选择账本"报错的问题。

### 具体修改

**后端**
- `backend/routers/export.py` → 新增 `GET /api/export/products-batch` 路由：
  - 参数 `product_ids`（必填）：逗号分隔的商品ID列表
  - 参数 `format`（可选）：`excel`（默认）或 `csv`
  - 按 `account_id` + `id.in_` 查询商品及库存，组装为文件流返回
  - 异常处理：非法ID返回400，空ID返回400，缺少账本头401由 `account_dep` 拦截

**前端**
- `frontend/src/api/index.js` → 新增 `exportProductsBatch(ids, format)` 方法：
  - 通过 axios 发起请求（自动携带 `X-Account-ID` 请求头）
  - `responseType: 'blob'` 接收二进制流
  - `URL.createObjectURL` 触发浏览器下载
- `frontend/src/views/Products.vue` →：
  - 表格首列新增复选框（`<el-table-column type="selection" />`）
  - 顶部导出按钮改为"批量导出"，未选择商品时禁用
  - 新增 `handleSelectionChange` 和 `exportBatch` 方法
  - 移除原 `exportData`（使用 `window.open`，无法携带请求头）

### 测试验证
| 测试项 | 结果 |
|--------|------|
| Excel 批量导出（带请求头） | 200 OK，`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| CSV 批量导出（带请求头） | 200 OK，`text/csv; charset=utf-8` |
| 非法 product_ids（如 `abc`） | 400，`product_ids 必须是逗号分隔的整数列表` |
| 空 product_ids | 400，`product_ids 不能为空` |
| 缺少 X-Account-ID 请求头 | 401，`缺少 X-Account-ID 请求头，请先选择账本` |
| 前端构建 | 通过（✓ built in 7.32s）|

---

## 2026-05-01 库存商品批量导出接口修复

### 变更概述
修复前端批量导出仍提示"没选择账本"的问题。根因是 axios 响应拦截器 `res => res.data` 会解包响应，blob 类型被错误处理；同时原实现使用 `api.get()` 经过拦截器后返回的是被 unwrap 的数据而非原始响应。

### 具体修改
- `frontend/src/api/index.js` → `exportProductsBatch` 方法重写：
  - 改为直接使用 `axios.get()` 而非 `api.get()`，绕过响应拦截器
  - 手动构造完整 URL（`${baseURL}/export/products-batch?...`）
  - 手动携带 `X-Account-ID` 和 `X-Operator` 请求头
  - `responseType: 'blob'` 确保 `res.data` 为 Blob 对象
  - 移除错误注释（拦截器不会返回 blob，必须绕过）

### 测试验证
| 测试项 | 结果 |
|--------|------|
| 后端返回 blob 数据 | 200 OK，Excel 4993 bytes，`isinstance(bytes)` True |
| CSV 导出 | 200 OK，`text/csv; charset=utf-8` |
| 前端构建 | 通过（✓ built in 10.04s）|

---

## 2026-05-01 业务逻辑漏洞修复（10项）

### 变更概述
通过审查SKILL.md文档与后端代码比对，发现并修复10个业务逻辑漏洞/不一致问题，涵盖税务计算、项目汇总、库存联动、API参数、文档同步等方面。

### 具体修改

**1. 企业所得税计算未过滤取消订单（严重）**
- `backend/routers/income_tax.py` → `total_revenue` 和 `total_cost` 查询添加 `status == "completed"` 过滤条件，已取消的销售单/采购单不再计入企业所得税的收入和成本

**2. 销售单项目切换时旧项目汇总未重算（严重）**
- `backend/crud/orders.py` → `update_sale_order` 中 `project_id_to_update` 改为 `project_ids_to_update = set()`，items替换路径中旧项目和新项目都加入集合；非items路径中新增 project_id 变更处理（联动3：删除旧项目收入+创建新项目收入），所有受影响项目统一遍历重算汇总

**3. 采购单项目切换时旧项目汇总未重算（严重）**
- `backend/crud/orders.py` → `update_purchase_order` 中 `project_id` 改为 `old_project_id`，新增 `project_ids_to_update = set()`；items替换路径和状态切换路径中所有受影响项目ID都加入集合统一重算

**4. 采购单更新时status+items交互导致库存重复调整（严重）**
- `backend/crud/orders.py` → `update_purchase_order` 重构执行顺序：items替换时先setattr更新普通字段（含status），再基于new_status创建新行扣减库存；状态切换库存处理仅在不改items时生效（else分支），避免双重扣减

**5. 对账API参数名不一致 party_type vs type**
- `backend/routers/reconciliations.py` → 3处参数声明 `type` → `party_type`，内部所有引用同步修改，返回值key `"type"` → `"party_type"`
- `frontend/src/views/Reconciliations.vue` → `filter.type` → `filter.party_type`，模板绑定、API调用参数、结果展示同步修改

**6. 发票上传接口B5.1参数与代码不一致**
- `backend/routers/invoices.py` → `upload_pdf` 接口从仅接收 `file: UploadFile` 改为同时接收发票数据（Form字段：invoice_no, direction, invoice_type, amount_with_tax, tax_rate, counterparty_name, issue_date, project_name, notes）+ PDF文件，自动算税后创建发票记录并关联PDF文件路径

**7. 销售单取消时库存不回补（严重）**
- `backend/crud/linkage.py` → `sale_restore_inventory` 移除 `order.status != "completed"` 检查。原逻辑中setattr已将status改为cancelled导致回补被跳过，改为由调用方控制回补时机（update_sale_order中通过 `old_status == "completed"` 判断，delete_sale_order中无条件调用但函数内仍有deduct_inventory和project_id检查保护）

**8. 现金流量表项目成本过滤口径不一致**
- 经分析：`ProjectCost` 模型无 `payment_status` 字段（记录即视为已发生现金流出），`PurchaseOrder` 有该字段是因为采购可挂账。当前过滤逻辑（项目成本只按payment_method，采购单按payment_status+payment_method）合理，非bug

**9. 对账发票匹配用名称字符串而非ID关联**
- 经分析：`Invoice` 模型无 `counterparty_id` 字段，只有 `counterparty_name`。改用ID关联需添加字段+数据库migration，属架构变更，暂不修复

**10. SKILL.md文档参数名与代码不一致**
- `docs/SKILL.md` → `party_id` → `partner_id`（2处）；`party_type` 描述从"不传则返回全部"改为"必填"；B5.1上传接口描述更新为Form字段+file模式；版本号 v5.4.0 → v5.5.0

### 测试验证
| 测试项 | 结果 |
|--------|------|
| 后端 reconciliations 路由导入 | 通过（参数名已改为 party_type） |
| 后端 invoices 路由导入 | 通过（upload_pdf 接收 Form+File） |
| 后端 linkage 模块导入 | 通过（sale_restore_inventory 移除status检查） |
| 后端全模块联合导入验证 | 通过（reconciliations + invoices + linkage + orders） |
| 前端 Reconciliations.vue 修改确认 | 通过（filter.party_type, api参数同步） |

---

## 更新记录模板

```
## YYYY-MM-DD 简要标题

### 变更概述
一句话描述本次变更的目的和范围。

### 具体修改
- 修改1: 文件 → 改了什么
- 修改2: 文件 → 改了什么

### 测试验证
- 验证方法
- 验证结果
```