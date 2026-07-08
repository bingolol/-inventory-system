# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: products.spec.js >> 商品管理 >> 列表展示 >> 商品列表正确展示后端数据
- Location: tests\e2e\products.spec.js:11:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('th:has-text("编码")')
Expected: visible
Error: strict mode violation: locator('th:has-text("编码")') resolved to 2 elements:
    1) <th colspan="1" rowspan="1" scope="col" class="el-table_1_column_2 is-leaf el-table__cell">…</th> aka getByRole('columnheader', { name: '编码' })
    2) <th colspan="1" rowspan="1" scope="col" class="el-table_2_column_11 is-leaf el-table__cell">…</th> aka getByLabel('库存明细').locator('th').filter({ hasText: '编码' })

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('th:has-text("编码")')

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
                    - textbox "SKU精确匹配" [ref=e154]
                    - generic [ref=e156] [cursor=pointer]:
                      - generic:
                        - combobox [ref=e158]
                        - generic [ref=e159]: 分类筛选
                      - img [ref=e162]
                  - generic [ref=e164]:
                    - button "查询" [ref=e165] [cursor=pointer]:
                      - generic [ref=e166]:
                        - img [ref=e168]
                        - text: 查询
                    - button "重置" [ref=e170] [cursor=pointer]:
                      - generic [ref=e171]: 重置
                - generic [ref=e172]:
                  - generic [ref=e173]:
                    - table [ref=e175]:
                      - rowgroup [ref=e187]:
                        - row "选择所有行 编码 商品名称 分类 单位 进价 售价 库存 预警线 操作" [ref=e188]:
                          - columnheader "选择所有行" [ref=e189]:
                            - generic "选择所有行" [ref=e191] [cursor=pointer]:
                              - generic [ref=e192]:
                                - checkbox "选择所有行"
                          - columnheader "编码" [ref=e194]:
                            - generic [ref=e195]: 编码
                          - columnheader "商品名称" [ref=e196]:
                            - generic [ref=e197]: 商品名称
                          - columnheader "分类" [ref=e198]:
                            - generic [ref=e199]: 分类
                          - columnheader "单位" [ref=e200]:
                            - generic [ref=e201]: 单位
                          - columnheader "进价" [ref=e202]:
                            - generic [ref=e203]: 进价
                          - columnheader "售价" [ref=e204]:
                            - generic [ref=e205]: 售价
                          - columnheader "库存" [ref=e206]:
                            - generic [ref=e207]: 库存
                          - columnheader "预警线" [ref=e208]:
                            - generic [ref=e209]: 预警线
                          - columnheader "操作" [ref=e210]:
                            - generic [ref=e211]: 操作
                    - table [ref=e216]:
                      - rowgroup [ref=e228]:
                        - row "选择当前行 SKU-信息系统 信息系统服务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e229]:
                          - cell "选择当前行" [ref=e230]:
                            - generic "选择当前行" [ref=e232] [cursor=pointer]:
                              - generic [ref=e233]:
                                - checkbox "选择当前行"
                          - cell "SKU-信息系统" [ref=e235]:
                            - generic [ref=e236]: SKU-信息系统
                          - cell "信息系统服务" [ref=e237]:
                            - generic [ref=e238]: 信息系统服务
                          - cell "服务" [ref=e239]:
                            - generic [ref=e240]: 服务
                          - cell "个" [ref=e241]:
                            - generic [ref=e242]: 个
                          - cell "¥0.00" [ref=e243]:
                            - generic [ref=e244]: ¥0.00
                          - cell "¥0.00" [ref=e245]:
                            - generic [ref=e246]: ¥0.00
                          - cell "0" [ref=e247]:
                            - generic [ref=e248]: "0"
                          - cell "0" [ref=e249]:
                            - generic [ref=e250]: "0"
                          - cell "编辑 删除" [ref=e251]:
                            - generic [ref=e253]:
                              - button "编辑" [ref=e254] [cursor=pointer]:
                                - generic [ref=e255]: 编辑
                              - button "删除" [ref=e256] [cursor=pointer]:
                                - generic [ref=e257]: 删除
                        - row "选择当前行 SKU-修理修配 修理修配劳务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e258]:
                          - cell "选择当前行" [ref=e259]:
                            - generic "选择当前行" [ref=e261] [cursor=pointer]:
                              - generic [ref=e262]:
                                - checkbox "选择当前行"
                          - cell "SKU-修理修配" [ref=e264]:
                            - generic [ref=e265]: SKU-修理修配
                          - cell "修理修配劳务" [ref=e266]:
                            - generic [ref=e267]: 修理修配劳务
                          - cell "服务" [ref=e268]:
                            - generic [ref=e269]: 服务
                          - cell "个" [ref=e270]:
                            - generic [ref=e271]: 个
                          - cell "¥0.00" [ref=e272]:
                            - generic [ref=e273]: ¥0.00
                          - cell "¥0.00" [ref=e274]:
                            - generic [ref=e275]: ¥0.00
                          - cell "0" [ref=e276]:
                            - generic [ref=e277]: "0"
                          - cell "0" [ref=e278]:
                            - generic [ref=e279]: "0"
                          - cell "编辑 删除" [ref=e280]:
                            - generic [ref=e282]:
                              - button "编辑" [ref=e283] [cursor=pointer]:
                                - generic [ref=e284]: 编辑
                              - button "删除" [ref=e285] [cursor=pointer]:
                                - generic [ref=e286]: 删除
                        - row "选择当前行 SKU-微电子组 微电子组件 商品 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e287]:
                          - cell "选择当前行" [ref=e288]:
                            - generic "选择当前行" [ref=e290] [cursor=pointer]:
                              - generic [ref=e291]:
                                - checkbox "选择当前行"
                          - cell "SKU-微电子组" [ref=e293]:
                            - generic [ref=e294]: SKU-微电子组
                          - cell "微电子组件" [ref=e295]:
                            - generic [ref=e296]: 微电子组件
                          - cell "商品" [ref=e297]:
                            - generic [ref=e298]: 商品
                          - cell "个" [ref=e299]:
                            - generic [ref=e300]: 个
                          - cell "¥0.00" [ref=e301]:
                            - generic [ref=e302]: ¥0.00
                          - cell "¥0.00" [ref=e303]:
                            - generic [ref=e304]: ¥0.00
                          - cell "0" [ref=e305]:
                            - generic [ref=e306]: "0"
                          - cell "0" [ref=e307]:
                            - generic [ref=e308]: "0"
                          - cell "编辑 删除" [ref=e309]:
                            - generic [ref=e311]:
                              - button "编辑" [ref=e312] [cursor=pointer]:
                                - generic [ref=e313]: 编辑
                              - button "删除" [ref=e314] [cursor=pointer]:
                                - generic [ref=e315]: 删除
                        - row "选择当前行 SKU-其他加工 其他加工劳务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e316]:
                          - cell "选择当前行" [ref=e317]:
                            - generic "选择当前行" [ref=e319] [cursor=pointer]:
                              - generic [ref=e320]:
                                - checkbox "选择当前行"
                          - cell "SKU-其他加工" [ref=e322]:
                            - generic [ref=e323]: SKU-其他加工
                          - cell "其他加工劳务" [ref=e324]:
                            - generic [ref=e325]: 其他加工劳务
                          - cell "服务" [ref=e326]:
                            - generic [ref=e327]: 服务
                          - cell "个" [ref=e328]:
                            - generic [ref=e329]: 个
                          - cell "¥0.00" [ref=e330]:
                            - generic [ref=e331]: ¥0.00
                          - cell "¥0.00" [ref=e332]:
                            - generic [ref=e333]: ¥0.00
                          - cell "0" [ref=e334]:
                            - generic [ref=e335]: "0"
                          - cell "0" [ref=e336]:
                            - generic [ref=e337]: "0"
                          - cell "编辑 删除" [ref=e338]:
                            - generic [ref=e340]:
                              - button "编辑" [ref=e341] [cursor=pointer]:
                                - generic [ref=e342]: 编辑
                              - button "删除" [ref=e343] [cursor=pointer]:
                                - generic [ref=e344]: 删除
                        - row "选择当前行 SKU-维修备件 维修备件 商品 个 ¥0.00 ¥0.00 5 0 编辑 删除" [ref=e345]:
                          - cell "选择当前行" [ref=e346]:
                            - generic "选择当前行" [ref=e348] [cursor=pointer]:
                              - generic [ref=e349]:
                                - checkbox "选择当前行"
                          - cell "SKU-维修备件" [ref=e351]:
                            - generic [ref=e352]: SKU-维修备件
                          - cell "维修备件" [ref=e353]:
                            - generic [ref=e354]: 维修备件
                          - cell "商品" [ref=e355]:
                            - generic [ref=e356]: 商品
                          - cell "个" [ref=e357]:
                            - generic [ref=e358]: 个
                          - cell "¥0.00" [ref=e359]:
                            - generic [ref=e360]: ¥0.00
                          - cell "¥0.00" [ref=e361]:
                            - generic [ref=e362]: ¥0.00
                          - cell "5" [ref=e363]:
                            - generic [ref=e364]: "5"
                          - cell "0" [ref=e365]:
                            - generic [ref=e366]: "0"
                          - cell "编辑 删除" [ref=e367]:
                            - generic [ref=e369]:
                              - button "编辑" [ref=e370] [cursor=pointer]:
                                - generic [ref=e371]: 编辑
                              - button "删除" [ref=e372] [cursor=pointer]:
                                - generic [ref=e373]: 删除
                        - row "选择当前行 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e374]:
                          - cell "选择当前行" [ref=e375]:
                            - generic "选择当前行" [ref=e377] [cursor=pointer]:
                              - generic [ref=e378]:
                                - checkbox "选择当前行"
                          - cell [ref=e380]
                          - cell [ref=e381]
                          - cell [ref=e382]
                          - cell "个" [ref=e383]:
                            - generic [ref=e384]: 个
                          - cell "¥0.00" [ref=e385]:
                            - generic [ref=e386]: ¥0.00
                          - cell "¥0.00" [ref=e387]:
                            - generic [ref=e388]: ¥0.00
                          - cell "0" [ref=e389]:
                            - generic [ref=e390]: "0"
                          - cell "0" [ref=e391]:
                            - generic [ref=e392]: "0"
                          - cell "编辑 删除" [ref=e393]:
                            - generic [ref=e395]:
                              - button "编辑" [ref=e396] [cursor=pointer]:
                                - generic [ref=e397]: 编辑
                              - button "删除" [ref=e398] [cursor=pointer]:
                                - generic [ref=e399]: 删除
                        - row "选择当前行 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e400]:
                          - cell "选择当前行" [ref=e401]:
                            - generic "选择当前行" [ref=e403] [cursor=pointer]:
                              - generic [ref=e404]:
                                - checkbox "选择当前行"
                          - cell [ref=e406]
                          - cell [ref=e407]
                          - cell [ref=e408]
                          - cell "个" [ref=e409]:
                            - generic [ref=e410]: 个
                          - cell "¥0.00" [ref=e411]:
                            - generic [ref=e412]: ¥0.00
                          - cell "¥0.00" [ref=e413]:
                            - generic [ref=e414]: ¥0.00
                          - cell "0" [ref=e415]:
                            - generic [ref=e416]: "0"
                          - cell "0" [ref=e417]:
                            - generic [ref=e418]: "0"
                          - cell "编辑 删除" [ref=e419]:
                            - generic [ref=e421]:
                              - button "编辑" [ref=e422] [cursor=pointer]:
                                - generic [ref=e423]: 编辑
                              - button "删除" [ref=e424] [cursor=pointer]:
                                - generic [ref=e425]: 删除
                  - img [ref=e428]
                - generic [ref=e431]:
                  - generic [ref=e432]: 共 7 条
                  - generic [ref=e435] [cursor=pointer]:
                    - generic:
                      - combobox [ref=e437]
                      - generic [ref=e438]: 20条/页
                    - img [ref=e441]
                  - button "上一页" [disabled] [ref=e443]:
                    - generic:
                      - img
                  - list [ref=e444]:
                    - listitem "第 1 页" [ref=e445]: "1"
                  - button "下一页" [disabled] [ref=e446]:
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
> 15  |       await expect(page.locator('th:has-text("编码")')).toBeVisible();
      |                                                       ^ Error: expect(locator).toBeVisible() failed
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
  96  |       const rowText = await page.locator('.el-table__row:first-child').textContent();
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
```