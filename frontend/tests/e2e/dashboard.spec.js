import { test, expect } from '@playwright/test';

test.describe('仪表盘', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForTimeout(1000);
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('仪表盘页面正常加载', async ({ page }) => {
      await expect(page.locator('.d')).toBeVisible();
    });

    test('四个统计卡片正确展示', async ({ page }) => {
      const statCards = page.locator('.d-c');
      await expect(statCards).toHaveCount(4);

      await expect(page.locator('.d-cl:has-text("本月净利润")')).toBeVisible();
      await expect(page.locator('.d-cl:has-text("别人欠我")')).toBeVisible();
      await expect(page.locator('.d-cl:has-text("我欠别人")')).toBeVisible();
      await expect(page.locator('.d-cl:has-text("库存资金")')).toBeVisible();
    });
  });

  // ========== 统计数据展示 ==========
  test.describe('统计数据展示', () => {
    test('商品种类数值为数字', async ({ page }) => {
      const value = page.locator('.d-civ:has-text("种")').first();
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(Number(text?.replace(/[^0-9.-]/g, '').trim())).not.toBeNaN();
    });

    test('库存总量数值为数字', async ({ page }) => {
      const value = page.locator('.d-civ:has-text("件")').first();
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(Number(text?.replace(/[^0-9.-]/g, '').trim())).not.toBeNaN();
    });

    test('库存资金金额为有效金额格式', async ({ page }) => {
      const card = page.locator('.d-c').filter({ hasText: '库存资金' });
      const value = card.locator('.d-cv').first();
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(text).toMatch(/^-?[\d,]+\.\d{2}$/);
    });

    test('本月净利润金额为有效金额格式', async ({ page }) => {
      const card = page.locator('.d-c').filter({ hasText: '本月净利润' });
      const value = card.locator('.d-cv').first();
      await expect(value).toBeVisible();
      const text = await value.textContent();
      expect(text).toMatch(/^-?[\d,]+\.\d{2}$/);
    });
  });

  // ========== 趋势分析图表 ==========
  test.describe('趋势分析', () => {
    test('趋势分析卡片正确展示', async ({ page }) => {
      await expect(page.locator('.d-bt:has-text("收入趋势")')).toBeVisible();
      await expect(page.locator('v-chart, canvas')).toBeVisible();
    });
  });

  // ========== 库存预警 ==========
  test.describe('库存预警', () => {
    test('库存预警卡片正确展示', async ({ page }) => {
      await expect(page.locator('.d-bt:has-text("库存预警")')).toBeVisible();
    });

    test('有预警数据时展示表格或空状态', async ({ page }) => {
      const box = page.locator('.d-box').filter({ hasText: '库存预警' });
      const table = box.locator('.d-tbl');
      const empty = box.locator('div:has-text("暂无预警，库存状况良好")');

      const tableVisible = await table.isVisible().catch(() => false);
      const emptyVisible = await empty.isVisible().catch(() => false);

      expect(tableVisible || emptyVisible).toBeTruthy();
    });

    test('预警表格包含必要列', async ({ page }) => {
      const box = page.locator('.d-box').filter({ hasText: '库存预警' });
      const table = box.locator('.d-tbl');
      if (await table.isVisible().catch(() => false)) {
        await expect(box.locator('th:has-text("商品")')).toBeVisible();
        await expect(box.locator('th:has-text("编码")')).toBeVisible();
        await expect(box.locator('th:has-text("库存")')).toBeVisible();
      }
    });
  });

  // ========== 库存价值 ==========
  test.describe('库存价值', () => {
    test('库存资金卡片正确展示', async ({ page }) => {
      await expect(page.locator('.d-cl:has-text("库存资金")')).toBeVisible();
    });

    test('库存资金金额为有效金额格式', async ({ page }) => {
      const card = page.locator('.d-c').filter({ hasText: '库存资金' });
      const value = card.locator('.d-cv').first();
      if (await value.isVisible().catch(() => false)) {
        const text = await value.textContent();
        expect(text).toMatch(/^-?[\d,]+\.\d{2}$/);
      }
    });
  });
});
