import { test, expect } from '@playwright/test';

test.describe('会计规则指引', () => {
  const consoleErrors = [];
  const consoleWarnings = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors.length = 0;
    consoleWarnings.length = 0;

    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
      if (msg.type() === 'warning') consoleWarnings.push(msg.text());
    });

    page.on('pageerror', err => {
      consoleErrors.push(err.message);
    });

    await page.goto('/accounting-guide');
    await page.waitForTimeout(1500);
    await page.waitForSelector('.ag-shell, .el-empty', { timeout: 10000 });
  });

  test.afterEach(async () => {
    if (consoleErrors.length) {
      console.error('Console errors:', consoleErrors);
    }
    if (consoleWarnings.length) {
      console.warn('Console warnings:', consoleWarnings);
    }
    expect(consoleErrors).toEqual([]);
  });

  test('页面标题与导航正确显示', async ({ page }) => {
    await expect(page.locator('.ag-nav-hd')).toContainText('会计规则指引');
    await expect(page.locator('.ag-nav-item').first()).toBeVisible();
  });

  test('顶部信息栏展示账本与期间', async ({ page }) => {
    await expect(page.locator('.ag-info-bar')).toBeVisible();
  });

  test('九个模块全部渲染', async ({ page }) => {
    for (let i = 1; i <= 9; i++) {
      await expect(page.locator(`#module-${i}`)).toBeVisible();
    }
  });

  test('年份/季度筛选可切换并重新加载', async ({ page }) => {
    const yearSelect = page.locator('.ag-filters .el-select').first();
    await yearSelect.click();
    await page.waitForTimeout(300);
    const options = page.locator('.el-select-dropdown__list:visible li');
    await options.first().click();
    await page.waitForTimeout(1500);

    await expect(page.locator('.ag-info-bar')).toBeVisible();
  });

  test('左侧导航点击可滚动到模块', async ({ page }) => {
    const nav = page.locator('.ag-nav-item').nth(3);
    await nav.click();
    await page.waitForTimeout(800);
    await expect(nav).toHaveClass(/active/);
  });
});
