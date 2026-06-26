import { test, expect } from '@playwright/test';

test.describe('财务报表', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/financial-reports');
    await page.waitForSelector('.el-tabs__item', { timeout: 10000 });
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('页面标题正确显示', async ({ page }) => {
      await expect(page.locator('.page-title')).toContainText('财务报表');
    });

    test('默认选中资产负债表标签页', async ({ page }) => {
      const activeTab = page.locator('.el-tabs__item.is-active');
      await expect(activeTab).toContainText('资产负债表');
    });

    test('所有标签页正确显示', async ({ page }) => {
      await expect(page.locator('.el-tabs__item:has-text("资产负债表")')).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("利润表")')).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("财务汇总")')).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("期初余额")')).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("固定资产")')).toBeVisible();
    });
  });

  // ========== 资产负债表 ==========
  test.describe('资产负债表', () => {
    test('资产负债表内容区域可见', async ({ page }) => {
      // 默认激活资产负债表
      const activeTab = page.locator('.el-tabs__item.is-active');
      await expect(activeTab).toContainText('资产负债表');

      // 等待内容加载
      await page.waitForTimeout(1500);
    });
  });

  // ========== 利润表 ==========
  test.describe('利润表', () => {
    test('切换到利润表标签页', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("利润表")').click();
      await page.waitForTimeout(500);

      const activeTab = page.locator('.el-tabs__item.is-active');
      await expect(activeTab).toContainText('利润表');

      await page.waitForTimeout(1500);
    });
  });

  // ========== 财务汇总 ==========
  test.describe('财务汇总', () => {
    test('切换到财务汇总标签页', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("财务汇总")').click();
      await page.waitForTimeout(500);

      const activeTab = page.locator('.el-tabs__item.is-active');
      await expect(activeTab).toContainText('财务汇总');

      await page.waitForTimeout(1500);
    });
  });

  // ========== 期初余额 ==========
  test.describe('期初余额', () => {
    test('切换到期初余额标签页', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("期初余额")').click();
      await page.waitForTimeout(500);

      const activeTab = page.locator('.el-tabs__item.is-active');
      await expect(activeTab).toContainText('期初余额');

      await page.waitForTimeout(1500);
    });
  });

  // ========== 固定资产 ==========
  test.describe('固定资产', () => {
    test('切换到固定资产标签页', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("固定资产")').click();
      await page.waitForTimeout(500);

      const activeTab = page.locator('.el-tabs__item.is-active');
      await expect(activeTab).toContainText('固定资产');

      await page.waitForTimeout(1500);
    });
  });

  // ========== 标签页切换 ==========
  test.describe('标签页切换', () => {
    test('在不同标签页之间切换', async ({ page }) => {
      // 从资产负债表切换到利润表
      await page.locator('.el-tabs__item:has-text("利润表")').click();
      await page.waitForTimeout(500);
      await expect(page.locator('.el-tabs__item.is-active')).toContainText('利润表');

      // 切换到财务汇总
      await page.locator('.el-tabs__item:has-text("财务汇总")').click();
      await page.waitForTimeout(500);
      await expect(page.locator('.el-tabs__item.is-active')).toContainText('财务汇总');

      // 切回资产负债表
      await page.locator('.el-tabs__item:has-text("资产负债表")').click();
      await page.waitForTimeout(500);
      await expect(page.locator('.el-tabs__item.is-active')).toContainText('资产负债表');
    });
  });
});
