# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: products.spec.js >> 商品管理 >> 搜索功能 >> SKU精确匹配
- Location: tests\e2e\products.spec.js:79:5

# Error details

```
Error: locator.textContent: Error: strict mode violation: locator('.el-table__row:first-child') resolved to 2 elements:
    1) <tr class="el-table__row">…</tr> aka getByRole('row', { name: '选择当前行 SKU-信息系统 信息系统服务 服务 个 ¥0' })
    2) <tr class="el-table__row">…</tr> aka getByText('SKU-微电子组微电子组件商品个00正常¥0.00¥0.')

Call log:
  - waiting for locator('.el-table__row:first-child')

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
            - tab "商品目录" [selected] [ref=e121]
            - tab "库存明细" [ref=e122]
          - tabpanel "商品目录" [ref=e124]:
            - generic [ref=e126]:
              - generic [ref=e128]:
                - generic [ref=e129]: 商品列表
                - generic [ref=e130]:
                  - button "新增商品" [ref=e131] [cursor=pointer]:
                    - generic [ref=e132]:
                      - img [ref=e134]
                      - text: 新增商品
                  - button "批量导出" [disabled] [ref=e137]:
                    - generic [ref=e138]:
                      - img [ref=e140]
                      - text: 批量导出
              - generic [ref=e142]:
                - generic [ref=e143]:
                  - generic [ref=e144]:
                    - generic [ref=e146]:
                      - img [ref=e149]
                      - textbox "搜索名称/编码" [ref=e151]
                    - generic [ref=e153]:
                      - textbox "SKU精确匹配" [active] [ref=e154]: SKU-信息系统
                      - img [ref=e157] [cursor=pointer]
                    - generic [ref=e161] [cursor=pointer]:
                      - generic:
                        - combobox [ref=e163]
                        - generic [ref=e164]: 分类筛选
                      - img [ref=e167]
                  - generic [ref=e169]:
                    - button "查询" [ref=e170] [cursor=pointer]:
                      - generic [ref=e171]:
                        - img [ref=e173]
                        - text: 查询
                    - button "重置" [ref=e175] [cursor=pointer]:
                      - generic [ref=e176]: 重置
                - generic [ref=e178]:
                  - table [ref=e180]:
                    - rowgroup [ref=e192]:
                      - row "选择所有行 编码 商品名称 分类 单位 进价 售价 库存 预警线 操作" [ref=e193]:
                        - columnheader "选择所有行" [ref=e194]:
                          - generic "选择所有行" [ref=e196] [cursor=pointer]:
                            - generic [ref=e197]:
                              - checkbox "选择所有行"
                        - columnheader "编码" [ref=e199]:
                          - generic [ref=e200]: 编码
                        - columnheader "商品名称" [ref=e201]:
                          - generic [ref=e202]: 商品名称
                        - columnheader "分类" [ref=e203]:
                          - generic [ref=e204]: 分类
                        - columnheader "单位" [ref=e205]:
                          - generic [ref=e206]: 单位
                        - columnheader "进价" [ref=e207]:
                          - generic [ref=e208]: 进价
                        - columnheader "售价" [ref=e209]:
                          - generic [ref=e210]: 售价
                        - columnheader "库存" [ref=e211]:
                          - generic [ref=e212]: 库存
                        - columnheader "预警线" [ref=e213]:
                          - generic [ref=e214]: 预警线
                        - columnheader "操作" [ref=e215]:
                          - generic [ref=e216]: 操作
                  - table [ref=e221]:
                    - rowgroup [ref=e233]:
                      - row "选择当前行 SKU-信息系统 信息系统服务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e234]:
                        - cell "选择当前行" [ref=e235]:
                          - generic "选择当前行" [ref=e237] [cursor=pointer]:
                            - generic [ref=e238]:
                              - checkbox "选择当前行"
                        - cell "SKU-信息系统" [ref=e240]:
                          - generic [ref=e241]: SKU-信息系统
                        - cell "信息系统服务" [ref=e242]:
                          - generic [ref=e243]: 信息系统服务
                        - cell "服务" [ref=e244]:
                          - generic [ref=e245]: 服务
                        - cell "个" [ref=e246]:
                          - generic [ref=e247]: 个
                        - cell "¥0.00" [ref=e248]:
                          - generic [ref=e249]: ¥0.00
                        - cell "¥0.00" [ref=e250]:
                          - generic [ref=e251]: ¥0.00
                        - cell "0" [ref=e252]:
                          - generic [ref=e253]: "0"
                        - cell "0" [ref=e254]:
                          - generic [ref=e255]: "0"
                        - cell "编辑 删除" [ref=e256]:
                          - generic [ref=e258]:
                            - button "编辑" [ref=e259] [cursor=pointer]:
                              - generic [ref=e260]: 编辑
                            - button "删除" [ref=e261] [cursor=pointer]:
                              - generic [ref=e262]: 删除
                - generic [ref=e264]:
                  - generic [ref=e265]: 共 1 条
                  - generic [ref=e268] [cursor=pointer]:
                    - generic:
                      - combobox [ref=e270]
                      - generic [ref=e271]: 20条/页
                    - img [ref=e274]
                  - button "上一页" [disabled] [ref=e276]:
                    - generic:
                      - img
                  - list [ref=e277]:
                    - listitem "第 1 页" [ref=e278]: "1"
                  - button "下一页" [disabled] [ref=e279]:
                    - generic:
                      - img
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('商品管理', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     await page.goto('/products');
  6   |     await page.waitForSelector('.el-table__row', { timeout: 10000 });
  7   |   });
  8   | 
  9   |   // ========== 列表展示 ==========
  10  |   test.describe('列表展示', () => {
  11  |     test('商品列表正确展示后端数据', async ({ page }) => {
  12  |       const rows = await page.locator('.el-table__row').count();
  13  |       expect(rows).toBeGreaterThan(0);
  14  | 
  15  |       await expect(page.locator('th:has-text("编码")')).toBeVisible();
  16  |       await expect(page.locator('th:has-text("商品名称")')).toBeVisible();
  17  |       await expect(page.locator('th:has-text("分类")')).toBeVisible();
  18  |       await expect(page.locator('th:has-text("单位")')).toBeVisible();
  19  |       await expect(page.locator('th:has-text("进价")')).toBeVisible();
  20  |       await expect(page.locator('th:has-text("售价")')).toBeVisible();
  21  |       await expect(page.locator('th:has-text("库存")')).toBeVisible();
  22  |     });
  23  | 
  24  |     test('第一行数据包含有效内容', async ({ page }) => {
  25  |       const firstRow = page.locator('.el-table__row:first-child');
  26  |       const rowText = await firstRow.textContent();
  27  |       expect(rowText?.trim().length).toBeGreaterThan(5);
  28  |     });
  29  |   });
  30  | 
  31  |   // ========== 分页 ==========
  32  |   test.describe('分页功能', () => {
  33  |     test('切换页码加载不同数据', async ({ page }) => {
  34  |       // 先切换到10条/页确保有多页数据
  35  |       await page.locator('.el-pagination .el-select').click();
  36  |       await page.waitForTimeout(300);
  37  |       await page.getByRole('option', { name: '10条/页' }).click();
  38  |       await page.waitForTimeout(1500);
  39  | 
  40  |       const page2 = page.getByRole('listitem', { name: '第 2 页' });
  41  |       if (await page2.count() === 0) {
  42  |         test.skip(true, '数据不足一页，跳过翻页测试');
  43  |         return;
  44  |       }
  45  |       const firstRowText = await page.locator('.el-table__row:first-child').textContent();
  46  |       await page2.click();
  47  |       await page.waitForTimeout(1500);
  48  |       const newFirstRowText = await page.locator('.el-table__row:first-child').textContent();
  49  |       expect(newFirstRowText).not.toBe(firstRowText);
  50  |     });
  51  | 
  52  |     test('修改每页条数', async ({ page }) => {
  53  |       const rowsBefore = await page.locator('.el-table__row').count();
  54  | 
  55  |       await page.locator('.el-pagination .el-select').click();
  56  |       await page.waitForTimeout(300);
  57  | 
  58  |       await page.getByRole('option', { name: '10条/页' }).click();
  59  |       await page.waitForTimeout(1000);
  60  | 
  61  |       const rowsAfter = await page.locator('.el-table__row').count();
  62  |       expect(rowsAfter).toBeLessThanOrEqual(10);
  63  |       expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
  64  |     });
  65  |   });
  66  | 
  67  |   // ========== 搜索 ==========
  68  |   test.describe('搜索功能', () => {
  69  |     test('名称/编码搜索', async ({ page }) => {
  70  |       const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
  71  |       await searchInput.fill('测试');
  72  |       await searchInput.press('Enter');
  73  |       await page.waitForTimeout(1000);
  74  | 
  75  |       const rows = await page.locator('.el-table__row').count();
  76  |       expect(rows).toBeGreaterThanOrEqual(0);
  77  |     });
  78  | 
  79  |     test('SKU精确匹配', async ({ page }) => {
  80  |       const firstSku = await page.locator('.el-table__row:first-child td').nth(1).textContent();
  81  |       const skuValue = firstSku?.trim();
  82  | 
  83  |       if (!skuValue) {
  84  |         test.skip();
  85  |         return;
  86  |       }
  87  | 
  88  |       const skuInput = page.locator('input[placeholder="SKU精确匹配"]');
  89  |       await skuInput.fill(skuValue);
  90  |       await skuInput.press('Enter');
  91  |       await page.waitForTimeout(1000);
  92  | 
  93  |       const rows = await page.locator('.el-table__row').count();
  94  |       expect(rows).toBeGreaterThanOrEqual(1);
  95  | 
> 96  |       const rowText = await page.locator('.el-table__row:first-child').textContent();
      |                                                                        ^ Error: locator.textContent: Error: strict mode violation: locator('.el-table__row:first-child') resolved to 2 elements:
  97  |       expect(rowText).toContain(skuValue);
  98  |     });
  99  | 
  100 |     test('查询按钮触发搜索', async ({ page }) => {
  101 |       const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
  102 |       await searchInput.fill('测试');
  103 |       await page.locator('button:has-text("查询")').click();
  104 |       await page.waitForTimeout(1000);
  105 | 
  106 |       const rows = await page.locator('.el-table__row').count();
  107 |       expect(rows).toBeGreaterThanOrEqual(0);
  108 |     });
  109 | 
  110 |     test('清空搜索恢复全部数据', async ({ page }) => {
  111 |       const allCount = await page.locator('.el-table__row').count();
  112 | 
  113 |       const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
  114 |       await searchInput.fill('测试');
  115 |       await searchInput.press('Enter');
  116 |       await page.waitForTimeout(1000);
  117 | 
  118 |       const searchCount = await page.locator('.el-table__row').count();
  119 | 
  120 |       await searchInput.clear();
  121 |       await searchInput.press('Enter');
  122 |       await page.waitForTimeout(1000);
  123 | 
  124 |       const restoredCount = await page.locator('.el-table__row').count();
  125 |       expect(restoredCount).toBe(allCount);
  126 |       expect(searchCount).toBeLessThanOrEqual(restoredCount);
  127 |     });
  128 |   });
  129 | 
  130 |   // ========== 分类筛选 ==========
  131 |   test.describe('分类筛选', () => {
  132 |     test('按分类筛选商品', async ({ page }) => {
  133 |       const allCount = await page.locator('.el-table__row').count();
  134 | 
  135 |       const categorySelect = page.locator('.filter-bar .el-select');
  136 |       await categorySelect.click();
  137 |       await page.waitForTimeout(300);
  138 | 
  139 |       const dropdown = page.locator('.el-select-dropdown:visible');
  140 |       const options = dropdown.locator('li');
  141 |       const optionCount = await options.count();
  142 | 
  143 |       if (optionCount > 0) {
  144 |         await options.first().click();
  145 |         await page.waitForTimeout(1000);
  146 | 
  147 |         const filteredCount = await page.locator('.el-table__row').count();
  148 |         expect(filteredCount).toBeGreaterThanOrEqual(0);
  149 |         expect(filteredCount).toBeLessThanOrEqual(allCount);
  150 |       }
  151 |     });
  152 |   });
  153 | 
  154 |   // ========== 新增商品 ==========
  155 |   test.describe('新增商品', () => {
  156 |     test('打开新增对话框', async ({ page }) => {
  157 |       await page.locator('button:has-text("新增商品")').click();
  158 | 
  159 |       await expect(page.locator('.el-dialog')).toBeVisible();
  160 |       await expect(page.locator('.el-dialog__title')).toContainText('新增商品');
  161 |     });
  162 | 
  163 |     test('新增商品成功', async ({ page }) => {
  164 |       const timestamp = Date.now();
  165 |       const productName = `PW测试-${timestamp}`;
  166 |       const productSku = `PW-${timestamp}`;
  167 | 
  168 |       await page.locator('button:has-text("新增商品")').click();
  169 | 
  170 |       await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill(productName);
  171 |       await page.locator('.el-dialog .el-form-item:has-text("编码") input').fill(productSku);
  172 |       await page.locator('.el-dialog .el-form-item:has-text("分类") input').fill('测试分类');
  173 |       await page.locator('.el-dialog .el-form-item:has-text("单位") input').fill('个');
  174 | 
  175 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  176 | 
  177 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  178 |       await expect(page.locator('.el-dialog')).not.toBeVisible();
  179 | 
  180 |       await page.waitForTimeout(1000);
  181 | 
  182 |       const searchInput = page.locator('input[placeholder="SKU精确匹配"]');
  183 |       await searchInput.fill(productSku);
  184 |       await searchInput.press('Enter');
  185 |       await page.waitForTimeout(1000);
  186 | 
  187 |       const rows = await page.locator('.el-table__row').count();
  188 |       expect(rows).toBe(1);
  189 | 
  190 |       const cellText = await page.locator('.el-table__row:first-child').textContent();
  191 |       expect(cellText).toContain(productSku);
  192 |     });
  193 | 
  194 |     test('新增商品表单校验', async ({ page }) => {
  195 |       await page.locator('button:has-text("新增商品")').click();
  196 | 
```