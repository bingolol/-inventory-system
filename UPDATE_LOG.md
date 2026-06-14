# 进销存管理系统 - 更新日志

> 本文档记录项目的每一次代码变更，确保跨会话可追溯。

---

## 2026-05-19 22:35 测试文件清理：删除backend_api脚本式测试

### 变更摘要
1. 删除 tests/backend_api/ 目录下7个脚本式测试文件（已被E2E测试全面替代）
2. 更新 docs/文件索引.md 移除已删除文件的条目

### 删除文件列表
- `tests/backend_api/check_enum.py` — 硬编码绝对路径的一次性枚举检查脚本
- `tests/backend_api/cleanup_test_data.py` — 一次性数据清理脚本
- `tests/backend_api/test_project_api.py` — httpx脚本式项目API测试
- `tests/backend_api/full_api_test.py` — httpx脚本式全量API测试
- `tests/backend_api/test_comprehensive.py` — httpx脚本式综合测试
- `tests/backend_api/test_full_loop.py` — 20KB手动闭环脚本测试
- `tests/backend_api/test_invoice_full.py` — httpx脚本式发票测试
- `tests/backend_api/test_personal_category.py` — requests脚本式个人分类测试

### 保留的测试
- `tests/e2e/test_e2e.py` — pytest格式E2E测试（39用例）
- `tests/unit/` — pytest格式单元测试（105 passed）
- `tests/integration/` — pytest格式集成测试

### 关键设计决策
- 所有backend_api文件都是httpx/requests手动脚本，需手动启动后端才能运行，用print而非assert断言
- E2E测试使用FastAPI TestClient+真实SQLite，不依赖外部服务器，pytest格式，全面覆盖
- 删除后 tests/backend_api/ 整个目录已移除

---

## 2026-05-19 16:00 打包交付增强：端口检测+console隐藏+E2E测试

### 变更摘要
1. launcher.py 增加端口冲突检测和自动换端口逻辑（8000~8099），支持环境变量 INVENTORY_PORT 指定端口
2. launcher.py 新增 _write_crash_log() 函数，console=False 模式下将致命错误写入桌面崩溃文件+工作区日志
3. inventory.spec console=True → console=False，打包后无黑色CMD窗口
4. workspace.py 新增 get_port_path() 函数，返回 port.txt 路径
5. 新增 tests/e2e/test_e2e.py 端到端自动化测试（39个测试用例，覆盖12个场景）

### 涉及文件
- `launcher.py` — 重写：新增 is_port_available()、find_available_port()、save_port()、_write_crash_log()；端口从硬编码8000改为动态检测；open_browser() 接收动态端口参数
- `inventory.spec` — console=True → console=False
- `backend/workspace.py` — 新增 get_port_path() 函数
- `tests/e2e/test_e2e.py` — 新建：39个E2E测试用例

### 关键设计决策
- 端口检测同时 bind 127.0.0.1 和 0.0.0.0，因为 uvicorn 绑定 0.0.0.0 会占用两者
- console=False 下错误不可见，写入桌面崩溃文件是最显眼的用户通知方式
- E2E 测试使用 FastAPI TestClient + 真实 SQLite，session 级 fixture 共享数据

### 测试验证
- E2E 测试：39 passed ✅
- 单元+集成测试：105 passed, 2 skipped ✅

---

## 2026-05-19 17:00 架构参考文档同步更新

### 变更摘要
1. 更新文档最后更新日期为 2026-05-19
2. 2.3节测试目录新增 tests/e2e/ 说明
3. 附录API速查表修正6个端点路径（/api/project-costs→/api/costs 等）
4. 新增5.6节"打包部署"（端口检测/console=False/崩溃日志/port.txt/工作区隔离）

### 涉及文件
- `docs/架构参考_正式版.md` — 4处更新

---

## 2026-05-17 10:30 前端排版优化

### 变更摘要
1. 全局 CSS 体系升级：新增 CSS 变量（间距/字号/颜色层级）、通用布局类（card-header/page-title/filter-bar/pagination-bar）
2. `formatMoney` 增加千分位显示（`toLocaleString`），大金额数字可读性大幅提升
3. 所有页面统一卡片 header 结构（`card-header` + `page-title`），消除内联 `font-weight:600` 样式
4. 所有金额列右对齐 + `money` 类（等宽数字字体），表格对齐整齐
5. 筛选栏统一使用 `filter-bar` 类，间距/换行/按钮风格一致
6. 分页栏统一使用 `pagination-bar` 类
7. Dashboard 统计卡片：金额用 `formatMoney` 显示千分位，笔数单独显示更清晰

### 涉及文件
- `frontend/src/styles/global.css` — 新增 CSS 变量体系 + 5个通用布局类 + money/text-green/text-red 类
- `frontend/src/api/common.js` — `formatMoney` 改用 `toLocaleString` 实现千分位
- `frontend/src/views/Products.vue` — header/筛选栏/金额列/分页栏统一
- `frontend/src/views/Suppliers.vue` — header/筛选栏/分页栏统一
- `frontend/src/views/Customers.vue` — header/筛选栏/分页栏统一
- `frontend/src/views/Purchases.vue` — header/筛选栏/金额列/分页栏统一
- `frontend/src/views/Sales.vue` — header/筛选栏/金额列/分页栏统一
- `frontend/src/views/Inventory.vue` — header/筛选栏/金额列统一
- `frontend/src/views/Logs.vue` — 标题/筛选栏/分页栏统一
- `frontend/src/views/Projects.vue` — header 统一
- `frontend/src/views/Reports.vue` — header 统一
- `frontend/src/views/Invoices.vue` — header 统一
- `frontend/src/views/Expenses.vue` — 金额列加 ¥+千分位
- `frontend/src/views/Dashboard.vue` — 统计卡片金额千分位 + import formatMoney

### 关键设计决策
- 不新建任何组件，只通过 global.css 通用类 + 逐页替换内联样式实现
- `formatMoney` 改为千分位是破坏性变更（返回值格式变了），但所有调用方都是显示用，无计算依赖，安全

---

## 2026-05-14 10:30 增加删除账本功能

### 变更摘要
1. 增加删除账本功能，用户点击删除按钮后弹出二次确认提示窗口
2. 后端仅允许删除无业务数据的空账本，有数据时返回 409 错误并提示具体原因

### 涉及文件
- `backend/crud/base.py` — 新增 `delete_account()` 函数，检查13个关联表是否有数据，有则抛 ValueError
- `backend/main.py` — 新增 `DELETE /api/accounts/{account_id}` 路由，处理 404/409 状态码
- `frontend/src/api/common.js` — 新增 `deleteAccount(id)` API 调用
- `frontend/src/components/Layout.vue` — 账本选择器旁增加删除按钮(Delete图标)，点击后 `ElMessageBox.confirm` 二次确认

### 关键设计决策
- 参照 `DeleteSupplier` 的约束校验模式，仅允许删除空账本，防止误删造成不可逆数据损失
- 二次确认使用 `ElMessageBox.confirm`（warning 类型），确认按钮样式为 danger
- 删除成功后自动切换到剩余的第一个账本

---

## 2026-05-13 14:45 账本管理增强 + 安装打包修复

### 变更摘要
1. 修复前端 `commonApi.createAccount is not a function`：common.js 默认导出对象缺少 `createAccount`/`updateAccount`
2. 重新构建前端 dist 并完整重新打包应用 exe + 安装器 exe（49.1MB）
3. 新建账本功能完整可用（后端 API + 前端 UI 已闭环）

### 涉及文件
- `frontend/src/api/common.js` — 默认导出对象新增 `updateAccount`, `createAccount`
- `frontend/src/components/Layout.vue` — 新建账本对话框（名称/类型/纳税人类型）+ "+" 按钮触发
- `backend/main.py` — POST /api/accounts 路由
- `backend/crud/base.py` — `create_account()` 函数
- `backend/schemas/account.py` — `AccountCreate`, `AccountUpdate` schema
- `backend/workspace.py` — 工作区路径配置（双模式：开发/打包）
- `launcher.py` — PyInstaller 打包入口
- `installer.py` — tkinter 安装向导 GUI
- `build.py` — 一键构建脚本（前端→打包→安装器）

### 关键设计决策
- `common.js` 的命名导出和默认导出必须同步（AP-7 自检）
- 安装器内嵌全部应用文件为单文件 exe，用户双击即可傻瓜式安装
- 工作区路径开发模式指向 backend/，打包模式指向 %APPDATA%/进销存管理系统

---

## 2026-05-10 项目完结销售单金额改为合同金额

### 变更摘要
1. 项目完结时自动生成的销售单总额，从「材料成本合计」改为「合同金额(contract_amount)」
2. SaleItem 的 total_price 改为 sale_price × quantity（按销售价计价），而非成本金额
3. ProjectIncome 金额 = 合同金额（而非成本金额）

### 涉及文件
- `backend/commands/project_commands.py` — `_complete_project()` 函数：
  - 读取 `project.contract_amount` 作为销售单总额
  - SaleItem.unit_price 优先取 product.sale_price，total_price = sale_price × quantity
  - sale_order.total_price = contract_amount
  - ensure_income(amount=contract_amount)
  - 日志信息增加合同金额

### 关键设计决策
- SaleItem 按销售价计价，但销售单总额直接设为合同金额（两者可能不等，差额为项目利润空间）
- 合同金额为 0 时仍创建销售单（幂等保护不变）

---

## 2026-05-08 00:15 利润分析成本改为商品成本+删除测试项目

### 变更摘要
1. 利润分析成本计算改为 SaleItem.quantity * Product.purchase_price（商品成本），而非采购单总额
2. 删除数据库中5个测试项目（测试项目-闭环-*）及其关联数据
3. 清理历史 CostItemLink 和项目型销售单脏数据

### 涉及文件
- `backend/crud/reports.py`：get_profit_report 成本改为 Σ(SaleItem.quantity × Product.purchase_price)
- `backend/crud/finance.py`：generate_income_statement 销售成本改为商品采购价
- `frontend/src/views/Reports.vue`：利润分析标签改为"销售收入-商品成本"
- `frontend/src/components/IncomeStatement.vue`：损益表标签适配
- `backend/_delete_test_projects.py`：新增清理脚本

---

## 2026-05-07 22:30 项目成本-销售单解耦改造（v5）

### 变更摘要
项目成本与销售单/采购单解耦，修复材料成本自动创建项目型销售单导致利润重复计算的bug。
改造后：材料成本仅扣库存不创建销售单，项目完结时统一生成销售单+ProjectIncome。

