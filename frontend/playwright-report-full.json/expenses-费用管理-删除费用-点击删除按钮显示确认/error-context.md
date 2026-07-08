# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: expenses.spec.js >> 费用管理 >> 删除费用 >> 点击删除按钮显示确认
- Location: tests\e2e\expenses.spec.js:199:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: locator.click: Test timeout of 60000ms exceeded.
Call log:
  - waiting for locator('.el-table__row:first-child button:has-text("删除")')

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
        - heading "费用支出" [level=2] [ref=e99]
        - generic [ref=e100]: 费用管理 · 个人垫付
      - generic [ref=e101]:
        - button "A admin" [ref=e103] [cursor=pointer]:
          - generic [ref=e104]: A
          - generic [ref=e105]: admin
          - img [ref=e107]
        - text: 2026/07/07周二
    - main [ref=e109]:
      - generic [ref=e110]:
        - generic [ref=e113]: 费用支出
        - generic [ref=e115]:
          - tablist [ref=e119]:
            - tab "费用管理" [selected] [ref=e121]
            - tab "个人垫付" [ref=e122]
          - tabpanel "费用管理" [ref=e124]:
            - generic [ref=e125]:
              - generic [ref=e126]:
                - generic [ref=e128]:
                  - generic [ref=e129]: 本月费用
                  - generic [ref=e130]: "0.00"
                - generic [ref=e132]:
                  - generic [ref=e133]: 筛选合计
                  - generic [ref=e134]: 9,940.00
                - generic [ref=e136]:
                  - generic [ref=e137]: 记录数
                  - generic [ref=e138]: 14 笔
              - generic [ref=e139]:
                - generic [ref=e141]:
                  - generic [ref=e142]: 费用管理
                  - button "新增费用" [ref=e144] [cursor=pointer]:
                    - generic [ref=e145]:
                      - img [ref=e147]
                      - text: 新增费用
                - generic [ref=e149]:
                  - generic [ref=e150]:
                    - generic [ref=e153] [cursor=pointer]:
                      - generic:
                        - combobox [ref=e155]
                        - generic [ref=e156]: 年份
                      - img [ref=e159]
                    - generic [ref=e161]:
                      - button "查询" [ref=e162] [cursor=pointer]:
                        - generic [ref=e163]:
                          - img [ref=e165]
                          - text: 查询
                      - button "重置" [ref=e167] [cursor=pointer]:
                        - generic [ref=e168]: 重置
                      - button "付款管理" [ref=e169] [cursor=pointer]:
                        - generic [ref=e170]:
                          - img [ref=e172]
                          - text: 付款管理
                  - generic [ref=e175]:
                    - table [ref=e177]:
                      - rowgroup [ref=e186]:
                        - row "日期 类别 功能分类 金额 付款状态 描述 操作" [ref=e187]:
                          - columnheader "日期" [ref=e188]:
                            - generic [ref=e189]: 日期
                          - columnheader "类别" [ref=e190]:
                            - generic [ref=e191]: 类别
                          - columnheader "功能分类" [ref=e192]:
                            - generic [ref=e193]: 功能分类
                          - columnheader "金额" [ref=e194]:
                            - generic [ref=e195]: 金额
                          - columnheader "付款状态" [ref=e196]:
                            - generic [ref=e197]: 付款状态
                          - columnheader "描述" [ref=e198]:
                            - generic [ref=e199]: 描述
                          - columnheader "操作" [ref=e200]:
                            - generic [ref=e201]: 操作
                    - table [ref=e206]:
                      - rowgroup [ref=e215]:
                        - row "2025-12-31 房租 管理费用 -1,300.00 unpaid 2025年12月房租 编辑 付款 冲红" [ref=e216]:
                          - cell "2025-12-31" [ref=e217]:
                            - generic [ref=e218]: 2025-12-31
                          - cell "房租" [ref=e219]:
                            - generic [ref=e222]: 房租
                          - cell "管理费用" [ref=e223]:
                            - generic [ref=e225]: 管理费用
                          - cell "-1,300.00" [ref=e226]:
                            - generic [ref=e227]: "-1,300.00"
                          - cell "unpaid" [ref=e228]:
                            - generic [ref=e230]: unpaid
                          - cell "2025年12月房租" [ref=e231]:
                            - generic [ref=e232]: 2025年12月房租
                          - cell "编辑 付款 冲红" [ref=e233]:
                            - generic [ref=e235]:
                              - button "编辑" [ref=e236] [cursor=pointer]:
                                - generic [ref=e237]: 编辑
                              - button "付款" [ref=e238] [cursor=pointer]:
                                - generic [ref=e239]: 付款
                              - button "冲红" [ref=e240] [cursor=pointer]:
                                - generic [ref=e241]: 冲红
                        - row "2025-12-31 水电 管理费用 -120.00 unpaid 2025年12月水电 编辑 付款 冲红" [ref=e242]:
                          - cell "2025-12-31" [ref=e243]:
                            - generic [ref=e244]: 2025-12-31
                          - cell "水电" [ref=e245]:
                            - generic [ref=e248]: 水电
                          - cell "管理费用" [ref=e249]:
                            - generic [ref=e251]: 管理费用
                          - cell "-120.00" [ref=e252]:
                            - generic [ref=e253]: "-120.00"
                          - cell "unpaid" [ref=e254]:
                            - generic [ref=e256]: unpaid
                          - cell "2025年12月水电" [ref=e257]:
                            - generic [ref=e258]: 2025年12月水电
                          - cell "编辑 付款 冲红" [ref=e259]:
                            - generic [ref=e261]:
                              - button "编辑" [ref=e262] [cursor=pointer]:
                                - generic [ref=e263]: 编辑
                              - button "付款" [ref=e264] [cursor=pointer]:
                                - generic [ref=e265]: 付款
                              - button "冲红" [ref=e266] [cursor=pointer]:
                                - generic [ref=e267]: 冲红
                        - row "2026-1-31 房租 管理费用 -1,300.00 unpaid 2026年1月房租 编辑 付款 冲红" [ref=e268]:
                          - cell "2026-1-31" [ref=e269]:
                            - generic [ref=e270]: 2026-1-31
                          - cell "房租" [ref=e271]:
                            - generic [ref=e274]: 房租
                          - cell "管理费用" [ref=e275]:
                            - generic [ref=e277]: 管理费用
                          - cell "-1,300.00" [ref=e278]:
                            - generic [ref=e279]: "-1,300.00"
                          - cell "unpaid" [ref=e280]:
                            - generic [ref=e282]: unpaid
                          - cell "2026年1月房租" [ref=e283]:
                            - generic [ref=e284]: 2026年1月房租
                          - cell "编辑 付款 冲红" [ref=e285]:
                            - generic [ref=e287]:
                              - button "编辑" [ref=e288] [cursor=pointer]:
                                - generic [ref=e289]: 编辑
                              - button "付款" [ref=e290] [cursor=pointer]:
                                - generic [ref=e291]: 付款
                              - button "冲红" [ref=e292] [cursor=pointer]:
                                - generic [ref=e293]: 冲红
                        - row "2026-1-31 水电 管理费用 -120.00 unpaid 2026年1月水电 编辑 付款 冲红" [ref=e294]:
                          - cell "2026-1-31" [ref=e295]:
                            - generic [ref=e296]: 2026-1-31
                          - cell "水电" [ref=e297]:
                            - generic [ref=e300]: 水电
                          - cell "管理费用" [ref=e301]:
                            - generic [ref=e303]: 管理费用
                          - cell "-120.00" [ref=e304]:
                            - generic [ref=e305]: "-120.00"
                          - cell "unpaid" [ref=e306]:
                            - generic [ref=e308]: unpaid
                          - cell "2026年1月水电" [ref=e309]:
                            - generic [ref=e310]: 2026年1月水电
                          - cell "编辑 付款 冲红" [ref=e311]:
                            - generic [ref=e313]:
                              - button "编辑" [ref=e314] [cursor=pointer]:
                                - generic [ref=e315]: 编辑
                              - button "付款" [ref=e316] [cursor=pointer]:
                                - generic [ref=e317]: 付款
                              - button "冲红" [ref=e318] [cursor=pointer]:
                                - generic [ref=e319]: 冲红
                        - row "2026-2-28 房租 管理费用 -1,300.00 unpaid 2026年2月房租 编辑 付款 冲红" [ref=e320]:
                          - cell "2026-2-28" [ref=e321]:
                            - generic [ref=e322]: 2026-2-28
                          - cell "房租" [ref=e323]:
                            - generic [ref=e326]: 房租
                          - cell "管理费用" [ref=e327]:
                            - generic [ref=e329]: 管理费用
                          - cell "-1,300.00" [ref=e330]:
                            - generic [ref=e331]: "-1,300.00"
                          - cell "unpaid" [ref=e332]:
                            - generic [ref=e334]: unpaid
                          - cell "2026年2月房租" [ref=e335]:
                            - generic [ref=e336]: 2026年2月房租
                          - cell "编辑 付款 冲红" [ref=e337]:
                            - generic [ref=e339]:
                              - button "编辑" [ref=e340] [cursor=pointer]:
                                - generic [ref=e341]: 编辑
                              - button "付款" [ref=e342] [cursor=pointer]:
                                - generic [ref=e343]: 付款
                              - button "冲红" [ref=e344] [cursor=pointer]:
                                - generic [ref=e345]: 冲红
                        - row "2026-2-28 水电 管理费用 -120.00 unpaid 2026年2月水电 编辑 付款 冲红" [ref=e346]:
                          - cell "2026-2-28" [ref=e347]:
                            - generic [ref=e348]: 2026-2-28
                          - cell "水电" [ref=e349]:
                            - generic [ref=e352]: 水电
                          - cell "管理费用" [ref=e353]:
                            - generic [ref=e355]: 管理费用
                          - cell "-120.00" [ref=e356]:
                            - generic [ref=e357]: "-120.00"
                          - cell "unpaid" [ref=e358]:
                            - generic [ref=e360]: unpaid
                          - cell "2026年2月水电" [ref=e361]:
                            - generic [ref=e362]: 2026年2月水电
                          - cell "编辑 付款 冲红" [ref=e363]:
                            - generic [ref=e365]:
                              - button "编辑" [ref=e366] [cursor=pointer]:
                                - generic [ref=e367]: 编辑
                              - button "付款" [ref=e368] [cursor=pointer]:
                                - generic [ref=e369]: 付款
                              - button "冲红" [ref=e370] [cursor=pointer]:
                                - generic [ref=e371]: 冲红
                        - row "2026-3-31 房租 管理费用 -1,300.00 unpaid 2026年3月房租 编辑 付款 冲红" [ref=e372]:
                          - cell "2026-3-31" [ref=e373]:
                            - generic [ref=e374]: 2026-3-31
                          - cell "房租" [ref=e375]:
                            - generic [ref=e378]: 房租
                          - cell "管理费用" [ref=e379]:
                            - generic [ref=e381]: 管理费用
                          - cell "-1,300.00" [ref=e382]:
                            - generic [ref=e383]: "-1,300.00"
                          - cell "unpaid" [ref=e384]:
                            - generic [ref=e386]: unpaid
                          - cell "2026年3月房租" [ref=e387]:
                            - generic [ref=e388]: 2026年3月房租
                          - cell "编辑 付款 冲红" [ref=e389]:
                            - generic [ref=e391]:
                              - button "编辑" [ref=e392] [cursor=pointer]:
                                - generic [ref=e393]: 编辑
                              - button "付款" [ref=e394] [cursor=pointer]:
                                - generic [ref=e395]: 付款
                              - button "冲红" [ref=e396] [cursor=pointer]:
                                - generic [ref=e397]: 冲红
                        - row "2026-3-31 水电 管理费用 -120.00 unpaid 2026年3月水电 编辑 付款 冲红" [ref=e398]:
                          - cell "2026-3-31" [ref=e399]:
                            - generic [ref=e400]: 2026-3-31
                          - cell "水电" [ref=e401]:
                            - generic [ref=e404]: 水电
                          - cell "管理费用" [ref=e405]:
                            - generic [ref=e407]: 管理费用
                          - cell "-120.00" [ref=e408]:
                            - generic [ref=e409]: "-120.00"
                          - cell "unpaid" [ref=e410]:
                            - generic [ref=e412]: unpaid
                          - cell "2026年3月水电" [ref=e413]:
                            - generic [ref=e414]: 2026年3月水电
                          - cell "编辑 付款 冲红" [ref=e415]:
                            - generic [ref=e417]:
                              - button "编辑" [ref=e418] [cursor=pointer]:
                                - generic [ref=e419]: 编辑
                              - button "付款" [ref=e420] [cursor=pointer]:
                                - generic [ref=e421]: 付款
                              - button "冲红" [ref=e422] [cursor=pointer]:
                                - generic [ref=e423]: 冲红
                        - row "2026-4-30 房租 管理费用 -1,300.00 unpaid 2026年4月房租 编辑 付款 冲红" [ref=e424]:
                          - cell "2026-4-30" [ref=e425]:
                            - generic [ref=e426]: 2026-4-30
                          - cell "房租" [ref=e427]:
                            - generic [ref=e430]: 房租
                          - cell "管理费用" [ref=e431]:
                            - generic [ref=e433]: 管理费用
                          - cell "-1,300.00" [ref=e434]:
                            - generic [ref=e435]: "-1,300.00"
                          - cell "unpaid" [ref=e436]:
                            - generic [ref=e438]: unpaid
                          - cell "2026年4月房租" [ref=e439]:
                            - generic [ref=e440]: 2026年4月房租
                          - cell "编辑 付款 冲红" [ref=e441]:
                            - generic [ref=e443]:
                              - button "编辑" [ref=e444] [cursor=pointer]:
                                - generic [ref=e445]: 编辑
                              - button "付款" [ref=e446] [cursor=pointer]:
                                - generic [ref=e447]: 付款
                              - button "冲红" [ref=e448] [cursor=pointer]:
                                - generic [ref=e449]: 冲红
                        - row "2026-4-30 水电 管理费用 -120.00 unpaid 2026年4月水电 编辑 付款 冲红" [ref=e450]:
                          - cell "2026-4-30" [ref=e451]:
                            - generic [ref=e452]: 2026-4-30
                          - cell "水电" [ref=e453]:
                            - generic [ref=e456]: 水电
                          - cell "管理费用" [ref=e457]:
                            - generic [ref=e459]: 管理费用
                          - cell "-120.00" [ref=e460]:
                            - generic [ref=e461]: "-120.00"
                          - cell "unpaid" [ref=e462]:
                            - generic [ref=e464]: unpaid
                          - cell "2026年4月水电" [ref=e465]:
                            - generic [ref=e466]: 2026年4月水电
                          - cell "编辑 付款 冲红" [ref=e467]:
                            - generic [ref=e469]:
                              - button "编辑" [ref=e470] [cursor=pointer]:
                                - generic [ref=e471]: 编辑
                              - button "付款" [ref=e472] [cursor=pointer]:
                                - generic [ref=e473]: 付款
                              - button "冲红" [ref=e474] [cursor=pointer]:
                                - generic [ref=e475]: 冲红
                        - row "2026-5-31 房租 管理费用 -1,300.00 unpaid 2026年5月房租 编辑 付款 冲红" [ref=e476]:
                          - cell "2026-5-31" [ref=e477]:
                            - generic [ref=e478]: 2026-5-31
                          - cell "房租" [ref=e479]:
                            - generic [ref=e482]: 房租
                          - cell "管理费用" [ref=e483]:
                            - generic [ref=e485]: 管理费用
                          - cell "-1,300.00" [ref=e486]:
                            - generic [ref=e487]: "-1,300.00"
                          - cell "unpaid" [ref=e488]:
                            - generic [ref=e490]: unpaid
                          - cell "2026年5月房租" [ref=e491]:
                            - generic [ref=e492]: 2026年5月房租
                          - cell "编辑 付款 冲红" [ref=e493]:
                            - generic [ref=e495]:
                              - button "编辑" [ref=e496] [cursor=pointer]:
                                - generic [ref=e497]: 编辑
                              - button "付款" [ref=e498] [cursor=pointer]:
                                - generic [ref=e499]: 付款
                              - button "冲红" [ref=e500] [cursor=pointer]:
                                - generic [ref=e501]: 冲红
                        - row "2026-5-31 水电 管理费用 -120.00 unpaid 2026年5月水电 编辑 付款 冲红" [ref=e502]:
                          - cell "2026-5-31" [ref=e503]:
                            - generic [ref=e504]: 2026-5-31
                          - cell "水电" [ref=e505]:
                            - generic [ref=e508]: 水电
                          - cell "管理费用" [ref=e509]:
                            - generic [ref=e511]: 管理费用
                          - cell "-120.00" [ref=e512]:
                            - generic [ref=e513]: "-120.00"
                          - cell "unpaid" [ref=e514]:
                            - generic [ref=e516]: unpaid
                          - cell "2026年5月水电" [ref=e517]:
                            - generic [ref=e518]: 2026年5月水电
                          - cell "编辑 付款 冲红" [ref=e519]:
                            - generic [ref=e521]:
                              - button "编辑" [ref=e522] [cursor=pointer]:
                                - generic [ref=e523]: 编辑
                              - button "付款" [ref=e524] [cursor=pointer]:
                                - generic [ref=e525]: 付款
                              - button "冲红" [ref=e526] [cursor=pointer]:
                                - generic [ref=e527]: 冲红
                        - row "2026-6-30 房租 管理费用 -1,300.00 unpaid 2026年6月房租 编辑 付款 冲红" [ref=e528]:
                          - cell "2026-6-30" [ref=e529]:
                            - generic [ref=e530]: 2026-6-30
                          - cell "房租" [ref=e531]:
                            - generic [ref=e534]: 房租
                          - cell "管理费用" [ref=e535]:
                            - generic [ref=e537]: 管理费用
                          - cell "-1,300.00" [ref=e538]:
                            - generic [ref=e539]: "-1,300.00"
                          - cell "unpaid" [ref=e540]:
                            - generic [ref=e542]: unpaid
                          - cell "2026年6月房租" [ref=e543]:
                            - generic [ref=e544]: 2026年6月房租
                          - cell "编辑 付款 冲红" [ref=e545]:
                            - generic [ref=e547]:
                              - button "编辑" [ref=e548] [cursor=pointer]:
                                - generic [ref=e549]: 编辑
                              - button "付款" [ref=e550] [cursor=pointer]:
                                - generic [ref=e551]: 付款
                              - button "冲红" [ref=e552] [cursor=pointer]:
                                - generic [ref=e553]: 冲红
                        - row "2026-6-30 水电 管理费用 -120.00 unpaid 2026年6月水电 编辑 付款 冲红" [ref=e554]:
                          - cell "2026-6-30" [ref=e555]:
                            - generic [ref=e556]: 2026-6-30
                          - cell "水电" [ref=e557]:
                            - generic [ref=e560]: 水电
                          - cell "管理费用" [ref=e561]:
                            - generic [ref=e563]: 管理费用
                          - cell "-120.00" [ref=e564]:
                            - generic [ref=e565]: "-120.00"
                          - cell "unpaid" [ref=e566]:
                            - generic [ref=e568]: unpaid
                          - cell "2026年6月水电" [ref=e569]:
                            - generic [ref=e570]: 2026年6月水电
                          - cell "编辑 付款 冲红" [ref=e571]:
                            - generic [ref=e573]:
                              - button "编辑" [ref=e574] [cursor=pointer]:
                                - generic [ref=e575]: 编辑
                              - button "付款" [ref=e576] [cursor=pointer]:
                                - generic [ref=e577]: 付款
                              - button "冲红" [ref=e578] [cursor=pointer]:
                                - generic [ref=e579]: 冲红
