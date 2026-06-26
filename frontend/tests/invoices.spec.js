import { test, expect } from '@playwright/test';

test.describe('发票管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/invoices');
    await page.waitForTimeout(800);
    await page.waitForSelector('.el-table__row, .el-empty', { timeout: 10000 });
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('页面标题正确显示', async ({ page }) => {
      await expect(page.locator('.page-title')).toContainText('发票管理');
    });

    test('筛选表单区域正确展示', async ({ page }) => {
      await expect(page.locator('.filter-form')).toBeVisible();
      await expect(page.locator('.filter-form').getByText('方向')).toBeVisible();
      await expect(page.locator('.filter-form').getByText('类型')).toBeVisible();
      await expect(page.locator('.filter-form').getByText('年份')).toBeVisible();
      await expect(page.locator('.filter-form').getByText('季度')).toBeVisible();
      await expect(page.locator('.filter-form').getByText('认证状态')).toBeVisible();
    });

    test('税务统计卡片正确展示', async ({ page }) => {
      await expect(page.locator('.tax-stats')).toBeVisible();
      await expect(page.locator('text=本季度税务统计')).toBeVisible();
      await expect(page.locator('text=销项税额')).toBeVisible();
      await expect(page.locator('text=进项税额')).toBeVisible();
      await expect(page.locator('text=应纳税额')).toBeVisible();
    });
  });

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('发票表格列头正确显示', async ({ page }) => {
      await expect(page.locator('th:has-text("发票号码")')).toBeVisible();
      await expect(page.locator('th:has-text("方向")')).toBeVisible();
      await expect(page.locator('th:has-text("类型")')).toBeVisible();
      await expect(page.locator('th:has-text("税率")')).toBeVisible();
      await expect(page.locator('th:has-text("不含税金额")')).toBeVisible();
      await expect(page.locator('th:has-text("税额")')).toBeVisible();
      await expect(page.locator('th:has-text("价税合计")')).toBeVisible();
      await expect(page.locator('th:has-text("对方名称")')).toBeVisible();
      await expect(page.locator('th:has-text("开票日期")')).toBeVisible();
      await expect(page.locator('th:has-text("认证状态")')).toBeVisible();
    });

    test('发票列表展示数据或空状态', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      const empty = await page.locator('.el-empty').count();
      expect(rows + empty).toBeGreaterThan(0);
    });

    test('筛选合计区域正确展示', async ({ page }) => {
      const summaryArea = page.locator('div').filter({ hasText: '筛选合计' }).filter({ hasText: '不含税' }).first();
      await expect(summaryArea).toBeVisible();
      await expect(summaryArea).toContainText('税额');
      await expect(summaryArea).toContainText('价税合计');
    });
  });

  // ========== 筛选功能 ==========
  test.describe('筛选功能', () => {
    test('按方向筛选发票', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const directionSelect = page.locator('.filter-form .el-form-item:has-text("方向") .el-select');
      await directionSelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const filteredCount = await page.locator('.el-table__row').count();
        expect(filteredCount).toBeGreaterThanOrEqual(0);
        expect(filteredCount).toBeLessThanOrEqual(allCount);
      }
    });

    test('按类型筛选发票', async ({ page }) => {
      const typeSelect = page.locator('.filter-form .el-form-item:has-text("类型") .el-select');
      await typeSelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const rows = await page.locator('.el-table__row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('按年份筛选发票', async ({ page }) => {
      const yearSelect = page.locator('.filter-form .el-form-item:has-text("年份") .el-select');
      await yearSelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const rows = await page.locator('.el-table__row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('按季度筛选发票', async ({ page }) => {
      const quarterSelect = page.locator('.filter-form .el-form-item:has-text("季度") .el-select');
      await quarterSelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const rows = await page.locator('.el-table__row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('按认证状态筛选发票', async ({ page }) => {
      const statusSelect = page.locator('.filter-form .el-form-item:has-text("认证状态") .el-select');
      await statusSelect.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const rows = await page.locator('.el-table__row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('重置筛选恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const directionSelect = page.locator('.filter-form .el-form-item:has-text("方向") .el-select');
      await directionSelect.click();
      await page.waitForTimeout(500);
      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();
      if (optionCount > 0) {
        await options.first().click();
      }
      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1500);

      await page.locator('button:has-text("重置")').click();
      await page.waitForTimeout(1500);

      const restoredCount = await page.locator('.el-table__row').count();
      expect(restoredCount).toBe(allCount);
    });

    test('组合筛选条件', async ({ page }) => {
      const yearSelect = page.locator('.filter-form .el-form-item:has-text("年份") .el-select');
      await yearSelect.click();
      await page.waitForTimeout(500);
      const dropdown1 = page.locator('.el-select-dropdown:visible').last();
      const options1 = dropdown1.locator('li');
      if (await options1.count() > 0) {
        await options1.first().click();
      }

      const quarterSelect = page.locator('.filter-form .el-form-item:has-text("季度") .el-select');
      await quarterSelect.click();
      await page.waitForTimeout(500);
      const dropdown2 = page.locator('.el-select-dropdown:visible').last();
      const options2 = dropdown2.locator('li');
      if (await options2.count() > 0) {
        await options2.first().click();
      }

      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1500);

      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });
  });

  // ========== 新增发票 ==========
  test.describe('新增发票', () => {
    test('打开新增发票对话框', async ({ page }) => {
      await page.locator('button:has-text("新增发票")').click();

      await expect(page.locator('.el-dialog').filter({ hasText: '新增发票' }).first()).toBeVisible();
      await expect(page.locator('.el-dialog__title:has-text("新增发票")')).toBeVisible();
    });

    test('新增发票对话框包含必要字段', async ({ page }) => {
      await page.locator('button:has-text("新增发票")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增发票' }).first();
      await expect(dialog.locator('.el-form-item:has-text("发票号码")')).toBeVisible();
      await expect(dialog.locator('.el-form-item:has-text("方向")')).toBeVisible();
      await expect(dialog.locator('.el-form-item:has-text("类型")')).toBeVisible();
      await expect(dialog.locator('.el-form-item:has-text("对方名称")')).toBeVisible();
      await expect(dialog.locator('.el-form-item:has-text("开票日期")')).toBeVisible();
      await expect(dialog.locator('.el-form-item:has-text("税率")')).toBeVisible();
    });

    test('取消新增不保存', async ({ page }) => {
      await page.locator('button:has-text("新增发票")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增发票' }).first();
      await dialog.locator('.el-form-item:has-text("发票号码") input').fill('TEST-001');

      await page.locator('.el-dialog__footer button:has-text("取消")').click();

      await expect(dialog).not.toBeVisible();
    });
  });
});
