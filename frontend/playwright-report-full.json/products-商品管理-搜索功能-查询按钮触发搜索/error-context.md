# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: products.spec.js >> 商品管理 >> 搜索功能 >> 查询按钮触发搜索
- Location: tests\e2e\products.spec.js:100:5

# Error details

```
Error: locator.click: Error: strict mode violation: locator('button:has-text("查询")') resolved to 2 elements:
    1) <button type="button" data-v-f4672e2a="" aria-disabled="false" class="el-button el-button--primary">…</button> aka getByRole('button', { name: '查询' })
    2) <button type="button" data-v-f4672e2a="" aria-disabled="false" class="el-button el-button--primary">…</button> aka getByLabel('库存明细').locator('button').filter({ hasText: '查询' })

Call log:
  - waiting for locator('button:has-text("查询")')

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
                      - textbox "搜索名称/编码" [active] [ref=e151]: 测试
                      - img [ref=e154] [cursor=pointer]
                    - textbox "SKU精确匹配" [ref=e159]
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
                - generic [ref=e177]:
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
                        - row "选择当前行 SKU-修理修配 修理修配劳务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e263]:
                          - cell "选择当前行" [ref=e264]:
                            - generic "选择当前行" [ref=e266] [cursor=pointer]:
                              - generic [ref=e267]:
                                - checkbox "选择当前行"
                          - cell "SKU-修理修配" [ref=e269]:
                            - generic [ref=e270]: SKU-修理修配
                          - cell "修理修配劳务" [ref=e271]:
                            - generic [ref=e272]: 修理修配劳务
                          - cell "服务" [ref=e273]:
                            - generic [ref=e274]: 服务
                          - cell "个" [ref=e275]:
                            - generic [ref=e276]: 个
                          - cell "¥0.00" [ref=e277]:
                            - generic [ref=e278]: ¥0.00
                          - cell "¥0.00" [ref=e279]:
                            - generic [ref=e280]: ¥0.00
                          - cell "0" [ref=e281]:
                            - generic [ref=e282]: "0"
                          - cell "0" [ref=e283]:
                            - generic [ref=e284]: "0"
                          - cell "编辑 删除" [ref=e285]:
                            - generic [ref=e287]:
                              - button "编辑" [ref=e288] [cursor=pointer]:
                                - generic [ref=e289]: 编辑
                              - button "删除" [ref=e290] [cursor=pointer]:
                                - generic [ref=e291]: 删除
                        - row "选择当前行 SKU-微电子组 微电子组件 商品 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e292]:
                          - cell "选择当前行" [ref=e293]:
                            - generic "选择当前行" [ref=e295] [cursor=pointer]:
                              - generic [ref=e296]:
                                - checkbox "选择当前行"
                          - cell "SKU-微电子组" [ref=e298]:
                            - generic [ref=e299]: SKU-微电子组
                          - cell "微电子组件" [ref=e300]:
                            - generic [ref=e301]: 微电子组件
                          - cell "商品" [ref=e302]:
                            - generic [ref=e303]: 商品
                          - cell "个" [ref=e304]:
                            - generic [ref=e305]: 个
                          - cell "¥0.00" [ref=e306]:
                            - generic [ref=e307]: ¥0.00
                          - cell "¥0.00" [ref=e308]:
                            - generic [ref=e309]: ¥0.00
                          - cell "0" [ref=e310]:
                            - generic [ref=e311]: "0"
                          - cell "0" [ref=e312]:
                            - generic [ref=e313]: "0"
                          - cell "编辑 删除" [ref=e314]:
                            - generic [ref=e316]:
                              - button "编辑" [ref=e317] [cursor=pointer]:
                                - generic [ref=e318]: 编辑
                              - button "删除" [ref=e319] [cursor=pointer]:
                                - generic [ref=e320]: 删除
                        - row "选择当前行 SKU-其他加工 其他加工劳务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e321]:
                          - cell "选择当前行" [ref=e322]:
                            - generic "选择当前行" [ref=e324] [cursor=pointer]:
                              - generic [ref=e325]:
                                - checkbox "选择当前行"
                          - cell "SKU-其他加工" [ref=e327]:
                            - generic [ref=e328]: SKU-其他加工
                          - cell "其他加工劳务" [ref=e329]:
                            - generic [ref=e330]: 其他加工劳务
                          - cell "服务" [ref=e331]:
                            - generic [ref=e332]: 服务
                          - cell "个" [ref=e333]:
                            - generic [ref=e334]: 个
                          - cell "¥0.00" [ref=e335]:
                            - generic [ref=e336]: ¥0.00
                          - cell "¥0.00" [ref=e337]:
                            - generic [ref=e338]: ¥0.00
                          - cell "0" [ref=e339]:
                            - generic [ref=e340]: "0"
                          - cell "0" [ref=e341]:
                            - generic [ref=e342]: "0"
                          - cell "编辑 删除" [ref=e343]:
                            - generic [ref=e345]:
                              - button "编辑" [ref=e346] [cursor=pointer]:
                                - generic [ref=e347]: 编辑
                              - button "删除" [ref=e348] [cursor=pointer]:
                                - generic [ref=e349]: 删除
                        - row "选择当前行 SKU-维修备件 维修备件 商品 个 ¥0.00 ¥0.00 5 0 编辑 删除" [ref=e350]:
                          - cell "选择当前行" [ref=e351]:
                            - generic "选择当前行" [ref=e353] [cursor=pointer]:
                              - generic [ref=e354]:
                                - checkbox "选择当前行"
                          - cell "SKU-维修备件" [ref=e356]:
                            - generic [ref=e357]: SKU-维修备件
                          - cell "维修备件" [ref=e358]:
                            - generic [ref=e359]: 维修备件
                          - cell "商品" [ref=e360]:
                            - generic [ref=e361]: 商品
                          - cell "个" [ref=e362]:
                            - generic [ref=e363]: 个
                          - cell "¥0.00" [ref=e364]:
                            - generic [ref=e365]: ¥0.00
                          - cell "¥0.00" [ref=e366]:
                            - generic [ref=e367]: ¥0.00
                          - cell "5" [ref=e368]:
                            - generic [ref=e369]: "5"
                          - cell "0" [ref=e370]:
                            - generic [ref=e371]: "0"
                          - cell "编辑 删除" [ref=e372]:
                            - generic [ref=e374]:
                              - button "编辑" [ref=e375] [cursor=pointer]:
                                - generic [ref=e376]: 编辑
                              - button "删除" [ref=e377] [cursor=pointer]:
                                - generic [ref=e378]: 删除
                        - row "选择当前行 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e379]:
                          - cell "选择当前行" [ref=e380]:
                            - generic "选择当前行" [ref=e382] [cursor=pointer]:
                              - generic [ref=e383]:
                                - checkbox "选择当前行"
                          - cell [ref=e385]
                          - cell [ref=e386]
                          - cell [ref=e387]
                          - cell "个" [ref=e388]:
                            - generic [ref=e389]: 个
                          - cell "¥0.00" [ref=e390]:
                            - generic [ref=e391]: ¥0.00
                          - cell "¥0.00" [ref=e392]:
                            - generic [ref=e393]: ¥0.00
                          - cell "0" [ref=e394]:
                            - generic [ref=e395]: "0"
                          - cell "0" [ref=e396]:
                            - generic [ref=e397]: "0"
                          - cell "编辑 删除" [ref=e398]:
                            - generic [ref=e400]:
                              - button "编辑" [ref=e401] [cursor=pointer]:
                                - generic [ref=e402]: 编辑
                              - button "删除" [ref=e403] [cursor=pointer]:
                                - generic [ref=e404]: 删除
                        - row "选择当前行 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e405]:
                          - cell "选择当前行" [ref=e406]:
                            - generic "选择当前行" [ref=e408] [cursor=pointer]:
                              - generic [ref=e409]:
                                - checkbox "选择当前行"
                          - cell [ref=e411]
                          - cell [ref=e412]
                          - cell [ref=e413]
                          - cell "个" [ref=e414]:
                            - generic [ref=e415]: 个
                          - cell "¥0.00" [ref=e416]:
                            - generic [ref=e417]: ¥0.00
                          - cell "¥0.00" [ref=e418]:
                            - generic [ref=e419]: ¥0.00
                          - cell "0" [ref=e420]:
                            - generic [ref=e421]: "0"
                          - cell "0" [ref=e422]:
                            - generic [ref=e423]: "0"
                          - cell "编辑 删除" [ref=e424]:
                            - generic [ref=e426]:
                              - button "编辑" [ref=e427] [cursor=pointer]:
                                - generic [ref=e428]: 编辑
                              - button "删除" [ref=e429] [cursor=pointer]:
                                - generic [ref=e430]: 删除
                  - img [ref=e433]
                - generic [ref=e436]:
                  - generic [ref=e437]: 共 7 条
                  - generic [ref=e440] [cursor=pointer]:
                    - generic:
                      - combobox [ref=e442]
                      - generic [ref=e443]: 20条/页
                    - img [ref=e446]
                  - button "上一页" [disabled] [ref=e448]:
                    - generic:
                      - img
                  - list [ref=e449]:
                    - listitem "第 1 页" [ref=e450]: "1"
                  - button "下一页" [disabled] [ref=e451]:
                    - generic:
                      - img
```

# Test source

```ts
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
  96  |       const rowText = await page.locator('.el-table__row:first-child').textContent();
  97  |       expect(rowText).toContain(skuValue);
  98  |     });
  99  | 
  100 |     test('查询按钮触发搜索', async ({ page }) => {
  101 |       const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
  102 |       await searchInput.fill('测试');
> 103 |       await page.locator('button:has-text("查询")').click();
      |                                                   ^ Error: locator.click: Error: strict mode violation: locator('button:has-text("查询")') resolved to 2 elements:
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
  197 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  198 | 
  199 |       await expect(page.locator('.el-form-item__error').first()).toBeVisible();
  200 |     });
  201 | 
  202 |     test('取消新增不保存', async ({ page }) => {
  203 |       await page.locator('button:has-text("新增商品")').click();
```