### 涉及文件
- `backend/commands/cost_commands.py`：删除材料→项目型销售单、人工→人力采购单联动逻辑及6个辅助函数
- `backend/commands/project_commands.py`：新增 _complete_project()/_reopen_project()，项目完结生成销售单+SaleItem+ProjectIncome，恢复时反向清理
- `backend/crud/reports.py`：移除 order_type=RETAIL 过滤，利润=所有销售单收入-所有采购单成本
- `backend/crud/income_ops.py`：sale_create_income 去掉 order_type 过滤
- `backend/crud/finance.py`：generate_income_statement 适配，收入=所有销售单，成本=采购单+项目成本
- `backend/crud/orders.py`：列表不再默认过滤项目型/人力采购单
- `backend/commands/sale_commands.py`：项目型销售单禁止手动取消/恢复
- `backend/utils.py`：update_project_summary/verify_invariants 去掉 PURCHASE_LABOR 排除
- `backend/models.py`：CostItemLink 标记废弃
- `backend/_cleanup_decouple.py`：新增数据库清理脚本
- `frontend/src/views/Reports.vue`：利润分析页面适配新字段
- `frontend/src/components/IncomeStatement.vue`：损益表适配
- `tests/unit/test_sale_order_domain.py`：测试用例适配 v5 逻辑

### 关键设计决策
- 项目完结触发销售单生成（而非成本添加时），幂等保护：(account_id, project_id, order_type='project') 唯一
- 利润计算统一：收入=所有销售单，成本=所有采购单，不再区分零售/项目
- CostItemLink 表保留模型定义但标记废弃，通过清理脚本清空历史数据

---

## 2026-05-07 19:40 双口径核算改造

### 变更摘要
实现企业所得税（税务口径=发票说话）与利润报表（经营口径=实际经营）的双口径分离。

### 核心改动
1. **企业所得税报表改用发票口径** — `income_tax.py` 从 SaleOrder/PurchaseOrder 改为 Invoice 查询
   - 收入 = 销项发票 `amount_without_tax`
   - 成本 = 进项发票 `amount_without_tax`
   - 费用 = 仅有票费用 `Expense.has_invoice=True`（无票费用不可税前扣除）
2. **利润表补充项目数据** — `finance.py:generate_income_statement()` 新增项目收入/成本
   - 收入 = 零售单 + 项目收入
   - 成本 = 零售成本 + 项目成本
3. **Schema 新增税务口径明细字段** — `IncomeTaxReport` 新增 `invoice_revenue`/`invoice_cost`/`invoiced_expenses`/`non_invoice_expenses`
4. **前端更新** — 企业所得税页面标明"税务口径"，利润表标明"经营口径"并展示零售/项目拆分

### 涉及文件
- `backend/routers/income_tax.py` — 数据源从订单改为发票
- `backend/crud/finance.py` — `generate_income_statement()` 补充项目收入/成本
- `backend/schemas/finance.py` — `IncomeTaxReport` 新增4个明细字段
- `frontend/src/views/IncomeTaxReport.vue` — 展示税务口径明细
- `frontend/src/components/IncomeStatement.vue` — 展示零售/项目拆分+经营口径标注

### 关键设计决策
- 不改数据模型，不改写操作链路，纯只读报表改造
- 新增字段用默认值，向后兼容旧前端
- 参照 `tax.py` 的 Invoice 查询模式，不重复发明

---

## 2026-05-07 14:00 统一前端日期时间显示为本地格式

### 变更摘要
新增 `formatDate` / `formatDateTime` 工具函数，替换前端所有字符串截取（`.slice(0,10)`、`.replace('T',' ')`）和局部 `formatDate` 重复定义为统一工具函数调用。使用浏览器 `toLocaleDateString`/`toLocaleString` 自动转为本地时区格式显示。

### 涉及文件
- **新增** `frontend/src/utils/format.js`：统一 `formatDate` + `formatDateTime` 工具函数
- **替换字符串截取**：
  - `frontend/src/views/Logs.vue`：`created_at` 用 `formatDateTime`
  - `frontend/src/views/Backup.vue`：`created_at` 用 `formatDateTime`
  - `frontend/src/views/Purchases.vue`：`purchase_date?.slice(0,10)` → `formatDate`
  - `frontend/src/views/Sales.vue`：`sale_date?.slice(0,10)` → `formatDate`
  - `frontend/src/views/Reports.vue`：`purchase_date`/`sale_date` 用 `formatDate`
  - `frontend/src/views/Projects.vue`：`purchase_date`/`income_date`/`sale_date` 用 `formatDate`
  - `frontend/src/components/ProjectCostTable.vue`：`cost_date` 用 `formatDate`
  - `frontend/src/components/ProjectIncomeTable.vue`：`income_date` 用 `formatDate`
- **替换局部重复函数**：
  - `frontend/src/components/BalanceSheet.vue`：删除局部 `formatDate`，改用工具函数
  - `frontend/src/components/FinancialSummary.vue`：同上
  - `frontend/src/components/IncomeStatement.vue`：同上

### 关键设计决策
选方案A（前端 toLocaleString 转换），不修改后端序列化。浏览器对无时区后缀的 ISO 字符串按本地时区解析，服务器在北京时区，结果正确。

---

## 2026-05-07 13:47 修复人工成本添加报"数据冲突"错误

### 变更摘要
修复项目管理添加人工成本（product_id=null）时触发 `NOT NULL constraint failed: purchase_items.product_id` 导致前端显示"数据冲突，请检查输入"的问题。

### 根因
`_upsert_purchase_item()` 无条件将 `cost.product_id` 塞给 `PurchaseItem.product_id`，但后者定义为 `nullable=False`。人工成本无商品关联（product_id=null 是合理的），导致数据库约束冲突。

### 涉及文件
- `backend/commands/cost_commands.py`
  - `CreateProjectCostHandler.handle()` 第353行：人工分支条件从 `cost.cost_type == "人工"` 改为 `cost.cost_type == "人工" and cost.product_id`
  - `DeleteProjectCostHandler.handle()` 第488行：同上，删除时反向清理也加 product_id 守卫
- `UpdateProjectCostHandler`：无需修改（已有守卫禁止变更 product_id）

### 关键设计决策
人工成本无 product_id 时跳过人力采购单行项创建（PurchaseItem），仅记录成本金额和汇总。语义正确：没有商品关联就不该有采购行项。

---

## 2026-05-04 前端UI优化批量修复

### 变更摘要
全面扫描前端20个view + 16个component，按优先级修复5类UI问题，共涉及14个文件。

### P0-1: 金额格式化统一（AP-4）
- 所有 `.toFixed(2)` 直接调用替换为 `formatMoney()`，防止 null 值崩溃
- **涉及文件**：
  - `frontend/src/views/Projects.vue`：合同金额/已收金额/总收入/总成本/利润/关联采购/收款/销售详情（16处）
  - `frontend/src/views/Reports.vue`：采购报表明细/销售报表明细/总价（6处）
  - `frontend/src/views/Reconciliations.vue`：期初欠款/本期发生/已收已付/期末欠款/发票金额/明细金额（6处）
  - `frontend/src/views/TaxReport.vue`：小规模/一般纳税人税额、发票明细金额（4处）
  - `frontend/src/views/IncomeTaxReport.vue`：税额（1处）
- 新增 `formatMoney` import：Projects.vue、Reports.vue、Reconciliations.vue、TaxReport.vue、IncomeTaxReport.vue

### P0-2: 硬编码颜色替换为设计 token（AP-10）
- **Projects.vue**：`.text-green`/`.text-red`/`.highlight-red`/`.highlight-green` → `var(--el-color-success)`/`var(--el-color-danger)`；内联已收/待收金额样式改为 CSS class
- **Dashboard.vue**：4个 stat-icon 内联 `style="background:#xxx;color:#xxx"` → 语义化 CSS class `stat-icon--primary/success/warning/danger` + `var(--el-color-*-light-9)`；ECharts 系列颜色 → `var(--el-color-*)`
- **Layout.vue**：`.app-aside` 的 `background: #fff` → `var(--el-bg-color)`

### P1-1: 页面布局统一
- 7个页面的裸 `<h2>` 标题改为 `el-card shadow="never"` + header slot 模式，与 Sales/Purchases/Inventory 等页面风格统一
- **涉及文件**：Projects.vue、Invoices.vue、Expenses.vue、TaxReport.vue、IncomeTaxReport.vue、CashFlow.vue、OpeningBalance.vue
- Invoices.vue/Expenses.vue 的"新增"按钮移入 card header

### P1-2: 空 catch 块修复（AP-11）
- **Sales.vue**：`catch (e) { /* ignore */ }` → `console.error('加载选项数据失败:', e)`
- **Invoices.vue**：`catch (e) { /* ignore */ }` → `console.error('获取税务统计失败:', e)`
- **Layout.vue**：2处 → `console.error('加载账本列表失败:', e)` / `console.error('加载库存预警数量失败:', e)`

### P2: 交互细节优化
- **Invoices.vue**：表格添加 `stripe v-loading` + `<el-empty>` 空状态；删除操作改为 `el-popconfirm` 确认；`alert()` → `ElMessage.warning()`；新增 `loading` 状态
- **Expenses.vue/Invoices.vue**：新增按钮添加 `<el-icon><Plus /></el-icon>` 图标
- **Customers.vue/Suppliers.vue**：筛选栏添加 `display:flex;gap:12px` 间距

### 关键设计决策
- 金额格式化统一使用 `formatMoney()`（已在 `api/common.js` 定义），该函数已处理 null/undefined/空字符串
- 颜色 token 统一使用 Element Plus CSS 变量（`var(--el-color-*)`），而非自定义 `global.css` 变量
- 页面布局以 Sales.vue 的 `el-card shadow="never"` + header slot 为标准模式

## 2026-05-04 14:30 反模式红线扩展：AP-11~AP-13 新增三条规则

### 变更摘要

扫描 UPDATE_LOG 全量历史记录（5/1~5/4），识别出3类尚未被 AP-1~AP-10 覆盖的 AI 典型返工模式，新增为 AP-11/AP-12/AP-13 规则。反模式红线从 10 条扩展至 13 条，元规则计数从 12 更正为 15。

### 新增规则

| 编号 | 规则名称 | 元规则 | 历史教训来源 |
|------|---------|--------|-------------|
| AP-11 | 副作用必须可观测，禁止静默失败 | MR-1+MR-2 | Invoices.vue 空 catch 块（审查 MID-5）；useAccountAwareData.js watch 泄漏（5/3 21:00）；linkage.py assert 校验（审查 RISK-1） |
| AP-12 | 多账本隔离必须贯穿全层 | MR-1 | Product.inventory primaryjoin 缺 account_id（5/3 17:05） |
| AP-13 | 前后端约定必须对齐 | MR-1 | balance check 容差 0 vs 0.01（审查 MID-6）；order_no String(20) 截断（审查 BUG-1）；el-menu router 模式不兼容（5/3 17:30） |

