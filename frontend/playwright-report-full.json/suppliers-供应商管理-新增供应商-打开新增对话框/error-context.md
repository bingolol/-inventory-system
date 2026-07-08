# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: suppliers.spec.js >> 供应商管理 >> 新增供应商 >> 打开新增对话框
- Location: tests\e2e\suppliers.spec.js:118:5

# Error details

```
TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('.el-table__row') to be visible
    21 × locator resolved to 6 elements. Proceeding with the first one: <tr class="el-table__row">…</tr>

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
            - tab "客户" [ref=e121]
            - tab "供应商" [selected] [ref=e122]
          - tabpanel "供应商" [ref=e124]:
            - generic [ref=e126]:
              - generic [ref=e128]:
                - generic [ref=e129]: 供应商列表
                - button "新增供应商" [ref=e130] [cursor=pointer]:
                  - generic [ref=e131]:
                    - img [ref=e133]
                    - text: 新增供应商
              - generic [ref=e135]:
                - generic [ref=e136]:
                  - generic [ref=e138]:
                    - img [ref=e141]
                    - textbox "搜索供应商名称" [ref=e143]
                  - button "查询" [ref=e144] [cursor=pointer]:
                    - generic [ref=e145]: 查询
                - generic [ref=e147]:
                  - table [ref=e149]:
                    - rowgroup [ref=e157]:
                      - row "供应商名称 联系人 电话 地址 备注 操作" [ref=e158]:
                        - columnheader "供应商名称" [ref=e159]:
                          - generic [ref=e160]: 供应商名称
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
                      - row "吴江恒净净化设备经营部 编辑 删除" [ref=e184]:
                        - cell "吴江恒净净化设备经营部" [ref=e185]:
                          - generic [ref=e186]: 吴江恒净净化设备经营部
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
                      - row "临泉县嘉涵商贸有限公司 编辑 删除" [ref=e197]:
                        - cell "临泉县嘉涵商贸有限公司" [ref=e198]:
                          - generic [ref=e199]: 临泉县嘉涵商贸有限公司
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
                      - row "乐清市申港电气厂 编辑 删除" [ref=e210]:
                        - cell "乐清市申港电气厂" [ref=e211]:
                          - generic [ref=e212]: 乐清市申港电气厂
                        - cell [ref=e213]
                        - cell [ref=e214]
                        - cell [ref=e215]
                        - cell [ref=e216]
                        - cell "编辑 删除" [ref=e217]:
                          - generic [ref=e218]:
                            - button "编辑" [ref=e219] [cursor=pointer]:
                              - generic [ref=e220]: 编辑
                            - button "删除" [ref=e221] [cursor=pointer]:
                              - generic [ref=e222]: 删除
                      - row "博控科技（淮安）有限公司 编辑 删除" [ref=e223]:
                        - cell "博控科技（淮安）有限公司" [ref=e224]:
                          - generic [ref=e225]: 博控科技（淮安）有限公司
                        - cell [ref=e226]
                        - cell [ref=e227]
                        - cell [ref=e228]
                        - cell [ref=e229]
                        - cell "编辑 删除" [ref=e230]:
                          - generic [ref=e231]:
                            - button "编辑" [ref=e232] [cursor=pointer]:
                              - generic [ref=e233]: 编辑
                            - button "删除" [ref=e234] [cursor=pointer]:
                              - generic [ref=e235]: 删除
                - generic [ref=e237]:
                  - generic [ref=e238]: 共 4 条
                  - generic [ref=e241] [cursor=pointer]:
                    - generic:
                      - combobox [ref=e243]
                      - generic [ref=e244]: 20条/页
                    - img [ref=e247]
                  - button "上一页" [disabled] [ref=e249]:
                    - generic:
                      - img
                  - list [ref=e250]:
                    - listitem "第 1 页" [ref=e251]: "1"
                  - button "下一页" [disabled] [ref=e252]:
                    - generic:
                      - img
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('供应商管理', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/suppliers');
> 6   |     await page.waitForSelector('.el-table__row', { timeout: 10000 });
      |                ^ TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
  7   |   });
  8   | 
  9   |   // ========== 列表展示 ==========
  10  |   test.describe('列表展示', () => {
  11  |     test('供应商列表正确展示后端数据', async ({ page }) => {
  12  |       const rows = await page.locator('.el-table__row').count();
  13  |       expect(rows).toBeGreaterThan(0);
  14  | 
  15  |       await expect(page.locator('th:has-text("供应商名称")')).toBeVisible();
  16  |       await expect(page.locator('th:has-text("联系人")')).toBeVisible();
  17  |       await expect(page.locator('th:has-text("电话")')).toBeVisible();
  18  |       await expect(page.locator('th:has-text("地址")')).toBeVisible();
  19  |       await expect(page.locator('th:has-text("备注")')).toBeVisible();
  20  |       await expect(page.locator('th:has-text("操作")')).toBeVisible();
  21  |     });
  22  | 
  23  |     test('第一行数据包含有效内容', async ({ page }) => {
  24  |       const firstRow = page.locator('.el-table__row:first-child');
  25  |       const rowText = await firstRow.textContent();
  26  |       expect(rowText?.trim().length).toBeGreaterThan(5);
  27  |     });
  28  | 
  29  |     test('页面标题显示"供应商列表"', async ({ page }) => {
  30  |       await expect(page.locator('.page-title')).toContainText('供应商列表');
  31  |     });
  32  | 
  33  |     test('新增按钮显示正确文本', async ({ page }) => {
  34  |       await expect(page.locator('.card-header button:has-text("新增供应商")')).toBeVisible();
  35  |     });
  36  |   });
  37  | 
  38  |   // ========== 分页 ==========
  39  |   test.describe('分页功能', () => {
  40  |     test('切换页码加载不同数据', async ({ page }) => {
  41  |       // 先切换到10条/页确保有多页数据
  42  |       await page.locator('.el-pagination .el-select').click();
  43  |       await page.waitForTimeout(300);
  44  |       await page.getByRole('option', { name: '10条/页' }).click();
  45  |       await page.waitForTimeout(1500);
  46  | 
  47  |       const page2 = page.locator('.el-pager li:has-text("2")');
  48  |       if (await page2.count() === 0) {
  49  |         test.skip(true, '数据不足一页，跳过翻页测试');
  50  |         return;
  51  |       }
  52  |       const firstRowText = await page.locator('.el-table__row:first-child').textContent();
  53  |       await page2.click();
  54  |       await page.waitForTimeout(1500);
  55  |       const newFirstRowText = await page.locator('.el-table__row:first-child').textContent();
  56  |       expect(newFirstRowText).not.toBe(firstRowText);
  57  |     });
  58  | 
  59  |     test('修改每页条数', async ({ page }) => {
  60  |       const rowsBefore = await page.locator('.el-table__row').count();
  61  | 
  62  |       await page.locator('.el-pagination .el-select').click();
  63  |       await page.waitForTimeout(300);
  64  | 
  65  |       await page.getByRole('option', { name: '10条/页' }).click();
  66  |       await page.waitForTimeout(1000);
  67  | 
  68  |       const rowsAfter = await page.locator('.el-table__row').count();
  69  |       expect(rowsAfter).toBeLessThanOrEqual(10);
  70  |       expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
  71  |     });
  72  |   });
  73  | 
  74  |   // ========== 搜索 ==========
  75  |   test.describe('搜索功能', () => {
  76  |     test('名称搜索', async ({ page }) => {
  77  |       const searchInput = page.locator('input[placeholder="搜索供应商名称"]');
  78  |       await searchInput.fill('测试');
  79  |       await searchInput.press('Enter');
  80  |       await page.waitForTimeout(1000);
  81  | 
  82  |       const rows = await page.locator('.el-table__row').count();
  83  |       expect(rows).toBeGreaterThanOrEqual(0);
  84  |     });
  85  | 
  86  |     test('查询按钮触发搜索', async ({ page }) => {
  87  |       const searchInput = page.locator('input[placeholder="搜索供应商名称"]');
  88  |       await searchInput.fill('测试');
  89  |       await page.locator('.filter-bar button:has-text("查询")').click();
  90  |       await page.waitForTimeout(1000);
  91  | 
  92  |       const rows = await page.locator('.el-table__row').count();
  93  |       expect(rows).toBeGreaterThanOrEqual(0);
  94  |     });
  95  | 
  96  |     test('清空搜索恢复全部数据', async ({ page }) => {
  97  |       const allCount = await page.locator('.el-table__row').count();
  98  | 
  99  |       const searchInput = page.locator('input[placeholder="搜索供应商名称"]');
  100 |       await searchInput.fill('测试');
  101 |       await searchInput.press('Enter');
  102 |       await page.waitForTimeout(1000);
  103 | 
  104 |       const searchCount = await page.locator('.el-table__row').count();
  105 | 
  106 |       await searchInput.clear();
```