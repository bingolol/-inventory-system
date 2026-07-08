# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: reports.spec.js >> 报表统计 >> 页面加载 >> 四个Tab正确展示
- Location: tests\e2e\reports.spec.js:15:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.el-tabs__item:has-text("总览")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.el-tabs__item:has-text("总览")')

```

```yaml
- complementary:
  - text: 进销存 巧游电子科技 一般纳税人
  - combobox
  - text: 巧游电子科技
  - img
  - text: ＋ ✎ −
  - navigation: ◉ 仪表盘 基础数据 ◻ 伙伴管理 ◻ 库存商品 业务处理 ◉ 销售开单 ◻ 采购入库 ◻ 发票录入 ◻ 资金流水 财务核算 ◉ 财务总览 ◻ 费用管理 ◻ 固定资产 ◻ 银行账户 ◻ 银行对账 ◻ 往来管理 财务报表 ◉ 资产负债表/利润表 ◉ 现金流量表 ◻ 会计账簿 ◻ 会计规则指引 期末处理 ◉ 期末税务 系统管理 ◻ 操作日志 ◻ 数据备份
- heading "仪表盘" [level=2]
- text: 快速导航到各功能模块
- button "A admin":
  - text: A admin
  - img
- text: 2026/07/07周二
- main:
  - text: 本月净利润 0.00 收入 0.00 成本 0.00 费用 0.00 毛利 0.00 别人欠我 0.00 未回款客户 0 家 销售笔数 0 我欠别人 578.00 未付供应商 2 家 库存资金 2,182.60 库存总量 5 件 商品种类 8 种 预警项 0 待办清单 2026年7月7日 · 2026年第3季度（7月~9月） 本月截止 7月初 — 检查上月月结 上月还没做月结的话尽快补做。月结不仅生成报表，还计提折旧、计算增值税，不做数据会跨月混淆。 截止：7月7日前
  - button "补做月结"
  - text: 上季度申报截止 — 增值税+企业所得税预缴 必须在9月15日前完成。逾期每日万分之五滞纳金！ 截止：9月15日
  - button "查税务报表"
  - text: 本月例行 7月15日前 — 完成上月税务申报 一般纳税人必须每月15日前申报增值税。小规模按季度申报，但仍建议每月查看税务掌握税负。
  - button "查税务"
  - text: 7月工资计提与发放 有员工的公司每月需记录工资费用：费用支出 → 新增费用 → 类别选"工资"。
  - button "记费用"
  - text: 日常维护 核对银行对账单（建议每周一次） 确保系统账面余额和银行实际余额一致。差异可能来自银行手续费未录、客户汇款未核销、支票未兑现。
  - button "去对账"
  - text: 催收逾期应收账款 重点关注超过90天未回款的客户。金额大的主动联系催收，逾期越久变坏账概率越大。
  - button "查往来"
  - text: 当天业务当天录入系统 采购入库、销售开单、费用支出、收款付款——每笔发生立刻录入，不要积压。 远期注意 残疾人就业保障金申报（7-9月） 各地申报时间略有不同。未安置残疾人需缴纳残保金，具体金额和截止时间咨询当地残联。 截止：以当地通知为准 关注连续12个月累计销售额 小规模纳税人连续12个月销售额超500万会被强制认定一般纳税人（不可逆）。每月要盯着滚动12个月的累计数。 截止：持续关注 业务概要 本月收入 0.00 本月成本 0.00 本月费用 0.00 销售笔数 0 商品种类 8 库存总量 5 业务处理 📦 采购入库 → 🧾 进项发票 → 💳 采购付款 📋 销售开单 → 🧾 销项发票 → 💰 收款 💸 费用 → 💳 付款 → 🏦 银行对账 → 🔒 月结 数据查看 📊 财务总览 🏦 银行账户 📄 财务报表 🏛️ 期末税务 🏦 银行对账 💰 收款管理 💳 付款管理 🏗️ 固定资产 🔒 期末处理 库存预警 全部 → 暂无预警，库存状况良好 收入趋势 近30天
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('报表统计', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/reports');
  6   |     await page.waitForTimeout(2000);
  7   |   });
  8   | 
  9   |   // ========== 页面加载 ==========
  10  |   test.describe('页面加载', () => {
  11  |     test('报表页面正常加载', async ({ page }) => {
  12  |       await expect(page.locator('.page-title:has-text("报表统计")')).toBeVisible();
  13  |     });
  14  | 
  15  |     test('四个Tab正确展示', async ({ page }) => {
> 16  |       await expect(page.locator('.el-tabs__item:has-text("总览")')).toBeVisible();
      |                                                                   ^ Error: expect(locator).toBeVisible() failed
  17  |       await expect(page.locator('.el-tabs__item:has-text("采购报表")')).toBeVisible();
  18  |       await expect(page.locator('.el-tabs__item:has-text("销售报表")')).toBeVisible();
  19  |       await expect(page.locator('.el-tabs__item:has-text("利润分析")')).toBeVisible();
  20  |     });
  21  | 
  22  |     test('导出按钮可见', async ({ page }) => {
  23  |       await expect(page.locator('button:has-text("导出当前报表")')).toBeVisible();
  24  |     });
  25  |   });
  26  | 
  27  |   // ========== 总览Tab ==========
  28  |   test.describe('总览Tab', () => {
  29  |     test('默认显示总览Tab', async ({ page }) => {
  30  |       const overviewTab = page.locator('.el-tabs__item:has-text("总览")');
  31  |       await expect(overviewTab).toHaveClass(/is-active/);
  32  |     });
  33  | 
  34  |     test('总览统计数据正确展示', async ({ page }) => {
  35  |       const tabPane = page.locator('.el-tab-pane').first();
  36  |       await expect(tabPane.locator('.stat-label:has-text("商品种类")')).toBeVisible();
  37  |       await expect(tabPane.locator('.stat-label:has-text("库存总量")')).toBeVisible();
  38  |       await expect(tabPane.locator('.stat-label:has-text("库存价值")')).toBeVisible();
  39  |       await expect(tabPane.locator('.stat-label:has-text("库存预警")')).toBeVisible();
  40  |     });
  41  | 
  42  |     test('库存价值包含人民币符号', async ({ page }) => {
  43  |       const value = page.locator('.el-tab-pane .stat-value:has-text("¥")').first();
  44  |       if (await value.isVisible().catch(() => false)) {
  45  |         const text = await value.textContent();
  46  |         expect(text).toContain('¥');
  47  |       }
  48  |     });
  49  |   });
  50  | 
  51  |   // ========== 采购报表Tab ==========
  52  |   test.describe('采购报表Tab', () => {
  53  |     test('切换到采购报表Tab', async ({ page }) => {
  54  |       await page.locator('.el-tabs__item:has-text("采购报表")').click();
  55  |       await page.waitForTimeout(1000);
  56  | 
  57  |       const purchaseTab = page.locator('.el-tabs__item:has-text("采购报表")');
  58  |       await expect(purchaseTab).toHaveClass(/is-active/);
  59  |     });
  60  | 
  61  |     test('采购报表展示日期筛选', async ({ page }) => {
  62  |       await page.locator('.el-tabs__item:has-text("采购报表")').click();
  63  |       await page.waitForTimeout(500);
  64  | 
  65  |       await expect(page.locator('.el-date-editor').first()).toBeVisible();
  66  |     });
  67  | 
  68  |     test('采购报表展示汇总信息', async ({ page }) => {
  69  |       await page.locator('.el-tabs__item:has-text("采购报表")').click();
  70  |       await page.waitForTimeout(1000);
  71  | 
  72  |       await expect(page.locator('text=采购总金额')).toBeVisible();
  73  |       await expect(page.locator('text=采购单数')).toBeVisible();
  74  |     });
  75  | 
  76  |     test('采购报表表格包含必要列', async ({ page }) => {
  77  |       await page.locator('.el-tabs__item:has-text("采购报表")').click();
  78  |       await page.waitForTimeout(1000);
  79  | 
  80  |       const table = page.locator('.el-tab-pane .el-table').first();
  81  |       if (await table.isVisible().catch(() => false)) {
  82  |         await expect(table.locator('th:has-text("单号")')).toBeVisible();
  83  |         await expect(table.locator('th:has-text("供应商")')).toBeVisible();
  84  |         await expect(table.locator('th:has-text("总价")')).toBeVisible();
  85  |         await expect(table.locator('th:has-text("日期")')).toBeVisible();
  86  |       }
  87  |     });
  88  |   });
  89  | 
  90  |   // ========== 销售报表Tab ==========
  91  |   test.describe('销售报表Tab', () => {
  92  |     test('切换到销售报表Tab', async ({ page }) => {
  93  |       await page.locator('.el-tabs__item:has-text("销售报表")').click();
  94  |       await page.waitForTimeout(1000);
  95  | 
  96  |       const saleTab = page.locator('.el-tabs__item:has-text("销售报表")');
  97  |       await expect(saleTab).toHaveClass(/is-active/);
  98  |     });
  99  | 
  100 |     test('销售报表展示日期筛选', async ({ page }) => {
  101 |       await page.locator('.el-tabs__item:has-text("销售报表")').click();
  102 |       await page.waitForTimeout(500);
  103 | 
  104 |       await expect(page.locator('.el-tab-pane:visible .el-date-editor')).toBeVisible();
  105 |     });
  106 | 
  107 |     test('销售报表展示汇总信息', async ({ page }) => {
  108 |       await page.locator('.el-tabs__item:has-text("销售报表")').click();
  109 |       await page.waitForTimeout(1000);
  110 | 
  111 |       await expect(page.locator('text=销售总金额')).toBeVisible();
  112 |       await expect(page.locator('text=销售单数')).toBeVisible();
  113 |     });
  114 | 
  115 |     test('销售报表表格包含必要列', async ({ page }) => {
  116 |       await page.locator('.el-tabs__item:has-text("销售报表")').click();
```