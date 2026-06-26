import { test, expect } from '@playwright/test';

test.describe('仪表盘', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(2000);
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('仪表盘页面正常加载', async ({ page }) => {
      await expect(page.locator('.dashboard')).toBeVisible();
    });

    test('四个统计卡片正确展示', async ({ page }) => {
      const statCards = page.locator('.stat-card');
      await expect(statCards).toHaveCount(4);

      await expect(page.locator('.stat-label:has-text("商品种类")')).toBeVisible();
      await expect(page.locator('.stat-label:has-text("库存总量")')).toBeVisible();
      await expect(page.locator('.stat-label:has-text("今日采购")')).toBeVisible();
      await expect(page.locator('.stat-label:has-text("今日销售")')).toBeVisible();
    });
  });

  // ========== 统计数据展示 ==========
  test.describe('统计数据展示', () => {
    test('商品种类数值为数字', async ({ page }) => {
      const value = page.locator('.stat-value').first();
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(Number(text?.trim())).not.toBeNaN();
    });

    test('库存总量数值为数字', async ({ page }) => {
      const value = page.locator('.stat-value').nth(1);
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(Number(text?.trim())).not.toBeNaN();
    });

    test('今日采购金额包含人民币符号', async ({ page }) => {
      const value = page.locator('.stat-value').nth(2);
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(text).toContain('¥');
    });

    test('今日销售金额包含人民币符号', async ({ page }) => {
      const value = page.locator('.stat-value').nth(3);
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(text).toContain('¥');
    });
  });

  // ========== 趋势分析图表 ==========
  test.describe('趋势分析', () => {
    test('趋势分析卡片正确展示', async ({ page }) => {
      await expect(page.locator('text=趋势分析')).toBeVisible();
      await expect(page.locator('v-chart, canvas')).toBeVisible();
    });

    test('默认选中近7天', async ({ page }) => {
      const radio7d = page.locator('.el-radio-button:has-text("近7天")');
      await expect(radio7d).toHaveClass(/is-active/);
    });

    test('切换到近30天', async ({ page }) => {
      await page.locator('.el-radio-button:has-text("近30天")').click();
      await page.waitForTimeout(1000);

      const radio30d = page.locator('.el-radio-button:has-text("近30天")');
      await expect(radio30d).toHaveClass(/is-active/);
    });

    test('切换到近90天', async ({ page }) => {
      await page.locator('.el-radio-button:has-text("近90天")').click();
      await page.waitForTimeout(1000);

      const radio90d = page.locator('.el-radio-button:has-text("近90天")');
      await expect(radio90d).toHaveClass(/is-active/);
    });
  });

  // ========== 库存预警 ==========
  test.describe('库存预警', () => {
    test('库存预警卡片正确展示', async ({ page }) => {
      await expect(page.locator('text=库存预警')).toBeVisible();
    });

    test('有预警数据时展示表格', async ({ page }) => {
      const table = page.locator('.el-card:has-text("库存预警") .el-table');
      const empty = page.locator('.el-card:has-text("库存预警") .el-empty');

      const tableVisible = await table.isVisible().catch(() => false);
      const emptyVisible = await empty.isVisible().catch(() => false);

      expect(tableVisible || emptyVisible).toBeTruthy();
    });

    test('预警表格包含必要列', async ({ page }) => {
      const table = page.locator('.el-card:has-text("库存预警") .el-table');
      if (await table.isVisible().catch(() => false)) {
        await expect(page.locator('th:has-text("商品")')).toBeVisible();
        await expect(page.locator('th:has-text("编码")')).toBeVisible();
        await expect(page.locator('th:has-text("库存")')).toBeVisible();
        await expect(page.locator('th:has-text("预警线")')).toBeVisible();
      }
    });
  });

  // ========== 库存价值 ==========
  test.describe('库存价值', () => {
    test('库存价值卡片正确展示', async ({ page }) => {
      await expect(page.locator('text=库存价值')).toBeVisible();
      await expect(page.locator('text=库存总价值（按进价计算）')).toBeVisible();
    });

    test('库存价值金额包含人民币符号', async ({ page }) => {
      const value = page.locator('.el-card:has-text("库存价值") .stat-value, .el-card:has-text("库存价值") [style*="font-size: 36px"]').first();
      if (await value.isVisible().catch(() => false)) {
        const text = await value.textContent();
        expect(text).toContain('¥');
      }
    });
  });
});
