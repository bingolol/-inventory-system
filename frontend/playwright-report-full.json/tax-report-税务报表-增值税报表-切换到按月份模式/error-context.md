# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tax-report.spec.js >> 税务报表 >> 增值税报表 >> 切换到按月份模式
- Location: tests\e2e\tax-report.spec.js:79:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: locator.click: Test timeout of 60000ms exceeded.
Call log:
  - waiting for locator('.vat-report-section').locator('text=按月份')

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
        - heading "期末税务" [level=2] [ref=e99]
        - generic [ref=e100]: 税务报表 · 期末处理
      - generic [ref=e101]:
        - button "A admin" [ref=e103] [cursor=pointer]:
          - generic [ref=e104]: A
          - generic [ref=e105]: admin
          - img [ref=e107]
        - text: 2026/07/07周二
    - main [ref=e109]:
      - generic [ref=e110]:
        - generic [ref=e113]: 期末税务
        - generic [ref=e115]:
          - tablist [ref=e119]:
            - tab "税务报表" [selected] [ref=e121]
            - tab "附加税申报" [ref=e122]
            - tab "期末处理" [ref=e123]
          - tabpanel "税务报表" [ref=e125]:
            - generic [ref=e127]:
              - generic [ref=e129]:
                - generic [ref=e130]: 税务报表
                - button "税务核对" [ref=e131] [cursor=pointer]:
                  - generic [ref=e132]: 税务核对
              - generic [ref=e133]:
                - generic [ref=e134]:
                  - generic [ref=e135]: "?"
                  - generic [ref=e136]:
                    - generic [ref=e137]: 增值税是你替税务局代收的钱（销项-进项），不是你自己的费用。企业所得税才是你赚了钱要缴的税（利润×税率）。两条线完全不同，别搞混。
                    - link "查看增值税和企业所得税详解 →" [ref=e138] [cursor=pointer]:
                      - /url: /accounting-guide
                  - generic "关闭提示" [ref=e139] [cursor=pointer]: ✕
                - generic [ref=e140]:
                  - tablist [ref=e144]:
                    - tab "增值税报表" [selected] [ref=e146]
                    - tab "企业所得税" [ref=e147]
                  - tabpanel "增值税报表" [ref=e149]:
                    - generic [ref=e150]:
                      - generic [ref=e151]:
                        - generic [ref=e152]: 一般纳税人
                        - radiogroup "radio-group" [ref=e153]:
                          - generic [ref=e154]:
                            - radio "按季度" [checked] [ref=e155]
                            - generic [ref=e156] [cursor=pointer]: 按季度
                          - generic [ref=e157]:
                            - radio "按月份" [ref=e158]
                            - generic [ref=e159] [cursor=pointer]: 按月份
                      - generic [ref=e160]:
                        - generic [ref=e162] [cursor=pointer]:
                          - generic:
                            - combobox [ref=e164]
                            - generic [ref=e165]: "2026"
                          - img [ref=e168]
                        - generic [ref=e171] [cursor=pointer]:
                          - generic:
                            - combobox [ref=e173]
                            - generic [ref=e174]: "3"
                          - img [ref=e177]
                        - button "查询" [ref=e179] [cursor=pointer]:
                          - generic [ref=e180]: 查询
                      - generic [ref=e181]:
                        - generic [ref=e182]:
                          - generic [ref=e183]: 2026年第3季度增值税报表
                          - generic [ref=e184]: 2026-07-01 ~ 2026-09-30
                        - table [ref=e191]:
                          - rowgroup [ref=e195]:
                            - row "销项税额 0.00" [ref=e196]:
                              - cell "销项税额" [ref=e197]:
                                - generic [ref=e199]: 销项税额
                              - cell "0.00" [ref=e200]:
                                - generic [ref=e201]: "0.00"
                            - row "进项税额 0.00" [ref=e202]:
                              - cell "进项税额" [ref=e203]:
                                - generic [ref=e205]: 进项税额
                              - cell "0.00" [ref=e206]:
                                - generic [ref=e207]: "0.00"
                            - row "应纳税额合计 0.00" [ref=e208]:
                              - cell "应纳税额合计" [ref=e209]:
                                - generic [ref=e211]: 应纳税额合计
                              - cell "0.00" [ref=e212]:
                                - generic [ref=e214]: "0.00"
                        - generic [ref=e215]:
                          - generic [ref=e216]: 涉及发票
                          - generic [ref=e217]:
                            - generic [ref=e218]:
                              - generic [ref=e219]: 销项发票
                              - generic [ref=e220]: 0 张
                              - generic [ref=e221]: 不含税 0.00
                            - generic [ref=e222]:
                              - generic [ref=e223]: 进项发票
                              - generic [ref=e224]: 0 张
                              - generic [ref=e225]: 不含税 0.00
                            - generic [ref=e226] [cursor=pointer]:
                              - generic [ref=e227]: 查看全部发票 →
                              - generic [ref=e228]: 共 0 张
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
  37  |       await expect(vatSection.locator('.el-form-item:has-text("季度")')).toBeVisible();
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
> 81  |       await vatSection.locator('text=按月份').click();
      |                                            ^ Error: locator.click: Test timeout of 60000ms exceeded.
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
  138 |       await yearFormItem.locator('.el-select').click();
  139 |       await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
  140 |       const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
  141 |       if (await yearOptions.count() > 0) {
  142 |         await yearOptions.first().click();
  143 |       }
  144 | 
  145 |       // 点击查询
  146 |       await vatSection.locator('button:has-text("查询")').click();
  147 |       await page.waitForTimeout(2000);
  148 | 
  149 |       // 如果有报表卡片，验证内部结构
  150 |       const reportCard = vatSection.locator('.report-card');
  151 |       if ((await reportCard.count()) > 0) {
  152 |         await expect(reportCard.locator('.report-header')).toBeVisible();
  153 |         await expect(reportCard.locator('.financial-table')).toBeVisible();
  154 |       }
  155 |     });
  156 |   });
  157 | 
  158 |   // ========== 企业所得税 ==========
  159 |   test.describe('企业所得税', () => {
  160 |     test.beforeEach(async ({ page }) => {
  161 |       // 先切换到企业所得税标签页
  162 |       await page.locator('.el-tabs__item:has-text("企业所得税")').click();
  163 |       await page.waitForTimeout(500);
  164 |     });
  165 | 
  166 |     test('企业所得税筛选区域正确展示', async ({ page }) => {
  167 |       const incomeSection = page.locator('.income-tax-report-section');
  168 |       await expect(incomeSection.locator('.el-form-item:has-text("年份")')).toBeVisible();
  169 |       await expect(incomeSection.locator('.el-form-item:has-text("季度")')).toBeVisible();
  170 |       await expect(incomeSection.locator('button:has-text("查询")')).toBeVisible();
  171 |     });
  172 | 
  173 |     test('按季度查询企业所得税报表', async ({ page }) => {
  174 |       const incomeSection = page.locator('.income-tax-report-section');
  175 | 
  176 |       // 选择年份
  177 |       const yearFormItem = incomeSection.locator('.el-form-item:has-text("年份")');
  178 |       await yearFormItem.locator('.el-select').click();
  179 |       await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
  180 |       const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
  181 |       if (await yearOptions.count() > 0) {
```