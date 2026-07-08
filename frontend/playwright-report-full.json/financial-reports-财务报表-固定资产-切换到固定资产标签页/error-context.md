# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: financial-reports.spec.js >> 财务报表 >> 固定资产 >> 切换到固定资产标签页
- Location: tests\e2e\financial-reports.spec.js:82:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: locator.click: Test timeout of 60000ms exceeded.
Call log:
  - waiting for locator('.el-tabs__item:has-text("固定资产")')

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
        - heading "财务报表" [level=2] [ref=e99]
        - generic [ref=e100]: 资产负债表 · 利润表 · 期初余额
      - generic [ref=e101]:
        - button "A admin" [ref=e103] [cursor=pointer]:
          - generic [ref=e104]: A
          - generic [ref=e105]: admin
          - img [ref=e107]
        - text: 2026/07/07周二
    - main [ref=e109]:
      - generic [ref=e111]:
        - generic [ref=e113]:
          - generic [ref=e114]: 财务报表
          - generic [ref=e115]:
            - text: 月结期间
            - generic [ref=e117]:
              - img [ref=e120]
              - combobox [ref=e122]: 2026-07
            - button "执行月结" [ref=e123] [cursor=pointer]:
              - generic [ref=e124]: 执行月结
        - generic [ref=e126]:
          - tablist [ref=e130]:
            - tab "资产负债表" [ref=e132]
            - tab "利润表" [selected] [ref=e133]
            - tab "期初余额" [ref=e134]
            - tab "小企业会计准则报表" [ref=e135]
          - tabpanel "利润表" [ref=e137]:
            - generic [ref=e138]:
              - generic [ref=e139]:
                - generic [ref=e141]:
                  - img [ref=e144]
                  - combobox "开始日期" [ref=e146]: 2026-01-01
                - generic [ref=e147]: 至
                - generic [ref=e149]:
                  - img [ref=e152]
                  - combobox "结束日期" [ref=e154]: 2026-07-07
                - button "查询" [ref=e155] [cursor=pointer]:
                  - generic [ref=e156]: 查询
              - generic [ref=e157]:
                - generic [ref=e158]:
                  - generic [ref=e159]:
                    - generic [ref=e160]: 利润表
                    - generic [ref=e161]: 2026-1-1 ~ 2026-7-7
                  - generic [ref=e162]:
                    - generic [ref=e163]: 净利润
                    - generic [ref=e164]: 21,802.68
                - generic [ref=e165]:
                  - generic [ref=e166]:
                    - generic [ref=e167]: 营业收入
                    - generic [ref=e168]: 31,887.14
                    - generic [ref=e169]: 本月已完成的销售订单金额合计
                  - generic [ref=e170]:
                    - generic [ref=e171]: 营业成本
                    - generic [ref=e172]: "0.00"
                    - generic [ref=e173]: 已售商品的成本合计
                  - generic [ref=e174]:
                    - generic [ref=e175]: 毛利润
                    - generic [ref=e176]: 31,887.14
                    - generic [ref=e177]: 营业收入 − 营业成本 = 毛利润
                - generic [ref=e178]:
                  - generic [ref=e179]: 费用明细
                  - generic [ref=e180]:
                    - generic [ref=e181]:
                      - generic [ref=e182]: 销售费用
                      - generic [ref=e183]: "0.00"
                    - generic [ref=e184]:
                      - generic [ref=e185]: 管理费用
                      - generic [ref=e186]: 8,812.85
                    - generic [ref=e187]:
                      - generic [ref=e188]: 财务费用
                      - generic [ref=e189]: "148.17"
                    - generic [ref=e190]:
                      - generic [ref=e191]: 费用合计
                      - generic [ref=e192]: 9,008.24
                - generic [ref=e193]:
                  - generic [ref=e194]:
                    - generic [ref=e195]: 毛利润 − 费用合计 = 营业利润
                    - generic [ref=e196]:
                      - text: 31,887.14 − 9,008.24 =
                      - strong [ref=e197]: 22,878.90
                  - generic [ref=e198]:
                    - generic [ref=e199]: 营业利润 + 营业外收入 − 营业外支出 = 利润总额
                    - generic [ref=e200]:
                      - text: 22,878.90 + 71.29 − 0.00 =
                      - strong [ref=e201]: 22,950.19
                  - generic [ref=e202]:
                    - generic [ref=e203]: 利润总额 − 所得税费用 = 净利润
                    - generic [ref=e204]:
                      - text: 22,950.19 − 1,147.51 =
                      - strong [ref=e205]: 21,802.68
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
  23  |       await expect(page.locator('.el-tabs__item:has-text("财务汇总")')).toBeVisible();
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
> 83  |       await page.locator('.el-tabs__item:has-text("固定资产")').click();
      |                                                             ^ Error: locator.click: Test timeout of 60000ms exceeded.
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