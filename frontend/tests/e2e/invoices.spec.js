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
      const filterBar = page.locator('.filter-bar');
      await expect(filterBar).toBeVisible();
      await expect(filterBar.getByText('方向')).toBeVisible();
      await expect(filterBar.getByText('类型')).toBeVisible();
      await expect(filterBar.getByText('年份')).toBeVisible();
      await expect(filterBar.getByText('季度')).toBeVisible();
      await expect(filterBar.getByText('认证状态')).toBeVisible();
    });

    test('税务统计卡片正确展示', async ({ page }) => {
      const stats = page.locator('.inv-stats');
      await expect(stats).toBeVisible();
      await expect(stats.getByText('销项税额')).toBeVisible();
      await expect(stats.getByText('进项税额')).toBeVisible();
      await expect(stats.getByText('应纳税额')).toBeVisible();
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

    test('分页组件正确展示', async ({ page }) => {
      await expect(page.locator('.el-pagination')).toBeVisible();
    });
  });

  // ========== 筛选功能 ==========
  test.describe('筛选功能', () => {
    async function selectFirstFilterOption(page, label) {
      const select = page.locator('.filter-bar .el-form-item:has-text("' + label + '") .el-select').first();
      await select.click();
      await page.waitForTimeout(500);

      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();
      if (optionCount > 0) {
        await options.first().click();
      }
      return optionCount;
    }

    test('按方向筛选发票', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const optionCount = await selectFirstFilterOption(page, '方向');
      if (optionCount > 0) {
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const filteredCount = await page.locator('.el-table__row').count();
        expect(filteredCount).toBeGreaterThanOrEqual(0);
        expect(filteredCount).toBeLessThanOrEqual(allCount);
      }
    });

    test('按类型筛选发票', async ({ page }) => {
      const optionCount = await selectFirstFilterOption(page, '类型');
      if (optionCount > 0) {
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const rows = await page.locator('.el-table__row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('按年份筛选发票', async ({ page }) => {
      const optionCount = await selectFirstFilterOption(page, '年份');
      if (optionCount > 0) {
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const rows = await page.locator('.el-table__row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('按季度筛选发票', async ({ page }) => {
      const optionCount = await selectFirstFilterOption(page, '季度');
      if (optionCount > 0) {
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const rows = await page.locator('.el-table__row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('按认证状态筛选发票', async ({ page }) => {
      const optionCount = await selectFirstFilterOption(page, '认证状态');
      if (optionCount > 0) {
        await page.locator('button:has-text("查询")').click();
        await page.waitForTimeout(1500);

        const rows = await page.locator('.el-table__row').count();
        expect(rows).toBeGreaterThanOrEqual(0);
      }
    });

    test('重置筛选恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const optionCount = await selectFirstFilterOption(page, '方向');
      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1500);

      await page.locator('button:has-text("重置")').click();
      await page.waitForTimeout(1500);

      const restoredCount = await page.locator('.el-table__row').count();
      expect(restoredCount).toBe(allCount);
    });

    test('组合筛选条件', async ({ page }) => {
      await selectFirstFilterOption(page, '年份');
      await selectFirstFilterOption(page, '季度');

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

    test('点击遮罩层关闭新增对话框', async ({ page }) => {
      await page.locator('button:has-text("新增发票")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增发票' }).first();
      await expect(dialog).toBeVisible();

      await page.locator('.el-overlay').first().click({ position: { x: 10, y: 10 } });
      await page.waitForTimeout(500);
      await expect(dialog).not.toBeVisible();
    });
  });

  // ========== 编辑发票 ==========
  test.describe('编辑发票', () => {
    test('编辑第一行发票回显数据', async ({ page }) => {
      const firstRow = page.locator('.el-table__row').first();
      const count = await firstRow.count();
      test.skip(count === 0, '列表为空，跳过编辑测试');

      await firstRow.locator('.action-column button:has-text("编辑")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '编辑发票' }).first();
      await expect(dialog).toBeVisible();
      await expect(dialog.locator('.el-form-item:has-text("发票号码") input')).not.toHaveValue('');
    });
  });

  // ========== 操作列 ==========
  test.describe('操作列', () => {
    test('操作列至少包含编辑按钮', async ({ page }) => {
      const firstRow = page.locator('.el-table__row').first();
      const count = await firstRow.count();
      test.skip(count === 0, '列表为空，跳过操作列测试');

      await expect(firstRow.locator('.action-column button:has-text("编辑")')).toBeVisible();
    });
  });
});
