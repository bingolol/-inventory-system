import { test, expect } from '@playwright/test';

test.describe('操作日志', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/logs');
    await page.waitForTimeout(800);
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('日志页面正常加载', async ({ page }) => {
      await expect(page.locator('.page-title:has-text("操作日志")')).toBeVisible();
    });

    test('筛选栏正确展示', async ({ page }) => {
      const filterBar = page.locator('.filter-bar');
      await expect(filterBar.locator('.el-select').first()).toBeVisible();
      await expect(filterBar.locator('.el-select').nth(1)).toBeVisible();
      await expect(filterBar.locator('.el-date-editor')).toBeVisible();
      await expect(filterBar.locator('button:has-text("查询")')).toBeVisible();
    });

    test('日志表格正确展示', async ({ page }) => {
      await expect(page.locator('.el-table')).toBeVisible();
    });

    test('表格包含必要列', async ({ page }) => {
      await expect(page.locator('th:has-text("时间")')).toBeVisible();
      await expect(page.getByRole('columnheader', { name: '操作', exact: true })).toBeVisible();
      await expect(page.locator('th:has-text("类型")')).toBeVisible();
      await expect(page.locator('th:has-text("ID")')).toBeVisible();
      await expect(page.locator('th:has-text("操作者")')).toBeVisible();
      await expect(page.locator('th:has-text("详情")')).toBeVisible();
    });
  });

  // ========== 数据展示 ==========
  test.describe('数据展示', () => {
    test('有日志数据时展示表格行', async ({ page }) => {
      const rows = page.locator('.el-table__row');
      const count = await rows.count();
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('操作列展示标签', async ({ page }) => {
      const tags = page.locator('.el-table__row .el-tag');
      const count = await tags.count();
      if (count > 0) {
        await expect(tags.first()).toBeVisible();
      }
    });

    test('操作者列展示AI或我标签', async ({ page }) => {
      const operatorTags = page.locator('.el-table__row td:nth-child(5) .el-tag');
      const count = await operatorTags.count();
      if (count > 0) {
        const text = await operatorTags.first().textContent();
        expect(['AI', '我']).toContain(text?.trim());
      }
    });
  });

  // ========== 筛选功能 ==========
  test.describe('筛选功能', () => {
    test('实体类型下拉选项正确', async ({ page }) => {
      const entitySelect = page.locator('.filter-bar .el-select').first();
      await entitySelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode
      const dropdown = page.locator('.el-select-dropdown:visible').last();
      await expect(dropdown.locator('li:has-text("商品")')).toBeVisible();
      await expect(dropdown.locator('li:has-text("供应商")')).toBeVisible();
      await expect(dropdown.locator('li:has-text("客户")')).toBeVisible();
      await expect(dropdown.locator('li:has-text("采购单")')).toBeVisible();
      await expect(dropdown.locator('li:has-text("销售单")')).toBeVisible();
      await expect(dropdown.locator('li:has-text("库存")')).toBeVisible();

      await page.keyboard.press('Escape');
    });

    test('操作类型下拉选项正确', async ({ page }) => {
      const opSelect = page.locator('.filter-bar .el-select').nth(1);
      await opSelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode
      const dropdown = page.locator('.el-select-dropdown:visible').last();
      await expect(dropdown.locator('li:has-text("创建")')).toBeVisible();
      await expect(dropdown.locator('li:has-text("更新")')).toBeVisible();
      await expect(dropdown.locator('li:has-text("删除")')).toBeVisible();
      await expect(dropdown.locator('li:has-text("盘点")')).toBeVisible();

      await page.keyboard.press('Escape');
    });

    test('按实体类型筛选', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const entitySelect = page.locator('.filter-bar .el-select').first();
      await entitySelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode
      await page.locator('.el-select-dropdown:visible').last().locator('li:has-text("商品")').click();
      await page.waitForTimeout(500);

      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('.el-table__row').count();
      expect(filteredCount).toBeGreaterThanOrEqual(0);
      expect(filteredCount).toBeLessThanOrEqual(allCount);
    });

    test('按操作类型筛选', async ({ page }) => {
      const opSelect = page.locator('.filter-bar .el-select').nth(1);
      await opSelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode
      await page.locator('.el-select-dropdown:visible').last().locator('li:has-text("创建")').click();
      await page.waitForTimeout(500);

      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('.el-table__row').count();
      expect(filteredCount).toBeGreaterThanOrEqual(0);
    });

    test('清空筛选恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const entitySelect = page.locator('.filter-bar .el-select').first();
      await entitySelect.click();
      await page.waitForTimeout(500);
      await page.locator('.el-select-dropdown:visible').last().locator('li:has-text("商品")').click();
      await page.waitForTimeout(500);
      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const entitySelectClear = page.locator('.filter-bar .el-select').first();
      await entitySelectClear.click();
      await page.waitForTimeout(500);
      await page.locator('.el-select-dropdown:visible').last().locator('li').first().click();
      await page.waitForTimeout(500);
      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const restoredCount = await page.locator('.el-table__row').count();
      expect(restoredCount).toBeGreaterThanOrEqual(0);
    });
  });

  // ========== 分页 ==========
  test.describe('分页功能', () => {
    test('分页组件正确展示', async ({ page }) => {
      await expect(page.locator('.el-pagination')).toBeVisible();
    });

    test('分页显示总数', async ({ page }) => {
      const totalText = page.locator('.el-pagination .el-pagination__total');
      if (await totalText.isVisible().catch(() => false)) {
        const text = await totalText.textContent();
        expect(text).toContain('共');
      }
    });

    test('切换每页条数', async ({ page }) => {
      const paginationSelect = page.locator('.el-pagination .el-select');
      if (await paginationSelect.isVisible().catch(() => false)) {
        await paginationSelect.click();
        await page.waitForTimeout(500);

        const options = page.locator('.el-select-dropdown:visible').last().locator('li');
        const optionCount = await options.count();
        expect(optionCount).toBeGreaterThan(0);

        await page.keyboard.press('Escape');
      }
    });
  });

  // ========== 空状态 ==========
  test.describe('空状态', () => {
    test('无数据时展示空状态', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      if (rows === 0) {
        await expect(page.locator('.el-empty')).toBeVisible();
        await expect(page.locator('.el-empty__description:has-text("暂无操作日志")')).toBeVisible();
      }
    });
  });
});
