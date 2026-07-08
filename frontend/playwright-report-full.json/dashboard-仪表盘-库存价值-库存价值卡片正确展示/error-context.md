# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard.spec.js >> 仪表盘 >> 库存价值 >> 库存价值卡片正确展示
- Location: tests\e2e\dashboard.spec.js:115:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=库存价值')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=库存价值')

```

```yaml
- complementary:
  - text: 进销存 巧游电子科技 一般纳税人
  - combobox
  - text: 巧游电子科技
  - img
  - text: ＋ ✎ −
  - navigation: ◉ 仪表盘 基础数据 ◻ 伙伴管理 ◻ 库存商品 业务处理 ◉ 销售开单 ◻ 采购入库 ◻ 发票录入 ◻ 资金流水 财务核算 ◉ 财务总览 ◻ 费用管理 ◻ 固定资产 ◻ 银行账户 ◻ 银行对账 ◻ 往来管理 财务报表 ◉ 资产负债表/利润表 ◉ 现金流量表 ◻ 会计账簿 ◻ 会计规则指引 期末处理 ◉ 期末税务 系统管理 ◻ 操作日志 ◻ 数据备份
- heading "仪表盘" [level=2]
- text: 快速导航到各功能模块
- button "A admin":
  - text: A admin
  - img
- text: 2026/07/07周二
- main:
  - text: 本月净利润 0.00 收入 0.00 成本 0.00 费用 0.00 毛利 0.00 别人欠我 0.00 未回款客户 0 家 销售笔数 0 我欠别人 578.00 未付供应商 2 家 库存资金 2,182.60 库存总量 5 件 商品种类 8 种 预警项 0 待办清单 2026年7月7日 · 2026年第3季度（7月~9月） 本月截止 7月初 — 检查上月月结 上月还没做月结的话尽快补做。月结不仅生成报表，还计提折旧、计算增值税，不做数据会跨月混淆。 截止：7月7日前
  - button "补做月结"
  - text: 上季度申报截止 — 增值税+企业所得税预缴 必须在9月15日前完成。逾期每日万分之五滞纳金！ 截止：9月15日
  - button "查税务报表"
  - text: 本月例行 7月15日前 — 完成上月税务申报 一般纳税人必须每月15日前申报增值税。小规模按季度申报，但仍建议每月查看税务掌握税负。
  - button "查税务"
  - text: 7月工资计提与发放 有员工的公司每月需记录工资费用：费用支出 → 新增费用 → 类别选"工资"。
  - button "记费用"
  - text: 日常维护 核对银行对账单（建议每周一次） 确保系统账面余额和银行实际余额一致。差异可能来自银行手续费未录、客户汇款未核销、支票未兑现。
  - button "去对账"
  - text: 催收逾期应收账款 重点关注超过90天未回款的客户。金额大的主动联系催收，逾期越久变坏账概率越大。
  - button "查往来"
  - text: 当天业务当天录入系统 采购入库、销售开单、费用支出、收款付款——每笔发生立刻录入，不要积压。 远期注意 残疾人就业保障金申报（7-9月） 各地申报时间略有不同。未安置残疾人需缴纳残保金，具体金额和截止时间咨询当地残联。 截止：以当地通知为准 关注连续12个月累计销售额 小规模纳税人连续12个月销售额超500万会被强制认定一般纳税人（不可逆）。每月要盯着滚动12个月的累计数。 截止：持续关注 业务概要 本月收入 0.00 本月成本 0.00 本月费用 0.00 销售笔数 0 商品种类 8 库存总量 5 业务处理 📦 采购入库 → 🧾 进项发票 → 💳 采购付款 📋 销售开单 → 🧾 销项发票 → 💰 收款 💸 费用 → 💳 付款 → 🏦 银行对账 → 🔒 月结 数据查看 📊 财务总览 🏦 银行账户 📄 财务报表 🏛️ 期末税务 🏦 银行对账 💰 收款管理 💳 付款管理 🏗️ 固定资产 🔒 期末处理 库存预警 全部 → 暂无预警，库存状况良好 收入趋势 近30天
