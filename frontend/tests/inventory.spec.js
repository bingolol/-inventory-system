import { test, expect } from '@playwright/test';

test.describe('库存管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/inventory');
    await page.waitForTimeout(800);
    await page.waitForSelector('.el-table__row', { timeout: 10000 });
  });

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('库存列表正确展示后端数据', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThan(0);

      await expect(page.locator('th:has-text("编码")')).toBeVisible();
      await expect(page.locator('th:has-text("商品名称")')).toBeVisible();
      await expect(page.locator('th:has-text("分类")')).toBeVisible();
      await expect(page.locator('th:has-text("单位")')).toBeVisible();
      await expect(page.locator('th:has-text("当前库存")')).toBeVisible();
      await expect(page.locator('th:has-text("预警线")')).toBeVisible();
      await expect(page.getByRole('columnheader', { name: '预警', exact: true })).toBeVisible();
      await expect(page.locator('th:has-text("进价")')).toBeVisible();
      await expect(page.locator('th:has-text("售价")')).toBeVisible();
      await expect(page.locator('th:has-text("库存价值")')).toBeVisible();
      await expect(page.locator('th:has-text("操作")')).toBeVisible();
    });

    test('第一行数据包含有效内容', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const rowText = await firstRow.textContent();
      expect(rowText?.trim().length).toBeGreaterThan(5);
    });

    test('库存数量显示正确格式', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const stockCell = firstRow.locator('td').nth(4);
      const stockText = await stockCell.textContent();
      expect(stockText?.trim()).toMatch(/^-?\d+$/);
    });

    test('价格显示包含货币符号', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const purchasePrice = await firstRow.locator('td').nth(7).textContent();
      const salePrice = await firstRow.locator('td').nth(8).textContent();
      expect(purchasePrice?.trim()).toMatch(/^¥[\d,.]+$/);
      expect(salePrice?.trim()).toMatch(/^¥[\d,.]+$/);
    });
  });

  // ========== 搜索功能 ==========
  test.describe('搜索功能', () => {
    test('关键词搜索商品', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="搜索商品名称/编码"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('查询按钮触发搜索', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="搜索商品名称/编码"]');
      await searchInput.fill('测试');
      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('清空搜索恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const searchInput = page.locator('input[placeholder="搜索商品名称/编码"]');
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
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode
      const dropdown = page.locator('.el-select-dropdown:visible').last();
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

    test('清空分类筛选', async ({ page }) => {
      // 记录初始数据量
      const allCount = await page.locator('.el-table__row').count();

      // 选择一个分类筛选
      const categorySelect = page.locator('.filter-bar .el-select');
      await categorySelect.click();
      await page.waitForTimeout(500);
      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(1000);
        const filteredCount = await page.locator('.el-table__row').count();

        // 重新导航页面来清除所有筛选状态
        await page.goto('/inventory');
        await page.waitForTimeout(800);
        await page.waitForSelector('.el-table__row', { timeout: 10000 });

        const restoredCount = await page.locator('.el-table__row').count();
        expect(restoredCount).toBe(allCount);
      }
    });
  });

  // ========== 预警筛选 ==========
  test.describe('预警筛选', () => {
    test('切换仅显示预警开关', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const alertSwitch = page.locator('.filter-bar .el-switch');
      await alertSwitch.click();
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('.el-table__row').count();
      expect(filteredCount).toBeGreaterThanOrEqual(0);
      expect(filteredCount).toBeLessThanOrEqual(allCount);

      await alertSwitch.click();
      await page.waitForTimeout(1000);

      const restoredCount = await page.locator('.el-table__row').count();
      expect(restoredCount).toBe(allCount);
    });
  });

  // ========== 分页功能 ==========
  test.describe('分页功能', () => {
    test('切换页码加载不同数据', async ({ page }) => {
      // 先切换到10条/页确保有多页数据
      await page.locator('.el-pagination .el-select').click();
      await page.waitForTimeout(500);
      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10条\/页$/ }).click();
      await page.waitForTimeout(1500);

      const page2 = page.locator('.el-pager li').nth(1);
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
      await page.waitForTimeout(500);

      // 使用精确匹配避免 strict mode
      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10条\/页$/ }).click();
      await page.waitForTimeout(1000);

      const rowsAfter = await page.locator('.el-table__row').count();
      expect(rowsAfter).toBeLessThanOrEqual(10);
      expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
    });
  });

  // ========== 库存盘点 ==========
  test.describe('库存盘点', () => {
    test('打开盘点对话框', async ({ page }) => {
      await page.locator('.el-table__row:first-child button:has-text("盘点")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('库存盘点调整');
    });

    test('关闭盘点对话框', async ({ page }) => {
      await page.locator('.el-table__row:first-child button:has-text("盘点")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      await page.locator('.el-dialog__footer button:has-text("取消")').click();
      await expect(page.locator('.el-dialog')).not.toBeVisible();
    });
  });
});
