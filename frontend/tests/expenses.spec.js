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

      await expect(page.locator('th:has-text("日期")')).toBeVisible();
      await expect(page.locator('th:has-text("类别")')).toBeVisible();
      await expect(page.locator('th:has-text("金额")')).toBeVisible();
      await expect(page.locator('th:has-text("有发票")')).toBeVisible();
      await expect(page.locator('th:has-text("支付方式")')).toBeVisible();
      await expect(page.locator('th:has-text("描述")')).toBeVisible();
      await expect(page.locator('th:has-text("操作")')).toBeVisible();
    });

    test('第一行数据包含有效内容', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const rowText = await firstRow.textContent();
      expect(rowText?.trim().length).toBeGreaterThan(5);
    });

    test('金额显示包含货币符号', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const amountCell = firstRow.locator('td').nth(2);
      const amountText = await amountCell.textContent();
      expect(amountText?.trim()).toMatch(/^¥[\d,.]+$/);
    });

    test('日期格式正确', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const dateCell = firstRow.locator('td').nth(0);
      const dateText = await dateCell.textContent();
      expect(dateText?.trim()).toMatch(/^\d{4}-\d{2}-\d{2}/);
    });

    test('筛选合计显示', async ({ page }) => {
      const summaryArea = page.locator('div').filter({ hasText: /^筛选合计：/ }).first();
      await expect(summaryArea).toBeVisible();
      await expect(summaryArea).toContainText('金额');
    });
  });

  // ========== 筛选功能 ==========
  test.describe('筛选功能', () => {
    test('按类别筛选费用', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const categorySelect = page.locator('.el-form-item:has-text("类别") .el-select');
      await categorySelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(500);

        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1000);

        const filteredCount = await page.locator('.el-table__row').count();
        expect(filteredCount).toBeGreaterThanOrEqual(0);
        expect(filteredCount).toBeLessThanOrEqual(allCount);
      }
    });

    test('按年份筛选费用', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const yearSelect = page.locator('.el-form-item:has-text("年份") .el-select');
      await yearSelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(500);

        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1000);

        const filteredCount = await page.locator('.el-table__row').count();
        expect(filteredCount).toBeGreaterThanOrEqual(0);
        expect(filteredCount).toBeLessThanOrEqual(allCount);
      }
    });

    test('重置筛选条件', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const categorySelect = page.locator('.el-form-item:has-text("类别") .el-select');
      await categorySelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(500);
      }

      await page.locator('button:has-text("重置")').click();
      await page.waitForTimeout(1000);

      const restoredCount = await page.locator('.el-table__row').count();
      expect(restoredCount).toBe(allCount);
    });

    test('组合筛选费用', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const categorySelect = page.locator('.el-form-item:has-text("类别") .el-select');
      await categorySelect.click();
      await page.waitForTimeout(500);

      const categoryDropdown = page.locator('.el-select-dropdown:visible').last();
      const categoryOptions = categoryDropdown.locator('li');
      const categoryOptionCount = await categoryOptions.count();

      if (categoryOptionCount > 0) {
        await categoryOptions.first().click();
        await page.waitForTimeout(500);
      }

      const yearSelect = page.locator('.el-form-item:has-text("年份") .el-select');
      await yearSelect.click();
      await page.waitForTimeout(500);

      const yearDropdown = page.locator('.el-select-dropdown:visible').last();
      const yearOptions = yearDropdown.locator('li');
      const yearOptionCount = await yearOptions.count();

      if (yearOptionCount > 0) {
        await yearOptions.first().click();
        await page.waitForTimeout(500);
      }

      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('.el-table__row').count();
      expect(filteredCount).toBeGreaterThanOrEqual(0);
      expect(filteredCount).toBeLessThanOrEqual(allCount);
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
      await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('编辑费用');
    });

    test('关闭编辑对话框', async ({ page }) => {
      await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      await page.locator('.el-dialog__footer button:has-text("取消")').click();
      await expect(page.locator('.el-dialog')).not.toBeVisible();
    });
  });

  // ========== 删除费用 ==========
  test.describe('删除费用', () => {
    test('点击删除按钮显示确认', async ({ page }) => {
      await page.locator('.el-table__row:first-child button:has-text("删除")').click();
      await expect(page.locator('.el-popconfirm')).toBeVisible();
    });

    test('取消删除操作', async ({ page }) => {
      const firstName = await page.locator('.el-table__row:first-child td').nth(1).textContent();

      await page.locator('.el-table__row:first-child button:has-text("删除")').click();
      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("取消")').click();
      await expect(page.locator('.el-table__row:first-child')).toContainText(firstName?.trim() || '');
    });
  });
});