```

# Test source

```ts
  16  |       const statCards = page.locator('.stat-card');
  17  |       await expect(statCards).toHaveCount(4);
  18  | 
  19  |       await expect(page.locator('.stat-label:has-text("商品种类")')).toBeVisible();
  20  |       await expect(page.locator('.stat-label:has-text("库存总量")')).toBeVisible();
  21  |       await expect(page.locator('.stat-label:has-text("今日采购")')).toBeVisible();
  22  |       await expect(page.locator('.stat-label:has-text("今日销售")')).toBeVisible();
  23  |     });
  24  |   });
  25  | 
  26  |   // ========== 统计数据展示 ==========
  27  |   test.describe('统计数据展示', () => {
  28  |     test('商品种类数值为数字', async ({ page }) => {
  29  |       const value = page.locator('.stat-value').first();
  30  |       await expect(value).toBeVisible();
  31  |       const text = await value.textContent();
  32  |       expect(Number(text?.trim())).not.toBeNaN();
  33  |     });
  34  | 
  35  |     test('库存总量数值为数字', async ({ page }) => {
  36  |       const value = page.locator('.stat-value').nth(1);
  37  |       await expect(value).toBeVisible();
  38  |       const text = await value.textContent();
  39  |       expect(Number(text?.trim())).not.toBeNaN();
  40  |     });
  41  | 
  42  |     test('今日采购金额包含人民币符号', async ({ page }) => {
  43  |       const value = page.locator('.stat-value').nth(2);
  44  |       await expect(value).toBeVisible();
  45  |       const text = await value.textContent();
  46  |       expect(text).toContain('¥');
  47  |     });
  48  | 
  49  |     test('今日销售金额包含人民币符号', async ({ page }) => {
  50  |       const value = page.locator('.stat-value').nth(3);
  51  |       await expect(value).toBeVisible();
  52  |       const text = await value.textContent();
  53  |       expect(text).toContain('¥');
  54  |     });
  55  |   });
  56  | 
  57  |   // ========== 趋势分析图表 ==========
  58  |   test.describe('趋势分析', () => {
  59  |     test('趋势分析卡片正确展示', async ({ page }) => {
  60  |       await expect(page.locator('text=趋势分析')).toBeVisible();
  61  |       await expect(page.locator('v-chart, canvas')).toBeVisible();
  62  |     });
  63  | 
  64  |     test('默认选中近7天', async ({ page }) => {
  65  |       const radio7d = page.locator('.el-radio-button:has-text("近7天")');
  66  |       await expect(radio7d).toHaveClass(/is-active/);
  67  |     });
  68  | 
  69  |     test('切换到近30天', async ({ page }) => {
  70  |       await page.locator('.el-radio-button:has-text("近30天")').click();
  71  |       await page.waitForTimeout(1000);
  72  | 
  73  |       const radio30d = page.locator('.el-radio-button:has-text("近30天")');
  74  |       await expect(radio30d).toHaveClass(/is-active/);
  75  |     });
  76  | 
  77  |     test('切换到近90天', async ({ page }) => {
  78  |       await page.locator('.el-radio-button:has-text("近90天")').click();
  79  |       await page.waitForTimeout(1000);
  80  | 
  81  |       const radio90d = page.locator('.el-radio-button:has-text("近90天")');
  82  |       await expect(radio90d).toHaveClass(/is-active/);
  83  |     });
  84  |   });
  85  | 
  86  |   // ========== 库存预警 ==========
  87  |   test.describe('库存预警', () => {
  88  |     test('库存预警卡片正确展示', async ({ page }) => {
  89  |       await expect(page.locator('text=库存预警')).toBeVisible();
  90  |     });
  91  | 
  92  |     test('有预警数据时展示表格', async ({ page }) => {
  93  |       const table = page.locator('.el-card:has-text("库存预警") .el-table');
  94  |       const empty = page.locator('.el-card:has-text("库存预警") .el-empty');
  95  | 
  96  |       const tableVisible = await table.isVisible().catch(() => false);
  97  |       const emptyVisible = await empty.isVisible().catch(() => false);
  98  | 
  99  |       expect(tableVisible || emptyVisible).toBeTruthy();
  100 |     });
  101 | 
  102 |     test('预警表格包含必要列', async ({ page }) => {
  103 |       const table = page.locator('.el-card:has-text("库存预警") .el-table');
  104 |       if (await table.isVisible().catch(() => false)) {
  105 |         await expect(page.locator('th:has-text("商品")')).toBeVisible();
  106 |         await expect(page.locator('th:has-text("编码")')).toBeVisible();
  107 |         await expect(page.locator('th:has-text("库存")')).toBeVisible();
  108 |         await expect(page.locator('th:has-text("预警线")')).toBeVisible();
  109 |       }
  110 |     });
  111 |   });
  112 | 
  113 |   // ========== 库存价值 ==========
  114 |   test.describe('库存价值', () => {
  115 |     test('库存价值卡片正确展示', async ({ page }) => {
> 116 |       await expect(page.locator('text=库存价值')).toBeVisible();
      |                                               ^ Error: expect(locator).toBeVisible() failed
  117 |       await expect(page.locator('text=库存总价值（按进价计算）')).toBeVisible();
  118 |     });
  119 | 
  120 |     test('库存价值金额包含人民币符号', async ({ page }) => {
  121 |       const value = page.locator('.el-card:has-text("库存价值") .stat-value, .el-card:has-text("库存价值") [style*="font-size: 36px"]').first();
  122 |       if (await value.isVisible().catch(() => false)) {
  123 |         const text = await value.textContent();
  124 |         expect(text).toContain('¥');
  125 |       }
  126 |     });
  127 |   });
  128 | });
  129 | 
```