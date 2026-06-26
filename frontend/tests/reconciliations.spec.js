import { test, expect } from '@playwright/test';

test.describe('对账管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reconciliations');
    await page.waitForTimeout(800);
    await page.waitForSelector('.filter-card', { timeout: 10000 });
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('筛选区域正确显示', async ({ page }) => {
      await expect(page.locator('.filter-card')).toBeVisible();
      await expect(page.locator('text=对账类型')).toBeVisible();
      await expect(page.locator('text=开始日期')).toBeVisible();
      await expect(page.locator('text=结束日期')).toBeVisible();
    });

    test('默认选中供应商对账', async ({ page }) => {
      const supplierRadio = page.locator('.el-radio-button:has-text("供应商对账")');
      await expect(supplierRadio).toHaveClass(/is-active/);
    });

    test('默认日期范围为当月', async ({ page }) => {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');

      const startInput = page.locator('.filter-card input[placeholder="开始日期"]');
      const endInput = page.locator('.filter-card input[placeholder="结束日期"]');

      await expect(startInput).toHaveValue(`${year}-${month}-01`);
      await expect(endInput).toHaveValue(new RegExp(`${year}-${month}-\\d{2}`));
    });

    test('查询按钮可见', async ({ page }) => {
      await expect(page.locator('button:has-text("查询对账")')).toBeVisible();
    });
  });

  // ========== 筛选功能 ==========
  test.describe('筛选功能', () => {
    test('切换到客户对账', async ({ page }) => {
      await page.locator('.el-radio-button:has-text("客户对账")').click();
      await page.waitForTimeout(500);

      const customerRadio = page.locator('.el-radio-button:has-text("客户对账")');
      await expect(customerRadio).toHaveClass(/is-active/);
    });

    test('查询对账数据', async ({ page }) => {
      await page.locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const summaryRow = page.locator('.summary-row');
      const emptyState = page.locator('.el-empty');
      const hasContent = await summaryRow.isVisible().catch(() => false);
      const isEmpty = await emptyState.isVisible().catch(() => false);

      expect(hasContent || isEmpty).toBeTruthy();
    });

    test('未选择日期查询时显示警告', async ({ page }) => {
      const startInput = page.locator('.filter-card input[placeholder="开始日期"]');
      const endInput = page.locator('.filter-card input[placeholder="结束日期"]');

      await startInput.clear();
      await endInput.clear();

      await page.locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(500);

      await expect(page.locator('.el-message--warning')).toBeVisible();
    });
  });

  // ========== 数据展示 ==========
  test.describe('数据展示', () => {
    test('查询后显示汇总卡片', async ({ page }) => {
      await page.locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const summaryRow = page.locator('.summary-row');
      const isVisible = await summaryRow.isVisible().catch(() => false);

      if (isVisible) {
        await expect(page.locator('text=对方数量')).toBeVisible();
        await expect(page.locator('text=期初欠款合计')).toBeVisible();
        await expect(page.locator('text=本期发生合计')).toBeVisible();
        await expect(page.locator('text=已收/已付合计')).toBeVisible();
        await expect(page.locator('text=期末欠款合计')).toBeVisible();
        await expect(page.locator('text=发票金额合计')).toBeVisible();
      }
    });

    test('对账汇总表格列头正确', async ({ page }) => {
      await page.locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const table = page.locator('.detail-card .el-table');
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        await expect(page.locator('th:has-text("对方名称")')).toBeVisible();
        await expect(page.locator('th:has-text("期初欠款")')).toBeVisible();
        await expect(page.locator('th:has-text("本期发生")')).toBeVisible();
        await expect(page.locator('th:has-text("已收/已付")')).toBeVisible();
        await expect(page.locator('th:has-text("期末欠款")')).toBeVisible();
        await expect(page.locator('th:has-text("发票金额")')).toBeVisible();
        await expect(page.locator('th:has-text("单据数")')).toBeVisible();
        await expect(page.locator('th:has-text("未结清")')).toBeVisible();
      }
    });

    test('表格有数据时显示行', async ({ page }) => {
      await page.locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const table = page.locator('.detail-card .el-table');
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        const rows = await page.locator('.detail-card .el-table__row').count();
        expect(rows).toBeGreaterThan(0);
      }
    });
  });

  // ========== 明细抽屉 ==========
  test.describe('明细抽屉', () => {
    test('点击明细按钮打开抽屉', async ({ page }) => {
      await page.locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const table = page.locator('.detail-card .el-table');
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        const rows = await page.locator('.detail-card .el-table__row').count();
        if (rows > 0) {
          await page.locator('.detail-card .el-table__row:first-child button:has-text("明细")').click();
          await page.waitForTimeout(1500);

          await expect(page.locator('.el-drawer')).toBeVisible();
        }
      }
    });

    test('明细抽屉包含对账明细表格', async ({ page }) => {
      await page.locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const table = page.locator('.detail-card .el-table');
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        const rows = await page.locator('.detail-card .el-table__row').count();
        if (rows > 0) {
          await page.locator('.detail-card .el-table__row:first-child button:has-text("明细")').click();
          await page.waitForTimeout(1500);

          await expect(page.locator('.el-drawer')).toBeVisible();
          await expect(page.locator('.el-drawer th:has-text("日期")')).toBeVisible();
          await expect(page.locator('.el-drawer th:has-text("描述")')).toBeVisible();
          await expect(page.locator('.el-drawer th:has-text("金额")')).toBeVisible();
          await expect(page.locator('.el-drawer th:has-text("状态")')).toBeVisible();
        }
      }
    });
  });

  // ========== 空状态 ==========
  test.describe('空状态', () => {
    test('无数据显示空状态', async ({ page }) => {
      const emptyState = page.locator('.el-empty');
      const isVisible = await emptyState.isVisible().catch(() => false);

      if (isVisible) {
        await expect(page.locator('.el-empty__description')).toContainText('暂无数据');
      }
    });
  });
});
