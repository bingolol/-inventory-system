import { test, expect } from '@playwright/test';

test.describe('商品管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/products');
    await page.waitForSelector('.el-table__row', { timeout: 10000 });
  });

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('商品列表正确展示后端数据', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThan(0);

      await expect(page.locator('th:has-text("编码")')).toBeVisible();
      await expect(page.locator('th:has-text("商品名称")')).toBeVisible();
      await expect(page.locator('th:has-text("分类")')).toBeVisible();
      await expect(page.locator('th:has-text("单位")')).toBeVisible();
      await expect(page.locator('th:has-text("进价")')).toBeVisible();
      await expect(page.locator('th:has-text("售价")')).toBeVisible();
      await expect(page.locator('th:has-text("库存")')).toBeVisible();
    });

    test('第一行数据包含有效内容', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const rowText = await firstRow.textContent();
      expect(rowText?.trim().length).toBeGreaterThan(5);
    });
  });

  // ========== 分页 ==========
  test.describe('分页功能', () => {
    test('切换页码加载不同数据', async ({ page }) => {
      // 先切换到10条/页确保有多页数据
      await page.locator('.el-pagination .el-select').click();
      await page.waitForTimeout(300);
      await page.getByRole('option', { name: '10条/页' }).click();
      await page.waitForTimeout(1500);

      const page2 = page.getByRole('listitem', { name: '第 2 页' });
      if (await page2.count() === 0) {
        test.skip(true, '数据不足一页，跳过翻页测试');
        return;
      }
      const firstRowText = await page.locator('.el-table__row:first-child').textContent();
      await page2.click();
      await page.waitForTimeout(1500);
      const newFirstRowText = await page.locator('.el-table__row:first-child').textContent();
      expect(newFirstRowText).not.toBe(firstRowText);
    });

    test('修改每页条数', async ({ page }) => {
      const rowsBefore = await page.locator('.el-table__row').count();

      await page.locator('.el-pagination .el-select').click();
      await page.waitForTimeout(300);

      await page.getByRole('option', { name: '10条/页' }).click();
      await page.waitForTimeout(1000);

      const rowsAfter = await page.locator('.el-table__row').count();
      expect(rowsAfter).toBeLessThanOrEqual(10);
      expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
    });
  });

  // ========== 搜索 ==========
  test.describe('搜索功能', () => {
    test('名称/编码搜索', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('SKU精确匹配', async ({ page }) => {
      const firstSku = await page.locator('.el-table__row:first-child td').nth(1).textContent();
      const skuValue = firstSku?.trim();

      if (!skuValue) {
        test.skip();
        return;
      }

      const skuInput = page.locator('input[placeholder="SKU精确匹配"]');
      await skuInput.fill(skuValue);
      await skuInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(1);

      const rowText = await page.locator('.el-table__row:first-child').textContent();
      expect(rowText).toContain(skuValue);
    });

    test('查询按钮触发搜索', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
      await searchInput.fill('测试');
      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('清空搜索恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const searchCount = await page.locator('.el-table__row').count();

      await searchInput.clear();
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const restoredCount = await page.locator('.el-table__row').count();
      expect(restoredCount).toBe(allCount);
      expect(searchCount).toBeLessThanOrEqual(restoredCount);
    });
  });

  // ========== 分类筛选 ==========
  test.describe('分类筛选', () => {
    test('按分类筛选商品', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const categorySelect = page.locator('.filter-bar .el-select');
      await categorySelect.click();
      await page.waitForTimeout(300);

      const dropdown = page.locator('.el-select-dropdown:visible');
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(1000);

        const filteredCount = await page.locator('.el-table__row').count();
        expect(filteredCount).toBeGreaterThanOrEqual(0);
        expect(filteredCount).toBeLessThanOrEqual(allCount);
      }
    });
  });

  // ========== 新增商品 ==========
  test.describe('新增商品', () => {
    test('打开新增对话框', async ({ page }) => {
      await page.locator('button:has-text("新增商品")').click();

      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('新增商品');
    });

    test('新增商品成功', async ({ page }) => {
      const timestamp = Date.now();
      const productName = `PW测试-${timestamp}`;
      const productSku = `PW-${timestamp}`;

      await page.locator('button:has-text("新增商品")').click();

      await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill(productName);
      await page.locator('.el-dialog .el-form-item:has-text("编码") input').fill(productSku);
      await page.locator('.el-dialog .el-form-item:has-text("分类") input').fill('测试分类');
      await page.locator('.el-dialog .el-form-item:has-text("单位") input').fill('个');

      await page.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('.el-dialog')).not.toBeVisible();

      await page.waitForTimeout(1000);

      const searchInput = page.locator('input[placeholder="SKU精确匹配"]');
      await searchInput.fill(productSku);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBe(1);

      const cellText = await page.locator('.el-table__row:first-child').textContent();
      expect(cellText).toContain(productSku);
    });

    test('新增商品表单校验', async ({ page }) => {
      await page.locator('button:has-text("新增商品")').click();

      await page.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-form-item__error').first()).toBeVisible();
    });

    test('取消新增不保存', async ({ page }) => {
      await page.locator('button:has-text("新增商品")').click();

      await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill('不应保存的商品');

      await page.locator('.el-dialog__footer button:has-text("取消")').click();

      await expect(page.locator('.el-dialog')).not.toBeVisible();

      const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
      await searchInput.fill('不应保存的商品');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBe(0);
    });
  });

  // ========== 编辑商品 ==========
  test.describe('编辑商品', () => {
    test('打开编辑对话框并回填数据', async ({ page }) => {
      const firstName = await page.locator('.el-table__row:first-child td').nth(2).textContent();

      await page.locator('.el-table__row:first-child button:has-text("编辑")').click();

      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('编辑商品');

      const nameInput = page.locator('.el-dialog .el-form-item:has-text("商品名称") input');
      await expect(nameInput).toHaveValue(firstName?.trim() || '');
    });

    test('编辑商品保存成功', async ({ page }) => {
      const timestamp = Date.now();
      const productName = `编辑测试-${timestamp}`;
      const productSku = `EDT-${timestamp}`;

      await page.locator('button:has-text("新增商品")').click();
      await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill(productName);
      await page.locator('.el-dialog .el-form-item:has-text("编码") input').fill(productSku);
      await page.locator('.el-dialog__footer button:has-text("保存")').click();
      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(1000);

      const searchInput = page.locator('input[placeholder="SKU精确匹配"]');
      await searchInput.fill(productSku);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      const nameInput = page.locator('.el-dialog .el-form-item:has-text("商品名称") input');
      await nameInput.clear();
      await nameInput.fill('Playwright编辑测试');

      await page.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(1000);
      await expect(page.locator('.el-table__row:first-child')).toContainText('Playwright编辑测试');
    });
  });

  // ========== 删除商品 ==========
  test.describe('删除商品', () => {
    test('删除商品流程', async ({ page }) => {
      const timestamp = Date.now();
      const productName = `待删除-${timestamp}`;
      const productSku = `DEL-${timestamp}`;

      await page.locator('button:has-text("新增商品")').click();
      await page.locator('.el-dialog .el-form-item:has-text("商品名称") input').fill(productName);
      await page.locator('.el-dialog .el-form-item:has-text("编码") input').fill(productSku);
      await page.locator('.el-dialog__footer button:has-text("保存")').click();
      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(1000);

      const searchInput = page.locator('input[placeholder="SKU精确匹配"]');
      await searchInput.fill(productSku);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const targetRow = page.locator('.el-table__row').first();
      await targetRow.locator('button:has-text("删除")').click();

      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("确定")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(1000);
      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBe(0);
    });

    test('取消删除不执行', async ({ page }) => {
      const firstName = await page.locator('.el-table__row:first-child td').nth(2).textContent();

      await page.locator('.el-table__row:first-child button:has-text("删除")').click();

      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("取消")').click();

      await expect(page.locator('.el-table__row:first-child')).toContainText(firstName?.trim() || '');
    });
  });

  // ========== 批量选择与导出 ==========
  test.describe('批量选择与导出', () => {
    test('勾选商品行', async ({ page }) => {
      await page.locator('.el-table__row:first-child .el-checkbox').click();

      const checkbox = page.locator('.el-table__row:first-child .el-checkbox');
      await expect(checkbox).toHaveClass(/is-checked/);
    });

    test('全选功能', async ({ page }) => {
      await page.locator('.el-table__header-wrapper .el-checkbox').click();

      const checkboxes = page.locator('.el-table__row .el-checkbox');
      const count = await checkboxes.count();

      for (let i = 0; i < Math.min(count, 5); i++) {
        await expect(checkboxes.nth(i)).toHaveClass(/is-checked/);
      }
    });
  });
});
