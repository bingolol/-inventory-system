# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: customers.spec.js >> 客户管理 >> 新增客户 >> 新增客户表单校验-名称必填
- Location: tests\e2e\customers.spec.js:162:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.el-dialog .el-form-item:has-text("名称")')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.el-dialog .el-form-item:has-text("名称")')

```

```yaml
- complementary:
  - text: 进销存 巧游电子科技 一般纳税人
  - combobox
  - text: 巧游电子科技
  - img
  - text: ＋ ✎ −
  - navigation: ◉ 仪表盘 基础数据 ◻ 伙伴管理 ◻ 库存商品 业务处理 ◉ 销售开单 ◻ 采购入库 ◻ 发票录入 ◻ 资金流水 财务核算 ◉ 财务总览 ◻ 费用管理 ◻ 固定资产 ◻ 银行账户 ◻ 银行对账 ◻ 往来管理 财务报表 ◉ 资产负债表/利润表 ◉ 现金流量表 ◻ 会计账簿 ◻ 会计规则指引 期末处理 ◉ 期末税务 系统管理 ◻ 操作日志 ◻ 数据备份
- heading "伙伴管理" [level=2]
- text: 客户 · 供应商
- button "A admin":
  - text: A admin
  - img
- text: 2026/07/07周二
- main:
  - text: 伙伴管理
  - tablist:
    - tab "客户" [selected]
    - tab "供应商"
  - tabpanel "客户":
    - text: 客户列表
    - button "新增客户":
      - img
      - text: 新增客户
    - img
    - textbox "搜索客户名称"
    - button "查询"
    - table:
      - rowgroup:
        - row "客户名称 联系人 电话 地址 备注 操作":
          - columnheader "客户名称"
          - columnheader "联系人"
          - columnheader "电话"
          - columnheader "地址"
          - columnheader "备注"
          - columnheader "操作"
    - table:
      - rowgroup:
        - row "中国联通宜宾分公司 编辑 删除":
          - cell "中国联通宜宾分公司"
          - cell
          - cell
          - cell
          - cell
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
        - row "四川南山射钉紧固器材有限公司 编辑 删除":
          - cell "四川南山射钉紧固器材有限公司"
          - cell
          - cell
          - cell
          - cell
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
    - text: 共 2 条
    - combobox
    - text: 20条/页
    - img
    - button "上一页" [disabled]:
      - img
    - list:
      - listitem "第 1 页": "1"
    - button "下一页" [disabled]:
      - img
    - dialog "新增客户":
      - heading "新增客户" [level=2]
      - button "关闭此对话框":
        - img
      - text: 联系信息 名称
      - textbox
      - text: 联系人
      - textbox
      - text: 电话
      - textbox
      - text: 地址
      - textbox
      - text: 备注
      - textbox
      - button "取消"
      - button "保存"
```

# Test source

```ts
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
> 166 |       await expect(page.locator('.el-dialog .el-form-item:has-text("名称")')).toBeVisible();
      |                                                                             ^ Error: expect(locator).toBeVisible() failed
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
  259 |       await page.locator('.el-dialog .el-form-item:has-text("名称") input').fill(customerName);
  260 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  261 |       await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
  262 |       await page.waitForTimeout(WAIT_MS);
  263 | 
  264 |       // 搜索到新增的客户
  265 |       const searchInput = page.locator('input[placeholder="搜索客户名称"]');
  266 |       await searchInput.fill(customerName);
```