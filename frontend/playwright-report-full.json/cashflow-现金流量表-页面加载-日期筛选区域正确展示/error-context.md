# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: cashflow.spec.js >> 现金流量表 >> 页面加载 >> 日期筛选区域正确展示
- Location: tests\e2e\cashflow.spec.js:15:5

# Error details

```
TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('.cash-flow-container') to be visible

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e6]: 进销存
      - generic [ref=e7]: 巧游电子科技
      - generic [ref=e8]: 一般纳税人
    - generic [ref=e9]:
      - generic [ref=e11] [cursor=pointer]:
        - generic:
          - combobox [ref=e13]
          - generic [ref=e14]: 巧游电子科技
        - img [ref=e17]
      - generic [ref=e19]:
        - generic "新建账本" [ref=e20] [cursor=pointer]: ＋
        - generic "重命名" [ref=e21] [cursor=pointer]: ✎
        - generic "删除" [ref=e22] [cursor=pointer]: −
    - navigation [ref=e23]:
      - generic [ref=e24] [cursor=pointer]:
        - generic [ref=e25]: ◉
        - generic [ref=e26]: 仪表盘
      - generic [ref=e27]:
        - generic [ref=e28]: 基础数据
        - generic [ref=e29] [cursor=pointer]:
          - generic [ref=e30]: ◻
          - generic [ref=e31]: 伙伴管理
        - generic [ref=e32] [cursor=pointer]:
          - generic [ref=e33]: ◻
          - generic [ref=e34]: 库存商品
      - generic [ref=e35]:
        - generic [ref=e36]: 业务处理
        - generic [ref=e37] [cursor=pointer]:
          - generic [ref=e38]: ◉
          - generic [ref=e39]: 销售开单
        - generic [ref=e40] [cursor=pointer]:
          - generic [ref=e41]: ◻
          - generic [ref=e42]: 采购入库
        - generic [ref=e43] [cursor=pointer]:
          - generic [ref=e44]: ◻
          - generic [ref=e45]: 发票录入
        - generic [ref=e46] [cursor=pointer]:
          - generic [ref=e47]: ◻
          - generic [ref=e48]: 资金流水
      - generic [ref=e49]:
        - generic [ref=e50]: 财务核算
        - generic [ref=e51] [cursor=pointer]:
          - generic [ref=e52]: ◉
          - generic [ref=e53]: 财务总览
        - generic [ref=e54] [cursor=pointer]:
          - generic [ref=e55]: ◻
          - generic [ref=e56]: 费用管理
        - generic [ref=e57] [cursor=pointer]:
          - generic [ref=e58]: ◻
          - generic [ref=e59]: 固定资产
        - generic [ref=e60] [cursor=pointer]:
          - generic [ref=e61]: ◻
          - generic [ref=e62]: 银行账户
        - generic [ref=e63] [cursor=pointer]:
          - generic [ref=e64]: ◻
          - generic [ref=e65]: 银行对账
        - generic [ref=e66] [cursor=pointer]:
          - generic [ref=e67]: ◻
          - generic [ref=e68]: 往来管理
      - generic [ref=e69]:
        - generic [ref=e70]: 财务报表
        - generic [ref=e71] [cursor=pointer]:
          - generic [ref=e72]: ◉
          - generic [ref=e73]: 资产负债表/利润表
        - generic [ref=e74] [cursor=pointer]:
          - generic [ref=e75]: ◉
          - generic [ref=e76]: 现金流量表
        - generic [ref=e77] [cursor=pointer]:
          - generic [ref=e78]: ◻
          - generic [ref=e79]: 会计账簿
        - generic [ref=e80] [cursor=pointer]:
          - generic [ref=e81]: ◻
          - generic [ref=e82]: 会计规则指引
      - generic [ref=e83]:
        - generic [ref=e84]: 期末处理
        - generic [ref=e85] [cursor=pointer]:
          - generic [ref=e86]: ◉
          - generic [ref=e87]: 期末税务
      - generic [ref=e88]:
        - generic [ref=e89]: 系统管理
        - generic [ref=e90] [cursor=pointer]:
          - generic [ref=e91]: ◻
          - generic [ref=e92]: 操作日志
        - generic [ref=e93] [cursor=pointer]:
          - generic [ref=e94]: ◻
          - generic [ref=e95]: 数据备份
  - generic [ref=e96]:
    - generic [ref=e97]:
      - generic [ref=e98]:
        - heading "现金流量表" [level=2] [ref=e99]
        - generic [ref=e100]: 经营活动 · 投资活动 · 筹资活动现金流
      - generic [ref=e101]:
        - button "A admin" [ref=e103] [cursor=pointer]:
          - generic [ref=e104]: A
          - generic [ref=e105]: admin
          - img [ref=e107]
        - text: 2026/07/07周二
    - main [ref=e109]:
      - generic [ref=e110]:
        - generic [ref=e111]:
          - generic [ref=e112]:
            - generic [ref=e113]: 现金流量表
            - button "新增流水" [ref=e114] [cursor=pointer]:
              - generic [ref=e115]: 新增流水
          - generic [ref=e116]:
            - generic [ref=e118]:
              - img [ref=e121]
              - combobox "开始日期" [ref=e123]: 2026-01-01
            - generic [ref=e124]: 至
            - generic [ref=e126]:
              - img [ref=e129]
              - combobox "结束日期" [ref=e131]: 2026-07-07
            - button "查询" [ref=e132] [cursor=pointer]:
              - generic [ref=e133]: 查询
        - generic [ref=e134]:
          - generic [ref=e136]:
            - generic [ref=e137]: 经营
            - generic [ref=e138]:
              - generic [ref=e139]: 流入
              - generic [ref=e140]: 33,237.83
            - generic [ref=e141]:
              - generic [ref=e142]: 流出
              - generic [ref=e143]: "150.00"
            - generic [ref=e144]:
              - generic [ref=e145]: 净额
              - generic [ref=e146]: 33,087.83
          - generic [ref=e148]:
            - generic [ref=e149]: 投资
            - generic [ref=e150]:
              - generic [ref=e151]: 流入
              - generic [ref=e152]: "0.00"
            - generic [ref=e153]:
              - generic [ref=e154]: 流出
              - generic [ref=e155]: "0.00"
            - generic [ref=e156]:
              - generic [ref=e157]: 净额
              - generic [ref=e158]: "0.00"
          - generic [ref=e160]:
            - generic [ref=e161]: 筹资
            - generic [ref=e162]:
              - generic [ref=e163]: 流入
              - generic [ref=e164]: "0.00"
            - generic [ref=e165]:
              - generic [ref=e166]: 流出
              - generic [ref=e167]: "0.00"
            - generic [ref=e168]:
              - generic [ref=e169]: 净额
              - generic [ref=e170]: "0.00"
        - table [ref=e172]:
          - row "项目 金额" [ref=e173]:
            - columnheader "项目" [ref=e174]
            - columnheader "金额" [ref=e175]
          - row "净现金流量 33,087.83" [ref=e176]:
            - cell "净现金流量" [ref=e177]
            - cell "33,087.83" [ref=e178]
          - row "期初余额 1,927.21" [ref=e179]:
            - cell "期初余额" [ref=e180]
            - cell "1,927.21" [ref=e181]
          - row "期末余额 35,015.04" [ref=e182]:
            - cell "期末余额" [ref=e183]
            - cell "35,015.04" [ref=e184]
        - generic [ref=e185]:
          - generic [ref=e187]: 现金流水
          - generic [ref=e188]: 暂无流水记录
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('现金流量表', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/cash-flows');
> 6   |     await page.waitForSelector('.cash-flow-container', { timeout: 10000 });
      |                ^ TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
  7   |   });
  8   | 
  9   |   // ========== 页面加载 ==========
  10  |   test.describe('页面加载', () => {
  11  |     test('页面标题正确显示', async ({ page }) => {
  12  |       await expect(page.locator('.cash-flow-container')).toContainText('现金流量表');
  13  |     });
  14  | 
  15  |     test('日期筛选区域正确展示', async ({ page }) => {
  16  |       await expect(page.locator('.cash-flow-container .el-form-item:has-text("开始日期")')).toBeVisible();
  17  |       await expect(page.locator('.cash-flow-container .el-form-item:has-text("结束日期")')).toBeVisible();
  18  |       await expect(page.locator('.cash-flow-container .query-form button:has-text("查询")')).toBeVisible();
  19  |       await expect(page.locator('.cash-flow-container .query-form button:has-text("新增现金流水")')).toBeVisible();
  20  |     });
  21  |   });
  22  | 
  23  |   // ========== 现金流量表展示 ==========
  24  |   test.describe('现金流量表展示', () => {
  25  |     test('经营活动区域正确展示', async ({ page }) => {
  26  |       const reportCard = page.locator('.cash-flow-container .report-card');
  27  |       if (await reportCard.count() === 0) return;
  28  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '一、经营活动产生的现金流量' })).toBeVisible();
  29  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '一、经营活动产生的现金流量' }).locator('.el-statistic').filter({ hasText: '现金流入' })).toBeVisible();
  30  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '一、经营活动产生的现金流量' }).locator('.el-statistic').filter({ hasText: '现金流出' })).toBeVisible();
  31  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '一、经营活动产生的现金流量' }).locator('.el-statistic').filter({ hasText: '经营活动净现金流' })).toBeVisible();
  32  |     });
  33  | 
  34  |     test('投资活动区域正确展示', async ({ page }) => {
  35  |       const reportCard = page.locator('.cash-flow-container .report-card');
  36  |       if (await reportCard.count() === 0) return;
  37  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '二、投资活动产生的现金流量' })).toBeVisible();
  38  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '二、投资活动产生的现金流量' }).locator('.el-statistic').filter({ hasText: '投资活动净现金流' })).toBeVisible();
  39  |     });
  40  | 
  41  |     test('筹资活动区域正确展示', async ({ page }) => {
  42  |       const reportCard = page.locator('.cash-flow-container .report-card');
  43  |       if (await reportCard.count() === 0) return;
  44  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '三、筹资活动产生的现金流量' })).toBeVisible();
  45  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '三、筹资活动产生的现金流量' }).locator('.el-statistic').filter({ hasText: '筹资活动净现金流' })).toBeVisible();
  46  |     });
  47  | 
  48  |     test('汇总区域正确展示', async ({ page }) => {
  49  |       const reportCard = page.locator('.cash-flow-container .report-card');
  50  |       if (await reportCard.count() === 0) return;
  51  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '四、现金及现金等价物净增加额' })).toBeVisible();
  52  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '四、现金及现金等价物净增加额' }).locator('.el-statistic').filter({ hasText: '净现金流量' })).toBeVisible();
  53  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '四、现金及现金等价物净增加额' }).locator('.el-statistic').filter({ hasText: '期初现金余额' })).toBeVisible();
  54  |       await expect(reportCard.locator('.flow-section').filter({ hasText: '四、现金及现金等价物净增加额' }).locator('.el-statistic').filter({ hasText: '期末现金余额' })).toBeVisible();
  55  |     });
  56  |   });
  57  | 
  58  |   // ========== 日期筛选功能 ==========
  59  |   test.describe('日期筛选功能', () => {
  60  |     test('修改开始日期后查询', async ({ page }) => {
  61  |       // 点击开始日期输入框打开日期选择器
  62  |       const startDateInput = page.locator('.cash-flow-container .el-form-item:has-text("开始日期")').locator('.el-date-editor input');
  63  |       await startDateInput.click();
  64  |       await page.waitForTimeout(500);
  65  |       await page.keyboard.press('Escape');
  66  |       await page.waitForTimeout(300);
  67  | 
  68  |       // 等待 loading 消失后点击查询
  69  |       const queryBtn = page.locator('.cash-flow-container .query-form button:has-text("查询")');
  70  |       await queryBtn.click();
  71  |       // 等待请求完成（loading 指示器消失）
  72  |       await page.waitForTimeout(3000);
  73  | 
  74  |       // 查询后页面仍正常显示（report-card 可能存在也可能不存在，取决于数据）
  75  |       await expect(page.locator('.cash-flow-container .transaction-card')).toBeVisible();
  76  |     });
  77  | 
  78  |     test('修改结束日期后查询', async ({ page }) => {
  79  |       // 点击结束日期输入框打开日期选择器
  80  |       const endDateInput = page.locator('.cash-flow-container .el-form-item:has-text("结束日期")').locator('.el-date-editor input');
  81  |       await endDateInput.click();
  82  |       await page.waitForTimeout(500);
  83  |       await page.keyboard.press('Escape');
  84  |       await page.waitForTimeout(300);
  85  | 
  86  |       // 等待 loading 消失后点击查询
  87  |       const queryBtn = page.locator('.cash-flow-container .query-form button:has-text("查询")');
  88  |       await queryBtn.click();
  89  |       await page.waitForTimeout(3000);
  90  | 
  91  |       // 查询后页面仍正常显示
  92  |       await expect(page.locator('.cash-flow-container .transaction-card')).toBeVisible();
  93  |     });
  94  | 
  95  |     test('默认日期范围为当年', async ({ page }) => {
  96  |       const startDateInput = page.locator('.cash-flow-container .el-form-item:has-text("开始日期")').locator('.el-date-editor input');
  97  |       const endDateInput = page.locator('.cash-flow-container .el-form-item:has-text("结束日期")').locator('.el-date-editor input');
  98  | 
  99  |       const startValue = await startDateInput.inputValue();
  100 |       const endValue = await endDateInput.inputValue();
  101 | 
  102 |       // 验证日期格式为 YYYY-MM-DD（由于时区差异，年初日期可能偏移到上一年末）
  103 |       expect(startValue).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  104 |       expect(endValue).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  105 |       // 结束日期应为今天（UTC 格式）
  106 |       const today = new Date().toISOString().split('T')[0];
```