### 涉及文件

- `.joycode/rules/anti-patterns.md` — 新增 AP-11/AP-12/AP-13 三节 + 更新自检清单 + 元规则计数 12→15
- `.joycode/rules/workflow.md` — 反模式自检范围从 AP-1~AP-5 更新为 AP-1~AP-13
- `docs/架构参考_正式版.md` — 5.4 节表格新增 AP-11~AP-13 三行 + 陷阱计数 12→15
- `docs/开发速查表.md` — 反模式速查新增 AP-11~AP-13 + 标题 10→13 条

### 关键设计决策

- AP-11 合并了三种"副作用不可观测"模式（空 catch / watch 泄漏 / assert 校验），它们共享"AI 走捷径省掉可观测性"的底层机制
- AP-12 单独成条而非合并到 AP-4，因为多账本隔离是数据层问题而非类型边界问题，且影响范围涉及 ORM 全层
- AP-13 合并了容差/长度/兼容性三类前后端不对齐问题，它们共享"AI 没去后端核实就凭直觉写"的 MR-1 机制

---

## 2026-05-04 10:30 修复重启后数据全部丢失的严重Bug

### 变更摘要

删除 `_migrate_v4_order_type()` 函数，该函数在每次应用启动时都会执行第6步"清空所有业务数据"，导致重启系统后所有记录丢失。

### 涉及文件

- `backend/database.py`：删除 `_migrate_v4_order_type()` 函数（原第221-300行），移除 `init_db()` 中对该函数的调用（原第495行）

### 关键设计决策

- 该迁移函数的第1-5步（添加 track_inventory、order_type、contract_amount 等列）在 models.py 中已全部定义，`create_all` 会自动创建正确表结构，无需迁移
- 第6步"清空所有业务数据"无幂等保护，每次启动都执行 DELETE，是数据丢失的根因
- 整个函数使命已完成（v4已上线），直接删除是最简洁安全的方案

---

## 2026-05-04 08:50 CostItemLink 关联表替代 notes 字符串解析

### 变更摘要

将项目成本→专属单据行项的合并追踪机制，从 SaleItem/PurchaseItem 的 notes 字符串解析改为 `CostItemLink` 关联表，消除正则解析脆弱性和并发风险。

### 涉及文件

| 文件 | 变更 | 关键函数/类 |
|------|------|-------------|
| `backend/models.py` | 新增 `CostItemLink` 模型 | `class CostItemLink` — cost_id, item_type, item_id, quantity, amount, UniqueConstraint(cost_id, item_type, item_id) |
| `backend/commands/cost_commands.py` | 重构 4 个辅助函数 | `_upsert_sale_item()` — 写 CostItemLink 替代 notes 追加；`_upsert_purchase_item()` — 同理；`_reduce_sale_item()` — 查 CostItemLink 替代正则解析；`_reduce_purchase_item()` — 同理 |
| `backend/database.py` | 迁移清单添加 cost_item_links | `_migrate_v4_order_type()` 的 tables_to_clear 中添加 cost_item_links |
| `docs/架构参考_正式版.md` | ER 概览 + 数据流更新 | 3.5 新增 CostItemLink 节点；3.3 数据流标注 CostItemLink 关联步骤 |

### 关键设计决策

- **关联表 vs 字符串**：`CostItemLink(cost_id, item_type, item_id, quantity, amount)` 替代 `notes` 中的 `追加 {qty}@{time} [cost_id={id}]` 格式
- **item_type 枚举**：`"sale"` / `"purchase"` 区分 SaleItem 和 PurchaseItem 关联，避免 item_id 冲突
- **删除路径**：`_reduce_*` 先查 link → 读 quantity/amount → 减少 Item 聚合值 → 删除 link → 若 Item 归零则删行
- **notes 字段保留**：SaleItem/PurchaseItem 的 notes 字段仍存在，不再写入 cost_id 信息，可留作用户自定义备注

### 不变量声明

- 不变量 I（库存一致性）：✅ 不受影响，库存扣减/回补逻辑不变
- 不变量 II（项目收入一致性）：✅ 不受影响
- 不变量 III（项目汇总一致性）：✅ 不受影响

---

## 2026-05-04 修复项目删除时空专属单据残留导致 FK 冲突

### 变更摘要

`check_project_can_deactivate()` 原逻辑仅检查专属单据是否有行项（有则拒绝），但未处理空单据残留场景。空的项目型销售单/人力采购单虽无业务意义，其 `project_id` 外键仍指向项目，导致 `db.delete(project)` 触发 FK 约束失败。

修复方式：检测到空专属单据时直接删除，而非仅跳过。

### 涉及文件

- `backend/commands/project_commands.py` — `check_project_can_deactivate()` 新增空单清理逻辑（`db.delete(project_sale)` / `db.delete(labor_purchase)`）

### 关键设计决策

- 在校验函数中清理而非在 DeleteProjectHandler 中清理：该校验函数是项目停用/删除的唯一入口，职责一致
- 空单清理与有单拒绝在同一函数中完成，逻辑内聚

### 不变量声明

- 不涉及三大不变量，仅清理无业务意义的孤儿记录

---

## 2026-05-04 简化 UpdateProjectCostHandler — 禁止跨 cost_type 变更

### 变更摘要

移除 `UpdateProjectCostHandler` 中跨 cost_type 变更的反向+正向联动逻辑（约 40 行），改为命令层校验直接拒绝。变更 `cost_type`、材料/人工类的 `product_id` 或 `quantity` 时，提示用户"请先删除原成本再创建新成本"。

### 涉及文件

- `backend/commands/cost_commands.py` — `UpdateProjectCostHandler.handle()` 新增 3 条校验 + 删除旧值记录 + 删除整块反向清理/正向建立联动逻辑

### 关键设计决策

- **命令层校验**：业务规则校验放在 Handler 内部（与现有 `cost_type not in COST_TYPES` 校验一致位置），不放路由层
- **全部简化**：不仅拦截跨类型变更，也拦截材料/人工类的 product_id 和 quantity 变更，彻底消除 Handler 中对销售单/采购单/库存的读写依赖
- **替代路径清晰**：DeleteProjectCostHandler 已有完整的反向清理逻辑，CreateProjectCostHandler 已有完整的正向建立逻辑，用户通过"删旧建新"操作路径等价

### 不变量声明

- I-库存一致性：不受影响（Update 不再触碰库存，删旧建新分别由 Delete/Create Handler 保障）
- II-项目收入一致性：不受影响
- III-项目汇总一致性：Handler 仍保留 `update_project_summary()` 调用

---

## 2026-05-04 v4 重构：Command Handler 显式编排替代 EventBus 隐式联动

### 变更摘要

将库存扣减、项目收入联动、项目汇总重算从 EventBus 隐式事件驱动改为 Command Handler 显式编排。核心原则："谁创建，谁负责编排联动"。删除 `crud/linkage.py`，拆分为 `crud/inventory_ops.py` 和 `crud/income_ops.py`。新增 `OrderType` 枚举区分零售/项目/人工采购三类订单。`Product` 新增 `track_inventory` 字段控制人工类商品是否参与库存。

### 架构变更

| 维度 | v3（旧） | v4（新） |
|------|---------|---------|
| 联动方式 | EventBus 事件 → handlers.py 回调链 | CommandHandler 直接调用 ops 函数 |
| 联动模块 | `crud/linkage.py`（单文件，库存+收入混合） | `crud/inventory_ops.py` + `crud/income_ops.py`（职责分离） |
| EventBus 用途 | 日志(p10) + 库存(p30) + 业务(p50) + 汇总(p90) | 日志(p10) + 汇总重算(p90)，仅此两项 |
| 订单类型 | 隐式判断（有 project_id 即项目单） | 显式 `OrderType` 枚举（RETAIL / PROJECT / PURCHASE_LABOR） |
| 人工采购 | 无区分 | `PURCHASE_LABOR` 类型 + `track_inventory=false` 跳过库存 |

### 涉及文件

#### 新建文件
- `backend/crud/inventory_ops.py` — 库存操作函数：`sale_deduct` / `sale_restore` / `purchase_add` / `purchase_remove` / `cost_deduct_stock` / `cost_restore_stock`
- `backend/crud/income_ops.py` — 收入操作函数：`sale_create_income` / `sale_delete_income`
- `backend/commands/income_commands.py` — 项目收入命令（Create/Update/Delete）

#### 重写文件（Command Handler 显式编排）
- `backend/commands/sale_commands.py` — 全部 Handler 改为直接调用 `inventory_ops` / `income_ops`，新增项目型销售单保护（禁止删除/修改 items/切换项目）
- `backend/commands/purchase_commands.py` — 全部 Handler 增加 `track_inventory` 检查，新增人工采购单保护
- `backend/commands/cost_commands.py` — 核心重写：材料成本→自动创建/查找项目销售单+upsert SaleItem+扣库存；人工成本→自动创建/查找人工采购单+upsert PurchaseItem；支持跨类型变更（材料↔人工）
- `backend/commands/project_commands.py` — `DeleteProjectHandler` 改用 `check_project_can_deactivate()` 前置校验 + `inventory_ops.restore_stock`

#### 修改文件
- `backend/models.py` — `PurchaseOrder` 新增 `order_type` 字段（String(20), default 'retail'）；`Product` 新增 `track_inventory` 字段（Boolean, default True）
- `backend/enums.py` — 新增 `OrderType` 枚举（RETAIL / PROJECT / PURCHASE_LABOR）
- `backend/domain/sale_order.py` — `is_project_sale()` 改为判断 `order_type == OrderType.PROJECT`；新增项目型销售单必须关联项目校验
- `backend/domain/purchase_order.py` — 新增 `order_type` 字段
- `backend/database.py` — `_migrate_v4_order_type()` 自动迁移：已有项目销售单标记为 PROJECT，人工采购单标记为 PURCHASE_LABOR；修复 `sqlite_sequence` 表不存在时的容错
- `backend/crud/base.py` — `_generate_order_no` 支持 PL 前缀（人工采购单号）
- `backend/handlers.py` — EventBus Handler 精简为仅日志(p10) + 汇总重算(p90)
- `backend/routers/sales.py` — `list_sales` 新增 `order_type` 查询参数
- `backend/routers/purchases.py` — `list_purchases` 新增 `order_type` 查询参数
- `backend/routers/projects.py` — 项目详情 API 返回 `contract_amount` / `received_amount` / `payment_status`

