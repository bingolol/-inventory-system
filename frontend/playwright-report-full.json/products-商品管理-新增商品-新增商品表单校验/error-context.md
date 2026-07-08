# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: products.spec.js >> 商品管理 >> 新增商品 >> 新增商品表单校验
- Location: tests\e2e\products.spec.js:194:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.el-form-item__error').first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.el-form-item__error').first()

```

```yaml
- complementary:
  - text: 进销存 巧游电子科技 一般纳税人
  - combobox
  - text: 巧游电子科技
  - img
  - text: ＋ ✎ −
  - navigation: ◉ 仪表盘 基础数据 ◻ 伙伴管理 ◻ 库存商品 业务处理 ◉ 销售开单 ◻ 采购入库 ◻ 发票录入 ◻ 资金流水 财务核算 ◉ 财务总览 ◻ 费用管理 ◻ 固定资产 ◻ 银行账户 ◻ 银行对账 ◻ 往来管理 财务报表 ◉ 资产负债表/利润表 ◉ 现金流量表 ◻ 会计账簿 ◻ 会计规则指引 期末处理 ◉ 期末税务 系统管理 ◻ 操作日志 ◻ 数据备份
- heading "库存商品" [level=2]
- text: 商品目录 · 库存明细
- button "A admin":
  - text: A admin
  - img
- text: 2026/07/07周二
- main:
  - text: 库存商品
  - tablist:
    - tab "商品目录" [selected]
    - tab "库存明细"
  - tabpanel "商品目录":
    - text: 商品列表
    - button "新增商品":
      - img
      - text: 新增商品
    - button "批量导出" [disabled]:
      - img
      - text: 批量导出
    - img
    - textbox "搜索名称/编码"
    - textbox "SKU精确匹配"
    - combobox
    - text: 分类筛选
    - img
    - button "查询":
      - img
      - text: 查询
    - button "重置"
    - table:
      - rowgroup:
        - row "选择所有行 编码 商品名称 分类 单位 进价 售价 库存 预警线 操作":
          - columnheader "选择所有行":
            - checkbox "选择所有行"
          - columnheader "编码"
          - columnheader "商品名称"
          - columnheader "分类"
          - columnheader "单位"
          - columnheader "进价"
          - columnheader "售价"
          - columnheader "库存"
          - columnheader "预警线"
          - columnheader "操作"
    - table:
      - rowgroup:
        - row "选择当前行 SKU-信息系统 信息系统服务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除":
          - cell "选择当前行":
            - checkbox "选择当前行"
          - cell "SKU-信息系统"
          - cell "信息系统服务"
          - cell "服务"
          - cell "个"
          - cell "¥0.00"
          - cell "¥0.00"
          - cell "0"
          - cell "0"
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
        - row "选择当前行 SKU-修理修配 修理修配劳务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除":
          - cell "选择当前行":
            - checkbox "选择当前行"
          - cell "SKU-修理修配"
          - cell "修理修配劳务"
          - cell "服务"
          - cell "个"
          - cell "¥0.00"
          - cell "¥0.00"
          - cell "0"
          - cell "0"
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
        - row "选择当前行 SKU-微电子组 微电子组件 商品 个 ¥0.00 ¥0.00 0 0 编辑 删除":
          - cell "选择当前行":
            - checkbox "选择当前行"
          - cell "SKU-微电子组"
          - cell "微电子组件"
          - cell "商品"
          - cell "个"
          - cell "¥0.00"
          - cell "¥0.00"
          - cell "0"
          - cell "0"
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
        - row "选择当前行 SKU-其他加工 其他加工劳务 服务 个 ¥0.00 ¥0.00 0 0 编辑 删除":
          - cell "选择当前行":
            - checkbox "选择当前行"
          - cell "SKU-其他加工"
          - cell "其他加工劳务"
          - cell "服务"
          - cell "个"
          - cell "¥0.00"
          - cell "¥0.00"
          - cell "0"
          - cell "0"
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
        - row "选择当前行 SKU-维修备件 维修备件 商品 个 ¥0.00 ¥0.00 5 0 编辑 删除":
          - cell "选择当前行":
            - checkbox "选择当前行"
          - cell "SKU-维修备件"
          - cell "维修备件"
          - cell "商品"
          - cell "个"
          - cell "¥0.00"
          - cell "¥0.00"
          - cell "5"
          - cell "0"
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
        - row "选择当前行 个 ¥0.00 ¥0.00 0 0 编辑 删除":
          - cell "选择当前行":
            - checkbox "选择当前行"
          - cell
          - cell
          - cell
          - cell "个"
          - cell "¥0.00"
          - cell "¥0.00"
          - cell "0"
          - cell "0"
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
        - row "选择当前行 个 ¥0.00 ¥0.00 0 0 编辑 删除":
          - cell "选择当前行":
            - checkbox "选择当前行"
          - cell
          - cell
          - cell
          - cell "个"
          - cell "¥0.00"
          - cell "¥0.00"
          - cell "0"
          - cell "0"
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
        - row "选择当前行 个 ¥0.00 ¥0.00 0 0 编辑 删除":
          - cell "选择当前行":
            - checkbox "选择当前行"
          - cell
          - cell
          - cell
          - cell "个"
          - cell "¥0.00"
          - cell "¥0.00"
          - cell "0"
          - cell "0"
          - cell "编辑 删除":
            - button "编辑"
            - button "删除"
    - text: 共 8 条
    - combobox
    - text: 20条/页
    - img
    - button "上一页" [disabled]:
      - img
    - list:
      - listitem "第 1 页": "1"
    - button "下一页" [disabled]:
      - img
```

# Test source

```ts
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
  197 |       await page.locator('.el-dialog__footer button:has-text("保存")').click();
  198 | 
> 199 |       await expect(page.locator('.el-form-item__error').first()).toBeVisible();
      |                                                                  ^ Error: expect(locator).toBeVisible() failed
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
  241 |       await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill(productName);
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
```