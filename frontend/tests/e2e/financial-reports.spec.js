import { test, expect } from '@playwright/test';

function activeMainTab(page) {
  return page.locator('.el-tabs__header').first().locator('.el-tabs__item.is-active');
}

function mainTabByText(page, text) {
  return page.locator('.el-tabs__header').first().locator('.el-tabs__item').filter({ hasText: text });
}

test.describe('财务报表', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/financial-reports');
    await page.waitForSelector('.el-tabs__item', { timeout: 10000 });
    await page.waitForTimeout(500);
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('页面标题正确显示', async ({ page }) => {
      await expect(page.locator('.page-title:has-text("财务报表")')).toBeVisible();
    });

    test('默认选中利润表标签页', async ({ page }) => {
      await expect(activeMainTab(page)).toContainText('利润表');
    });

    test('所有标签页正确显示', async ({ page }) => {
      await expect(mainTabByText(page, '资产负债表')).toBeVisible();
      await expect(mainTabByText(page, '利润表')).toBeVisible();
      await expect(mainTabByText(page, '期初余额')).toBeVisible();
      await expect(mainTabByText(page, '小企业会计准则报表')).toBeVisible();
    });
  });

  // ========== 资产负债表 ==========
  test.describe('资产负债表', () => {
    test('切换到资产负债表标签页', async ({ page }) => {
      await mainTabByText(page, '资产负债表').click();
      await page.waitForTimeout(500);
      await expect(activeMainTab(page)).toContainText('资产负债表');
      await page.waitForTimeout(1000);
    });
  });

  // ========== 利润表 ==========
  test.describe('利润表', () => {
    test('利润表标签页默认激活', async ({ page }) => {
      await expect(activeMainTab(page)).toContainText('利润表');
      await page.waitForTimeout(1000);
    });
  });

  // ========== 期初余额 ==========
  test.describe('期初余额', () => {
    test('切换到期初余额标签页', async ({ page }) => {
      await mainTabByText(page, '期初余额').click();
      await page.waitForTimeout(500);
      await expect(activeMainTab(page)).toContainText('期初余额');
      await page.waitForTimeout(1000);
    });
  });

  // ========== 小企业会计准则报表 ==========
  test.describe('小企业会计准则报表', () => {
    test('切换到小企业会计准则报表标签页', async ({ page }) => {
      await mainTabByText(page, '小企业会计准则报表').click();
      await page.waitForTimeout(500);
      await expect(activeMainTab(page)).toContainText('小企业会计准则报表');
      await page.waitForTimeout(1000);
    });
  });

  // ========== 标签页切换 ==========
  test.describe('标签页切换', () => {
    test('在不同标签页之间切换', async ({ page }) => {
      await mainTabByText(page, '资产负债表').click();
      await page.waitForTimeout(500);
      await expect(activeMainTab(page)).toContainText('资产负债表');

      await mainTabByText(page, '期初余额').click();
      await page.waitForTimeout(500);
      await expect(activeMainTab(page)).toContainText('期初余额');

      await mainTabByText(page, '利润表').click();
      await page.waitForTimeout(500);
      await expect(activeMainTab(page)).toContainText('利润表');
    });
  });
});