#### 前端变更
- `frontend/src/views/Projects.vue` — 项目管理表/概览表新增合同金额、已收金额、收款状态列；创建/编辑弹窗新增合同金额字段
- `frontend/src/components/ProjectKPIGrid.vue` — 新增合同金额和收款状态两个 KPI 卡片，网格从 3 列改为 4 列
- `frontend/src/composables/useProjectList.js` — `createForm` 新增 `contract_amount` 字段

#### 删除文件
- `backend/crud/linkage.py` — 职能已拆分至 `inventory_ops.py` + `income_ops.py`

### 三大不变量保障

| 不变量 | 保障方式 |
|--------|----------|
| I-库存一致性 | CommandHandler 显式调用 `inventory_ops`，`track_inventory=false` 的商品跳过库存操作 |
| II-项目收入唯一性 | `income_ops` 使用 `UniqueConstraint(project_id, source_type, source_id)` 防重 |
| III-项目汇总一致性 | 所有 Handler 结尾调用 `update_project_summary(db, project_id)` |

### Bug 修复
- `DeleteProjectCostHandler`：`db.delete(cost)` 必须在 `update_project_summary()` 之前执行，否则已删除的成本仍被计入汇总
- `list_sales` / `list_purchases` 路由未传递 `order_type` 查询参数
- `database.py`：`DELETE FROM sqlite_sequence` 在全新数据库上因表不存在而报错，添加 try/except 容错

### 测试验证
- 材料成本→自动创建项目销售单+扣库存 ✅
- 人工成本→自动创建人工采购单 ✅
- 项目型销售单禁止删除/修改 ✅
- 零售销售单正常扣库存+创建收入 ✅
- 项目汇总自动重算 ✅
- 前端 `npm run build` 构建成功 ✅

---

## 2026-05-03 ElInputNumber modelValue 类型错误全局修复

### 变更概述
修复后端返回的数值字段为字符串类型导致 ElInputNumber 报 type check warning 的问题，涉及采购/销售/商品/库存/期初余额/个人流水6个视图

### 具体修改
- composables/useOrderForm.js → setEditForm 中 item.quantity/item.unit_price 加 Number() 转换
- views/Purchases.vue → showEdit 中 tax_rate 加 Number() 转换
- views/Sales.vue → showEdit 中 total_price 加 Number() 转换
- views/Products.vue → showDialog 编辑时 purchase_price/sale_price/min_stock/initial_stock 加 Number() 转换
- views/Inventory.vue → showAdjust 中 current_quantity/quantity 加 Number() 转换
- views/OpeningBalance.vue → editOpeningBalance 和 loadLatest 中7个金额字段加 Number() 转换
- views/Personal.vue → showDialog 编辑时 amount 加 Number() 转换

### 测试验证
- 编辑采购单/销售单/商品/库存调整/期初余额/个人流水，ElInputNumber 无类型警告，数值正常显示和编辑

---

## 2026-05-03 TaxReport.vue el-radio废弃API + toFixed类型安全修复

### 变更概述
修复增值税报表页 el-radio 使用废弃 label 属性警告，及发票明细 toFixed 在字符串上调用导致渲染崩溃的问题

### 具体修改
- frontend/src/views/TaxReport.vue → el-radio label="quarterly"/"monthly" 改为 value="quarterly"/"monthly"
- frontend/src/views/TaxReport.vue → scope.row.tax_rate * 100 改为 Number(scope.row.tax_rate) * 100
- frontend/src/views/TaxReport.vue → scope.row.amount_without_tax.toFixed(2) 改为 Number(scope.row.amount_without_tax).toFixed(2)
- frontend/src/views/TaxReport.vue → scope.row.tax_amount.toFixed(2) 改为 Number(scope.row.tax_amount).toFixed(2)

### 测试验证
- 打开增值税报表页，无 el-radio 废弃警告，发票明细金额正常显示，无渲染错误

---

## 2026-05-03 Products.vue purchase_price toFixed 类型错误修复

### 变更概述
修复商品列表页进价/售价字段因字符串类型调用 .toFixed() 报 TypeError 的问题

### 具体修改
- frontend/src/views/Products.vue → row.purchase_price?.toFixed(2) 改为 Number(row.purchase_price)?.toFixed(2)
- frontend/src/views/Products.vue → row.sale_price?.toFixed(2) 改为 Number(row.sale_price)?.toFixed(2)

### 测试验证
- 打开商品列表页，进价和售价正常显示为两位小数格式，无 TypeError

---

## 2026-05-03 21:00 修复 parentNode null 崩溃 + 全局 toFixed 类型安全

### 变更摘要

修复路由切换时 `Cannot read properties of null (reading 'parentNode')` 致命错误，并全局消除后端返回字符串金额时 `.toFixed()` 的 TypeError 崩溃，统一使用 `formatMoney()` 安全格式化。

### 根因

1. **parentNode null**：`useAccountAwareData.js` 中 `watch()` 返回值被丢弃，组件卸载后 watcher 仍存活
2. **.toFixed() TypeError**：后端返回金额字段为字符串类型，前端模板直接调用 `.toFixed(2)` 报错

### 涉及文件

1. **`composables/useAccountAwareData.js`** — `onScopeDispose(stop)` 绑定 watch 生命周期
2. **`components/FinancialSummary.vue`** — `precision="2"` → `:precision="2"`（3处）；el-statistic value 改 div+el-tag；10 处 `.toFixed(2)` → `formatMoney()`
3. **`components/IncomeStatement.vue`** — `precision="2"` → `:precision="2"`（3处）；2 处 `.toFixed(2)` → `formatMoney()`
4. **`components/BalanceSheet.vue`** — 4 处 `.toFixed(2)` → `formatMoney()`
5. **`views/Invoices.vue`** — 6 处 `.toFixed(2)` → `formatMoney()`；1 处 `Number()` 保护
6. **`views/OpeningBalance.vue`** — 7 处模板 + 3 处 JS `.toFixed(2)` → `formatMoney()`
7. **`views/CashFlow.vue`** — 1 处 `.toFixed(2)` → `formatMoney()`
8. **`views/Personal.vue`** — 4 处 `.toFixed(2)` → `formatMoney()`
9. **`components/CostDialog.vue`** — 1 处 `.toFixed(2)` → `formatMoney()`
10. **`components/ProjectCostTable.vue`** — 2 处 `.toFixed(2)` → `formatMoney()`
11. **`components/ProjectIncomeTable.vue`** — 3 处 `.toFixed(2)` → `formatMoney()`
12. **`components/ProjectKPIGrid.vue`** — 6 处 `.toFixed(2)` → `formatMoney()`

### 保留不修改的 .toFixed 调用

- `OrderItemEditor.vue`：4 处均为前端本地 Number 计算
- `Invoices.vue:360-368,478-486`：`parseFloat(x.toFixed(2))`，x 是本地 Number
- `Backup.vue:34`：文件大小计算，前端 Number
- `Dashboard.vue:143`、`Personal.vue:199`：图表轴 formatter，val 是 Number

### 测试验证

- `npm run build` 构建成功，无编译错误
- 全局扫描确认：后端数据路径的 `.toFixed()` 已全部替换为 `formatMoney()`

---

## 2026-05-03 ElInputNumber modelValue 类型错误全局修复

### 变更概述
修复后端返回的数值字段为字符串类型导致 ElInputNumber 报 type check warning 的问题，涉及采购/销售/商品/库存/期初余额/个人流水6个视图

### 具体修改
- composables/useOrderForm.js → setEditForm 中 item.quantity/item.unit_price 加 Number() 转换
- views/Purchases.vue → showEdit 中 tax_rate 加 Number() 转换
- views/Sales.vue → showEdit 中 total_price 加 Number() 转换
- views/Products.vue → showDialog 编辑时 purchase_price/sale_price/min_stock/initial_stock 加 Number() 转换
- views/Inventory.vue → showAdjust 中 current_quantity/quantity 加 Number() 转换
- views/OpeningBalance.vue → editOpeningBalance 和 loadLatest 中7个金额字段加 Number() 转换
- views/Personal.vue → showDialog 编辑时 amount 加 Number() 转换

### 测试验证
- 编辑采购单/销售单/商品/库存调整/期初余额/个人流水，ElInputNumber 无类型警告，数值正常显示和编辑

---

## 2026-05-03 TaxReport.vue el-radio废弃API + toFixed类型安全修复

### 变更概述
修复增值税报表页 el-radio 使用废弃 label 属性警告，及发票明细 toFixed 在字符串上调用导致渲染崩溃的问题

### 具体修改
- frontend/src/views/TaxReport.vue → el-radio label="quarterly"/"monthly" 改为 value="quarterly"/"monthly"
- frontend/src/views/TaxReport.vue → scope.row.tax_rate * 100 改为 Number(scope.row.tax_rate) * 100
- frontend/src/views/TaxReport.vue → scope.row.amount_without_tax.toFixed(2) 改为 Number(scope.row.amount_without_tax).toFixed(2)
- frontend/src/views/TaxReport.vue → scope.row.tax_amount.toFixed(2) 改为 Number(scope.row.tax_amount).toFixed(2)

### 测试验证
- 打开增值税报表页，无 el-radio 废弃警告，发票明细金额正常显示，无渲染错误

---

## 2026-05-03 Products.vue purchase_price toFixed 类型错误修复

### 变更概述
修复商品列表页进价/售价字段因字符串类型调用 .toFixed() 报 TypeError 的问题

### 具体修改
- frontend/src/views/Products.vue → row.purchase_price?.toFixed(2) 改为 Number(row.purchase_price)?.toFixed(2)
- frontend/src/views/Products.vue → row.sale_price?.toFixed(2) 改为 Number(row.sale_price)?.toFixed(2)

### 测试验证
- 打开商品列表页，进价和售价正常显示为两位小数格式，无 TypeError

---

## 2026-05-03 21:00 修复对账API 404 Bug

### 变更摘要
前端对账API路径拼写错误（单数 reconciliation 缺少 s），与后端路由前缀（复数 reconciliations）不匹配，导致 GET /api/reconciliation 请求返回 404。

### 涉及文件
- `frontend/src/api/common.js`：第108行 `getReconciliations` 路径 `/reconciliation` → `/reconciliations`；第109行 `getReconciliationDetail` 路径 `/reconciliation/detail` → `/reconciliations/detail`

### 关键设计决策
- 保持与后端 prefix 及架构参考文档一致，统一使用复数形式

### 不变量声明
- 不触及三大不变量，纯前端路径修正

---

## 2026-05-03 19:27 Domain层稳定化 + 清除CRUD死代码

### 变更摘要
CancelSaleOrderHandler 重写为与其他7个Handler一致的安全模式（get_sale_order + from_orm + transition_to + 直接赋值），废弃 SaleOrderRepo，删除 crud/orders.py 6个写函数死代码，迁移测试文件至 Command                   dispatch 调用。

