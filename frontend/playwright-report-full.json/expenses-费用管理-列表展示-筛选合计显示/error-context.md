# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: expenses.spec.js >> 费用管理 >> 列表展示 >> 筛选合计显示
- Location: tests\e2e\expenses.spec.js:45:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('div').filter({ hasText: /^筛选合计：/ }).first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('div').filter({ hasText: /^筛选合计：/ }).first()

```

```yaml
- complementary:
  - text: 进销存 巧游电子科技 一般纳税人
  - combobox
  - text: 巧游电子科技
  - img
  - text: ＋ ✎ −
  - navigation: ◉ 仪表盘 基础数据 ◻ 伙伴管理 ◻ 库存商品 业务处理 ◉ 销售开单 ◻ 采购入库 ◻ 发票录入 ◻ 资金流水 财务核算 ◉ 财务总览 ◻ 费用管理 ◻ 固定资产 ◻ 银行账户 ◻ 银行对账 ◻ 往来管理 财务报表 ◉ 资产负债表/利润表 ◉ 现金流量表 ◻ 会计账簿 ◻ 会计规则指引 期末处理 ◉ 期末税务 系统管理 ◻ 操作日志 ◻ 数据备份
- heading "费用支出" [level=2]
- text: 费用管理 · 个人垫付
- button "A admin":
  - text: A admin
  - img
