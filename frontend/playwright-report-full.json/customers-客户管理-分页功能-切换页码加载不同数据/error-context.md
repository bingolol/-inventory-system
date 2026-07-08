# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: customers.spec.js >> 客户管理 >> 分页功能 >> 切换页码加载不同数据
- Location: tests\e2e\customers.spec.js:42:5

# Error details

```
Error: locator.click: Error: strict mode violation: locator('.el-pagination .el-select') resolved to 2 elements:
    1) <div class="el-select">…</div> aka locator('div').filter({ hasText: /^20条\/页$/ }).first()
    2) <div class="el-select">…</div> aka locator('div').filter({ hasText: /^20条\/页$/ }).nth(4)

Call log:
  - waiting for locator('.el-pagination .el-select')

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
                    - textbox "搜索客户名称" [ref=e143]
                  - button "查询" [ref=e144] [cursor=pointer]:
                    - generic [ref=e145]: 查询
                - generic [ref=e147]:
                  - table [ref=e149]:
                    - rowgroup [ref=e157]:
                      - row "客户名称 联系人 电话 地址 备注 操作" [ref=e158]:
                        - columnheader "客户名称" [ref=e159]:
                          - generic [ref=e160]: 客户名称
                        - columnheader "联系人" [ref=e161]:
                          - generic [ref=e162]: 联系人
                        - columnheader "电话" [ref=e163]:
                          - generic [ref=e164]: 电话
                        - columnheader "地址" [ref=e165]:
                          - generic [ref=e166]: 地址
                        - columnheader "备注" [ref=e167]:
                          - generic [ref=e168]: 备注
                        - columnheader "操作" [ref=e169]:
                          - generic [ref=e170]: 操作
                  - table [ref=e175]:
                    - rowgroup [ref=e183]:
                      - row "中国联通宜宾分公司 编辑 删除" [ref=e184]:
                        - cell "中国联通宜宾分公司" [ref=e185]:
                          - generic [ref=e186]: 中国联通宜宾分公司
                        - cell [ref=e187]
                        - cell [ref=e188]
                        - cell [ref=e189]
                        - cell [ref=e190]
                        - cell "编辑 删除" [ref=e191]:
                          - generic [ref=e192]:
                            - button "编辑" [ref=e193] [cursor=pointer]:
                              - generic [ref=e194]: 编辑
                            - button "删除" [ref=e195] [cursor=pointer]:
                              - generic [ref=e196]: 删除
                      - row "四川南山射钉紧固器材有限公司 编辑 删除" [ref=e197]:
                        - cell "四川南山射钉紧固器材有限公司" [ref=e198]:
                          - generic [ref=e199]: 四川南山射钉紧固器材有限公司
                        - cell [ref=e200]
                        - cell [ref=e201]
                        - cell [ref=e202]
                        - cell [ref=e203]
                        - cell "编辑 删除" [ref=e204]:
                          - generic [ref=e205]:
                            - button "编辑" [ref=e206] [cursor=pointer]:
                              - generic [ref=e207]: 编辑
                            - button "删除" [ref=e208] [cursor=pointer]:
                              - generic [ref=e209]: 删除
                - generic [ref=e211]:
                  - generic [ref=e212]: 共 2 条
                  - generic [ref=e215] [cursor=pointer]:
                    - generic:
                      - combobox [ref=e217]
                      - generic [ref=e218]: 20条/页
                    - img [ref=e221]
                  - button "上一页" [disabled] [ref=e223]:
                    - generic:
                      - img
                  - list [ref=e224]:
                    - listitem "第 1 页" [ref=e225]: "1"
                  - button "下一页" [disabled] [ref=e226]:
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
> 44  |       await page.locator('.el-pagination .el-select').click();
      |                                                       ^ Error: locator.click: Error: strict mode violation: locator('.el-pagination .el-select') resolved to 2 elements:
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
  94  |       await page.locator('.filter-bar button:has-text("查询")').click();
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
```