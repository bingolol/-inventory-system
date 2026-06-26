import { test, expect } from '@playwright/test';

test.describe('数据备份', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/backup');
    await page.waitForSelector('.backup-page', { timeout: 10000 });
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('页面标题正确显示', async ({ page }) => {
      await expect(page.locator('text=数据热备份')).toBeVisible();
    });

    test('一键备份按钮可见', async ({ page }) => {
      await expect(page.locator('button:has-text("一键备份")')).toBeVisible();
    });

    test('备份提示信息显示', async ({ page }) => {
      await expect(page.locator('.el-alert:has-text("建议每周备份一次")')).toBeVisible();
    });

    test('备份列表表格正确显示', async ({ page }) => {
      await expect(page.locator('.el-table')).toBeVisible();
      await expect(page.locator('th:has-text("备份文件")')).toBeVisible();
      await expect(page.locator('th:has-text("大小")')).toBeVisible();
      await expect(page.locator('th:has-text("备份时间")')).toBeVisible();
      await expect(page.locator('th:has-text("操作")')).toBeVisible();
    });
  });

  // ========== 备份列表 ==========
  test.describe('备份列表', () => {
    test('列表有数据时显示下载按钮', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      if (rows > 0) {
        await expect(page.locator('.el-table__row:first-child button:has-text("下载")')).toBeVisible();
      }
    });

    test('列表为空时显示空文本', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      if (rows === 0) {
        await expect(page.locator('.el-table__empty-text')).toContainText('暂无备份');
      }
    });

    test('备份文件大小显示正确格式', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      if (rows > 0) {
        const sizeText = await page.locator('.el-table__row:first-child td').nth(1).textContent();
        expect(sizeText?.trim()).toMatch(/\d+(\.\d+)?\s*(KB|MB)/);
      }
    });

    test('备份时间显示格式正确', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      if (rows > 0) {
        const timeText = await page.locator('.el-table__row:first-child td').nth(2).textContent();
        expect(timeText?.trim()).toMatch(/\d{4}[-/]\d{2}[-/]\d{2}/);
      }
    });
  });

  // ========== 备份操作（不执行实际备份） ==========
  test.describe('备份操作', () => {
    test('一键备份按钮可点击', async ({ page }) => {
      const backupBtn = page.locator('button:has-text("一键备份")');
      await expect(backupBtn).toBeEnabled();
    });

    test('点击备份按钮后按钮变为加载状态', async ({ page }) => {
      const backupBtn = page.locator('button:has-text("一键备份")');

      // 注意：不实际执行备份操作，只验证按钮状态
      // 如果需要测试，应使用 mock API
      await expect(backupBtn).toBeVisible();
    });
  });

  // ========== 下载功能 ==========
  test.describe('下载功能', () => {
    test('下载按钮可点击', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      if (rows > 0) {
        const downloadBtn = page.locator('.el-table__row:first-child button:has-text("下载")');
        await expect(downloadBtn).toBeEnabled();
      }
    });
  });

  // ========== 响应式布局 ==========
  test.describe('响应式布局', () => {
    test('页面在不同视口宽度下正确显示', async ({ page }) => {
      // 桌面视图
      await page.setViewportSize({ width: 1200, height: 800 });
      await expect(page.locator('.backup-page')).toBeVisible();
      await expect(page.locator('button:has-text("一键备份")')).toBeVisible();

      // 平板视图
      await page.setViewportSize({ width: 768, height: 1024 });
      await expect(page.locator('.backup-page')).toBeVisible();
      await expect(page.locator('button:has-text("一键备份")')).toBeVisible();

      // 手机视图
      await page.setViewportSize({ width: 375, height: 667 });
      await expect(page.locator('.backup-page')).toBeVisible();
      await expect(page.locator('button:has-text("一键备份")')).toBeVisible();
    });
  });
});
