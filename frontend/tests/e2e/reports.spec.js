import { test, expect } from '@playwright/test';

test.describe('财务总览', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/financial-overview');
    await page.waitForTimeout(1000);
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('财务总览页面正常加载', async ({ page }) => {
      await expect(page.locator('.fo')).toBeVisible();
      await expect(page.locator('.fo-bt:has-text("核心指标")')).toBeVisible();
    });

    test('四个核心指标卡片正确展示', async ({ page }) => {
      await expect(page.locator('.kpi-card:has-text("别人欠我")')).toBeVisible();
      await expect(page.locator('.kpi-card:has-text("我欠别人")')).toBeVisible();
      await expect(page.locator('.kpi-card:has-text("本月净利润")')).toBeVisible();
      await expect(page.locator('.kpi-card:has-text("库存资金")')).toBeVisible();
    });
  });

  // ========== 核心指标 ==========
  test.describe('核心指标', () => {
    test('指标金额为有效金额格式', async ({ page }) => {
      const cards = page.locator('.kpi-card');
      const count = await cards.count();
      expect(count).toBeGreaterThanOrEqual(4);
      for (let i = 0; i < Math.min(count, 4); i++) {
        const value = cards.nth(i).locator('.kpi-value').first();
        if (await value.isVisible().catch(() => false)) {
          const text = await value.textContent();
          expect(text).toMatch(/^-?[\d,.]+\.\d{2}$/);
        }
      }
    });
  });

  // ========== 财务健康度 ==========
  test.describe('财务健康度', () => {
    test('健康度指标区域可见', async ({ page }) => {
      await expect(page.locator('.fo-bt:has-text("财务健康度")')).toBeVisible();
      await expect(page.locator('.fo-metric').first()).toBeVisible();
    });

    test('包含关键健康度指标', async ({ page }) => {
      await expect(page.locator('.fo-ml:has-text("资产负债率")')).toBeVisible();
      await expect(page.locator('.fo-ml:has-text("流动比率")')).toBeVisible();
      await expect(page.locator('.fo-ml:has-text("权益比率")')).toBeVisible();
    });
  });

  // ========== 资产负债摘要 ==========
  test.describe('资产负债摘要', () => {
    test('资产负债摘要区域可见', async ({ page }) => {
      await expect(page.locator('.fo-bt:has-text("资产负债摘要")')).toBeVisible();
    });

    test('资产、负债、权益三列展示', async ({ page }) => {
      await expect(page.locator('.fo-th:has-text("资产")')).toBeVisible();
      await expect(page.locator('.fo-th:has-text("负债")')).toBeVisible();
      await expect(page.locator('.fo-th:has-text("权益")')).toBeVisible();
    });

    test('摘要金额格式正确', async ({ page }) => {
      const values = page.locator('.fo-tv');
      const count = await values.count();
      expect(count).toBeGreaterThan(0);
      for (let i = 0; i < count; i++) {
        const text = await values.nth(i).textContent();
        expect(text).toMatch(/^-?[\d,.]+\.\d{2}$/);
      }
    });
  });

  // ========== 税务与利润 ==========
  test.describe('税务与利润', () => {
    test('税务与利润区域可见', async ({ page }) => {
      await expect(page.locator('.fo-bt:has-text("税务与利润")')).toBeVisible();
    });

    test('包含增值税、企业所得税、利润速览、现金流量卡片', async ({ page }) => {
      await expect(page.locator('.fo-qh:has-text("增值税")')).toBeVisible();
      await expect(page.locator('.fo-qh:has-text("企业所得税")')).toBeVisible();
      await expect(page.locator('.fo-qh:has-text("利润速览")')).toBeVisible();
      await expect(page.locator('.fo-qh:has-text("现金流量")')).toBeVisible();
    });
  });

  // ========== 近期费用 ==========
  test.describe('近期费用', () => {
    test('近期费用区域可见', async ({ page }) => {
      await expect(page.locator('.fo-bt:has-text("近期费用")')).toBeVisible();
    });

    test('费用表格或空状态正确展示', async ({ page }) => {
      const table = page.locator('.fo-tbl');
      const empty = page.locator('.fo-tbl-wrap').locator('div:has-text("暂无")');
      const hasTable = await table.isVisible().catch(() => false);
      const hasEmpty = await empty.isVisible().catch(() => false);
      expect(hasTable || hasEmpty).toBeTruthy();
    });
  });
});