- text: 2026/07/07周二
- main:
  - text: 费用支出
  - tablist:
    - tab "费用管理" [selected]
    - tab "个人垫付"
  - tabpanel "费用管理":
    - text: 本月费用 0.00 筛选合计 9,940.00 记录数 14 笔 费用管理
    - button "新增费用":
      - img
      - text: 新增费用
    - combobox
    - text: 年份
    - img
    - button "查询":
      - img
      - text: 查询
    - button "重置"
    - button "付款管理":
      - img
      - text: 付款管理
    - table:
      - rowgroup:
        - row "日期 类别 功能分类 金额 付款状态 描述 操作":
          - columnheader "日期"
          - columnheader "类别"
          - columnheader "功能分类"
          - columnheader "金额"
          - columnheader "付款状态"
          - columnheader "描述"
          - columnheader "操作"
    - table:
      - rowgroup:
        - row "2025-12-31 房租 管理费用 -1,300.00 unpaid 2025年12月房租 编辑 付款 冲红":
          - cell "2025-12-31"
          - cell "房租"
          - cell "管理费用"
          - cell "-1,300.00"
          - cell "unpaid"
          - cell "2025年12月房租"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2025-12-31 水电 管理费用 -120.00 unpaid 2025年12月水电 编辑 付款 冲红":
          - cell "2025-12-31"
          - cell "水电"
          - cell "管理费用"
          - cell "-120.00"
          - cell "unpaid"
          - cell "2025年12月水电"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-1-31 房租 管理费用 -1,300.00 unpaid 2026年1月房租 编辑 付款 冲红":
          - cell "2026-1-31"
          - cell "房租"
          - cell "管理费用"
          - cell "-1,300.00"
          - cell "unpaid"
          - cell "2026年1月房租"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-1-31 水电 管理费用 -120.00 unpaid 2026年1月水电 编辑 付款 冲红":
          - cell "2026-1-31"
          - cell "水电"
          - cell "管理费用"
          - cell "-120.00"
          - cell "unpaid"
          - cell "2026年1月水电"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-2-28 房租 管理费用 -1,300.00 unpaid 2026年2月房租 编辑 付款 冲红":
          - cell "2026-2-28"
          - cell "房租"
          - cell "管理费用"
          - cell "-1,300.00"
          - cell "unpaid"
          - cell "2026年2月房租"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-2-28 水电 管理费用 -120.00 unpaid 2026年2月水电 编辑 付款 冲红":
          - cell "2026-2-28"
          - cell "水电"
          - cell "管理费用"
          - cell "-120.00"
          - cell "unpaid"
          - cell "2026年2月水电"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-3-31 房租 管理费用 -1,300.00 unpaid 2026年3月房租 编辑 付款 冲红":
          - cell "2026-3-31"
          - cell "房租"
          - cell "管理费用"
          - cell "-1,300.00"
          - cell "unpaid"
          - cell "2026年3月房租"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-3-31 水电 管理费用 -120.00 unpaid 2026年3月水电 编辑 付款 冲红":
          - cell "2026-3-31"
          - cell "水电"
          - cell "管理费用"
          - cell "-120.00"
          - cell "unpaid"
          - cell "2026年3月水电"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-4-30 房租 管理费用 -1,300.00 unpaid 2026年4月房租 编辑 付款 冲红":
          - cell "2026-4-30"
          - cell "房租"
          - cell "管理费用"
          - cell "-1,300.00"
          - cell "unpaid"
          - cell "2026年4月房租"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-4-30 水电 管理费用 -120.00 unpaid 2026年4月水电 编辑 付款 冲红":
          - cell "2026-4-30"
          - cell "水电"
          - cell "管理费用"
          - cell "-120.00"
          - cell "unpaid"
          - cell "2026年4月水电"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-5-31 房租 管理费用 -1,300.00 unpaid 2026年5月房租 编辑 付款 冲红":
          - cell "2026-5-31"
          - cell "房租"
          - cell "管理费用"
          - cell "-1,300.00"
          - cell "unpaid"
          - cell "2026年5月房租"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-5-31 水电 管理费用 -120.00 unpaid 2026年5月水电 编辑 付款 冲红":
          - cell "2026-5-31"
          - cell "水电"
          - cell "管理费用"
          - cell "-120.00"
          - cell "unpaid"
          - cell "2026年5月水电"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-6-30 房租 管理费用 -1,300.00 unpaid 2026年6月房租 编辑 付款 冲红":
          - cell "2026-6-30"
          - cell "房租"
          - cell "管理费用"
          - cell "-1,300.00"
          - cell "unpaid"
          - cell "2026年6月房租"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
        - row "2026-6-30 水电 管理费用 -120.00 unpaid 2026年6月水电 编辑 付款 冲红":
          - cell "2026-6-30"
          - cell "水电"
          - cell "管理费用"
          - cell "-120.00"
          - cell "unpaid"
          - cell "2026年6月水电"
          - cell "编辑 付款 冲红":
            - button "编辑"
            - button "付款"
            - button "冲红"
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('费用管理', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/expenses');
  6   |     await page.waitForTimeout(800);
  7   |     await page.waitForSelector('.el-table__row', { timeout: 10000 });
  8   |   });
  9   | 
  10  |   // ========== 列表展示 ==========
  11  |   test.describe('列表展示', () => {
  12  |     test('费用列表正确展示后端数据', async ({ page }) => {
  13  |       const rows = await page.locator('.el-table__row').count();
  14  |       expect(rows).toBeGreaterThan(0);
  15  | 
  16  |       await expect(page.locator('th:has-text("日期")')).toBeVisible();
  17  |       await expect(page.locator('th:has-text("类别")')).toBeVisible();
  18  |       await expect(page.locator('th:has-text("金额")')).toBeVisible();
  19  |       await expect(page.locator('th:has-text("有发票")')).toBeVisible();
  20  |       await expect(page.locator('th:has-text("支付方式")')).toBeVisible();
  21  |       await expect(page.locator('th:has-text("描述")')).toBeVisible();
  22  |       await expect(page.locator('th:has-text("操作")')).toBeVisible();
  23  |     });
  24  | 
  25  |     test('第一行数据包含有效内容', async ({ page }) => {
  26  |       const firstRow = page.locator('.el-table__row:first-child');
  27  |       const rowText = await firstRow.textContent();
  28  |       expect(rowText?.trim().length).toBeGreaterThan(5);
  29  |     });
  30  | 
  31  |     test('金额显示包含货币符号', async ({ page }) => {
  32  |       const firstRow = page.locator('.el-table__row:first-child');
  33  |       const amountCell = firstRow.locator('td').nth(2);
  34  |       const amountText = await amountCell.textContent();
  35  |       expect(amountText?.trim()).toMatch(/^¥[\d,.]+$/);
  36  |     });
  37  | 
  38  |     test('日期格式正确', async ({ page }) => {
  39  |       const firstRow = page.locator('.el-table__row:first-child');
  40  |       const dateCell = firstRow.locator('td').nth(0);
  41  |       const dateText = await dateCell.textContent();
  42  |       expect(dateText?.trim()).toMatch(/^\d{4}-\d{2}-\d{2}/);
  43  |     });
  44  | 
  45  |     test('筛选合计显示', async ({ page }) => {
  46  |       const summaryArea = page.locator('div').filter({ hasText: /^筛选合计：/ }).first();
> 47  |       await expect(summaryArea).toBeVisible();
      |                                 ^ Error: expect(locator).toBeVisible() failed
  48  |       await expect(summaryArea).toContainText('金额');
  49  |     });
  50  |   });
  51  | 
  52  |   // ========== 筛选功能 ==========
  53  |   test.describe('筛选功能', () => {
  54  |     test('按类别筛选费用', async ({ page }) => {
  55  |       const allCount = await page.locator('.el-table__row').count();
  56  | 
  57  |       const categorySelect = page.locator('.el-form-item:has-text("类别") .el-select');
  58  |       await categorySelect.click();
  59  |       await page.waitForTimeout(500);
  60  | 
  61  |       const dropdown = page.locator('.el-select-dropdown:visible').last();
  62  |       const options = dropdown.locator('li');
  63  |       const optionCount = await options.count();
  64  | 
  65  |       if (optionCount > 0) {
  66  |         await options.first().click();
  67  |         await page.waitForTimeout(500);
  68  | 
  69  |         await page.locator('button:has-text("查询")').click();
  70  |         await page.waitForTimeout(1000);
  71  | 
  72  |         const filteredCount = await page.locator('.el-table__row').count();
  73  |         expect(filteredCount).toBeGreaterThanOrEqual(0);
  74  |         expect(filteredCount).toBeLessThanOrEqual(allCount);
  75  |       }
  76  |     });
  77  | 
  78  |     test('按年份筛选费用', async ({ page }) => {
  79  |       const allCount = await page.locator('.el-table__row').count();
  80  | 
  81  |       const yearSelect = page.locator('.el-form-item:has-text("年份") .el-select');
  82  |       await yearSelect.click();
  83  |       await page.waitForTimeout(500);
  84  | 
  85  |       const dropdown = page.locator('.el-select-dropdown:visible').last();
  86  |       const options = dropdown.locator('li');
  87  |       const optionCount = await options.count();
  88  | 
  89  |       if (optionCount > 0) {
  90  |         await options.first().click();
  91  |         await page.waitForTimeout(500);
  92  | 
  93  |         await page.locator('button:has-text("查询")').click();
  94  |         await page.waitForTimeout(1000);
  95  | 
  96  |         const filteredCount = await page.locator('.el-table__row').count();
  97  |         expect(filteredCount).toBeGreaterThanOrEqual(0);
  98  |         expect(filteredCount).toBeLessThanOrEqual(allCount);
  99  |       }
  100 |     });
  101 | 
  102 |     test('重置筛选条件', async ({ page }) => {
  103 |       const allCount = await page.locator('.el-table__row').count();
  104 | 
  105 |       const categorySelect = page.locator('.el-form-item:has-text("类别") .el-select');
  106 |       await categorySelect.click();
  107 |       await page.waitForTimeout(500);
  108 | 
  109 |       const dropdown = page.locator('.el-select-dropdown:visible').last();
  110 |       const options = dropdown.locator('li');
  111 |       const optionCount = await options.count();
  112 | 
  113 |       if (optionCount > 0) {
  114 |         await options.first().click();
  115 |         await page.waitForTimeout(500);
  116 |       }
  117 | 
  118 |       await page.locator('button:has-text("重置")').click();
  119 |       await page.waitForTimeout(1000);
  120 | 
  121 |       const restoredCount = await page.locator('.el-table__row').count();
  122 |       expect(restoredCount).toBe(allCount);
  123 |     });
  124 | 
  125 |     test('组合筛选费用', async ({ page }) => {
  126 |       const allCount = await page.locator('.el-table__row').count();
  127 | 
  128 |       const categorySelect = page.locator('.el-form-item:has-text("类别") .el-select');
  129 |       await categorySelect.click();
  130 |       await page.waitForTimeout(500);
  131 | 
  132 |       const categoryDropdown = page.locator('.el-select-dropdown:visible').last();
  133 |       const categoryOptions = categoryDropdown.locator('li');
  134 |       const categoryOptionCount = await categoryOptions.count();
  135 | 
  136 |       if (categoryOptionCount > 0) {
  137 |         await categoryOptions.first().click();
  138 |         await page.waitForTimeout(500);
  139 |       }
  140 | 
  141 |       const yearSelect = page.locator('.el-form-item:has-text("年份") .el-select');
  142 |       await yearSelect.click();
  143 |       await page.waitForTimeout(500);
  144 | 
  145 |       const yearDropdown = page.locator('.el-select-dropdown:visible').last();
  146 |       const yearOptions = yearDropdown.locator('li');
  147 |       const yearOptionCount = await yearOptions.count();
```