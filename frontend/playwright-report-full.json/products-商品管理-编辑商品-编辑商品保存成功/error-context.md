# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: products.spec.js >> 商品管理 >> 编辑商品 >> 编辑商品保存成功
- Location: tests\e2e\products.spec.js:235:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: locator.fill: Test timeout of 60000ms exceeded.
Call log:
  - waiting for locator('.el-dialog .el-form-item:has-text("商品名称") input')

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
            - generic [ref=e125]:
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
                        - row "选择当前行 个 ¥0.00 ¥0.00 0 0 编辑 删除" [ref=e426]:
                          - cell "选择当前行" [ref=e427]:
                            - generic "选择当前行" [ref=e429] [cursor=pointer]:
                              - generic [ref=e430]:
                                - checkbox "选择当前行"
                          - cell [ref=e432]
                          - cell [ref=e433]
                          - cell [ref=e434]
                          - cell "个" [ref=e435]:
                            - generic [ref=e436]: 个
                          - cell "¥0.00" [ref=e437]:
                            - generic [ref=e438]: ¥0.00
                          - cell "¥0.00" [ref=e439]:
                            - generic [ref=e440]: ¥0.00
                          - cell "0" [ref=e441]:
                            - generic [ref=e442]: "0"
                          - cell "0" [ref=e443]:
                            - generic [ref=e444]: "0"
                          - cell "编辑 删除" [ref=e445]:
                            - generic [ref=e447]:
                              - button "编辑" [ref=e448] [cursor=pointer]:
                                - generic [ref=e449]: 编辑
                              - button "删除" [ref=e450] [cursor=pointer]:
                                - generic [ref=e451]: 删除
                  - generic [ref=e453]:
                    - generic [ref=e454]: 共 8 条
                    - generic [ref=e457] [cursor=pointer]:
                      - generic:
                        - combobox [ref=e459]
                        - generic [ref=e460]: 20条/页
                      - img [ref=e463]
                    - button "上一页" [disabled] [ref=e465]:
                      - generic:
                        - img
                    - list [ref=e466]:
                      - listitem "第 1 页" [ref=e467]: "1"
                    - button "下一页" [disabled] [ref=e468]:
                      - generic:
                        - img
              - dialog "新增商品" [ref=e470]:
                - generic [active] [ref=e471]:
                  - generic [ref=e472]:
                    - heading "新增商品" [level=2] [ref=e473]
                    - button "关闭此对话框" [ref=e474] [cursor=pointer]:
                      - img [ref=e476]
                  - generic [ref=e479]:
                    - generic [ref=e480]:
                      - generic [ref=e482]: 基本信息
                      - generic [ref=e483]:
                        - generic [ref=e484]:
                          - generic [ref=e485]: 商品名称
                          - textbox [ref=e488]
                        - generic [ref=e489]:
                          - generic [ref=e490]: 编码
                          - textbox [ref=e493]
                        - generic [ref=e494]:
                          - generic [ref=e495]: 分类
                          - textbox [ref=e498]
                        - generic [ref=e499]:
                          - generic [ref=e500]: 单位
                          - textbox [ref=e503]: 个
                    - generic [ref=e504]:
                      - generic [ref=e506]: 价格库存
                      - generic [ref=e507]:
                        - generic [ref=e508]:
                          - generic [ref=e509]: 进价
                          - generic [ref=e510]:
                            - button "减少数值" [ref=e511]:
                              - img [ref=e513]
                            - button "增加数值" [ref=e515] [cursor=pointer]:
                              - img [ref=e517]
                            - spinbutton [ref=e521]: "0.00"
                        - generic [ref=e522]:
                          - generic [ref=e523]: 售价
                          - generic [ref=e524]:
                            - button "减少数值" [ref=e525]:
                              - img [ref=e527]
                            - button "增加数值" [ref=e529] [cursor=pointer]:
                              - img [ref=e531]
                            - spinbutton [ref=e535]: "0.00"
                        - generic [ref=e536]:
                          - generic [ref=e537]: 预警库存
                          - generic [ref=e538]:
                            - button "减少数值" [ref=e539]:
                              - img [ref=e541]
                            - button "增加数值" [ref=e543] [cursor=pointer]:
                              - img [ref=e545]
                            - spinbutton [ref=e549]: "0"
                        - generic [ref=e550]:
                          - generic [ref=e551]: 描述
                          - textbox [ref=e553]
                  - generic [ref=e554]:
                    - button "取消" [ref=e555] [cursor=pointer]:
                      - generic [ref=e556]: 取消
                    - button "保存" [ref=e557] [cursor=pointer]:
                      - generic [ref=e558]: 保存
