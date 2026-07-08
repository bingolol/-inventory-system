# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: financial-reports.spec.js >> 财务报表 >> 页面加载 >> 所有标签页正确显示
- Location: tests\e2e\financial-reports.spec.js:20:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.el-tabs__item:has-text("财务汇总")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.el-tabs__item:has-text("财务汇总")')

```

```yaml
- complementary:
  - text: 进销存 巧游电子科技 一般纳税人
  - combobox
  - text: 巧游电子科技
  - img
  - text: ＋ ✎ −
  - navigation: ◉ 仪表盘 基础数据 ◻ 伙伴管理 ◻ 库存商品 业务处理 ◉ 销售开单 ◻ 采购入库 ◻ 发票录入 ◻ 资金流水 财务核算 ◉ 财务总览 ◻ 费用管理 ◻ 固定资产 ◻ 银行账户 ◻ 银行对账 ◻ 往来管理 财务报表 ◉ 资产负债表/利润表 ◉ 现金流量表 ◻ 会计账簿 ◻ 会计规则指引 期末处理 ◉ 期末税务 系统管理 ◻ 操作日志 ◻ 数据备份
- heading "财务报表" [level=2]
- text: 资产负债表 · 利润表 · 期初余额
- button "A admin":
  - text: A admin
  - img
