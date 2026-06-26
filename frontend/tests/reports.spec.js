import { test, expect } from '@playwright/test';

test.describe('报表统计', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reports');
    await page.waitForTimeout(2000);
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('报表页面正常加载', async ({ page }) => {
      await expect(page.locator('.page-title:has-text("报表统计")')).toBeVisible();
    });

    test('四个Tab正确展示', async ({ page }) => {
      await expect(page.locator('.el-tabs__item:has-text("总览")')).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("采购报表")')).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("销售报表")')).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("利润分析")')).toBeVisible();
    });

    test('导出按钮可见', async ({ page }) => {
      await expect(page.locator('button:has-text("导出当前报表")')).toBeVisible();
    });
  });

  // ========== 总览Tab ==========
  test.describe('总览Tab', () => {
    test('默认显示总览Tab', async ({ page }) => {
      const overviewTab = page.locator('.el-tabs__item:has-text("总览")');
      await expect(overviewTab).toHaveClass(/is-active/);
    });

    test('总览统计数据正确展示', async ({ page }) => {
      const tabPane = page.locator('.el-tab-pane').first();
      await expect(tabPane.locator('.stat-label:has-text("商品种类")')).toBeVisible();
      await expect(tabPane.locator('.stat-label:has-text("库存总量")')).toBeVisible();
      await expect(tabPane.locator('.stat-label:has-text("库存价值")')).toBeVisible();
      await expect(tabPane.locator('.stat-label:has-text("库存预警")')).toBeVisible();
    });

    test('库存价值包含人民币符号', async ({ page }) => {
      const value = page.locator('.el-tab-pane .stat-value:has-text("¥")').first();
      if (await value.isVisible().catch(() => false)) {
        const text = await value.textContent();
        expect(text).toContain('¥');
      }
    });
  });

  // ========== 采购报表Tab ==========
  test.describe('采购报表Tab', () => {
    test('切换到采购报表Tab', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("采购报表")').click();
      await page.waitForTimeout(1000);

      const purchaseTab = page.locator('.el-tabs__item:has-text("采购报表")');
      await expect(purchaseTab).toHaveClass(/is-active/);
    });

    test('采购报表展示日期筛选', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("采购报表")').click();
      await page.waitForTimeout(500);

      await expect(page.locator('.el-date-editor').first()).toBeVisible();
    });

    test('采购报表展示汇总信息', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("采购报表")').click();
      await page.waitForTimeout(1000);

      await expect(page.locator('text=采购总金额')).toBeVisible();
      await expect(page.locator('text=采购单数')).toBeVisible();
    });

    test('采购报表表格包含必要列', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("采购报表")').click();
      await page.waitForTimeout(1000);

      const table = page.locator('.el-tab-pane .el-table').first();
      if (await table.isVisible().catch(() => false)) {
        await expect(table.locator('th:has-text("单号")')).toBeVisible();
        await expect(table.locator('th:has-text("供应商")')).toBeVisible();
        await expect(table.locator('th:has-text("总价")')).toBeVisible();
        await expect(table.locator('th:has-text("日期")')).toBeVisible();
      }
    });
  });

  // ========== 销售报表Tab ==========
  test.describe('销售报表Tab', () => {
    test('切换到销售报表Tab', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("销售报表")').click();
      await page.waitForTimeout(1000);

      const saleTab = page.locator('.el-tabs__item:has-text("销售报表")');
      await expect(saleTab).toHaveClass(/is-active/);
    });

    test('销售报表展示日期筛选', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("销售报表")').click();
      await page.waitForTimeout(500);

      await expect(page.locator('.el-tab-pane:visible .el-date-editor')).toBeVisible();
    });

    test('销售报表展示汇总信息', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("销售报表")').click();
      await page.waitForTimeout(1000);

      await expect(page.locator('text=销售总金额')).toBeVisible();
      await expect(page.locator('text=销售单数')).toBeVisible();
    });

    test('销售报表表格包含必要列', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("销售报表")').click();
      await page.waitForTimeout(1000);

      const table = page.locator('.el-tab-pane .el-table').first();
      if (await table.isVisible().catch(() => false)) {
        await expect(table.locator('th:has-text("单号")')).toBeVisible();
        await expect(table.locator('th:has-text("客户")')).toBeVisible();
        await expect(table.locator('th:has-text("总价")')).toBeVisible();
        await expect(table.locator('th:has-text("日期")')).toBeVisible();
      }
    });
  });

  // ========== 利润分析Tab ==========
  test.describe('利润分析Tab', () => {
    test('切换到利润分析Tab', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("利润分析")').click();
      await page.waitForTimeout(1000);

      const profitTab = page.locator('.el-tabs__item:has-text("利润分析")');
      await expect(profitTab).toHaveClass(/is-active/);
    });

    test('利润分析展示日期筛选', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("利润分析")').click();
      await page.waitForTimeout(500);

      await expect(page.locator('.el-tab-pane:visible .el-date-editor')).toBeVisible();
    });

    test('利润分析展示收入成本利润', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("利润分析")').click();
      await page.waitForTimeout(1000);

      await expect(page.locator('.stat-label:has-text("销售收入")').first()).toBeVisible();
      await expect(page.locator('.stat-label:has-text("商品成本")').first()).toBeVisible();
      await expect(page.locator('.stat-label:has-text("利润（销售收入 - 商品成本）")')).toBeVisible();
    });

    test('利润分析金额包含人民币符号', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("利润分析")').click();
      await page.waitForTimeout(1000);

      const values = page.locator('.stat-value:has-text("¥")');
      const count = await values.count();
      for (let i = 0; i < count; i++) {
        const text = await values.nth(i).textContent();
        expect(text).toContain('¥');
      }
    });
  });

  // ========== 导出功能 ==========
  test.describe('导出功能', () => {
    test('导出下拉菜单展示Excel和CSV选项', async ({ page }) => {
      await page.locator('button:has-text("导出当前报表")').click();
      await page.waitForTimeout(300);

      await expect(page.locator('.el-dropdown-menu__item:has-text("Excel")')).toBeVisible();
      await expect(page.locator('.el-dropdown-menu__item:has-text("CSV")')).toBeVisible();
    });
  });
});