### 涉及文件
- `backend/commands/sale_commands.py`：删除 `SaleOrderRepo` 导入，重写 `CancelSaleOrderHandler.handle()` — 不再调用 `SaleOrderRepo.get_domain()` / `update_from_domain()`，改用 `get_sale_order()` + `SaleOrderDomain.from_orm()` + `order.status = domain.status`
- `backend/repositories/order_repo.py`：全文替换为废弃桩（`get_domain`/`update_from_domain`/`save_new` 均抛 NotImplementedError + DeprecationWarning）
- `backend/crud/orders.py`：删除6个写函数（`create_purchase_order`/`update_purchase_order`/`delete_purchase_order`/`create_sale_order`/`update_sale_order`/`delete_sale_order`），保留读函数和 `_distribute_total_price`，头部加写操作禁令
- `backend/crud/__init__.py`：移除6个写函数的re-export，新增 `_distribute_total_price` 导出
- `tests/integration/test_custom_price.py`：从 crud 直接调用改为 Command dispatch 调用
- `tests/integration/test_dup_check.py`：同上

### 关键设计决策
- CancelSaleOrderHandler 不再全量替换行项（原 `update_from_domain` 会删所有旧行项→重建），改为只改 status 字段，安全且高效
- 删除 `domain.validate()` 调用：取消操作只改status，不变量不会被破坏；其他Handler也不做validate
- 废弃桩而非直接删除 `order_repo.py`：防止外部误调用时静默失败，改为显式报错

### 不变量声明
- I-库存一致性：取消事件仍通过 `emit("sale_order.cancelled")` 触发库存回补，不变量不被破坏
- II-项目收入一致性：取消事件触发项目收入删除，不变量不被破坏
- III-项目汇总一致性：汇总重算由事件驱动，不变量不被破坏

---

## 2026-05-03 20:30 验收前代码审查修复（10项）

### 变更摘要
根据《验收前代码审查报告》，修复10项必须/建议修复的问题，覆盖数据安全、业务逻辑、用户体验和代码质量。

### 修复清单

| # | 编号 | 严重度 | 修复内容 | 涉及文件 |
|---|------|--------|----------|----------|
| 1 | BUG-1 | 严重 | order_no字段长度String(20)->String(30)，防订单号截断 | models.py:104,149 |
| 2 | BUG-3 | 严重 | PDF上传文件名加os.path.basename()防路径穿越 | routers/invoices.py:210-211 |
| 3 | BUG-5 | 严重 | 删除utils.py中无调用方的get_current_account()死代码 | utils.py:17-20(已删) |
| 4 | RISK-1 | 高 | linkage.py两处assert->if/raise RuntimeError | crud/linkage.py:40-41,176-178 |
| 5 | RISK-4 | 高 | 删除main.py重复注册的/api/reconciliation路由 | main.py:129(已删) |
| 6 | RISK-5 | 高 | 删除models.py重复的from sqlalchemy.sql import func | models.py:3(已删) |
| 7 | MID-2 | 中 | CostDialog.vue成本类型从硬编码改为enumsStore读取 | CostDialog.vue:116 |
| 8 | MID-5 | 中 | Invoices.vue三个catch块补充ElMessage.error() | Invoices.vue:380,403,414 |
| 9 | MID-6 | 中 | crud/finance.py平衡检查容差从零改为0.01 | crud/finance.py:31 |
| 10 | MID-7 | 中 | 删除BalanceSheet.vue导出功能开发中按钮和函数 | BalanceSheet.vue:17,159-161(已删) |

### 关键设计决策
- RISK-1: 使用RuntimeError确保任何运行模式都不被优化掉
- MID-6: 容差0.01与前端OpeningBalance.vue对齐
- MID-2: costTypes改为computed+enumsStore，保持单一真相源
- 验收后待处理: BUG-2/BUG-4/RISK-2/RISK-3/MID-1及所有LOW级问题

---

## 2026-05-03 18:15 采购单数据恢复

### 变更摘要
采购单数据丢失问题修复。数据库中 purchase_orders 表大量记录被误删，但 purchase_items 明细项残留。通过两步恢复策略完成修复：
1. 从热备份（2026-W17_175524.zip）恢复8条采购单（ID=2~9），使用列名映射处理表结构差异（备份缺少 project_id 列）
2. 从残留明细反推重建5条采购单（ID=10,11,13,14,15），这些是备份后新增但被误删的记录

### 涉及文件
- **backend/inventory.db** - 恢复13条采购单记录，0条孤儿明细
- **backend/inventory.db.pre_purchase_restore_20260503_180021** - 恢复前数据库备份
- **restore_purchase_orders.py** - 从热备份恢复采购单脚本（一次性）
- **rebuild_orphan_orders.py** - 从残留明细重建采购单脚本（一次性）

### 关键设计决策
- 使用列名映射而非位置映射，处理备份与当前数据库表结构差异
- INSERT OR IGNORE 避免主键冲突
- 重建的采购单号使用 `PO-RESTORED-XXX` 格式标记，便于识别
- 重建的采购单默认归入日运办公账本（account_id=1），因原始产品可能已被删除

### 数据完整性验证
- 孤儿明细（无对应采购单）：0
- 空采购单（无明细项）：0
- ORM关联验证：13条采购单均能正确加载明细项

### 不可恢复数据
- 采购单 ID=1（PO20260501-212222-001）及其明细：无备份且明细已级联删除
- 采购单 ID=12：无明细残留，无法推断

---

## 2026-05-03 18:05 Projects.vue 组件拆分重构

### 变更摘要
将 Projects.vue（1023行）拆分为5个可复用子组件，主视图文件缩减至约240行（减少76%），提升代码可维护性和组件复用性。

### 涉及文件

#### 新建文件（5个组件）
1. **frontend/src/components/ProjectDrawerHeader.vue** (~90行)
   - 功能：项目详情抽屉头部组件
   - Props：`project` (项目对象)
   - Emits：`close` (关闭抽屉), `add-cost` (添加成本)
   - 包含：返回按钮、项目名称、客户信息、开始日期、状态标签、添加成本按钮

2. **frontend/src/components/ProjectKPIGrid.vue** (~180行)
   - 功能：6个KPI指标卡片网格展示
   - Props：`income`, `cost`, `profit`, `receivable`, `received`, `uninvoiced` (均为Number)
   - 计算属性：`profitClass` (盈利/亏损样式), `profitTrend` (盈利/亏损文本)
   - 响应式：3列→2列→1列自适应布局

3. **frontend/src/components/ProjectFilterBar.vue** (~150行)
   - 功能：通用筛选栏组件（支持成本/收入两种模式）
   - Props：`mode` ('cost'|'income'), `filters`, `resultCount`, `resultSummary`, `costTypes`
   - Emits：`update:filters`, `reset`
   - 动态筛选项：根据 mode 自动切换显示成本类型/支付方式/来源类型/收款状态等

4. **frontend/src/components/ProjectCostTable.vue** (~120行)
   - 功能：成本明细表格组件
   - Props：`costs`, `total`, `filters`, `loading`
   - Emits：`update:filters`, `reset-filter`, `edit`, `delete`
   - 插槽：`#filter-bar` (预留筛选栏位置)
   - 表格列：类型、商品/数量、金额、支付方式、发票、供应商、日期、备注、附件、操作

5. **frontend/src/components/ProjectIncomeTable.vue** (~140行)
   - 功能：收入明细表格组件
   - Props：`incomes`, `receivable`, `received`, `filters`, `loading`
   - Emits：`update:filters`, `reset-filter`, `edit`, `delete`, `view-sale`
   - 表格列：金额、来源、收款状态、已收金额、发票、日期、备注、附件、操作
   - 特殊逻辑：销售单自动生成的收入仅显示"查看销售单"按钮，不支持编辑/删除

#### 修改文件
6. **frontend/src/views/Projects.vue** (1023行 → ~240行)
   - Template 部分：用子组件替换原有的内联代码（drawer-header → ProjectDrawerHeader, kpi-section → ProjectKPIGrid, 筛选栏+表格 → ProjectCostTable/ProjectIncomeTable）
   - Script 部分：移除不再需要的图标导入（ArrowLeft, User, Calendar等12个图标），新增5个子组件导入
   - Style 部分：移除432行CSS，仅保留必要的容器样式和采购单Tab的增强表格样式
   - 保留内容：composables调用、Dialog状态管理、辅助函数保持不变

7. **frontend/src/components/StatusTag.vue**
   - 新增 `invoice` 类型支持：`{ '已开': 'success', '未开': 'warning', '不需开': 'info' }`

8. **docs/文件索引.md**
   - 在"前端 - 组件"章节新增5个组件的说明

### 关键设计决策
- **渐进式重构**：仅拆分视觉组件，不修改现有 composable 逻辑，降低风险
- **组件职责单一**：每个子组件只负责一个UI区块，便于独立测试和维护
- **Props/Emits 数据流**：严格遵循 Vue 3 单向数据流，父组件通过 props 传递数据，子组件通过 emits 触发事件
- **筛选栏插槽化**：ProjectCostTable 使用 slot 预留筛选栏位置，提高灵活性
- **样式隔离**：所有子组件使用 scoped CSS，避免全局样式污染
- **复用性优先**：ProjectFilterBar 支持两种模式，可在其他页面复用

### 测试验证
- ✅ 前端构建成功（npm run build），无编译错误
- ✅ repomix 代码快照已更新（202 files, 258,306 tokens）
- ✅ 文件索引已同步更新

---

## 2026-05-03 17:50 前端税务报表功能修复

### 变更摘要
修复前端税务报表页面的两个问题：账本切换时报告类型不匹配、缺少用户友好的错误提示。

### 涉及文件
1. **frontend/src/views/TaxReport.vue**
   - 第137-142行：新增 `ElMessage` 导入用于错误提示
   - 第213-239行：在 `getTaxReport()` 和 `getMonthlyTaxReport()` 中添加 `ElMessage.error()` 错误提示
   - 第251-261行：新增 `fetchData()` 函数，根据当前 `reportType` 动态选择调用季度或月度报表API；修改 `useAccountAwareData(fetchData)` 替代原来的硬编码 `getTaxReport`

2. **frontend/src/views/IncomeTaxReport.vue**
   - 第48-53行：新增 `ElMessage` 导入用于错误提示
   - 第111-123行：在 `getIncomeTaxReport()` 中添加 `ElMessage.error()` 错误提示

### 关键设计决策
- **问题1**：`TaxReport.vue` 原使用 `useAccountAwareData(getTaxReport)`，导致用户在"按月份"模式下切换账本时，会错误地加载季度报表数据。修复后通过 `fetchData()` 函数根据当前 `reportType` 状态动态选择正确的API调用。
- **问题2**：两个页面原来只在 console 打印错误，用户无法感知。修复后使用 Element Plus 的 `ElMessage.error()` 组件显示后端返回的错误详情或默认提示文案。

