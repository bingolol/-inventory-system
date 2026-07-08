# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: reconciliations.spec.js >> 对账管理 >> 明细抽屉 >> 明细抽屉包含对账明细表格
- Location: tests\e2e\reconciliations.spec.js:149:5

# Error details

```
TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('.filter-card') to be visible

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
        - heading "往来管理" [level=2] [ref=e99]
        - generic [ref=e100]: 对账汇总 · 账龄分析
      - generic [ref=e101]:
        - button "A admin" [ref=e103] [cursor=pointer]:
          - generic [ref=e104]: A
          - generic [ref=e105]: admin
          - img [ref=e107]
        - text: 2026/07/07周二
    - main [ref=e109]:
      - generic [ref=e111]:
        - generic [ref=e113]:
          - generic [ref=e114]: 往来管理
          - radiogroup "radio-group" [ref=e116]:
            - generic [ref=e117] [cursor=pointer]:
              - radio "客户" [checked] [ref=e119]
              - generic [ref=e121]: 客户
            - generic [ref=e122] [cursor=pointer]:
              - radio "供应商" [ref=e124]
              - generic [ref=e126]: 供应商
        - generic [ref=e128]:
          - tablist [ref=e132]:
            - tab "对账汇总" [selected] [ref=e134]
            - tab "账龄分析" [ref=e135]
          - tabpanel "对账汇总" [ref=e137]:
            - generic [ref=e138]:
              - generic [ref=e140]:
                - img [ref=e143]
                - combobox "开始日期" [ref=e145]: 2026-07-01
              - generic [ref=e147]:
                - img [ref=e150]
                - combobox "结束日期" [ref=e152]: 2026-07-07
              - button "查询对账" [ref=e153] [cursor=pointer]:
                - generic [ref=e154]: 查询对账
            - generic [ref=e155]:
              - generic [ref=e156]:
                - generic [ref=e157]: 对方数量
                - text: "0"
              - generic [ref=e158]:
                - generic [ref=e159]: 期初欠款
                - text: "0.00"
              - generic [ref=e160]:
                - generic [ref=e161]: 本期发生
                - text: "0.00"
              - generic [ref=e162]:
                - generic [ref=e163]: 已收/已付
                - text: "0.00"
              - generic [ref=e164]:
                - generic [ref=e165]: 期末欠款
                - text: "0.00"
              - generic [ref=e166]:
                - generic [ref=e167]: 发票金额
                - text: "0.00"
            - generic [ref=e168]:
              - img [ref=e170]
              - paragraph [ref=e187]: 暂无数据
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('对账管理', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/reconciliations');
  6   |     await page.waitForTimeout(800);
> 7   |     await page.waitForSelector('.filter-card', { timeout: 10000 });
      |                ^ TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
  8   |   });
  9   | 
  10  |   // ========== 页面加载 ==========
  11  |   test.describe('页面加载', () => {
  12  |     test('筛选区域正确显示', async ({ page }) => {
  13  |       await expect(page.locator('.filter-card')).toBeVisible();
  14  |       await expect(page.locator('text=对账类型')).toBeVisible();
  15  |       await expect(page.locator('text=开始日期')).toBeVisible();
  16  |       await expect(page.locator('text=结束日期')).toBeVisible();
  17  |     });
  18  | 
  19  |     test('默认选中供应商对账', async ({ page }) => {
  20  |       const supplierRadio = page.locator('.el-radio-button:has-text("供应商对账")');
  21  |       await expect(supplierRadio).toHaveClass(/is-active/);
  22  |     });
  23  | 
  24  |     test('默认日期范围为当月', async ({ page }) => {
  25  |       const now = new Date();
  26  |       const year = now.getFullYear();
  27  |       const month = String(now.getMonth() + 1).padStart(2, '0');
  28  | 
  29  |       const startInput = page.locator('.filter-card input[placeholder="开始日期"]');
  30  |       const endInput = page.locator('.filter-card input[placeholder="结束日期"]');
  31  | 
  32  |       await expect(startInput).toHaveValue(`${year}-${month}-01`);
  33  |       await expect(endInput).toHaveValue(new RegExp(`${year}-${month}-\\d{2}`));
  34  |     });
  35  | 
  36  |     test('查询按钮可见', async ({ page }) => {
  37  |       await expect(page.locator('button:has-text("查询对账")')).toBeVisible();
  38  |     });
  39  |   });
  40  | 
  41  |   // ========== 筛选功能 ==========
  42  |   test.describe('筛选功能', () => {
  43  |     test('切换到客户对账', async ({ page }) => {
  44  |       await page.locator('.el-radio-button:has-text("客户对账")').click();
  45  |       await page.waitForTimeout(500);
  46  | 
  47  |       const customerRadio = page.locator('.el-radio-button:has-text("客户对账")');
  48  |       await expect(customerRadio).toHaveClass(/is-active/);
  49  |     });
  50  | 
  51  |     test('查询对账数据', async ({ page }) => {
  52  |       await page.locator('button:has-text("查询对账")').click();
  53  |       await page.waitForTimeout(2000);
  54  | 
  55  |       const summaryRow = page.locator('.summary-row');
  56  |       const emptyState = page.locator('.el-empty');
  57  |       const hasContent = await summaryRow.isVisible().catch(() => false);
  58  |       const isEmpty = await emptyState.isVisible().catch(() => false);
  59  | 
  60  |       expect(hasContent || isEmpty).toBeTruthy();
  61  |     });
  62  | 
  63  |     test('未选择日期查询时显示警告', async ({ page }) => {
  64  |       const startInput = page.locator('.filter-card input[placeholder="开始日期"]');
  65  |       const endInput = page.locator('.filter-card input[placeholder="结束日期"]');
  66  | 
  67  |       await startInput.clear();
  68  |       await endInput.clear();
  69  | 
  70  |       await page.locator('button:has-text("查询对账")').click();
  71  |       await page.waitForTimeout(500);
  72  | 
  73  |       await expect(page.locator('.el-message--warning')).toBeVisible();
  74  |     });
  75  |   });
  76  | 
  77  |   // ========== 数据展示 ==========
  78  |   test.describe('数据展示', () => {
  79  |     test('查询后显示汇总卡片', async ({ page }) => {
  80  |       await page.locator('button:has-text("查询对账")').click();
  81  |       await page.waitForTimeout(2000);
  82  | 
  83  |       const summaryRow = page.locator('.summary-row');
  84  |       const isVisible = await summaryRow.isVisible().catch(() => false);
  85  | 
  86  |       if (isVisible) {
  87  |         await expect(page.locator('text=对方数量')).toBeVisible();
  88  |         await expect(page.locator('text=期初欠款合计')).toBeVisible();
  89  |         await expect(page.locator('text=本期发生合计')).toBeVisible();
  90  |         await expect(page.locator('text=已收/已付合计')).toBeVisible();
  91  |         await expect(page.locator('text=期末欠款合计')).toBeVisible();
  92  |         await expect(page.locator('text=发票金额合计')).toBeVisible();
  93  |       }
  94  |     });
  95  | 
  96  |     test('对账汇总表格列头正确', async ({ page }) => {
  97  |       await page.locator('button:has-text("查询对账")').click();
  98  |       await page.waitForTimeout(2000);
  99  | 
  100 |       const table = page.locator('.detail-card .el-table');
  101 |       const isVisible = await table.isVisible().catch(() => false);
  102 | 
  103 |       if (isVisible) {
  104 |         await expect(page.locator('th:has-text("对方名称")')).toBeVisible();
  105 |         await expect(page.locator('th:has-text("期初欠款")')).toBeVisible();
  106 |         await expect(page.locator('th:has-text("本期发生")')).toBeVisible();
  107 |         await expect(page.locator('th:has-text("已收/已付")')).toBeVisible();
```