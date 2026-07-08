# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: financial-reports.spec.js >> 财务报表 >> 期初余额 >> 切换到期初余额标签页
- Location: tests\e2e\financial-reports.spec.js:69:5

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: locator('.el-tabs__item.is-active')
Expected substring: "期初余额"
Error: strict mode violation: locator('.el-tabs__item.is-active') resolved to 2 elements:
    1) <div role="tab" tabindex="0" aria-selected="true" id="tab-opening-balance" aria-controls="pane-opening-balance" class="el-tabs__item is-top is-active">…</div> aka getByRole('tab', { name: '期初余额' })
    2) <div role="tab" id="tab-bs" tabindex="0" aria-selected="true" aria-controls="pane-bs" class="el-tabs__item is-top is-active">…</div> aka getByText('资产负债表（会小企01表）')

Call log:
  - Expect "toContainText" with timeout 5000ms
  - waiting for locator('.el-tabs__item.is-active')

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
            - tab "利润表" [ref=e133]
            - tab "期初余额" [active] [selected] [ref=e134] [cursor=pointer]
            - tab "小企业会计准则报表" [ref=e135]
          - tabpanel "期初余额" [ref=e137]:
            - generic [ref=e139]:
              - generic [ref=e142]: 期初余额设置
              - generic [ref=e143]:
                - generic [ref=e144]:
                  - generic [ref=e145]:
                    - generic [ref=e146]: 期初日期
                    - generic [ref=e148]:
                      - img [ref=e151]
                      - combobox "选择日期" [ref=e153]: 2026-07-07
                  - generic [ref=e154]:
                    - generic [ref=e155]:
                      - generic [ref=e157]: 流动资产
                      - generic [ref=e158]:
                        - generic [ref=e159]:
                          - generic [ref=e160]: 现金余额
                          - generic [ref=e161]:
                            - button "减少数值" [ref=e162]:
                              - img [ref=e164]
                            - button "增加数值" [ref=e166] [cursor=pointer]:
                              - img [ref=e168]
                            - spinbutton [ref=e172]: "0.00"
                        - generic [ref=e173]:
                          - generic [ref=e174]: 银行存款
                          - generic [ref=e175]:
                            - button "减少数值" [ref=e176]:
                              - img [ref=e178]
                            - button "增加数值" [ref=e180] [cursor=pointer]:
                              - img [ref=e182]
                            - spinbutton [ref=e186]: "0.00"
                        - generic [ref=e187]:
                          - generic [ref=e188]: 应收账款
                          - generic [ref=e189]:
                            - button "减少数值" [ref=e190]:
                              - img [ref=e192]
                            - button "增加数值" [ref=e194] [cursor=pointer]:
                              - img [ref=e196]
                            - spinbutton [ref=e200]: "0.00"
                        - generic [ref=e201]:
                          - generic [ref=e202]: 库存价值
                          - generic [ref=e203]:
                            - button "减少数值" [ref=e204]:
                              - img [ref=e206]
                            - button "增加数值" [ref=e208] [cursor=pointer]:
                              - img [ref=e210]
                            - spinbutton [ref=e214]: "0.00"
                    - generic [ref=e215]:
                      - generic [ref=e217]: 非流动资产
                      - generic [ref=e218]:
                        - generic [ref=e219]:
                          - generic [ref=e220]: 固定资产原值
                          - generic [ref=e221]:
                            - button "减少数值" [ref=e222]:
                              - img [ref=e224]
                            - button "增加数值" [ref=e226] [cursor=pointer]:
                              - img [ref=e228]
                            - spinbutton [ref=e232]: "0.00"
                        - generic [ref=e233]:
                          - generic [ref=e234]: 累计折旧
                          - generic [ref=e235]:
                            - button "减少数值" [ref=e236]:
                              - img [ref=e238]
                            - button "增加数值" [ref=e240] [cursor=pointer]:
                              - img [ref=e242]
                            - spinbutton [ref=e246]: "0.00"
                        - generic [ref=e247]:
                          - generic [ref=e248]: 无形资产原值
                          - generic [ref=e249]:
                            - button "减少数值" [ref=e250]:
                              - img [ref=e252]
                            - button "增加数值" [ref=e254] [cursor=pointer]:
                              - img [ref=e256]
                            - spinbutton [ref=e260]: "0.00"
                        - generic [ref=e261]:
                          - generic [ref=e262]: 累计摊销
                          - generic [ref=e263]:
                            - button "减少数值" [ref=e264]:
                              - img [ref=e266]
                            - button "增加数值" [ref=e268] [cursor=pointer]:
                              - img [ref=e270]
                            - spinbutton [ref=e274]: "0.00"
                    - generic [ref=e275]:
                      - generic [ref=e277]: 流动负债
                      - generic [ref=e278]:
                        - generic [ref=e279]:
                          - generic [ref=e280]: 应付账款
                          - generic [ref=e281]:
                            - button "减少数值" [ref=e282]:
                              - img [ref=e284]
                            - button "增加数值" [ref=e286] [cursor=pointer]:
                              - img [ref=e288]
                            - spinbutton [ref=e292]: "0.00"
                        - generic [ref=e293]:
                          - generic [ref=e294]: 应交税费
                          - generic [ref=e295]:
                            - button "减少数值" [ref=e296]:
                              - img [ref=e298]
                            - button "增加数值" [ref=e300] [cursor=pointer]:
                              - img [ref=e302]
                            - spinbutton [ref=e306]: "0.00"
                    - generic [ref=e307]:
                      - generic [ref=e309]: 非流动负债
                      - generic [ref=e311]:
                        - generic [ref=e312]: 长期借款
                        - generic [ref=e313]:
                          - button "减少数值" [ref=e314]:
                            - img [ref=e316]
                          - button "增加数值" [ref=e318] [cursor=pointer]:
                            - img [ref=e320]
                          - spinbutton [ref=e324]: "0.00"
                    - generic [ref=e325]:
                      - generic [ref=e327]: 权益
                      - generic [ref=e328]:
                        - generic [ref=e329]:
                          - generic [ref=e330]: 实收资本
                          - generic [ref=e331]:
                            - button "减少数值" [ref=e332]:
                              - img [ref=e334]
                            - button "增加数值" [ref=e336] [cursor=pointer]:
                              - img [ref=e338]
                            - spinbutton [ref=e342]: "0.00"
                        - generic [ref=e343]:
                          - generic [ref=e344]: 未分配利润
                          - generic [ref=e345]:
                            - button "减少数值" [ref=e346]:
                              - img [ref=e348]
                            - button "增加数值" [ref=e350] [cursor=pointer]:
                              - img [ref=e352]
                            - spinbutton [ref=e356]: "0.00"
                  - generic [ref=e357]:
                    - generic [ref=e358]:
                      - generic [ref=e359]: ✓
                      - generic [ref=e360]: 资产负债平衡
                    - generic [ref=e361]:
                      - generic [ref=e362]: 资产 0.00
                      - generic [ref=e363]: =
                      - generic [ref=e364]: 负债 0.00
                      - generic [ref=e365]: +
                      - generic [ref=e366]: 权益 0.00
                  - generic [ref=e367]:
                    - button "保存期初" [ref=e368] [cursor=pointer]:
                      - generic [ref=e369]: 保存期初
                    - button "重置" [ref=e370] [cursor=pointer]:
                      - generic [ref=e371]: 重置
                - generic [ref=e372]:
                  - generic [ref=e373]: 历史记录
                  - generic [ref=e375]:
                    - table [ref=e377]:
                      - rowgroup [ref=e384]:
                        - row "期初日期 资产 负债 权益 操作" [ref=e385]:
                          - columnheader "期初日期" [ref=e386]:
                            - generic [ref=e387]: 期初日期
                          - columnheader "资产" [ref=e388]:
                            - generic [ref=e389]: 资产
                          - columnheader "负债" [ref=e390]:
                            - generic [ref=e391]: 负债
                          - columnheader "权益" [ref=e392]:
                            - generic [ref=e393]: 权益
                          - columnheader "操作" [ref=e394]:
                            - generic [ref=e395]: 操作
                    - table [ref=e400]:
                      - rowgroup [ref=e407]:
                        - row "2025-12-31 ¥1,927.21 ¥0.00 ¥0.00 编辑 删除" [ref=e408]:
                          - cell "2025-12-31" [ref=e409]:
                            - generic [ref=e410]: 2025-12-31
                          - cell "¥1,927.21" [ref=e411]:
                            - generic [ref=e412]: ¥1,927.21
                          - cell "¥0.00" [ref=e413]:
                            - generic [ref=e414]: ¥0.00
                          - cell "¥0.00" [ref=e415]:
                            - generic [ref=e416]: ¥0.00
                          - cell "编辑 删除" [ref=e417]:
                            - generic [ref=e418]:
                              - button "编辑" [ref=e419] [cursor=pointer]:
                                - generic [ref=e420]: 编辑
                              - button "删除" [ref=e421] [cursor=pointer]:
                                - generic [ref=e422]: 删除
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
> 74  |       await expect(activeTab).toContainText('期初余额');
      |                               ^ Error: expect(locator).toContainText(expected) failed
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