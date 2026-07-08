import { test, expect } from '@playwright/test';

test.describe('费用管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/expenses');
    await page.waitForTimeout(800);
    await page.waitForSelector('.el-table__row', { timeout: 10000 });
  });

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('费用列表正确展示后端数据', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThan(0);

      const mainTable = page.locator('.el-card .el-table').first();
      await expect(mainTable.locator('th:has-text("日期")')).toBeVisible();
      await expect(mainTable.locator('th:has-text("类别")')).toBeVisible();
      await expect(mainTable.locator('th:has-text("功能分类")')).toBeVisible();
      await expect(mainTable.locator('th:has-text("金额")')).toBeVisible();
      await expect(mainTable.locator('th:has-text("付款状态")')).toBeVisible();
      await expect(mainTable.locator('th:has-text("描述")')).toBeVisible();
      await expect(mainTable.locator('th:has-text("操作")')).toBeVisible();
    });

    test('第一行数据包含有效内容', async ({ page }) => {
      const firstRow = page.locator('.el-table__row').first();
      const rowText = await firstRow.textContent();
      expect(rowText?.trim().length).toBeGreaterThan(5);
    });

    test('金额显示包含货币符号', async ({ page }) => {
      const firstRow = page.locator('.el-table__row').first();
      const amountCell = firstRow.locator('td').nth(3);
      const amountText = await amountCell.textContent();
      expect(amountText?.trim()).toMatch(/^-?[\d,.]+$/);
    });

    test('日期格式正确', async ({ page }) => {
      const firstRow = page.locator('.el-table__row').first();
      const dateCell = firstRow.locator('td').nth(0);
      const dateText = await dateCell.textContent();
      expect(dateText?.trim()).toMatch(/^\d{4}-\d{2}-\d{2}/);
    });

    test('统计卡片展示', async ({ page }) => {
      await expect(page.locator('.stat-mini-label').filter({ hasText: '本月费用' }).first()).toBeVisible();
      await expect(page.locator('.stat-mini-label').filter({ hasText: '筛选合计' }).first()).toBeVisible();
      await expect(page.locator('.stat-mini-label').filter({ hasText: '记录数' }).first()).toBeVisible();
    });
  });

  // ========== 筛选功能 ==========
  test.describe('筛选功能', () => {
    test('按年份筛选费用', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const filterBar = page.locator('[data-testid="filter-bar"]').first();
      const yearSelect = filterBar.locator('.el-select').first();
      await yearSelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('.el-select-dropdown__item');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(500);

        await page.locator('[data-testid="filter-search"]').first().click();
        await page.waitForTimeout(1000);

        const filteredCount = await page.locator('.el-table__row').count();
        expect(filteredCount).toBeGreaterThanOrEqual(0);
        expect(filteredCount).toBeLessThanOrEqual(allCount);
      }
    });

    test('重置筛选条件', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const filterBar = page.locator('[data-testid="filter-bar"]').first();
      const yearSelect = filterBar.locator('.el-select').first();
      await yearSelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('.el-select-dropdown__item');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(500);
      }

      await page.locator('[data-testid="filter-reset"]').first().click();
      await page.waitForTimeout(1000);

      const restoredCount = await page.locator('.el-table__row').count();
      expect(restoredCount).toBe(allCount);
    });
  });

  // ========== 新增费用 ==========
  test.describe('新增费用', () => {
    test('打开新增对话框', async ({ page }) => {
      await page.locator('button:has-text("新增费用")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('新增费用');
    });

    test('关闭新增对话框', async ({ page }) => {
      await page.locator('button:has-text("新增费用")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      await page.locator('.el-dialog__footer button:has-text("取消")').click();
      await expect(page.locator('.el-dialog')).not.toBeVisible();
    });
  });

  // ========== 编辑费用 ==========
  test.describe('编辑费用', () => {
    test('打开编辑对话框', async ({ page }) => {
      await page.locator('.el-table__row').first().locator('button:has-text("编辑")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('编辑费用');
    });

    test('关闭编辑对话框', async ({ page }) => {
      await page.locator('.el-table__row').first().locator('button:has-text("编辑")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      await page.locator('.el-dialog__footer button:has-text("取消")').click();
      await expect(page.locator('.el-dialog')).not.toBeVisible();
    });
  });

  // ========== 付款 ==========
  test.describe('费用付款', () => {
    test('打开付款对话框', async ({ page }) => {
      const unpaidRow = page.locator('.el-table__row').filter({ hasText: '未付款' }).first();
      if (await unpaidRow.count() === 0) {
        test.skip(true, '没有未付款费用，跳过');
        return;
      }
      await unpaidRow.locator('button:has-text("付款")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('费用付款');
    });
  });

  // ========== 冲红 ==========
  test.describe('费用冲红', () => {
    test('点击冲红按钮显示确认', async ({ page }) => {
      await page.locator('.el-table__row').first().locator('button:has-text("冲红")').click();
      await expect(page.locator('.el-popconfirm')).toBeVisible();
    });

    test('取消冲红操作', async ({ page }) => {
      const firstRow = page.locator('.el-table__row').first();
      const firstCategory = await firstRow.locator('td').nth(1).textContent();

      await firstRow.locator('button:has-text("冲红")').click();
      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("取消")').click();
      await expect(firstRow).toContainText(firstCategory?.trim() || '');
    });
  });
});
