# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: personal.spec.js >> 个人收支 >> 汇总卡片 >> 本月结余卡片显示
- Location: tests\e2e\personal.spec.js:66:5

# Error details

```
TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('.el-table__row') to be visible

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
        - heading "个人流水" [level=2] [ref=e99]
        - generic [ref=e100]: 个人账本收支记录
      - generic [ref=e101]:
        - button "A admin" [ref=e103] [cursor=pointer]:
          - generic [ref=e104]: A
          - generic [ref=e105]: admin
          - img [ref=e107]
        - text: 2026/07/07周二
    - main [ref=e109]:
      - generic [ref=e110]:
        - generic [ref=e111]:
          - generic [ref=e115]:
            - generic [ref=e116]: ¥0.00
            - generic [ref=e117]: 本月收入
          - generic [ref=e121]:
            - generic [ref=e122]: ¥0.00
            - generic [ref=e123]: 本月支出
          - generic [ref=e127]:
            - generic [ref=e128]: ¥0.00
            - generic [ref=e129]: 本月结余
        - generic [ref=e130]:
          - generic [ref=e134]:
            - generic [ref=e135]: 分类统计
            - radiogroup "radio-group" [ref=e136]:
              - generic [ref=e137]:
                - radio "支出" [checked] [ref=e138]
                - generic [ref=e139] [cursor=pointer]: 支出
              - generic [ref=e140]:
                - radio "收入" [ref=e141]
                - generic [ref=e142] [cursor=pointer]: 收入
          - generic [ref=e150]:
            - generic [ref=e151]: 月度趋势
            - radiogroup "radio-group" [ref=e152]:
              - generic [ref=e153]:
                - radio "全部" [checked] [ref=e154]
                - generic [ref=e155] [cursor=pointer]: 全部
              - generic [ref=e156]:
                - radio "支出" [ref=e157]
                - generic [ref=e158] [cursor=pointer]: 支出
              - generic [ref=e159]:
                - radio "收入" [ref=e160]
                - generic [ref=e161] [cursor=pointer]: 收入
        - generic [ref=e166]:
          - generic [ref=e168]:
            - generic [ref=e169]: 流水记录
            - button "记一笔" [ref=e170] [cursor=pointer]:
              - generic [ref=e171]:
                - img [ref=e173]
                - text: 记一笔
          - generic [ref=e175]:
            - generic [ref=e176]:
              - generic [ref=e178] [cursor=pointer]:
                - generic:
                  - combobox [ref=e180]
                  - generic [ref=e181]: 类型筛选
                - img [ref=e184]
              - generic [ref=e187] [cursor=pointer]:
                - generic:
                  - combobox [ref=e189]
                  - generic [ref=e190]: 分类筛选
                - img [ref=e193]
              - generic [ref=e195]:
                - img [ref=e197]
                - combobox "开始日期" [ref=e199]
                - generic [ref=e200]: 至
                - combobox "结束日期" [ref=e201]
              - button "查询" [ref=e202] [cursor=pointer]:
                - generic [ref=e203]: 查询
            - generic [ref=e205]:
              - table [ref=e207]:
                - rowgroup [ref=e216]:
                  - row "日期 类型 分类 金额 备注 附件 操作" [ref=e217]:
                    - columnheader "日期" [ref=e218]:
                      - generic [ref=e219]: 日期
                    - columnheader "类型" [ref=e220]:
                      - generic [ref=e221]: 类型
                    - columnheader "分类" [ref=e222]:
                      - generic [ref=e223]: 分类
                    - columnheader "金额" [ref=e224]:
                      - generic [ref=e225]: 金额
                    - columnheader "备注" [ref=e226]:
                      - generic [ref=e227]: 备注
                    - columnheader "附件" [ref=e228]:
                      - generic [ref=e229]: 附件
                    - columnheader "操作" [ref=e230]:
                      - generic [ref=e231]: 操作
              - generic [ref=e235]:
                - table:
                  - rowgroup
                - generic [ref=e237]: 暂无数据
            - generic [ref=e238]:
              - generic [ref=e239]:
                - generic [ref=e240]: 筛选合计：
                - generic [ref=e241]: 收入 ¥0.00
                - generic [ref=e242]: 支出 ¥0.00
                - generic [ref=e243]: 结余 ¥0.00
              - generic [ref=e244]:
                - generic [ref=e245]: 共 0 条
                - generic [ref=e248] [cursor=pointer]:
                  - generic:
                    - combobox [ref=e250]
                    - generic [ref=e251]: 20条/页
                  - img [ref=e254]
                - button "上一页" [disabled] [ref=e256]:
                  - generic:
                    - img
                - list [ref=e257]:
                  - listitem "第 1 页" [ref=e258]: "1"
                - button "下一页" [disabled] [ref=e259]:
                  - generic:
                    - img
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('个人收支', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/personal');
  6   |     await page.waitForTimeout(800);
> 7   |     await page.waitForSelector('.el-table__row', { timeout: 10000 });
      |                ^ TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
  8   |   });
  9   | 
  10  |   // ========== 列表展示 ==========
  11  |   test.describe('列表展示', () => {
  12  |     test('收支列表正确展示后端数据', async ({ page }) => {
  13  |       const rows = await page.locator('.el-table__row').count();
  14  |       expect(rows).toBeGreaterThan(0);
  15  | 
  16  |       await expect(page.locator('th:has-text("日期")')).toBeVisible();
  17  |       await expect(page.locator('th:has-text("类型")')).toBeVisible();
  18  |       await expect(page.locator('th:has-text("分类")')).toBeVisible();
  19  |       await expect(page.locator('th:has-text("金额")')).toBeVisible();
  20  |       await expect(page.locator('th:has-text("备注")')).toBeVisible();
  21  |       await expect(page.locator('th:has-text("操作")')).toBeVisible();
  22  |     });
  23  | 
  24  |     test('第一行数据包含有效内容', async ({ page }) => {
  25  |       const firstRow = page.locator('.el-table__row:first-child');
  26  |       const rowText = await firstRow.textContent();
  27  |       expect(rowText?.trim().length).toBeGreaterThan(5);
  28  |     });
  29  | 
  30  |     test('金额显示包含货币符号', async ({ page }) => {
  31  |       const firstRow = page.locator('.el-table__row:first-child');
  32  |       const amountCell = firstRow.locator('td').nth(3);
  33  |       const amountText = await amountCell.textContent();
  34  |       expect(amountText?.trim()).toMatch(/^[+-]¥[\d,.]+$/);
  35  |     });
  36  | 
  37  |     test('日期格式正确', async ({ page }) => {
  38  |       const firstRow = page.locator('.el-table__row:first-child');
  39  |       const dateCell = firstRow.locator('td').nth(0);
  40  |       const dateText = await dateCell.textContent();
  41  |       expect(dateText?.trim()).toMatch(/^\d{4}-\d{2}-\d{2}/);
  42  |     });
  43  | 
  44  |     test('类型标签显示正确', async ({ page }) => {
  45  |       const firstRow = page.locator('.el-table__row:first-child');
  46  |       const typeCell = firstRow.locator('td').nth(1);
  47  |       const typeText = await typeCell.textContent();
  48  |       expect(typeText?.trim()).toMatch(/^(收入|支出)$/);
  49  |     });
  50  |   });
  51  | 
  52  |   // ========== 汇总卡片 ==========
  53  |   test.describe('汇总卡片', () => {
  54  |     test('本月收入卡片显示', async ({ page }) => {
  55  |       const incomeCard = page.locator('.el-card:has-text("本月收入")');
  56  |       await expect(incomeCard).toBeVisible();
  57  |       await expect(incomeCard).toContainText('¥');
  58  |     });
  59  | 
  60  |     test('本月支出卡片显示', async ({ page }) => {
  61  |       const expenseCard = page.locator('.el-card:has-text("本月支出")');
  62  |       await expect(expenseCard).toBeVisible();
  63  |       await expect(expenseCard).toContainText('¥');
  64  |     });
  65  | 
  66  |     test('本月结余卡片显示', async ({ page }) => {
  67  |       const balanceCard = page.locator('.el-card:has-text("本月结余")');
  68  |       await expect(balanceCard).toBeVisible();
  69  |       await expect(balanceCard).toContainText('¥');
  70  |     });
  71  |   });
  72  | 
  73  |   // ========== 筛选功能 ==========
  74  |   test.describe('筛选功能', () => {
  75  |     test('按类型筛选收支', async ({ page }) => {
  76  |       const allCount = await page.locator('.el-table__row').count();
  77  | 
  78  |       const typeSelect = page.locator('.el-select:has-text("类型筛选")');
  79  |       await typeSelect.click();
  80  |       await page.waitForTimeout(500);
  81  | 
  82  |       // 使用 .last() 避免 strict mode 冲突
  83  |       await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: '收入' }).click();
  84  |       await page.waitForTimeout(1000);
  85  | 
  86  |       const filteredCount = await page.locator('.el-table__row').count();
  87  |       expect(filteredCount).toBeGreaterThanOrEqual(0);
  88  |       expect(filteredCount).toBeLessThanOrEqual(allCount);
  89  |     });
  90  | 
  91  |     test('按分类筛选收支', async ({ page }) => {
  92  |       const allCount = await page.locator('.el-table__row').count();
  93  | 
  94  |       const categorySelect = page.locator('.el-select:has-text("分类筛选")');
  95  |       await categorySelect.click();
  96  |       await page.waitForTimeout(500);
  97  | 
  98  |       const dropdown = page.locator('.el-select-dropdown:visible').last();
  99  |       const options = dropdown.locator('li');
  100 |       const optionCount = await options.count();
  101 | 
  102 |       if (optionCount > 0) {
  103 |         await options.first().click();
  104 |         await page.waitForTimeout(1000);
  105 | 
  106 |         const filteredCount = await page.locator('.el-table__row').count();
  107 |         expect(filteredCount).toBeGreaterThanOrEqual(0);
```