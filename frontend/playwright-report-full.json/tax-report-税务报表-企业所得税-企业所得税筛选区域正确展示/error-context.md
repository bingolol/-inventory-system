# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: tax-report.spec.js >> 税务报表 >> 企业所得税 >> 企业所得税筛选区域正确展示
- Location: tests\e2e\tax-report.spec.js:166:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.income-tax-report-section').locator('.el-form-item:has-text("年份")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.income-tax-report-section').locator('.el-form-item:has-text("年份")')

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
      - tab "增值税报表"
      - tab "企业所得税" [selected]
    - tabpanel "企业所得税":
      - combobox
      - text: "2026"
      - img
      - combobox
      - text: 第三季度
      - img
      - button "查询"
      - text: 企业所得税 2026年第3季度 应纳企业所得税 0.00 税率
      - strong: 25.0%
      - text: 营业收入 + 0.00 营业成本 - 0.00 毛利润 0.00 减：可税前扣除费用 - 0.00 应纳税所得额 0.00 应纳企业所得税 0.00 按会计准则口径计算 · 数据来自总账利润表
```

# Test source

```ts
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
> 168 |       await expect(incomeSection.locator('.el-form-item:has-text("年份")')).toBeVisible();
      |                                                                           ^ Error: expect(locator).toBeVisible() failed
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
  182 |         await yearOptions.first().click();
  183 |       }
  184 | 
  185 |       // 选择季度
  186 |       const quarterFormItem = incomeSection.locator('.el-form-item:has-text("季度")');
  187 |       await quarterFormItem.locator('.el-select').click();
  188 |       await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
  189 |       const quarterOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
  190 |       if (await quarterOptions.count() > 0) {
  191 |         await quarterOptions.first().click();
  192 |       }
  193 | 
  194 |       // 点击查询
  195 |       await incomeSection.locator('button:has-text("查询")').click();
  196 |       await page.waitForTimeout(2000);
  197 | 
  198 |       // 验证报表卡片或空状态存在
  199 |       const reportCard = incomeSection.locator('.report-card');
  200 |       const emptyState = incomeSection.locator('.el-empty');
  201 |       const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
  202 |       expect(hasContent).toBeTruthy();
  203 |     });
  204 | 
  205 |     test('企业所得税报表内容区域正确展示', async ({ page }) => {
  206 |       const incomeSection = page.locator('.income-tax-report-section');
  207 | 
  208 |       // 选择年份
  209 |       const yearFormItem = incomeSection.locator('.el-form-item:has-text("年份")');
  210 |       await yearFormItem.locator('.el-select').click();
  211 |       await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
  212 |       const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
  213 |       if (await yearOptions.count() > 0) {
  214 |         await yearOptions.first().click();
  215 |       }
  216 | 
  217 |       // 点击查询
  218 |       await incomeSection.locator('button:has-text("查询")').click();
  219 |       await page.waitForTimeout(2000);
  220 | 
  221 |       // 如果有报表卡片，验证内部结构
  222 |       const reportCard = incomeSection.locator('.report-card');
  223 |       if ((await reportCard.count()) > 0) {
  224 |         await expect(reportCard.locator('.report-header')).toBeVisible();
  225 |         await expect(reportCard.locator('.financial-table')).toBeVisible();
  226 |       }
  227 |     });
  228 |   });
  229 | 
  230 |   // ========== 标签页切换 ==========
  231 |   test.describe('标签页切换', () => {
  232 |     test('在不同标签页之间切换', async ({ page }) => {
  233 |       await page.locator('.el-tabs__item:has-text("企业所得税")').click();
  234 |       await page.waitForTimeout(500);
  235 |       await expect(page.locator('.el-tabs__item.is-active')).toContainText('企业所得税');
  236 | 
  237 |       await page.locator('.el-tabs__item:has-text("增值税报表")').click();
  238 |       await page.waitForTimeout(500);
  239 |       await expect(page.locator('.el-tabs__item.is-active')).toContainText('增值税报表');
  240 |     });
  241 | 
  242 |     test('切换标签页后筛选条件保持', async ({ page }) => {
  243 |       const vatSection = page.locator('.vat-report-section');
  244 |       const yearFormItem = vatSection.locator('.el-form-item:has-text("年份")');
  245 | 
  246 |       // 初始状态年份表单可见
  247 |       await expect(yearFormItem).toBeVisible();
  248 | 
  249 |       // 切换到企业所得税再切回来
  250 |       await page.locator('.el-tabs__item:has-text("企业所得税")').click();
  251 |       await page.waitForTimeout(500);
  252 | 
  253 |       await page.locator('.el-tabs__item:has-text("增值税报表")').click();
  254 |       await page.waitForTimeout(500);
  255 | 
  256 |       // 验证年份表单仍然可见
  257 |       await expect(yearFormItem).toBeVisible();
  258 |     });
  259 |   });
  260 | });
  261 | 
```