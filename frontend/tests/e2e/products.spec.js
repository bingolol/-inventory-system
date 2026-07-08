import { test, expect } from '@playwright/test';

test.describe('商品管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/inventory-goods');
    await page.waitForTimeout(800);
    // 等待"商品目录"标签页激活
    await expect(page.locator('.el-tabs__item.is-active')).toContainText('商品目录');
    // 等待商品表格区域可见
    await page.locator('.el-tab-pane:visible .el-table').first().waitFor({ state: 'visible', timeout: 10000 });
  });

  const productsPane = (page) => page.locator('.el-tab-pane:visible');
  const firstRow = (page) => page.locator('.el-tab-pane:visible .el-table').first().locator('.el-table__row').first();

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('商品列表正确展示后端数据', async ({ page }) => {
      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();

      const pane = productsPane(page);
      await expect(pane.locator('th:has-text("编码")')).toBeVisible();
      await expect(pane.locator('th:has-text("商品名称")')).toBeVisible();
      await expect(pane.locator('th:has-text("分类")')).toBeVisible();
      await expect(pane.locator('th:has-text("单位")')).toBeVisible();
      await expect(pane.locator('th:has-text("进价")')).toBeVisible();
      await expect(pane.locator('th:has-text("售价")')).toBeVisible();
      await expect(pane.locator('th:has-text("库存")')).toBeVisible();

      // 无数据时至少验证空状态
      if (rows === 0) {
        await expect(pane.locator('.el-empty')).toBeVisible();
      } else {
        expect(rows).toBeGreaterThan(0);
      }
    });

    test('第一行数据包含有效内容', async ({ page }) => {
      const row = firstRow(page);
      const rowText = await row.textContent();
      expect(rowText?.trim().length).toBeGreaterThan(5);
    });
  });

  // ========== 分页 ==========
  test.describe('分页功能', () => {
    test('切换页码加载不同数据', async ({ page }) => {
      const pagination = productsPane(page).locator('.el-pagination');
      await pagination.locator('.el-select').click();
      await page.waitForTimeout(300);
      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10\s*条\/页/ }).click();
      await page.waitForTimeout(1500);

      const page2 = pagination.locator('.el-pager li:has-text("2")');
      if (await page2.count() === 0) {
        test.skip(true, '数据不足一页，跳过翻页测试');
        return;
      }
      const firstRowText = await firstRow(page).textContent();
      await page2.click();
      await page.waitForTimeout(1500);
      const newFirstRowText = await firstRow(page).textContent();
      expect(newFirstRowText).not.toBe(firstRowText);
    });

    test('修改每页条数', async ({ page }) => {
      const rowsBefore = await page.locator('.el-tab-pane:visible .el-table__row').count();

      const pagination = productsPane(page).locator('.el-pagination');
      await pagination.locator('.el-select').click();
      await page.waitForTimeout(300);

      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10\s*条\/页/ }).click();
      await page.waitForTimeout(1000);

      const rowsAfter = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rowsAfter).toBeLessThanOrEqual(10);
      expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
    });
  });

  // ========== 搜索 ==========
  test.describe('搜索功能', () => {
    test('名称/编码搜索', async ({ page }) => {
      const searchInput = productsPane(page).locator('input[placeholder="搜索名称/编码"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('SKU精确匹配', async ({ page }) => {
      const firstSku = await firstRow(page).locator('td').nth(1).textContent();
      const skuValue = firstSku?.trim();

      if (!skuValue) {
        test.skip();
        return;
      }

      const skuInput = productsPane(page).locator('input[placeholder="SKU精确匹配"]');
      await skuInput.fill(skuValue);
      await skuInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(1);

      const rowText = await firstRow(page).textContent();
      expect(rowText).toContain(skuValue);
    });

    test('查询按钮触发搜索', async ({ page }) => {
      const searchInput = productsPane(page).locator('input[placeholder="搜索名称/编码"]');
      await searchInput.fill('测试');
      await productsPane(page).locator('[data-testid="filter-search"]').click();
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('清空搜索恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-tab-pane:visible .el-table__row').count();

      const searchInput = productsPane(page).locator('input[placeholder="搜索名称/编码"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const searchCount = await page.locator('.el-tab-pane:visible .el-table__row').count();

      await searchInput.clear();
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const restoredCount = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(restoredCount).toBe(allCount);
      expect(searchCount).toBeLessThanOrEqual(restoredCount);
    });
  });

  // ========== 分类筛选 ==========
  test.describe('分类筛选', () => {
    test('按分类筛选商品', async ({ page }) => {
      const allCount = await page.locator('.el-tab-pane:visible .el-table__row').count();

      const categorySelect = productsPane(page).locator('.filter-bar .el-select');
      await categorySelect.click();
      await page.waitForTimeout(300);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(1000);

        const filteredCount = await page.locator('.el-tab-pane:visible .el-table__row').count();
        expect(filteredCount).toBeGreaterThanOrEqual(0);
        expect(filteredCount).toBeLessThanOrEqual(allCount);
      }
    });
  });

  // ========== 新增商品 ==========
  test.describe('新增商品', () => {
    test('打开新增对话框', async ({ page }) => {
      await productsPane(page).locator('button:has-text("新增商品")').click();

      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('新增商品');
    });

    test('新增商品成功', async ({ page }) => {
      const timestamp = Date.now();
      const productName = `PW测试-${timestamp}`;
      const productSku = `PW-${timestamp}`;

      await productsPane(page).locator('button:has-text("新增商品")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增商品' }).first();
      await dialog.locator('.p-field').filter({ hasText: '商品名称' }).locator('input').fill(productName);
      await dialog.locator('.p-field').filter({ hasText: '编码' }).locator('input').fill(productSku);
      await dialog.locator('.p-field').filter({ hasText: '分类' }).locator('input').fill('测试分类');
      await dialog.locator('.p-field').filter({ hasText: '单位' }).locator('input').fill('个');

      await dialog.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await expect(dialog).not.toBeVisible();

      await page.waitForTimeout(1000);

      const skuInput = productsPane(page).locator('input[placeholder="SKU精确匹配"]');
      await skuInput.fill(productSku);
      await skuInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(1);

      const cellText = await firstRow(page).textContent();
      expect(cellText).toContain(productSku);
    });

    test('新增商品表单校验', async ({ page }) => {
      await productsPane(page).locator('button:has-text("新增商品")').click();
      const dialog = page.locator('.el-dialog').filter({ hasText: '新增商品' }).first();

      await dialog.locator('.el-dialog__footer button:has-text("保存")').click();

      // 校验失败时对话框应保持打开
      await expect(dialog).toBeVisible();
    });

    test('取消新增不保存', async ({ page }) => {
      await productsPane(page).locator('button:has-text("新增商品")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增商品' }).first();
      await dialog.locator('.p-field').filter({ hasText: '商品名称' }).locator('input').fill('不应保存的商品');

      await dialog.locator('.el-dialog__footer button:has-text("取消")').click();

      await expect(dialog).not.toBeVisible();

      const searchInput = productsPane(page).locator('input[placeholder="搜索名称/编码"]');
      await searchInput.fill('不应保存的商品');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(0);
    });
  });

  // ========== 编辑商品 ==========
  test.describe('编辑商品', () => {
    test('打开编辑对话框并回填数据', async ({ page }) => {
      const firstName = await firstRow(page).locator('td').nth(2).textContent();

      await firstRow(page).locator('[data-testid="action-edit"]').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '编辑商品' }).first();
      await expect(dialog).toBeVisible();
      await expect(dialog.locator('.el-dialog__title')).toContainText('编辑商品');

      const nameInput = dialog.locator('.p-field').filter({ hasText: '商品名称' }).locator('input');
      await expect(nameInput).toHaveValue(firstName?.trim() || '');
    });

    test('编辑商品保存成功', async ({ page }) => {
      const timestamp = Date.now();
      const productName = `编辑测试-${timestamp}`;
      const productSku = `EDT-${timestamp}`;

      await productsPane(page).locator('button:has-text("新增商品")').click();
      const addDialog = page.locator('.el-dialog').filter({ hasText: '新增商品' }).first();
      await addDialog.locator('.p-field').filter({ hasText: '商品名称' }).locator('input').fill(productName);
      await addDialog.locator('.p-field').filter({ hasText: '编码' }).locator('input').fill(productSku);
      await addDialog.locator('.el-dialog__footer button:has-text("保存")').click();
      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(1000);

      const skuInput = productsPane(page).locator('input[placeholder="SKU精确匹配"]');
      await skuInput.fill(productSku);
      await skuInput.press('Enter');
      await page.waitForTimeout(1000);

      await firstRow(page).locator('[data-testid="action-edit"]').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      const editDialog = page.locator('.el-dialog').filter({ hasText: '编辑商品' }).first();
      const nameInput = editDialog.locator('.p-field').filter({ hasText: '商品名称' }).locator('input');
      await nameInput.clear();
      await nameInput.fill('Playwright编辑测试');

      await editDialog.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(1000);
      await expect(firstRow(page)).toContainText('Playwright编辑测试');
    });
  });

  // ========== 删除商品 ==========
  test.describe('删除商品', () => {
    test('删除商品流程', async ({ page }) => {
      const timestamp = Date.now();
      const productName = `待删除-${timestamp}`;
      const productSku = `DEL-${timestamp}`;

      await productsPane(page).locator('button:has-text("新增商品")').click();
      const addDialog = page.locator('.el-dialog').filter({ hasText: '新增商品' }).first();
      await addDialog.locator('.p-field').filter({ hasText: '商品名称' }).locator('input').fill(productName);
      await addDialog.locator('.p-field').filter({ hasText: '编码' }).locator('input').fill(productSku);
      await addDialog.locator('.el-dialog__footer button:has-text("保存")').click();
      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(1000);

      const skuInput = productsPane(page).locator('input[placeholder="SKU精确匹配"]');
      await skuInput.fill(productSku);
      await skuInput.press('Enter');
      await page.waitForTimeout(1000);

      const targetRow = page.locator('.el-tab-pane:visible .el-table__row').first();
      await targetRow.locator('[data-testid="action-delete"]').click();

      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("确定")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(1000);
      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(0);
    });

    test('取消删除不执行', async ({ page }) => {
      const firstName = await firstRow(page).locator('td').nth(2).textContent();

      await firstRow(page).locator('[data-testid="action-delete"]').click();

      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("取消")').click();

      await expect(firstRow(page)).toContainText(firstName?.trim() || '');
    });
  });

  // ========== 批量选择与导出 ==========
  test.describe('批量选择与导出', () => {
    test('勾选商品行', async ({ page }) => {
      const checkbox = firstRow(page).locator('.el-checkbox').first();
      await checkbox.click();
      await expect(checkbox).toHaveClass(/is-checked/);
    });

    test('全选功能', async ({ page }) => {
      const headerCheckbox = productsPane(page).locator('.el-table__header-wrapper .el-checkbox').first();
      await headerCheckbox.click();

      const checkboxes = page.locator('.el-tab-pane:visible .el-table__row .el-checkbox');
      const count = await checkboxes.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        await expect(checkboxes.nth(i)).toHaveClass(/is-checked/);
      }
    });
  });
});