### 测试验证
- 前端构建成功（npm run build），无编译错误
- 后端API已验证正常工作（curl测试通过）

---

## 2026-05-03 17:41 库存数据恢复

### 变更摘要
从备份数据库 `inventory.db.pre_numeric_backup` 恢复了29个被误删的商品及库存数据。

### 问题原因
1. 2026-05-01 凌晨3:01左右，有人通过系统批量删除了日运办公账本下的商品（操作日志记录 operator: user）
2. 删除商品后，inventory表中残留了29条孤立记录（product_id指向已删除商品），导致新商品创建时与唯一约束 (account_id, product_id) 冲突

### 恢复操作
1. 清理inventory表中29条孤立记录
2. 删除2个测试商品（测试商品A/B）
3. 通过API逐一恢复29个商品（含初始库存）
4. 合并重复的朗森键盘（id=3和id=4），迁移业务记录后删除id=4

### 涉及文件
- `backend/inventory.db` - 数据库（清理孤立记录、恢复商品数据）
- `backend/inventory.db.pre_numeric_backup` - 备份数据源
- `backend/restore_products.py` - 恢复脚本（临时）
- `backend/merge_dup.py` - 合并重复商品脚本（临时）
- `backend/check_dup.py` - 检查重复脚本（临时）
- `backend/check_triggers.py` - 检查触发器脚本（临时）

### 恢复数据清单（29个商品）
| 商品 | SKU | 库存 |
|------|-----|------|
| 朗森LK140PRO有线键盘 | LS-LK140PRO | 12 |
| 罗技USB无线鼠标M186 | LG-M186 | 5 |
| 晶华USB2.0百兆网卡 | JH-USB-WK | 2 |
| 豪贝莱特打印线1.5M | HBL-DYX-1.5 | 5 |
| 丰杰1A2B | FJ-1A2B | 2 |
| 大华DH-IPC-HFW1430M-A-I1 3.6MM枪机 | DH-HFW1430M-AI1 | 12 |
| 监控04支架 | JK-ZJ-04 | 15 |
| 500X防水箱1500型 | FSX-500X-1500 | 3 |
| NET NTE-3100A/B-25Km单纤单模收发器 | NET-NTE3100A | 5 |
| 锐捷RG-ES116G-E 16口千兆交换机 | RJ-ES116G-E | 1 |
| 中科ZKXC-TX845AT-LY-4MM摄像头 | ZK-TX845AT-LY4 | 1 |
| 昂达2.5寸SATA固态硬盘 256GB | AD-SSD-256G-SATA | 1 |
| 中科迅TA2516/AB 16路NVR | HSTTA2516/A816LNVR | 1 |
| 锐捷RG-EAP102(E)面板千兆AP | RJRG-EAP102(E)MBQZA | 0 |
| 锐捷RG-EAP162(G)双频千兆面板AP | RJRG-EAP162(G)SPQZMI | 0 |
| 锐捷RG-EG105G-P-L企业路由器 | RJRG-EG105G-P-LQYLY | 0 |
| 宏碁TF卡MSC100-32G | HQTFKMSC100-32G | 1 |
| 热镀锌管 DN20 6米 | RHDX-DN20-6M | 30 |
| DN20弯头 | DN20-WT | 10 |
| DN20直接 | DN20-ZJ | 10 |
| 帧田5口POE百兆交换机 | ZT-POE5 | 1 |
| 希捷2T监控盘 | XJ-2TJKP | 1 |
| 希捷4T监控硬盘 | XJ-4TST4000 | 1 |
| 大华 DH-NVR1104HC-HDS4 | DH-NVR1104HC | 1 |
| 大华 DH-NVR1108HC-HDS4 | DH-NVR1108HC | 1 |
| mSATA固态硬盘(60-64G随机品牌) | mSATA-SSD-60 | 1 |
| 丰雅牌A4纸 | FY-A4-500 | 24 |
| 永丰牌A4纸 | YF-A4-500 | 11 |
| 打印机维修 | FW-DYJWX | 0 |

---

## 2026-05-03 20:00 项目看板前端视觉优化（设计系统规范化）

### 变更摘要

对项目看板页面（Projects.vue）进行前端视觉优化，移除所有内联渐变样式，统一使用 Element Plus CSS 变量建立扁平化设计系统。增强了响应式布局支持，优化了筛选栏和表格的交互反馈。

### 涉及文件与修改点

**修改文件**：
- `frontend/src/views/Projects.vue` - 项目看板主页面样式重构
  - **KPI区域样式规范化**（第680-753行）：
    - 移除所有 `linear-gradient` 内联渐变背景
    - 改用 Element Plus 语义化颜色变量：
      - `.kpi-income`: `var(--el-color-success-light-9)` + `var(--el-color-success)`
      - `.kpi-cost`: `var(--el-color-warning-light-9)` + `var(--el-color-warning)`
      - `.kpi-profit.profit-positive`: `var(--el-color-primary-light-9)` + `var(--el-color-primary)`
      - `.kpi-profit.profit-negative`: `var(--el-color-danger-light-9)` + `var(--el-color-danger)`
      - `.kpi-receivable`: `var(--el-color-info-light-9)` + `var(--el-color-info)`
      - `.kpi-received`: `var(--el-color-success-light-9)` + `var(--el-color-success)`
      - `.kpi-uninvoiced`: `var(--el-color-warning-light-9)` + `var(--el-color-warning)`
    - KPI卡片背景从渐变改为纯色 `var(--el-fill-color-extra-light)`
    - 悬停阴影从 `0.08` 透明度降低至 `0.06`，更加柔和
    - 过渡动画从 `cubic-bezier(0.4, 0, 0.2, 1)` 简化为 `ease`
  
  - **筛选栏交互增强**（第799-815行）：
    - 背景从 `var(--el-fill-color-blank)` 改为 `var(--el-bg-color)` 提升对比度
    - 边框从 `lighter` 升级为 `light` 增加可见性
    - 新增 hover 状态：边框加深 + 轻微阴影 `0 1px 4px rgba(0, 0, 0, 0.04)`
    - 高亮色统一使用 Element Plus 变量：
      - `.highlight-blue`: `var(--el-color-info)` 替代硬编码 `#409eff`
      - `.highlight-green`: `var(--el-color-success)` 替代硬编码 `#67c23a`
  
  - **表格视觉层次优化**（第856-925行）：
    - 表头背景从 `var(--el-fill-color-light)` 改为 `var(--el-fill-color-extra-light)` 更浅
    - 表头 padding 增加至 `12px 0` 提升呼吸感
    - 行悬停过渡时间缩短至 `0.15s` 响应更快
    - 已收款金额颜色从硬编码改为 `var(--el-color-success)`
    - 附件缩略图悬停阴影从 `0.1` 降至 `0.08`
  
  - **响应式布局增强**（第927-1010行）：
    - 新增 `@media (max-width: 1024px)` 断点：
      - KPI网格从3列切换为2列
      - 筛选栏垂直堆叠，筛选项组占满宽度
      - 操作按钮右对齐
    - 优化 `@media (max-width: 768px)` 断点：
      - 抽屉头部改为垂直布局（flex-direction: column）
      - 右侧按钮区域独占一行并右对齐
      - KPI数值字号从20px降至18px
      - 筛选结果统计条支持换行显示
    - 新增 `@media (max-width: 480px)` 超小屏断点：
      - 容器padding从20px降至12px
      - KPI图标尺寸从48px降至40px
      - KPI标签字号从12px降至11px
      - KPI数值字号从20px降至16px

### 关键设计决策

1. **扁平化设计原则**：移除所有渐变背景，使用纯色+图标颜色的组合，符合现代UI设计趋势
2. **Element Plus设计token优先**：所有颜色、间距、圆角均使用框架提供的CSS变量，保证主题一致性
3. **渐进式响应式**：4个断点（1400px/1024px/768px/480px）覆盖从大屏到手机的完整场景
4. **微交互优化**：悬停阴影透明度从0.08降至0.06，过渡时间从0.3s降至0.2s，交互更轻量
5. **保持功能完整性**：仅修改视觉样式，不改变任何业务逻辑和数据流

### 技术亮点

- 完全消除硬编码颜色值（如 `#4caf50`, `#ff9800`），全部替换为语义化CSS变量
- 使用 Element Plus 的颜色层级系统（`-light-9` 等）实现一致的视觉层次
- 响应式布局采用 CSS Grid + Flexbox 组合方案
- 所有过渡动画统一使用 `ease` 缓动函数，保持交互一致性

### 不变量与约束合规声明

本次变更为纯前端UI/UX优化，不涉及：
- ✅ 后端业务逻辑
- ✅ 数据流和事件联动
- ✅ 三大不变量（库存一致性、项目收入一致性、项目汇总一致性）
- ✅ 7条业务逻辑约束

完全合规，无副作用风险。

### 测试验证

- 前端开发服务器启动成功（http://localhost:5175）
- 无编译错误或运行时警告
- 可通过预览浏览器查看实际效果

---

## 2026-05-03 19:45 项目详情抽屉UI/UX全面重构

### 变更摘要

对项目详情抽屉进行了全面的视觉和交互重构，从拥挤单调的布局升级为现代Dashboard风格的设计。提升了信息层次、视觉美感和用户体验，同时保持所有功能完整性。

### 涉及文件与修改点

**修改文件**：
- `frontend/src/views/Projects.vue` - 项目详情抽屉完整重构
  - **头部区域 redesign**：
    - 移除原生drawer header，使用自定义header组件
    - 添加返回按钮（带悬停动画）
    - 项目名称作为主标题（20px粗体）+ 状态标签并排
    - 客户信息和开始日期作为副标题（带图标）
    - "添加成本"按钮移至右上角
  
  - **KPI卡片系统重构**：
    - 从6列单行改为3×2网格布局（响应式：大屏3列、中屏2列、小屏1列）
    - 每个卡片添加语义化图标容器（渐变背景 + 主题色）
    - 收入（绿色）、成本（橙色）、利润（蓝色/红色动态）、待收款（紫色）、已收款（青色）、未开票（粉色）
    - 数值字号从16px提升至20px，增强可读性
    - 添加悬停效果（上移2px + 阴影）
    - 利润卡片动态显示"盈利"/"亏损"标签
  
  - **筛选器优化**：
    - 分组布局：左侧筛选项组 + 右侧搜索框和重置按钮
    - 添加搜索图标前缀
    - 筛选结果统计条移至表格上方（浅色背景条）
    - 成本和收入筛选汇总分别用不同颜色高亮
  
  - **表格增强**：
    - 添加斑马纹效果（`:stripe="true"`）
    - 表头背景色统一为浅灰色
    - 金额列加粗显示
    - 支付方式、发票状态使用彩色Tag标签
    - 附件缩略图增加圆角、边框和悬停放大效果
    - 空数据时显示Empty组件
  
  - **样式系统**：
    - 新增300+行CSS，建立完整设计系统
    - 使用Element Plus CSS变量保持一致性
    - 添加平滑过渡动画（cubic-bezier缓动函数）
    - 响应式断点：1400px（3→2列）、768px（移动端适配）
  
  - **脚本逻辑增强**：
    - 导入12个Element Plus图标组件
    - 新增`profitClass`计算属性（利润正负样式）
    - 新增`profitTrend`计算属性（盈利/亏损文本）
    - 新增`getInvoiceTagType`辅助函数（发票状态映射）
    - 格式化事件处理函数为多行结构

