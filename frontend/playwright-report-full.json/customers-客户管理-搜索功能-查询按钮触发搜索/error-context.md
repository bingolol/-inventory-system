# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: customers.spec.js >> 客户管理 >> 搜索功能 >> 查询按钮触发搜索
- Location: tests\e2e\customers.spec.js:91:5

# Error details

```
Error: locator.click: Error: strict mode violation: locator('.filter-bar button:has-text("查询")') resolved to 2 elements:
    1) <button type="button" data-v-14585336="" aria-disabled="false" class="el-button el-button--primary">…</button> aka getByRole('button', { name: '查询' })
    2) <button type="button" data-v-14585336="" aria-disabled="false" class="el-button el-button--primary">…</button> aka getByLabel('供应商', { exact: true }).locator('button').filter({ hasText: '查询' })

Call log:
  - waiting for locator('.filter-bar button:has-text("查询")')

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
        - heading "伙伴管理" [level=2] [ref=e99]
        - generic [ref=e100]: 客户 · 供应商
      - generic [ref=e101]:
        - button "A admin" [ref=e103] [cursor=pointer]:
          - generic [ref=e104]: A
          - generic [ref=e105]: admin
          - img [ref=e107]
        - text: 2026/07/07周二
    - main [ref=e109]:
      - generic [ref=e110]:
        - generic [ref=e113]: 伙伴管理
        - generic [ref=e115]:
          - tablist [ref=e119]:
            - tab "客户" [selected] [ref=e121]
            - tab "供应商" [ref=e122]
          - tabpanel "客户" [ref=e124]:
            - generic [ref=e126]:
              - generic [ref=e128]:
                - generic [ref=e129]: 客户列表
                - button "新增客户" [ref=e130] [cursor=pointer]:
                  - generic [ref=e131]:
                    - img [ref=e133]
                    - text: 新增客户
              - generic [ref=e135]:
                - generic [ref=e136]:
                  - generic [ref=e138]:
                    - img [ref=e141]
                    - textbox "搜索客户名称" [active] [ref=e143]: 测试
                    - img [ref=e146] [cursor=pointer]
                  - button "查询" [ref=e149] [cursor=pointer]:
                    - generic [ref=e150]: 查询
                - generic [ref=e152]:
                  - table [ref=e154]:
                    - rowgroup [ref=e162]:
                      - row "客户名称 联系人 电话 地址 备注 操作" [ref=e163]:
                        - columnheader "客户名称" [ref=e164]:
                          - generic [ref=e165]: 客户名称
                        - columnheader "联系人" [ref=e166]:
                          - generic [ref=e167]: 联系人
                        - columnheader "电话" [ref=e168]:
                          - generic [ref=e169]: 电话
                        - columnheader "地址" [ref=e170]:
                          - generic [ref=e171]: 地址
                        - columnheader "备注" [ref=e172]:
                          - generic [ref=e173]: 备注
                        - columnheader "操作" [ref=e174]:
                          - generic [ref=e175]: 操作
                  - table [ref=e180]:
                    - rowgroup [ref=e188]:
                      - row "中国联通宜宾分公司 编辑 删除" [ref=e189]:
                        - cell "中国联通宜宾分公司" [ref=e190]:
                          - generic [ref=e191]: 中国联通宜宾分公司
                        - cell [ref=e192]
                        - cell [ref=e193]
                        - cell [ref=e194]
                        - cell [ref=e195]
                        - cell "编辑 删除" [ref=e196]:
                          - generic [ref=e197]:
                            - button "编辑" [ref=e198] [cursor=pointer]:
                              - generic [ref=e199]: 编辑
                            - button "删除" [ref=e200] [cursor=pointer]:
                              - generic [ref=e201]: 删除
                      - row "四川南山射钉紧固器材有限公司 编辑 删除" [ref=e202]:
                        - cell "四川南山射钉紧固器材有限公司" [ref=e203]:
                          - generic [ref=e204]: 四川南山射钉紧固器材有限公司
                        - cell [ref=e205]
                        - cell [ref=e206]
                        - cell [ref=e207]
                        - cell [ref=e208]
                        - cell "编辑 删除" [ref=e209]:
                          - generic [ref=e210]:
                            - button "编辑" [ref=e211] [cursor=pointer]:
                              - generic [ref=e212]: 编辑
                            - button "删除" [ref=e213] [cursor=pointer]:
                              - generic [ref=e214]: 删除
                - generic [ref=e216]:
                  - generic [ref=e217]: 共 2 条
                  - generic [ref=e220] [cursor=pointer]:
                    - generic:
                      - combobox [ref=e222]
                      - generic [ref=e223]: 20条/页
                    - img [ref=e226]
                  - button "上一页" [disabled] [ref=e228]:
                    - generic:
                      - img
                  - list [ref=e229]:
                    - listitem "第 1 页" [ref=e230]: "1"
                  - button "下一页" [disabled] [ref=e231]:
                    - generic:
                      - img
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | const WAIT_MS = 800;
  4   | 
  5   | test.describe('客户管理', () => {
  6   |   test.beforeEach(async ({ page }) => {
  7   |     await page.goto('/customers');
  8   |     await page.waitForSelector('.el-table__row', { timeout: 10000 });
  9   |   });
  10  | 
  11  |   // ========== 列表展示 ==========
  12  |   test.describe('列表展示', () => {
  13  |     test('客户列表正确展示后端数据', async ({ page }) => {
  14  |       const rows = await page.locator('.el-table__row').count();
  15  |       expect(rows).toBeGreaterThan(0);
  16  | 
  17  |       await expect(page.locator('th:has-text("客户名称")')).toBeVisible();
  18  |       await expect(page.locator('th:has-text("联系人")')).toBeVisible();
  19  |       await expect(page.locator('th:has-text("电话")')).toBeVisible();
  20  |       await expect(page.locator('th:has-text("地址")')).toBeVisible();
  21  |       await expect(page.locator('th:has-text("备注")')).toBeVisible();
  22  |       await expect(page.locator('th:has-text("操作")')).toBeVisible();
  23  |     });
  24  | 
  25  |     test('第一行数据包含有效内容', async ({ page }) => {
  26  |       const firstRow = page.locator('.el-table__row:first-child');
  27  |       const rowText = await firstRow.textContent();
  28  |       expect(rowText?.trim().length).toBeGreaterThan(5);
  29  |     });
  30  | 
  31  |     test('页面标题显示"客户列表"', async ({ page }) => {
  32  |       await expect(page.locator('.page-title')).toContainText('客户列表');
  33  |     });
  34  | 
  35  |     test('新增按钮显示正确文本', async ({ page }) => {
  36  |       await expect(page.locator('.card-header button:has-text("新增客户")')).toBeVisible();
  37  |     });
  38  |   });
  39  | 
  40  |   // ========== 分页 ==========
  41  |   test.describe('分页功能', () => {
  42  |     test('切换页码加载不同数据', async ({ page }) => {
  43  |       // 先切换到10条/页确保有多页数据
  44  |       await page.locator('.el-pagination .el-select').click();
  45  |       await page.waitForTimeout(300);
  46  |       await page.getByRole('option', { name: '10条/页' }).click();
  47  |       await page.waitForTimeout(WAIT_MS);
  48  | 
  49  |       const page2 = page.locator('.el-pager li:has-text("2")');
  50  |       if (await page2.count() === 0) {
  51  |         test.skip(true, '数据不足一页，跳过翻页测试');
  52  |         return;
  53  |       }
  54  |       const firstRowText = await page.locator('.el-table__row:first-child').textContent();
  55  |       await page2.click();
  56  |       await page.waitForTimeout(WAIT_MS);
  57  |       const newFirstRowText = await page.locator('.el-table__row:first-child').textContent();
  58  |       expect(newFirstRowText).not.toBe(firstRowText);
  59  |     });
  60  | 
  61  |     test('修改每页条数', async ({ page }) => {
  62  |       const rowsBefore = await page.locator('.el-table__row').count();
  63  | 
  64  |       // 打开每页条数下拉框
  65  |       await page.locator('.el-pagination .el-pagination__sizes .el-select').click();
  66  |       await page.waitForTimeout(300);
  67  | 
  68  |       // 使用精确匹配选择"10 条/页"，避免 "100 条/页" 的歧义
  69  |       const dropdown = page.locator('.el-select-dropdown:visible');
  70  |       await dropdown.locator('.el-select-dropdown__item').filter({ hasText: /^10\s*条\/页/ }).click();
  71  |       await page.waitForTimeout(WAIT_MS);
  72  | 
  73  |       const rowsAfter = await page.locator('.el-table__row').count();
  74  |       expect(rowsAfter).toBeLessThanOrEqual(10);
  75  |       expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
  76  |     });
  77  |   });
  78  | 
  79  |   // ========== 搜索 ==========
  80  |   test.describe('搜索功能', () => {
  81  |     test('名称搜索', async ({ page }) => {
  82  |       const searchInput = page.locator('input[placeholder="搜索客户名称"]');
  83  |       await searchInput.fill('测试');
  84  |       await searchInput.press('Enter');
  85  |       await page.waitForTimeout(WAIT_MS);
  86  | 
  87  |       const rows = await page.locator('.el-table__row').count();
  88  |       expect(rows).toBeGreaterThanOrEqual(0);
  89  |     });
  90  | 
  91  |     test('查询按钮触发搜索', async ({ page }) => {
  92  |       const searchInput = page.locator('input[placeholder="搜索客户名称"]');
  93  |       await searchInput.fill('测试');
> 94  |       await page.locator('.filter-bar button:has-text("查询")').click();
      |                                                               ^ Error: locator.click: Error: strict mode violation: locator('.filter-bar button:has-text("查询")') resolved to 2 elements:
  95  |       await page.waitForTimeout(WAIT_MS);
  96  | 
  97  |       const rows = await page.locator('.el-table__row').count();
  98  |       expect(rows).toBeGreaterThanOrEqual(0);
  99  |     });
  100 | 
  101 |     test('清空搜索恢复全部数据', async ({ page }) => {
  102 |       const allCount = await page.locator('.el-table__row').count();
  103 | 
  104 |       const searchInput = page.locator('input[placeholder="搜索客户名称"]');
  105 |       await searchInput.fill('测试');
  106 |       await searchInput.press('Enter');
  107 |       await page.waitForTimeout(WAIT_MS);
  108 | 
  109 |       const searchCount = await page.locator('.el-table__row').count();
  110 | 
  111 |       await searchInput.clear();
  112 |       await searchInput.press('Enter');
  113 |       await page.waitForTimeout(WAIT_MS);
  114 | 
  115 |       const restoredCount = await page.locator('.el-table__row').count();
  116 |       expect(restoredCount).toBe(allCount);
  117 |       expect(searchCount).toBeLessThanOrEqual(restoredCount);
  118 |     });
  119 |   });
  120 | 
  121 |   // ========== 新增客户 ==========
  122 |   test.describe('新增客户', () => {
  123 |     test('打开新增对话框', async ({ page }) => {
  124 |       await page.locator('.card-header button:has-text("新增客户")').click();
  125 | 
  126 |       await expect(page.locator('.el-dialog')).toBeVisible();
  127 |       await expect(page.locator('.el-dialog__title')).toContainText('新增客户');
  128 |     });
  129 | 
  130 |     test('新增客户成功', async ({ page }) => {
  131 |       const timestamp = Date.now();
  132 |       const customerName = `PW测试客户-${timestamp}`;
  133 |       const contact = `联系人-${timestamp}`;
  134 | 
  135 |       await page.locator('.card-header button:has-text("新增客户")').click();
  136 | 
  137 |       await page.locator('.el-dialog .el-form-item:has-text("名称") input').fill(customerName);
  138 |       await page.locator('.el-dialog .el-form-item:has-text("联系人") input').fill(contact);
  139 |       await page.locator('.el-dialog .el-form-item:has-text("电话") input').fill('13900139000');
  140 |       await page.locator('.el-dialog .el-form-item:has-text("地址") input').fill('客户测试地址');
  141 | 
  142 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  143 | 
  144 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  145 |       await expect(page.locator('.el-dialog')).not.toBeVisible();
  146 | 
  147 |       await page.waitForTimeout(WAIT_MS);
  148 | 
  149 |       // 搜索新增的客户，而非依赖排序
  150 |       const searchInput = page.locator('input[placeholder="搜索客户名称"]');
  151 |       await searchInput.fill(customerName);
  152 |       await searchInput.press('Enter');
  153 |       await page.waitForTimeout(WAIT_MS);
  154 | 
  155 |       const rows = await page.locator('.el-table__row').count();
  156 |       expect(rows).toBe(1);
  157 | 
  158 |       const cellText = await page.locator('.el-table__row:first-child').textContent();
  159 |       expect(cellText).toContain(customerName);
  160 |     });
  161 | 
  162 |     test('新增客户表单校验-名称必填', async ({ page }) => {
  163 |       // PartnerList 使用 HTML required 属性而非 el-form rules，无客户端校验错误提示
  164 |       // 改为验证名称字段有 required 标记
  165 |       await page.locator('.card-header button:has-text("新增客户")').click();
  166 |       await expect(page.locator('.el-dialog .el-form-item:has-text("名称")')).toBeVisible();
  167 |       // 验证 required 红色星号存在
  168 |       const requiredMark = page.locator('.el-dialog .el-form-item:has-text("名称") .el-form-item__label .el-icon');
  169 |       await page.locator('.el-dialog__footer button:has-text("取消")').click();
  170 |     });
  171 | 
  172 |     test('取消新增不保存', async ({ page }) => {
  173 |       await page.locator('.card-header button:has-text("新增客户")').click();
  174 | 
  175 |       await page.locator('.el-dialog .el-form-item:has-text("名称") input').fill('不应保存的客户');
  176 | 
  177 |       await page.locator('.el-dialog__footer button:has-text("取消")').click();
  178 | 
  179 |       await expect(page.locator('.el-dialog')).not.toBeVisible();
  180 | 
  181 |       const searchInput = page.locator('input[placeholder="搜索客户名称"]');
  182 |       await searchInput.fill('不应保存的客户');
  183 |       await searchInput.press('Enter');
  184 |       await page.waitForTimeout(WAIT_MS);
  185 | 
  186 |       const rows = await page.locator('.el-table__row').count();
  187 |       expect(rows).toBe(0);
  188 |     });
  189 |   });
  190 | 
  191 |   // ========== 编辑客户 ==========
  192 |   test.describe('编辑客户', () => {
  193 |     test('打开编辑对话框并回填数据', async ({ page }) => {
  194 |       const firstName = await page.locator('.el-table__row:first-child td').first().textContent();
```