- text: 2026/07/07周二
- main:
  - text: 财务报表 月结期间
  - img
  - combobox: 2026-07
  - button "执行月结"
  - tablist:
    - tab "资产负债表"
    - tab "利润表" [selected]
    - tab "期初余额"
    - tab "小企业会计准则报表"
  - tabpanel "利润表":
    - img
    - combobox "开始日期": 2026-01-01
    - text: 至
    - img
    - combobox "结束日期": 2026-07-07
    - button "查询"
    - text: 利润表 2026-1-1 ~ 2026-7-7 净利润 21,802.68 营业收入 31,887.14 本月已完成的销售订单金额合计 营业成本 0.00 已售商品的成本合计 毛利润 31,887.14 营业收入 − 营业成本 = 毛利润 费用明细 销售费用 0.00 管理费用 8,812.85 财务费用 148.17 费用合计 9,008.24 毛利润 − 费用合计 = 营业利润 31,887.14 − 9,008.24 =
    - strong: 22,878.90
    - text: 营业利润 + 营业外收入 − 营业外支出 = 利润总额 22,878.90 + 71.29 − 0.00 =
    - strong: 22,950.19
    - text: 利润总额 − 所得税费用 = 净利润 22,950.19 − 1,147.51 =
    - strong: 21,802.68
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('财务报表', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/financial-reports');
  6   |     await page.waitForSelector('.el-tabs__item', { timeout: 10000 });
  7   |   });
  8   | 
  9   |   // ========== 页面加载 ==========
  10  |   test.describe('页面加载', () => {
  11  |     test('页面标题正确显示', async ({ page }) => {
  12  |       await expect(page.locator('.page-title')).toContainText('财务报表');
  13  |     });
  14  | 
  15  |     test('默认选中资产负债表标签页', async ({ page }) => {
  16  |       const activeTab = page.locator('.el-tabs__item.is-active');
  17  |       await expect(activeTab).toContainText('资产负债表');
  18  |     });
  19  | 
  20  |     test('所有标签页正确显示', async ({ page }) => {
  21  |       await expect(page.locator('.el-tabs__item:has-text("资产负债表")')).toBeVisible();
  22  |       await expect(page.locator('.el-tabs__item:has-text("利润表")')).toBeVisible();
> 23  |       await expect(page.locator('.el-tabs__item:has-text("财务汇总")')).toBeVisible();
      |                                                                     ^ Error: expect(locator).toBeVisible() failed
  24  |       await expect(page.locator('.el-tabs__item:has-text("期初余额")')).toBeVisible();
  25  |       await expect(page.locator('.el-tabs__item:has-text("固定资产")')).toBeVisible();
  26  |     });
  27  |   });
  28  | 
  29  |   // ========== 资产负债表 ==========
  30  |   test.describe('资产负债表', () => {
  31  |     test('资产负债表内容区域可见', async ({ page }) => {
  32  |       // 默认激活资产负债表
  33  |       const activeTab = page.locator('.el-tabs__item.is-active');
  34  |       await expect(activeTab).toContainText('资产负债表');
  35  | 
  36  |       // 等待内容加载
  37  |       await page.waitForTimeout(1500);
  38  |     });
  39  |   });
  40  | 
  41  |   // ========== 利润表 ==========
  42  |   test.describe('利润表', () => {
  43  |     test('切换到利润表标签页', async ({ page }) => {
  44  |       await page.locator('.el-tabs__item:has-text("利润表")').click();
  45  |       await page.waitForTimeout(500);
  46  | 
  47  |       const activeTab = page.locator('.el-tabs__item.is-active');
  48  |       await expect(activeTab).toContainText('利润表');
  49  | 
  50  |       await page.waitForTimeout(1500);
  51  |     });
  52  |   });
  53  | 
  54  |   // ========== 财务汇总 ==========
  55  |   test.describe('财务汇总', () => {
  56  |     test('切换到财务汇总标签页', async ({ page }) => {
  57  |       await page.locator('.el-tabs__item:has-text("财务汇总")').click();
  58  |       await page.waitForTimeout(500);
  59  | 
  60  |       const activeTab = page.locator('.el-tabs__item.is-active');
  61  |       await expect(activeTab).toContainText('财务汇总');
  62  | 
  63  |       await page.waitForTimeout(1500);
  64  |     });
  65  |   });
  66  | 
  67  |   // ========== 期初余额 ==========
  68  |   test.describe('期初余额', () => {
  69  |     test('切换到期初余额标签页', async ({ page }) => {
  70  |       await page.locator('.el-tabs__item:has-text("期初余额")').click();
  71  |       await page.waitForTimeout(500);
  72  | 
  73  |       const activeTab = page.locator('.el-tabs__item.is-active');
  74  |       await expect(activeTab).toContainText('期初余额');
  75  | 
  76  |       await page.waitForTimeout(1500);
  77  |     });
  78  |   });
  79  | 
  80  |   // ========== 固定资产 ==========
  81  |   test.describe('固定资产', () => {
  82  |     test('切换到固定资产标签页', async ({ page }) => {
  83  |       await page.locator('.el-tabs__item:has-text("固定资产")').click();
  84  |       await page.waitForTimeout(500);
  85  | 
  86  |       const activeTab = page.locator('.el-tabs__item.is-active');
  87  |       await expect(activeTab).toContainText('固定资产');
  88  | 
  89  |       await page.waitForTimeout(1500);
  90  |     });
  91  |   });
  92  | 
  93  |   // ========== 标签页切换 ==========
  94  |   test.describe('标签页切换', () => {
  95  |     test('在不同标签页之间切换', async ({ page }) => {
  96  |       // 从资产负债表切换到利润表
  97  |       await page.locator('.el-tabs__item:has-text("利润表")').click();
  98  |       await page.waitForTimeout(500);
  99  |       await expect(page.locator('.el-tabs__item.is-active')).toContainText('利润表');
  100 | 
  101 |       // 切换到财务汇总
  102 |       await page.locator('.el-tabs__item:has-text("财务汇总")').click();
  103 |       await page.waitForTimeout(500);
  104 |       await expect(page.locator('.el-tabs__item.is-active')).toContainText('财务汇总');
  105 | 
  106 |       // 切回资产负债表
  107 |       await page.locator('.el-tabs__item:has-text("资产负债表")').click();
  108 |       await page.waitForTimeout(500);
  109 |       await expect(page.locator('.el-tabs__item.is-active')).toContainText('资产负债表');
  110 |     });
  111 |   });
  112 | });
  113 | 
```