### 关键设计决策

1. **抽屉宽度从980px扩大至1200px**：给内容更多呼吸空间，避免信息拥挤
2. **KPI采用3×2网格而非6列单行**：提升在小屏幕上的可读性和响应式表现
3. **语义化色彩系统**：每个KPI指标使用不同的渐变色系，建立视觉记忆点
4. **悬停反馈机制**：KPI卡片和附件图片都有微妙的悬停动画，增强交互感
5. **筛选器左右分栏**：左侧专注条件筛选，右侧专注搜索和重置，职责清晰
6. **保留所有原有功能**：成本/收入筛选、销售单追溯、附件预览等功能完全保留

### 技术亮点

- 使用CSS Grid实现响应式KPI布局
- 线性渐变背景营造层次感（`linear-gradient`）
- cubic-bezier缓动函数实现自然动画
- Element Plus图标系统集成
- 计算属性动态样式绑定
- 完整的移动端媒体查询适配

### 不变量与约束合规声明

本次变更为纯前端UI/UX优化，不涉及：
- ✅ 后端业务逻辑
- ✅ 数据流和事件联动
- ✅ 三大不变量（库存一致性、项目收入一致性、项目汇总一致性）
- ✅ 7条业务逻辑约束

完全合规，无副作用风险。

---

## 2026-05-03 18:30 前端业务操作逻辑优化（P0-P1优先级）

### 变更摘要

对前端业务操作逻辑进行了三项核心优化：增强业务联动反馈、抽取订单列表通用逻辑、统一错误处理。提升了用户体验和代码可维护性。

### 涉及文件与修改点

**新增文件**：
- `frontend/src/composables/useOrderList.js` - 订单列表通用 composable
  - 封装加载、筛选、导出等通用逻辑
  - 支持通过配置区分采购/销售列表
  - 复用 `usePagination` 和统一错误处理
  
- `frontend/src/utils/errorHandler.js` - 统一错误处理工具
  - `handleError(error, options)` 函数
  - 支持 Pydantic 验证错误的友好展示
  - 可配置默认消息和是否显示详细信息

**修改文件**：
- `frontend/src/composables/useOrderForm.js`
  - 新增 `operationFeedback` 响应式对象（show/type/message/details）
  - 新增 `clearFeedback()` 方法清除反馈状态
  - 在返回值中暴露上述两个新属性/方法

- `frontend/src/components/PurchaseFormDialog.vue`
  - 新增 `operationFeedback` prop
  - 新增 `clear-feedback` 事件
  - 在对话框底部添加 el-alert 反馈组件展示联动信息

- `frontend/src/components/SaleFormDialog.vue`
  - 同 PurchaseFormDialog.vue 的修改

- `frontend/src/views/Purchases.vue`
  - 使用 `useOrderList` composable 替换原有的 list/keyword/dateRange/statusFilter/pagination 定义
  - 删除重复的 `loadData` 和 `exportData` 函数
  - 在 `handleSave` 中构建联动反馈信息（项目归集、入库商品数、总数量）
  - 传递 `operationFeedback` 给 PurchaseFormDialog 并监听 `clear-feedback` 事件

- `frontend/src/views/Sales.vue`
  - 同 Purchases.vue 的重构方式
  - 在 `handleSave` 中根据出库方式构建不同的反馈信息
    - 项目销售：显示项目归集和收入记录已生成
    - 零售出库：显示库存扣减和销售商品数
    - 不扣库存：显示出库方式

- `frontend/src/api/index.js`
  - 导出 `handleError` 供其他模块使用

- `docs/文件索引.md`
  - 新增 `useOrderList.js` 条目
  - 新增"前端 - 工具函数"章节，包含 `errorHandler.js`

### 关键设计决策

1. **操作反馈采用响应式对象而非 ElMessage**
   - 优势：可以展示结构化的详细信息（如多个联动指标）
   - 用户可以在关闭对话框前查看完整的操作结果

2. **订单列表逻辑抽取为 composable**
   - 遵循 DRY 原则，减少 ~80 行重复代码
   - 新增订单类型只需传入不同的 API 配置

3. **统一错误处理保留后端详细错误**
   - 优先展示 `error.response.data.detail`
   - 支持 Pydantic 数组格式验证错误
   - 提供默认消息作为兜底

### 测试验证

- 前端构建成功（vite build），无语法错误
- 所有修改的文件通过编译检查

### 跳过项说明

- 方案4（优化状态变更交互）和方案5（统一项目详情刷新机制）标记为低优先级，本次暂不执行

### 问题描述

多个页面出现 `TypeError: xxx.toFixed is not a function` 运行时错误。根本原因是后端API返回的金额字段为字符串类型（如 `"123.45"`），而前端模板直接使用 `.toFixed(2)` 方法，该方法仅在 Number 类型上可用。

### 涉及文件与修改点

**新增工具函数**：
- `frontend/src/api/common.js` - 新增 `formatMoney(value)` 工具函数
  - 处理 null/undefined/空字符串 → 返回 `'0.00'`
  - 使用 `Number()` 强制转换字符串为数字
  - NaN 情况兜底返回 `'0.00'`
  - 正常数字调用 `.toFixed(2)` 格式化

**修改的视图文件（共4个，10处调用点）**：

| 文件 | 修改行数 | 修改内容 |
|------|---------|---------|
| `frontend/src/views/Purchases.vue` | 第87行 import；第38、39、48行模板 | 导入 `formatMoney`，替换3处 `.toFixed(2)` 调用 |
| `frontend/src/views/Sales.vue` | 第83行 import；第34、35、44行模板 | 导入 `formatMoney`，替换3处 `.toFixed(2)` 调用 |
| `frontend/src/views/Inventory.vue` | 第95行 import；第51、54、57行模板 | 导入 `formatMoney`，替换3处 `.toFixed(2)` 调用（含库存价值计算表达式） |
| `frontend/src/views/Expenses.vue` | 第129行 import；第39行模板 | 导入 `formatMoney`，替换1处 `.toFixed(2)` 调用 |

### 关键设计决策

1. **抽取公共函数而非就地修复**：避免在10个位置重复写 `Number()` 包装逻辑，提高可维护性
2. **放在 `common.js` 而非新建文件**：该模块已有 `resolveImageUrl` 等工具函数，保持统一
3. **导出到 default export**：方便后续其他组件按需导入使用
4. **不修改后端**：纯前端展示层修复，符合任务约束

### 不变量与约束审查

- 三大不变量：不受影响（仅前端展示逻辑变更）
- 7条业务约束：不受影响（不涉及任何业务逻辑）

### 测试验证

- 已确认4个目标文件中不再有任何 `.toFixed()` 直接调用
- 已确认所有金额显示位置均已正确导入并使用 `formatMoney` 函数

## 2026-05-03 17:30 修复前端路由导航失效问题（P1优先级）

### 问题描述

通过左侧菜单栏点击导航时，路由跳转不正常：
- 点击"供应商管理"，URL不变化，页面不更新
- 点击"客户管理"，URL变为 `/customers` 但内容仍是商品管理
- 点击"采购管理"，URL变为 `/purchases` 但标题和内容混乱

但直接访问URL（如 `http://localhost:5173/suppliers`）时页面正常加载，说明路由配置本身无问题。

### 根本原因

`frontend/src/components/Layout.vue` 第19行的 `<el-menu>` 使用了 `router` 属性启用内置路由模式：
```vue
<el-menu :default-active="currentRoute" router class="app-menu" ...>
```

Element Plus 的 `el-menu` 内置 `router` 模式在某些场景下与 Vue Router 存在兼容性问题，导致：
1. 部分菜单项点击后无法触发路由跳转
2. 部分菜单项跳转后 `<router-view>` 未正确渲染对应组件

### 修复方案

将 `el-menu` 的内置 `router` 模式改为手动处理点击事件，完全控制路由跳转逻辑。

### 修改文件

**`frontend/src/components/Layout.vue`**：

1. **模板层（第19行）**：移除 `router` 属性，添加 `@select` 事件处理器
   ```vue
   <!-- 修改前 -->
   <el-menu :default-active="currentRoute" router class="app-menu" ...>
   
   <!-- 修改后 -->
   <el-menu :default-active="currentRoute" @select="handleMenuSelect" class="app-menu" ...>
   ```

2. **脚本层（第176-180行）**：新增 `handleMenuSelect` 函数
   ```javascript
   const handleMenuSelect = (index) => {
     if (index !== route.path) {
       router.push(index)
     }
   }
   ```

### 关键设计决策

- **手动控制优于内置模式**：通过 `@select` 事件 + `router.push()` 手动处理导航，避免依赖 `el-menu` 内置 router 模式的潜在兼容性问题
- **防重复跳转**：检查目标路径是否与当前路径相同，避免不必要的路由操作
- **保持响应式高亮**：`:default-active="currentRoute"` 保持不变，确保菜单项高亮状态正确

### 验证结果

- `npm run build` 构建成功，无编译错误
- 所有菜单项点击后能正确跳转并渲染对应页面内容

---

## 2026-05-03 17:15 修复图标组件导入缺失（Suppliers.vue / Customers.vue）

### 问题描述

`Suppliers.vue` 和 `Customers.vue` 在模板中使用了 Element Plus 的 `<Plus />` 和 `<Search />` 图标组件，但未在 `<script setup>` 中显式导入。

虽然项目已在 `main.js` 中通过全局注册使图标可用，但为了符合 Vue 3 最佳实践（显式声明依赖、提高代码可读性），补充了显式导入语句。

### 修复内容

- **`frontend/src/views/Suppliers.vue`**：
  - 第55行新增：`import { Plus, Search } from '@element-plus/icons-vue'`
  - 图标使用位置：第7行 `<Plus />`（新增按钮）、第12行 `<Search />`（搜索框前缀）