```

# Test source

```ts
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
  204 | 
  205 |       await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill('不应保存的商品');
  206 | 
  207 |       await page.locator('.el-dialog__footer button:has-text("取消")').click();
  208 | 
  209 |       await expect(page.locator('.el-dialog')).not.toBeVisible();
  210 | 
  211 |       const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
  212 |       await searchInput.fill('不应保存的商品');
  213 |       await searchInput.press('Enter');
  214 |       await page.waitForTimeout(1000);
  215 | 
  216 |       const rows = await page.locator('.el-table__row').count();
  217 |       expect(rows).toBe(0);
  218 |     });
  219 |   });
  220 | 
  221 |   // ========== 编辑商品 ==========
  222 |   test.describe('编辑商品', () => {
  223 |     test('打开编辑对话框并回填数据', async ({ page }) => {
  224 |       const firstName = await page.locator('.el-table__row:first-child td').nth(2).textContent();
  225 | 
  226 |       await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
  227 | 
  228 |       await expect(page.locator('.el-dialog')).toBeVisible();
  229 |       await expect(page.locator('.el-dialog__title')).toContainText('编辑商品');
  230 | 
  231 |       const nameInput = page.locator('.el-dialog .el-form-item:has-text("商品名称") input');
  232 |       await expect(nameInput).toHaveValue(firstName?.trim() || '');
  233 |     });
  234 | 
  235 |     test('编辑商品保存成功', async ({ page }) => {
  236 |       const timestamp = Date.now();
  237 |       const productName = `编辑测试-${timestamp}`;
  238 |       const productSku = `EDT-${timestamp}`;
  239 | 
  240 |       await page.locator('button:has-text("新增商品")').click();
> 241 |       await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill(productName);
      |                                                                             ^ Error: locator.fill: Test timeout of 60000ms exceeded.
  242 |       await page.locator('.el-dialog .el-form-item:has-text("编码") input').fill(productSku);
  243 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  244 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  245 |       await page.waitForTimeout(1000);
  246 | 
  247 |       const searchInput = page.locator('input[placeholder="SKU精确匹配"]');
  248 |       await searchInput.fill(productSku);
  249 |       await searchInput.press('Enter');
  250 |       await page.waitForTimeout(1000);
  251 | 
  252 |       await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
  253 |       await expect(page.locator('.el-dialog')).toBeVisible();
  254 | 
  255 |       const nameInput = page.locator('.el-dialog .el-form-item:has-text("商品名称") input');
  256 |       await nameInput.clear();
  257 |       await nameInput.fill('Playwright编辑测试');
  258 | 
  259 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  260 | 
  261 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  262 | 
  263 |       await page.waitForTimeout(1000);
  264 |       await expect(page.locator('.el-table__row:first-child')).toContainText('Playwright编辑测试');
  265 |     });
  266 |   });
  267 | 
  268 |   // ========== 删除商品 ==========
  269 |   test.describe('删除商品', () => {
  270 |     test('删除商品流程', async ({ page }) => {
  271 |       const timestamp = Date.now();
  272 |       const productName = `待删除-${timestamp}`;
  273 |       const productSku = `DEL-${timestamp}`;
  274 | 
  275 |       await page.locator('button:has-text("新增商品")').click();
  276 |       await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill(productName);
  277 |       await page.locator('.el-dialog .el-form-item:has-text("编码") input').fill(productSku);
  278 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  279 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  280 |       await page.waitForTimeout(1000);
  281 | 
  282 |       const searchInput = page.locator('input[placeholder="SKU精确匹配"]');
  283 |       await searchInput.fill(productSku);
  284 |       await searchInput.press('Enter');
  285 |       await page.waitForTimeout(1000);
  286 | 
  287 |       const targetRow = page.locator('.el-table__row').first();
  288 |       await targetRow.locator('button:has-text("删除")').click();
  289 | 
  290 |       await expect(page.locator('.el-popconfirm')).toBeVisible();
  291 | 
  292 |       await page.locator('.el-popconfirm button:has-text("确定")').click();
  293 | 
  294 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  295 | 
  296 |       await page.waitForTimeout(1000);
  297 |       const rows = await page.locator('.el-table__row').count();
  298 |       expect(rows).toBe(0);
  299 |     });
  300 | 
  301 |     test('取消删除不执行', async ({ page }) => {
  302 |       const firstName = await page.locator('.el-table__row:first-child td').nth(2).textContent();
  303 | 
  304 |       await page.locator('.el-table__row:first-child button:has-text("删除")').click();
  305 | 
  306 |       await expect(page.locator('.el-popconfirm')).toBeVisible();
  307 | 
  308 |       await page.locator('.el-popconfirm button:has-text("取消")').click();
  309 | 
  310 |       await expect(page.locator('.el-table__row:first-child')).toContainText(firstName?.trim() || '');
  311 |     });
  312 |   });
  313 | 
  314 |   // ========== 批量选择与导出 ==========
  315 |   test.describe('批量选择与导出', () => {
  316 |     test('勾选商品行', async ({ page }) => {
  317 |       await page.locator('.el-table__row:first-child .el-checkbox').click();
  318 | 
  319 |       const checkbox = page.locator('.el-table__row:first-child .el-checkbox');
  320 |       await expect(checkbox).toHaveClass(/is-checked/);
  321 |     });
  322 | 
  323 |     test('全选功能', async ({ page }) => {
  324 |       await page.locator('.el-table__header-wrapper .el-checkbox').click();
  325 | 
  326 |       const checkboxes = page.locator('.el-table__row .el-checkbox');
  327 |       const count = await checkboxes.count();
  328 | 
  329 |       for (let i = 0; i < Math.min(count, 5); i++) {
  330 |         await expect(checkboxes.nth(i)).toHaveClass(/is-checked/);
  331 |       }
  332 |     });
  333 |   });
  334 | });
  335 | 
```