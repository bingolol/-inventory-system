# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tax-report.spec.js >> 税务报表 >> 增值税报表 >> 默认按季度模式展示
- Location: tests\e2e\tax-report.spec.js:34:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.vat-report-section').locator('.el-form-item:has-text("季度")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.vat-report-section').locator('.el-form-item:has-text("季度")')

```

```yaml
- complementary:
  - text: 进销存 巧游电子科技 一般纳税人
  - combobox
  - text: 巧游电子科技
  - img
  - text: ＋ ✎ −
  - navigation: ◉ 仪表盘 基础数据 ◻ 伙伴管理 ◻ 库存商品 业务处理 ◉ 销售开单 ◻ 采购入库 ◻ 发票录入 ◻ 资金流水 财务核算 ◉ 财务总览 ◻ 费用管理 ◻ 固定资产 ◻ 银行账户 ◻ 银行对账 ◻ 往来管理 财务报表 ◉ 资产负债表/利润表 ◉ 现金流量表 ◻ 会计账簿 ◻ 会计规则指引 期末处理 ◉ 期末税务 系统管理 ◻ 操作日志 ◻ 数据备份
- heading "期末税务" [level=2]
- text: 税务报表 · 期末处理
- button "A admin":
  - text: A admin
  - img
- text: 2026/07/07周二
- main:
  - text: 期末税务
  - tablist:
    - tab "税务报表" [selected]
    - tab "附加税申报"
    - tab "期末处理"
  - tabpanel "税务报表":
    - text: 税务报表
    - button "税务核对"
    - text: "? 增值税是你替税务局代收的钱（销项-进项），不是你自己的费用。企业所得税才是你赚了钱要缴的税（利润×税率）。两条线完全不同，别搞混。"
    - link "查看增值税和企业所得税详解 →":
      - /url: /accounting-guide
    - text: ✕
    - tablist:
      - tab "增值税报表" [selected]
      - tab "企业所得税"
    - tabpanel "增值税报表":
      - text: 一般纳税人
      - radiogroup "radio-group":
        - radio "按季度" [checked]
        - text: 按季度
        - radio "按月份"
        - text: 按月份
      - combobox
      - text: "2026"
      - img
      - combobox
      - text: "3"
      - img
      - button "查询"
      - text: 2026年第3季度增值税报表 2026-07-01 ~ 2026-09-30
      - table:
        - rowgroup:
          - row "销项税额 0.00":
            - cell "销项税额"
            - cell "0.00"
          - row "进项税额 0.00":
            - cell "进项税额"
            - cell "0.00"
          - row "应纳税额合计 0.00":
            - cell "应纳税额合计"
            - cell "0.00"
      - text: 涉及发票 销项发票 0 张 不含税 0.00 进项发票 0 张 不含税 0.00 查看全部发票 → 共 0 张
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('税务报表', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/tax-report');
  6   |     await page.waitForSelector('.el-card', { timeout: 10000 });
  7   |   });
  8   | 
  9   |   // ========== 页面加载 ==========
  10  |   test.describe('页面加载', () => {
  11  |     test('页面标题正确显示', async ({ page }) => {
  12  |       await expect(page.locator('.page-title')).toContainText('税务报表');
  13  |     });
  14  | 
  15  |     test('标签页正确显示', async ({ page }) => {
  16  |       await expect(page.locator('.el-tabs__item:has-text("增值税报表")')).toBeVisible();
  17  |       await expect(page.locator('.el-tabs__item:has-text("企业所得税")')).toBeVisible();
  18  |     });
  19  | 
  20  |     test('默认选中增值税报表标签页', async ({ page }) => {
  21  |       const activeTab = page.locator('.el-tabs__item.is-active');
  22  |       await expect(activeTab).toContainText('增值税报表');
  23  |     });
  24  |   });
  25  | 
  26  |   // ========== 增值税报表 ==========
  27  |   test.describe('增值税报表', () => {
  28  |     test('增值税报表筛选区域正确展示', async ({ page }) => {
  29  |       const vatSection = page.locator('.vat-report-section');
  30  |       await expect(vatSection.locator('text=按季度')).toBeVisible();
  31  |       await expect(vatSection.locator('text=按月份')).toBeVisible();
  32  |     });
  33  | 
  34  |     test('默认按季度模式展示', async ({ page }) => {
  35  |       const vatSection = page.locator('.vat-report-section');
  36  |       // 按季度模式下，季度表单可见
> 37  |       await expect(vatSection.locator('.el-form-item:has-text("季度")')).toBeVisible();
      |                                                                        ^ Error: expect(locator).toBeVisible() failed
  38  |     });
  39  | 
  40  |     test('季度筛选表单正确展示', async ({ page }) => {
  41  |       const vatSection = page.locator('.vat-report-section');
  42  |       await expect(vatSection.locator('.el-form-item:has-text("年份")')).toBeVisible();
  43  |       await expect(vatSection.locator('.el-form-item:has-text("季度")')).toBeVisible();
  44  |       await expect(vatSection.locator('button:has-text("查询")')).toBeVisible();
  45  |     });
  46  | 
  47  |     test('按季度查询增值税报表', async ({ page }) => {
  48  |       const vatSection = page.locator('.vat-report-section');
  49  | 
  50  |       // 选择年份
  51  |       const yearFormItem = vatSection.locator('.el-form-item:has-text("年份")');
  52  |       await yearFormItem.locator('.el-select').click();
  53  |       await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
  54  |       const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
  55  |       if (await yearOptions.count() > 0) {
  56  |         await yearOptions.first().click();
  57  |       }
  58  | 
  59  |       // 选择季度
  60  |       const quarterFormItem = vatSection.locator('.el-form-item:has-text("季度")');
  61  |       await quarterFormItem.locator('.el-select').click();
  62  |       await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
  63  |       const quarterOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
  64  |       if (await quarterOptions.count() > 0) {
  65  |         await quarterOptions.first().click();
  66  |       }
  67  | 
  68  |       // 点击查询
  69  |       await vatSection.locator('button:has-text("查询")').click();
  70  |       await page.waitForTimeout(2000);
  71  | 
  72  |       // 验证报表卡片或空状态存在
  73  |       const reportCard = vatSection.locator('.report-card');
  74  |       const emptyState = vatSection.locator('.el-empty');
  75  |       const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
  76  |       expect(hasContent).toBeTruthy();
  77  |     });
  78  | 
  79  |     test('切换到按月份模式', async ({ page }) => {
  80  |       const vatSection = page.locator('.vat-report-section');
  81  |       await vatSection.locator('text=按月份').click();
  82  |       await page.waitForTimeout(500);
  83  | 
  84  |       // 切换后月份表单可见，季度表单不可见
  85  |       await expect(vatSection.locator('.el-form-item:has-text("月份")')).toBeVisible();
  86  |       await expect(vatSection.locator('.el-form-item:has-text("季度")')).not.toBeVisible();
  87  |     });
  88  | 
  89  |     test('月份筛选表单正确展示', async ({ page }) => {
  90  |       const vatSection = page.locator('.vat-report-section');
  91  |       await vatSection.locator('text=按月份').click();
  92  |       await page.waitForTimeout(500);
  93  | 
  94  |       await expect(vatSection.locator('.el-form-item:has-text("年份")')).toBeVisible();
  95  |       await expect(vatSection.locator('.el-form-item:has-text("月份")')).toBeVisible();
  96  |       await expect(vatSection.locator('button:has-text("查询")')).toBeVisible();
  97  |     });
  98  | 
  99  |     test('按月份查询增值税报表', async ({ page }) => {
  100 |       const vatSection = page.locator('.vat-report-section');
  101 |       await vatSection.locator('text=按月份').click();
  102 |       await page.waitForTimeout(500);
  103 | 
  104 |       // 选择年份
  105 |       const yearFormItem = vatSection.locator('.el-form-item:has-text("年份")');
  106 |       await yearFormItem.locator('.el-select').click();
  107 |       await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
  108 |       const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
  109 |       if (await yearOptions.count() > 0) {
  110 |         await yearOptions.first().click();
  111 |       }
  112 | 
  113 |       // 选择月份
  114 |       const monthFormItem = vatSection.locator('.el-form-item:has-text("月份")');
  115 |       await monthFormItem.locator('.el-select').click();
  116 |       await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
  117 |       const monthOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
  118 |       if (await monthOptions.count() > 0) {
  119 |         await monthOptions.first().click();
  120 |       }
  121 | 
  122 |       // 点击查询
  123 |       await vatSection.locator('button:has-text("查询")').click();
  124 |       await page.waitForTimeout(2000);
  125 | 
  126 |       // 验证报表卡片或空状态存在
  127 |       const reportCard = vatSection.locator('.report-card');
  128 |       const emptyState = vatSection.locator('.el-empty');
  129 |       const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
  130 |       expect(hasContent).toBeTruthy();
  131 |     });
  132 | 
  133 |     test('报表内容区域正确展示', async ({ page }) => {
  134 |       const vatSection = page.locator('.vat-report-section');
  135 | 
  136 |       // 选择年份
  137 |       const yearFormItem = vatSection.locator('.el-form-item:has-text("年份")');
```