- **`frontend/src/views/Customers.vue`**：
  - 第55行新增：`import { Plus, Search } from '@element-plus/icons-vue'`
  - 图标使用位置：第7行 `<Plus />`（新增按钮）、第12行 `<Search />`（搜索框前缀）

### 设计决策

- 保持与项目中其他视图文件一致的代码风格（尽管多数文件依赖全局注册，但显式导入是更推荐的 Vue 3 实践）
- 参考了 `TaxReport.vue` 和 `IncomeTaxReport.vue` 已有的图标导入模式

---

## 2026-05-03 17:05 修复命令导入与库存关系警告

### 问题1：ImportError - commands 模块未导出命令类

**现象**：启动后端时报错 `ImportError: cannot import name 'CreateProduct' from 'commands'`

**根因**：`commands/__init__.py` 虽然导入了各命令子模块（触发 `@register` 装饰器），但未在 `__all__` 列表中导出具体命令类，导致 router 层无法直接导入。

**修复内容**：
- **`backend/commands/__init__.py`**：
  - 从 `product_commands` 导出：`CreateProduct`, `UpdateProduct`, `DeleteProduct`, `AdjustInventory`
  - 从 `partner_commands` 导出：`CreateSupplier`, `UpdateSupplier`, `DeleteSupplier`, `CreateCustomer`, `UpdateCustomer`, `DeleteCustomer`
  - 从 `personal_commands` 导出：`CreatePersonalTransaction`, `UpdatePersonalTransaction`, `DeletePersonalTransaction`
  - 将上述13个命令类加入 `__all__` 列表

**设计决策**：保持命令注册机制不变（`@register` 装饰器自动注册到全局 registry），仅在包级别增加显式导出，符合 Python 包的常见实践。

---

### 问题2：SAWarning - Product.inventory 返回多行

**现象**：访问商品列表时 SQLAlchemy 发出警告 `Multiple rows returned with uselist=False for eagerly-loaded attribute 'Product.inventory'`

**根因分析**：
1. 多账本架构下，不同账本可以有相同的 `product_id`
2. `Product.inventory` 关系配置为 `uselist=False`（一对一），但 JOIN 条件仅为 `ON products.id = inventory.product_id`
3. 缺少 `account_id` 匹配条件，导致跨账本的相同 `product_id` 库存记录被同时匹配

**数据库验证**：发现 `product_id=2` 在 account_id=1 和 account_id=2 中各有库存记录

**修复内容**：
- **`backend/models.py:1`**：导入 `and_` 用于复合 JOIN 条件
- **`backend/models.py:64`**：修改 `Product.inventory` 关系配置，增加 `primaryjoin` 参数：
  ```python
  inventory = relationship("Inventory", back_populates="product", uselist=False,
                           primaryjoin="and_(Product.id==Inventory.product_id, Product.account_id==Inventory.account_id)")
  ```
- **`backend/crud/products.py:4,14,27`**：在 `list_products` 和 `get_product` 查询中使用 `joinedload` 预加载 inventory，避免懒加载时的 N+1 问题

**设计决策**：
- 不修改数据库 schema（唯一约束 `(account_id, product_id)` 已存在且正确）
- 在 ORM 层面通过 `primaryjoin` 明确关联条件，确保多账本隔离
- 使用 eager loading 提升性能，同时消除警告

**影响范围**：
- 商品列表、详情、导出功能不再产生警告
- 跨账本数据隔离得到保证

---

## 2026-05-01 销售单增强与多项修复

- **销售单自定义金额**: 支持 `total_price` 整单打折/抹零/含税包价，差额自动分配到各行单价 → `backend/schemas.py` SaleOrderCreate/Update 增加 total_price；`backend/crud/orders.py` 新增 `_distribute_total_price()` 差额分配；`frontend/src/views/Sales.vue` 新增自定义金额输入框。修复 `||null` 导致0值丢失改为 `??undefined`/`??null`
- **禁止同一商品重复行**: 销售/采购单同一商品重复添加返回400，三层防护（CRUD校验+前端防重+数据库UniqueConstraint） → `backend/crud/orders.py` 增加重复校验；`backend/models.py` 添加(order_id,product_id)唯一约束；`backend/database.py` 自动清理已有重复数据；前端Sales/Purchases.vue增加重复检测
- **客户选择自动新建**: 客户选择改为 `allow-create`，输入不存在名字自动创建客户 → `frontend/src/views/Sales.vue` customer_id→customer_name，handleSave中按名字查找/创建
- **导出功能修复**: 4个页面 `window.open()` 改为 `api.exportFile()` axios blob下载，解决缺少X-Account-ID请求头 → `frontend/src/api/index.js` 新增exportFile；Inventory/Purchases/Sales/Reports.vue替换
- **销售单价用户自填**: 移除选择商品自动填充sale_price逻辑 → `frontend/src/views/Sales.vue` 移除onItemProductChange/onEditItemProductChange自动填充
- **对账管理功能**: 新增对账页面，按供应商/客户维度实时计算对账数据 → `backend/routers/reconciliations.py` 新建（汇总+明细2接口）；`frontend/src/views/Reconciliations.vue` 新建；router/Layout注册
- **采购单付款状态修复**: PurchaseOrderUpdate/Out缺少payment_status导致无法修改和显示 → `backend/schemas.py` 补充字段；`backend/routers/purchases.py` _build_purchase_out添加
- **库存批量导出**: 新增批量选择导出Excel/CSV → `backend/routers/export.py` 新增products-batch路由；`frontend/src/views/Products.vue` 表格增加复选框+批量导出按钮
- **批量导出blob修复**: axios拦截器解包blob导致失败，改用原生axios.get绕过拦截器 → `frontend/src/api/index.js` exportProductsBatch重写
- **10项业务逻辑漏洞修复**: 所得税未过滤取消订单；销售/采购单项目切换旧汇总未重算；采购单status+items交互双重扣库存；对账参数名不一致；发票上传接口参数修正；销售单取消库存不回补；SKILL.md参数名同步 → `backend/routers/income_tax.py`、`backend/crud/orders.py`、`backend/routers/reconciliations.py`、`backend/routers/invoices.py`、`backend/crud/linkage.py`、`frontend/src/views/Reconciliations.vue`、`docs/SKILL.md` v5.5.0

---

## 2026-04-30 采购单+销售单行级编辑及体验优化

- 采购单支持行级商品编辑（修改数量/单价、删除行自动扣库存、行数归零自动删单）→ `backend/schemas.py` PurchaseOrderUpdate扩展；`backend/crud/orders.py` 重写update_purchase_order；`frontend/src/views/Purchases.vue` 增加编辑按钮+编辑弹窗
- 销售单对称支持行级编辑（零售库存回补/扣减、项目收入联动）→ `backend/schemas.py` SaleOrderUpdate扩展；`backend/crud/orders.py` 重写update_sale_order；`frontend/src/views/Sales.vue` 增加编辑按钮+编辑弹窗
- 采购单付款状态展示和编辑（列表标签+弹窗下拉）
- 编辑采购单支持修改税率

---

## 2026-04-29 查询优化与功能增强

- **采购/库存增加查询按钮**: 筛选器不再自动触发，改为查询按钮触发 → `backend/crud/orders.py` list_purchase_orders增加keyword；`backend/crud/products.py` list_inventory增加search+category；`backend/routers/purchases.py`/`inventory.py` 新增参数；前端Purchases/Inventory.vue增加搜索框+查询按钮
- **零售扣库存开关**: 销售单新增 `deduct_inventory` 字段，零售=true直接扣库存，项目业务不扣（防双扣）→ `backend/models.py`/`schemas.py`/`database.py`/`crud/linkage.py`/`crud/orders.py`/`routers/sales.py`；`frontend/src/views/Sales.vue` 新增开关
- **项目详情页优化**: 详情改为Drawer+首屏KPI+明细筛选+合计+收入追溯到销售单 → `frontend/src/views/Projects.vue`；`frontend/src/api/index.js` 新增getSale

---

## 2026-04-28 联动改造v2.4全量实施

- **阶段1数据层**: SaleOrder/PurchaseOrder新增project_id；ProjectCost新增product_id/quantity；ProjectIncome新增source_type/source_id+UniqueConstraint → `backend/models.py`/`database.py`/`schemas.py`
- **阶段2联动业务层**: 新建 `backend/crud/linkage.py` 5个联动函数（材料扣/回补/更新库存、销售创建/删除收入）；`backend/crud/base.py` _log改flush
- **阶段3统一计算**: `backend/utils.py` update_project_summary移除commit+新增采购成本计算；新增verify_invariants三大不变量验证
- **阶段4路由层改造**: `backend/routers/project_costs.py` 全部6端点改造（linkage+update_project_summary）；`backend/crud/orders.py` 销售单移除库存操作+增加收入联动、采购单增加项目汇总；`backend/routers/projects.py` GROUP BY聚合+采购单tab+verify-invariants+reconcile
- **阶段5前端改造**: Sales/Purchases.vue project_name→project_id；Projects.vue统一Project表+成本商品/数量列+收入来源列+采购单tab
- **成本添加弹窗**: Projects.vue新增"添加成本"按钮和弹窗（材料类选商品+自动算金额）
- **方案迭代**: v2.0精简重写→v2.1不变量强化→v2.2审查修正(7项)→v2.3拼写+回填策略→v2.4(5项修正:导入缺失/SQLite约束/销售单双扣/校验未实现/金额口径)
- **SKILL.md同步**: 联动API/字段/注意事项补全，v4.0.0→v5.0.0

---

## 2026-04-28 架构加固 + crud模块拆分

- **crud.py拆分为包目录**: 1496行单文件→`backend/crud/` 包目录（11个子模块+__init__.py re-export 76项，零破坏性）
- **事务包裹**: 所有写操作加 try/except + db.rollback() → crud/orders,partners,products,invoices,projects,personal,finance.py
- **金额精度**: 行金额/订单总额/报表金额统一 round(2) → crud/orders,invoices,reports,personal,finance.py
- **订单号并发冲突**: 格式增加HHMMSS时间戳 `{前缀}{日期}-{时分秒}-{序号}` → `backend/crud/base.py`
- **供应商/客户删除保护**: 有关联记录拒绝删除 → `backend/crud/partners.py`
- **CORS安全**: `allow_origins=["*"]` → localhost白名单+CORS_ORIGINS环境变量 → `backend/main.py`
- **前端API硬编码消除**: 改用Vite环境变量 → `frontend/src/api/index.js`、`.env.development`、`.env.production`
- **个人支出新增"烟酒"类别**: → `backend/enums.py`
- **SKILL.md文档同步**: 覆盖所有106个API端点，v3.0.0→v4.0.0