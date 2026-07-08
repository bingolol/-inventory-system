# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: inventory.spec.js >> 库存管理 >> 列表展示 >> 库存列表正确展示后端数据
- Location: tests\e2e\inventory.spec.js:12:5

# Error details

```
TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
Call log:
  - waiting for locator('.el-table__row') to be visible
    24 × locator resolved to 11 elements. Proceeding with the first one: <tr class="el-table__row">…</tr>

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
        - heading "库存商品" [level=2] [ref=e99]
        - generic [ref=e100]: 商品目录 · 库存明细
      - generic [ref=e101]:
        - button "A admin" [ref=e103] [cursor=pointer]:
          - generic [ref=e104]: A
          - generic [ref=e105]: admin
          - img [ref=e107]
        - text: 2026/07/07周二
    - main [ref=e109]:
      - generic [ref=e110]:
        - generic [ref=e113]: 库存商品
        - generic [ref=e115]:
          - tablist [ref=e119]:
            - tab "商品目录" [ref=e121]
            - tab "库存明细" [selected] [ref=e122]
          - tabpanel "库存明细" [ref=e124]:
            - generic [ref=e126]:
              - generic [ref=e128]:
                - generic [ref=e129]: 库存管理
                - button "导出" [ref=e132] [cursor=pointer]:
                  - generic [ref=e133]:
                    - img [ref=e135]
                    - text: 导出
              - generic [ref=e137]:
                - generic [ref=e138]:
                  - generic [ref=e139]:
                    - generic [ref=e141]:
                      - img [ref=e144]
                      - textbox "搜索商品名称/编码" [ref=e146]
                    - generic [ref=e148] [cursor=pointer]:
                      - generic:
                        - combobox [ref=e150]
                        - generic [ref=e151]: 分类筛选
                      - img [ref=e154]
                    - generic [ref=e156]:
                      - switch
                      - generic [ref=e160] [cursor=pointer]: 仅显示预警
                  - generic [ref=e161]:
                    - button "查询" [ref=e162] [cursor=pointer]:
                      - generic [ref=e163]:
                        - img [ref=e165]
                        - text: 查询
                    - button "重置" [ref=e167] [cursor=pointer]:
                      - generic [ref=e168]: 重置
                - generic [ref=e170]:
                  - table [ref=e172]:
                    - rowgroup [ref=e185]:
                      - row "编码 商品名称 分类 单位 当前库存 预警线 预警 进价 售价 库存价值 操作" [ref=e186]:
                        - columnheader "编码" [ref=e187]:
                          - generic [ref=e188]: 编码
                        - columnheader "商品名称" [ref=e189]:
                          - generic [ref=e190]: 商品名称
                        - columnheader "分类" [ref=e191]:
                          - generic [ref=e192]: 分类
                        - columnheader "单位" [ref=e193]:
                          - generic [ref=e194]: 单位
                        - columnheader "当前库存" [ref=e195]:
                          - generic [ref=e196]: 当前库存
                        - columnheader "预警线" [ref=e197]:
                          - generic [ref=e198]: 预警线
                        - columnheader "预警" [ref=e199]:
                          - generic [ref=e200]: 预警
                        - columnheader "进价" [ref=e201]:
                          - generic [ref=e202]: 进价
                        - columnheader "售价" [ref=e203]:
                          - generic [ref=e204]: 售价
                        - columnheader "库存价值" [ref=e205]:
                          - generic [ref=e206]: 库存价值
                        - columnheader "操作" [ref=e207]:
                          - generic [ref=e208]: 操作
                  - table [ref=e213]:
                    - rowgroup [ref=e226]:
                      - row "SKU-微电子组 微电子组件 商品 个 0 0 正常 ¥0.00 ¥0.00 ¥0.00 盘点" [ref=e227]:
                        - cell "SKU-微电子组" [ref=e228]:
                          - generic [ref=e229]: SKU-微电子组
                        - cell "微电子组件" [ref=e230]:
                          - generic [ref=e231]: 微电子组件
                        - cell "商品" [ref=e232]:
                          - generic [ref=e233]: 商品
                        - cell "个" [ref=e234]:
                          - generic [ref=e235]: 个
                        - cell "0" [ref=e236]:
                          - generic [ref=e237]: "0"
                        - cell "0" [ref=e238]:
                          - generic [ref=e239]: "0"
                        - cell "正常" [ref=e240]:
                          - generic [ref=e242]: 正常
                        - cell "¥0.00" [ref=e243]:
                          - generic [ref=e244]: ¥0.00
                        - cell "¥0.00" [ref=e245]:
                          - generic [ref=e246]: ¥0.00
                        - cell "¥0.00" [ref=e247]:
                          - generic [ref=e248]: ¥0.00
                        - cell "盘点" [ref=e249]:
                          - button "盘点" [ref=e252] [cursor=pointer]:
                            - generic [ref=e253]: 盘点
                      - row "SKU-维修备件 维修备件 商品 个 5 0 正常 ¥0.00 ¥0.00 ¥0.00 盘点" [ref=e254]:
                        - cell "SKU-维修备件" [ref=e255]:
                          - generic [ref=e256]: SKU-维修备件
                        - cell "维修备件" [ref=e257]:
                          - generic [ref=e258]: 维修备件
                        - cell "商品" [ref=e259]:
                          - generic [ref=e260]: 商品
                        - cell "个" [ref=e261]:
                          - generic [ref=e262]: 个
                        - cell "5" [ref=e263]:
                          - generic [ref=e264]: "5"
                        - cell "0" [ref=e265]:
                          - generic [ref=e266]: "0"
                        - cell "正常" [ref=e267]:
                          - generic [ref=e269]: 正常
                        - cell "¥0.00" [ref=e270]:
                          - generic [ref=e271]: ¥0.00
                        - cell "¥0.00" [ref=e272]:
                          - generic [ref=e273]: ¥0.00
                        - cell "¥0.00" [ref=e274]:
                          - generic [ref=e275]: ¥0.00
                        - cell "盘点" [ref=e276]:
                          - button "盘点" [ref=e279] [cursor=pointer]:
                            - generic [ref=e280]: 盘点
                      - row "个 0 0 正常 ¥0.00 ¥0.00 ¥0.00 盘点" [ref=e281]:
                        - cell [ref=e282]
                        - cell [ref=e283]
                        - cell [ref=e284]
                        - cell "个" [ref=e285]:
                          - generic [ref=e286]: 个
                        - cell "0" [ref=e287]:
                          - generic [ref=e288]: "0"
                        - cell "0" [ref=e289]:
                          - generic [ref=e290]: "0"
                        - cell "正常" [ref=e291]:
                          - generic [ref=e293]: 正常
                        - cell "¥0.00" [ref=e294]:
                          - generic [ref=e295]: ¥0.00
                        - cell "¥0.00" [ref=e296]:
                          - generic [ref=e297]: ¥0.00
                        - cell "¥0.00" [ref=e298]:
                          - generic [ref=e299]: ¥0.00
                        - cell "盘点" [ref=e300]:
                          - button "盘点" [ref=e303] [cursor=pointer]:
                            - generic [ref=e304]: 盘点
                      - row "个 0 0 正常 ¥0.00 ¥0.00 ¥0.00 盘点" [ref=e305]:
                        - cell [ref=e306]
                        - cell [ref=e307]
                        - cell [ref=e308]
                        - cell "个" [ref=e309]:
                          - generic [ref=e310]: 个
                        - cell "0" [ref=e311]:
                          - generic [ref=e312]: "0"
                        - cell "0" [ref=e313]:
                          - generic [ref=e314]: "0"
                        - cell "正常" [ref=e315]:
                          - generic [ref=e317]: 正常
                        - cell "¥0.00" [ref=e318]:
                          - generic [ref=e319]: ¥0.00
                        - cell "¥0.00" [ref=e320]:
                          - generic [ref=e321]: ¥0.00
                        - cell "¥0.00" [ref=e322]:
                          - generic [ref=e323]: ¥0.00
                        - cell "盘点" [ref=e324]:
                          - button "盘点" [ref=e327] [cursor=pointer]:
                            - generic [ref=e328]: 盘点
                - generic [ref=e330]:
                  - generic [ref=e331]: 共 4 条
                  - generic [ref=e334] [cursor=pointer]:
                    - generic:
                      - combobox [ref=e336]
                      - generic [ref=e337]: 20条/页
                    - img [ref=e340]
                  - button "上一页" [disabled] [ref=e342]:
                    - generic:
                      - img
                  - list [ref=e343]:
                    - listitem "第 1 页" [ref=e344]: "1"
                  - button "下一页" [disabled] [ref=e345]:
                    - generic:
                      - img
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('库存管理', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/inventory');
  6   |     await page.waitForTimeout(800);
> 7   |     await page.waitForSelector('.el-table__row', { timeout: 10000 });
      |                ^ TimeoutError: page.waitForSelector: Timeout 10000ms exceeded.
  8   |   });
  9   | 
  10  |   // ========== 列表展示 ==========
  11  |   test.describe('列表展示', () => {
  12  |     test('库存列表正确展示后端数据', async ({ page }) => {
  13  |       const rows = await page.locator('.el-table__row').count();
  14  |       expect(rows).toBeGreaterThan(0);
  15  | 
  16  |       await expect(page.locator('th:has-text("编码")')).toBeVisible();
  17  |       await expect(page.locator('th:has-text("商品名称")')).toBeVisible();
  18  |       await expect(page.locator('th:has-text("分类")')).toBeVisible();
  19  |       await expect(page.locator('th:has-text("单位")')).toBeVisible();
  20  |       await expect(page.locator('th:has-text("当前库存")')).toBeVisible();
  21  |       await expect(page.locator('th:has-text("预警线")')).toBeVisible();
  22  |       await expect(page.getByRole('columnheader', { name: '预警', exact: true })).toBeVisible();
  23  |       await expect(page.locator('th:has-text("进价")')).toBeVisible();
  24  |       await expect(page.locator('th:has-text("售价")')).toBeVisible();
  25  |       await expect(page.locator('th:has-text("库存价值")')).toBeVisible();
  26  |       await expect(page.locator('th:has-text("操作")')).toBeVisible();
  27  |     });
  28  | 
  29  |     test('第一行数据包含有效内容', async ({ page }) => {
  30  |       const firstRow = page.locator('.el-table__row:first-child');
  31  |       const rowText = await firstRow.textContent();
  32  |       expect(rowText?.trim().length).toBeGreaterThan(5);
  33  |     });
  34  | 
  35  |     test('库存数量显示正确格式', async ({ page }) => {
  36  |       const firstRow = page.locator('.el-table__row:first-child');
  37  |       const stockCell = firstRow.locator('td').nth(4);
  38  |       const stockText = await stockCell.textContent();
  39  |       expect(stockText?.trim()).toMatch(/^-?\d+$/);
  40  |     });
  41  | 
  42  |     test('价格显示包含货币符号', async ({ page }) => {
  43  |       const firstRow = page.locator('.el-table__row:first-child');
  44  |       const purchasePrice = await firstRow.locator('td').nth(7).textContent();
  45  |       const salePrice = await firstRow.locator('td').nth(8).textContent();
  46  |       expect(purchasePrice?.trim()).toMatch(/^¥[\d,.]+$/);
  47  |       expect(salePrice?.trim()).toMatch(/^¥[\d,.]+$/);
  48  |     });
  49  |   });
  50  | 
  51  |   // ========== 搜索功能 ==========
  52  |   test.describe('搜索功能', () => {
  53  |     test('关键词搜索商品', async ({ page }) => {
  54  |       const searchInput = page.locator('input[placeholder="搜索商品名称/编码"]');
  55  |       await searchInput.fill('测试');
  56  |       await searchInput.press('Enter');
  57  |       await page.waitForTimeout(1000);
  58  | 
  59  |       const rows = await page.locator('.el-table__row').count();
  60  |       expect(rows).toBeGreaterThanOrEqual(0);
  61  |     });
  62  | 
  63  |     test('查询按钮触发搜索', async ({ page }) => {
  64  |       const searchInput = page.locator('input[placeholder="搜索商品名称/编码"]');
  65  |       await searchInput.fill('测试');
  66  |       await page.locator('button:has-text("查询")').click();
  67  |       await page.waitForTimeout(1000);
  68  | 
  69  |       const rows = await page.locator('.el-table__row').count();
  70  |       expect(rows).toBeGreaterThanOrEqual(0);
  71  |     });
  72  | 
  73  |     test('清空搜索恢复全部数据', async ({ page }) => {
  74  |       const allCount = await page.locator('.el-table__row').count();
  75  | 
  76  |       const searchInput = page.locator('input[placeholder="搜索商品名称/编码"]');
  77  |       await searchInput.fill('测试');
  78  |       await searchInput.press('Enter');
  79  |       await page.waitForTimeout(1000);
  80  | 
  81  |       const searchCount = await page.locator('.el-table__row').count();
  82  | 
  83  |       await searchInput.clear();
  84  |       await searchInput.press('Enter');
  85  |       await page.waitForTimeout(1000);
  86  | 
  87  |       const restoredCount = await page.locator('.el-table__row').count();
  88  |       expect(restoredCount).toBe(allCount);
  89  |       expect(searchCount).toBeLessThanOrEqual(restoredCount);
  90  |     });
  91  |   });
  92  | 
  93  |   // ========== 分类筛选 ==========
  94  |   test.describe('分类筛选', () => {
  95  |     test('按分类筛选商品', async ({ page }) => {
  96  |       const allCount = await page.locator('.el-table__row').count();
  97  | 
  98  |       const categorySelect = page.locator('.filter-bar .el-select');
  99  |       await categorySelect.click();
  100 |       await page.waitForTimeout(500);
  101 | 
  102 |       // 使用 .last() 避免 strict mode
  103 |       const dropdown = page.locator('.el-select-dropdown:visible').last();
  104 |       const options = dropdown.locator('li');
  105 |       const optionCount = await options.count();
  106 | 
  107 |       if (optionCount > 0) {
```