```

# Test source

```ts
  100 |     });
  101 | 
  102 |     test('重置筛选条件', async ({ page }) => {
  103 |       const allCount = await page.locator('.el-table__row').count();
  104 | 
  105 |       const categorySelect = page.locator('.el-form-item:has-text("类别") .el-select');
  106 |       await categorySelect.click();
  107 |       await page.waitForTimeout(500);
  108 | 
  109 |       const dropdown = page.locator('.el-select-dropdown:visible').last();
  110 |       const options = dropdown.locator('li');
  111 |       const optionCount = await options.count();
  112 | 
  113 |       if (optionCount > 0) {
  114 |         await options.first().click();
  115 |         await page.waitForTimeout(500);
  116 |       }
  117 | 
  118 |       await page.locator('button:has-text("重置")').click();
  119 |       await page.waitForTimeout(1000);
  120 | 
  121 |       const restoredCount = await page.locator('.el-table__row').count();
  122 |       expect(restoredCount).toBe(allCount);
  123 |     });
  124 | 
  125 |     test('组合筛选费用', async ({ page }) => {
  126 |       const allCount = await page.locator('.el-table__row').count();
  127 | 
  128 |       const categorySelect = page.locator('.el-form-item:has-text("类别") .el-select');
  129 |       await categorySelect.click();
  130 |       await page.waitForTimeout(500);
  131 | 
  132 |       const categoryDropdown = page.locator('.el-select-dropdown:visible').last();
  133 |       const categoryOptions = categoryDropdown.locator('li');
  134 |       const categoryOptionCount = await categoryOptions.count();
  135 | 
  136 |       if (categoryOptionCount > 0) {
  137 |         await categoryOptions.first().click();
  138 |         await page.waitForTimeout(500);
  139 |       }
  140 | 
  141 |       const yearSelect = page.locator('.el-form-item:has-text("年份") .el-select');
  142 |       await yearSelect.click();
  143 |       await page.waitForTimeout(500);
  144 | 
  145 |       const yearDropdown = page.locator('.el-select-dropdown:visible').last();
  146 |       const yearOptions = yearDropdown.locator('li');
  147 |       const yearOptionCount = await yearOptions.count();
  148 | 
  149 |       if (yearOptionCount > 0) {
  150 |         await yearOptions.first().click();
  151 |         await page.waitForTimeout(500);
  152 |       }
  153 | 
  154 |       await page.locator('button:has-text("查询")').click();
  155 |       await page.waitForTimeout(1000);
  156 | 
  157 |       const filteredCount = await page.locator('.el-table__row').count();
  158 |       expect(filteredCount).toBeGreaterThanOrEqual(0);
  159 |       expect(filteredCount).toBeLessThanOrEqual(allCount);
  160 |     });
  161 |   });
  162 | 
  163 |   // ========== 新增费用 ==========
  164 |   test.describe('新增费用', () => {
  165 |     test('打开新增对话框', async ({ page }) => {
  166 |       await page.locator('button:has-text("新增费用")').click();
  167 |       await expect(page.locator('.el-dialog')).toBeVisible();
  168 |       await expect(page.locator('.el-dialog__title')).toContainText('新增费用');
  169 |     });
  170 | 
  171 |     test('关闭新增对话框', async ({ page }) => {
  172 |       await page.locator('button:has-text("新增费用")').click();
  173 |       await expect(page.locator('.el-dialog')).toBeVisible();
  174 | 
  175 |       await page.locator('.el-dialog__footer button:has-text("取消")').click();
  176 |       await expect(page.locator('.el-dialog')).not.toBeVisible();
  177 |     });
  178 |   });
  179 | 
  180 |   // ========== 编辑费用 ==========
  181 |   test.describe('编辑费用', () => {
  182 |     test('打开编辑对话框', async ({ page }) => {
  183 |       await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
  184 |       await expect(page.locator('.el-dialog')).toBeVisible();
  185 |       await expect(page.locator('.el-dialog__title')).toContainText('编辑费用');
  186 |     });
  187 | 
  188 |     test('关闭编辑对话框', async ({ page }) => {
  189 |       await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
  190 |       await expect(page.locator('.el-dialog')).toBeVisible();
  191 | 
  192 |       await page.locator('.el-dialog__footer button:has-text("取消")').click();
  193 |       await expect(page.locator('.el-dialog')).not.toBeVisible();
  194 |     });
  195 |   });
  196 | 
  197 |   // ========== 删除费用 ==========
  198 |   test.describe('删除费用', () => {
  199 |     test('点击删除按钮显示确认', async ({ page }) => {
> 200 |       await page.locator('.el-table__row:first-child button:has-text("删除")').click();
      |                                                                              ^ Error: locator.click: Test timeout of 60000ms exceeded.
  201 |       await expect(page.locator('.el-popconfirm')).toBeVisible();
  202 |     });
  203 | 
  204 |     test('取消删除操作', async ({ page }) => {
  205 |       const firstName = await page.locator('.el-table__row:first-child td').nth(1).textContent();
  206 | 
  207 |       await page.locator('.el-table__row:first-child button:has-text("删除")').click();
  208 |       await expect(page.locator('.el-popconfirm')).toBeVisible();
  209 | 
  210 |       await page.locator('.el-popconfirm button:has-text("取消")').click();
  211 |       await expect(page.locator('.el-table__row:first-child')).toContainText(firstName?.trim() || '');
  212 |     });
  213 |   });
  214 | });
  215 | 
```