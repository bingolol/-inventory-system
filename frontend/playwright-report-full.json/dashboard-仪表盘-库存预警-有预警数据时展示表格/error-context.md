# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard.spec.js >> 仪表盘 >> 库存预警 >> 有预警数据时展示表格
- Location: tests\e2e\dashboard.spec.js:92:5

# Error details

```
Error: expect(received).toBeTruthy()

Received: false
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
        - heading "仪表盘" [level=2] [ref=e99]
        - generic [ref=e100]: 快速导航到各功能模块
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
            - generic [ref=e114]: 本月净利润
            - generic [ref=e115]: "0.00"
            - generic [ref=e117]:
              - generic [ref=e118]: 收入
              - generic [ref=e119]: "0.00"
            - generic [ref=e120]:
              - generic [ref=e121]: 成本
              - generic [ref=e122]: "0.00"
            - generic [ref=e123]:
              - generic [ref=e124]: 费用
              - generic [ref=e125]: "0.00"
            - generic [ref=e126]:
              - generic [ref=e127]: 毛利
              - generic [ref=e128]: "0.00"
          - generic [ref=e129]:
            - generic [ref=e130]: 别人欠我
            - generic [ref=e131]: "0.00"
            - generic [ref=e133]:
              - generic [ref=e134]: 未回款客户
              - generic [ref=e135]: 0 家
            - generic [ref=e136]:
              - generic [ref=e137]: 销售笔数
              - generic [ref=e138]: "0"
          - generic [ref=e139]:
            - generic [ref=e140]: 我欠别人
            - generic [ref=e141]: "578.00"
            - generic [ref=e143]:
              - generic [ref=e144]: 未付供应商
              - generic [ref=e145]: 2 家
          - generic [ref=e146]:
            - generic [ref=e147]: 库存资金
            - generic [ref=e148]: 2,182.60
            - generic [ref=e150]:
              - generic [ref=e151]: 库存总量
              - generic [ref=e152]: 5 件
            - generic [ref=e153]:
              - generic [ref=e154]: 商品种类
              - generic [ref=e155]: 8 种
            - generic [ref=e156]:
              - generic [ref=e157]: 预警项
              - generic [ref=e158]: "0"
        - generic [ref=e160]:
          - generic [ref=e161]:
            - generic [ref=e162]: 待办清单
            - generic [ref=e163]: 2026年7月7日 · 2026年第3季度（7月~9月）
          - generic [ref=e164]:
            - generic [ref=e165]:
              - generic [ref=e166]: 本月截止
              - generic [ref=e167]:
                - generic [ref=e168]:
                  - generic [ref=e169]: 7月初 — 检查上月月结
                  - generic [ref=e170]: 上月还没做月结的话尽快补做。月结不仅生成报表，还计提折旧、计算增值税，不做数据会跨月混淆。
                  - generic [ref=e171]: 截止：7月7日前
                - button "补做月结" [ref=e172] [cursor=pointer]:
                  - generic [ref=e173]: 补做月结
              - generic [ref=e174]:
                - generic [ref=e175]:
                  - generic [ref=e176]: 上季度申报截止 — 增值税+企业所得税预缴
                  - generic [ref=e177]: 必须在9月15日前完成。逾期每日万分之五滞纳金！
                  - generic [ref=e178]: 截止：9月15日
                - button "查税务报表" [ref=e179] [cursor=pointer]:
                  - generic [ref=e180]: 查税务报表
            - generic [ref=e181]:
              - generic [ref=e182]: 本月例行
              - generic [ref=e183]:
                - generic [ref=e184]:
                  - generic [ref=e185]: 7月15日前 — 完成上月税务申报
                  - generic [ref=e186]: 一般纳税人必须每月15日前申报增值税。小规模按季度申报，但仍建议每月查看税务掌握税负。
                - button "查税务" [ref=e187] [cursor=pointer]:
                  - generic [ref=e188]: 查税务
              - generic [ref=e189]:
                - generic [ref=e190]:
                  - generic [ref=e191]: 7月工资计提与发放
                  - generic [ref=e192]: 有员工的公司每月需记录工资费用：费用支出 → 新增费用 → 类别选"工资"。
                - button "记费用" [ref=e193] [cursor=pointer]:
                  - generic [ref=e194]: 记费用
            - generic [ref=e195]:
              - generic [ref=e196]: 日常维护
              - generic [ref=e197]:
                - generic [ref=e198]:
                  - generic [ref=e199]: 核对银行对账单（建议每周一次）
                  - generic [ref=e200]: 确保系统账面余额和银行实际余额一致。差异可能来自银行手续费未录、客户汇款未核销、支票未兑现。
                - button "去对账" [ref=e201] [cursor=pointer]:
                  - generic [ref=e202]: 去对账
              - generic [ref=e203]:
                - generic [ref=e204]:
                  - generic [ref=e205]: 催收逾期应收账款
                  - generic [ref=e206]: 重点关注超过90天未回款的客户。金额大的主动联系催收，逾期越久变坏账概率越大。
                - button "查往来" [ref=e207] [cursor=pointer]:
                  - generic [ref=e208]: 查往来
              - generic [ref=e210]:
                - generic [ref=e211]: 当天业务当天录入系统
                - generic [ref=e212]: 采购入库、销售开单、费用支出、收款付款——每笔发生立刻录入，不要积压。
            - generic [ref=e213]:
              - generic [ref=e214]: 远期注意
              - generic [ref=e216]:
                - generic [ref=e217]: 残疾人就业保障金申报（7-9月）
                - generic [ref=e218]: 各地申报时间略有不同。未安置残疾人需缴纳残保金，具体金额和截止时间咨询当地残联。
                - generic [ref=e219]: 截止：以当地通知为准
              - generic [ref=e221]:
                - generic [ref=e222]: 关注连续12个月累计销售额
                - generic [ref=e223]: 小规模纳税人连续12个月销售额超500万会被强制认定一般纳税人（不可逆）。每月要盯着滚动12个月的累计数。
                - generic [ref=e224]: 截止：持续关注
        - generic [ref=e225]:
          - generic [ref=e226]:
            - generic [ref=e227]:
              - generic [ref=e229]: 业务概要
              - generic [ref=e230]:
                - generic [ref=e231]:
                  - generic [ref=e232]: 本月收入
                  - generic [ref=e233]: "0.00"
                - generic [ref=e234]:
                  - generic [ref=e235]: 本月成本
                  - generic [ref=e236]: "0.00"
                - generic [ref=e237]:
                  - generic [ref=e238]: 本月费用
                  - generic [ref=e239]: "0.00"
                - generic [ref=e240]:
                  - generic [ref=e241]: 销售笔数
                  - generic [ref=e242]: "0"
                - generic [ref=e243]:
                  - generic [ref=e244]: 商品种类
                  - generic [ref=e245]: "8"
                - generic [ref=e246]:
                  - generic [ref=e247]: 库存总量
                  - generic [ref=e248]: "5"
              - generic [ref=e250]: 业务处理
              - generic [ref=e251]:
                - generic [ref=e252] [cursor=pointer]:
                  - generic [ref=e253]: 📦
                  - generic [ref=e254]: 采购入库
                - generic [ref=e255]: →
                - generic [ref=e256] [cursor=pointer]:
                  - generic [ref=e257]: 🧾
                  - generic [ref=e258]: 进项发票
                - generic [ref=e259]: →
                - generic [ref=e260] [cursor=pointer]:
                  - generic [ref=e261]: 💳
                  - generic [ref=e262]: 采购付款
              - generic [ref=e263]:
                - generic [ref=e264] [cursor=pointer]:
                  - generic [ref=e265]: 📋
                  - generic [ref=e266]: 销售开单
                - generic [ref=e267]: →
                - generic [ref=e268] [cursor=pointer]:
                  - generic [ref=e269]: 🧾
                  - generic [ref=e270]: 销项发票
                - generic [ref=e271]: →
                - generic [ref=e272] [cursor=pointer]:
                  - generic [ref=e273]: 💰
                  - generic [ref=e274]: 收款
              - generic [ref=e275]:
                - generic [ref=e276] [cursor=pointer]:
                  - generic [ref=e277]: 💸
                  - generic [ref=e278]: 费用
                - generic [ref=e279]: →
                - generic [ref=e280] [cursor=pointer]:
                  - generic [ref=e281]: 💳
                  - generic [ref=e282]: 付款
                - generic [ref=e283]: →
                - generic [ref=e284] [cursor=pointer]:
                  - generic [ref=e285]: 🏦
                  - generic [ref=e286]: 银行对账
                - generic [ref=e287]: →
                - generic [ref=e288] [cursor=pointer]:
                  - generic [ref=e289]: 🔒
                  - generic [ref=e290]: 月结
              - generic [ref=e292]: 数据查看
              - generic [ref=e293]:
                - generic [ref=e294] [cursor=pointer]: 📊 财务总览
                - generic [ref=e295] [cursor=pointer]: 🏦 银行账户
                - generic [ref=e296] [cursor=pointer]: 📄 财务报表
                - generic [ref=e297] [cursor=pointer]: 🏛️ 期末税务
                - generic [ref=e298] [cursor=pointer]: 🏦 银行对账
                - generic [ref=e299] [cursor=pointer]: 💰 收款管理
                - generic [ref=e300] [cursor=pointer]: 💳 付款管理
                - generic [ref=e301] [cursor=pointer]: 🏗️ 固定资产
                - generic [ref=e302] [cursor=pointer]: 🔒 期末处理
            - generic [ref=e303]:
              - generic [ref=e304]:
                - generic [ref=e305]: 库存预警
                - generic [ref=e306] [cursor=pointer]: 全部 →
              - generic [ref=e307]: 暂无预警，库存状况良好
          - generic [ref=e310]:
            - generic [ref=e311]: 收入趋势
            - generic [ref=e312]: 近30天
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('仪表盘', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/dashboard');
  6   |     await page.waitForTimeout(2000);
  7   |   });
  8   | 
  9   |   // ========== 页面加载 ==========
  10  |   test.describe('页面加载', () => {
  11  |     test('仪表盘页面正常加载', async ({ page }) => {
  12  |       await expect(page.locator('.dashboard')).toBeVisible();
  13  |     });
  14  | 
  15  |     test('四个统计卡片正确展示', async ({ page }) => {
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
> 99  |       expect(tableVisible || emptyVisible).toBeTruthy();
      |                                            ^ Error: expect(received).toBeTruthy()
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
  116 |       await expect(page.locator('text=库存价值')).toBeVisible();
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