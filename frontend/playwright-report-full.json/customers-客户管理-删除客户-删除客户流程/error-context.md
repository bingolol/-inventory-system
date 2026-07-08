# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: customers.spec.js >> 客户管理 >> 删除客户 >> 删除客户流程
- Location: tests\e2e\customers.spec.js:253:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: locator.fill: Test timeout of 60000ms exceeded.
Call log:
  - waiting for locator('.el-dialog .el-form-item:has-text("名称") input')

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
            - generic [ref=e125]:
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
              - dialog "新增客户" [ref=e228]:
                - generic [active] [ref=e229]:
                  - generic [ref=e230]:
                    - heading "新增客户" [level=2] [ref=e231]
                    - button "关闭此对话框" [ref=e232] [cursor=pointer]:
                      - img [ref=e234]
                  - generic [ref=e238]:
                    - generic [ref=e240]: 联系信息
                    - generic [ref=e241]:
                      - generic [ref=e242]:
                        - generic [ref=e243]: 名称
                        - textbox [ref=e246]
                      - generic [ref=e247]:
                        - generic [ref=e248]: 联系人
                        - textbox [ref=e251]
                      - generic [ref=e252]:
                        - generic [ref=e253]: 电话
                        - textbox [ref=e256]
                      - generic [ref=e257]:
                        - generic [ref=e258]: 地址
                        - textbox [ref=e261]
                      - generic [ref=e262]:
                        - generic [ref=e263]: 备注
                        - textbox [ref=e265]
                  - generic [ref=e266]:
                    - button "取消" [ref=e267] [cursor=pointer]:
                      - generic [ref=e268]: 取消
                    - button "保存" [ref=e269] [cursor=pointer]:
                      - generic [ref=e270]: 保存
```

# Test source

```ts
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
  195 | 
  196 |       await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
  197 | 
  198 |       await expect(page.locator('.el-dialog')).toBeVisible();
  199 |       await expect(page.locator('.el-dialog__title')).toContainText('编辑客户');
  200 | 
  201 |       const nameInput = page.locator('.el-dialog .el-form-item:has-text("名称") input');
  202 |       await expect(nameInput).toHaveValue(firstName?.trim() || '');
  203 |     });
  204 | 
  205 |     test('编辑客户保存成功', async ({ page }) => {
  206 |       const timestamp = Date.now();
  207 |       const customerName = `编辑测试客户-${timestamp}`;
  208 |       const editedName = `Playwright编辑客户-${timestamp}`;
  209 | 
  210 |       // 先新增一个客户用于编辑
  211 |       await page.locator('.card-header button:has-text("新增客户")').click();
  212 |       await page.locator('.el-dialog .el-form-item:has-text("名称") input').fill(customerName);
  213 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  214 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  215 |       await page.waitForTimeout(WAIT_MS);
  216 | 
  217 |       // 搜索到新增的客户
  218 |       const searchInput = page.locator('input[placeholder="搜索客户名称"]');
  219 |       await searchInput.fill(customerName);
  220 |       await searchInput.press('Enter');
  221 |       await page.waitForTimeout(WAIT_MS);
  222 | 
  223 |       // 点击编辑
  224 |       await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
  225 |       await expect(page.locator('.el-dialog')).toBeVisible();
  226 | 
  227 |       const nameInput = page.locator('.el-dialog .el-form-item:has-text("名称") input');
  228 |       await nameInput.clear();
  229 |       await nameInput.fill(editedName);
  230 | 
  231 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  232 | 
  233 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  234 | 
  235 |       await page.waitForTimeout(WAIT_MS);
  236 | 
  237 |       // 重新搜索编辑后的客户名，不依赖行位置
  238 |       await searchInput.clear();
  239 |       await searchInput.fill(editedName);
  240 |       await searchInput.press('Enter');
  241 |       await page.waitForTimeout(WAIT_MS);
  242 | 
  243 |       const rows = await page.locator('.el-table__row').count();
  244 |       expect(rows).toBe(1);
  245 | 
  246 |       const cellText = await page.locator('.el-table__row:first-child').textContent();
  247 |       expect(cellText).toContain(editedName);
  248 |     });
  249 |   });
  250 | 
  251 |   // ========== 删除客户 ==========
  252 |   test.describe('删除客户', () => {
  253 |     test('删除客户流程', async ({ page }) => {
  254 |       const timestamp = Date.now();
  255 |       const customerName = `待删除客户-${timestamp}`;
  256 | 
  257 |       // 先新增一个客户用于删除
  258 |       await page.locator('.card-header button:has-text("新增客户")').click();
> 259 |       await page.locator('.el-dialog .el-form-item:has-text("名称") input').fill(customerName);
      |                                                                           ^ Error: locator.fill: Test timeout of 60000ms exceeded.
  260 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  261 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  262 |       await page.waitForTimeout(WAIT_MS);
  263 | 
  264 |       // 搜索到新增的客户
  265 |       const searchInput = page.locator('input[placeholder="搜索客户名称"]');
  266 |       await searchInput.fill(customerName);
  267 |       await searchInput.press('Enter');
  268 |       await page.waitForTimeout(WAIT_MS);
  269 | 
  270 |       // 点击删除
  271 |       const targetRow = page.locator('.el-table__row').first();
  272 |       await targetRow.locator('button:has-text("删除")').click();
  273 | 
  274 |       await expect(page.locator('.el-popconfirm')).toBeVisible();
  275 | 
  276 |       await page.locator('.el-popconfirm button:has-text("确定")').click();
  277 | 
  278 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  279 | 
  280 |       await page.waitForTimeout(WAIT_MS);
  281 |       const rows = await page.locator('.el-table__row').count();
  282 |       expect(rows).toBe(0);
  283 |     });
  284 | 
  285 |     test('取消删除不执行', async ({ page }) => {
  286 |       const firstName = await page.locator('.el-table__row:first-child td').first().textContent();
  287 | 
  288 |       await page.locator('.el-table__row:first-child button:has-text("删除")').click();
  289 | 
  290 |       await expect(page.locator('.el-popconfirm')).toBeVisible();
  291 | 
  292 |       await page.locator('.el-popconfirm button:has-text("取消")').click();
  293 | 
  294 |       await expect(page.locator('.el-table__row:first-child')).toContainText(firstName?.trim() || '');
  295 |     });
  296 |   });
  297 | });
  298 | 
```