import { test, expect } from '@playwright/test';

test.describe('往来管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/finance/receivable/aging');
    await page.waitForTimeout(800);
    await expect(page.locator('.el-tabs__item.is-active')).toContainText('对账汇总');
  });

  const pane = (page) => page.locator('.el-tab-pane:visible');

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('筛选区域正确显示', async ({ page }) => {
      await expect(pane(page).locator('.filter-bar')).toBeVisible();
      await expect(pane(page).locator('input[placeholder="开始日期"]')).toBeVisible();
      await expect(pane(page).locator('input[placeholder="结束日期"]')).toBeVisible();
      await expect(pane(page).locator('button:has-text("查询对账")')).toBeVisible();
    });

    test('默认选中客户类型', async ({ page }) => {
      const customerRadio = page.locator('.el-radio:has-text("客户")').first();
      await expect(customerRadio).toHaveClass(/is-checked/);
    });

    test('默认日期范围为当月', async ({ page }) => {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');

      const startInput = pane(page).locator('input[placeholder="开始日期"]');
      const endInput = pane(page).locator('input[placeholder="结束日期"]');

      await expect(startInput).toHaveValue(`${year}-${month}-01`);
      await expect(endInput).toHaveValue(new RegExp(`${year}-${month}-\\d{2}`));
    });
  });

  // ========== 筛选功能 ==========
  test.describe('筛选功能', () => {
    test('切换到供应商类型', async ({ page }) => {
      await page.locator('.el-radio:has-text("供应商")').first().click();
      await page.waitForTimeout(500);

      const supplierRadio = page.locator('.el-radio:has-text("供应商")').first();
      await expect(supplierRadio).toHaveClass(/is-checked/);
    });

    test('查询对账数据', async ({ page }) => {
      await pane(page).locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const summaryRow = pane(page).locator('.rc-stats');
      const emptyState = pane(page).locator('.el-empty');
      const hasContent = await summaryRow.isVisible().catch(() => false);
      const isEmpty = await emptyState.isVisible().catch(() => false);

      expect(hasContent || isEmpty).toBeTruthy();
    });
  });

  // ========== 数据展示 ==========
  test.describe('数据展示', () => {
    test('查询后显示汇总卡片', async ({ page }) => {
      await pane(page).locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const summaryRow = pane(page).locator('.rc-stats');
      const isVisible = await summaryRow.isVisible().catch(() => false);

      if (isVisible) {
        await expect(pane(page).locator('text=对方数量')).toBeVisible();
        await expect(pane(page).locator('text=期初欠款')).toBeVisible();
        await expect(pane(page).locator('text=本期发生')).toBeVisible();
        await expect(pane(page).locator('text=已收/已付')).toBeVisible();
        await expect(pane(page).locator('text=期末欠款')).toBeVisible();
        await expect(pane(page).locator('text=发票金额')).toBeVisible();
      }
    });

    test('对账汇总表格列头正确', async ({ page }) => {
      await pane(page).locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const table = pane(page).locator('.el-table').first();
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        await expect(pane(page).locator('th:has-text("对方名称")')).toBeVisible();
        await expect(pane(page).locator('th:has-text("期初欠款")')).toBeVisible();
        await expect(pane(page).locator('th:has-text("本期发生")')).toBeVisible();
        await expect(pane(page).locator('th:has-text("已收/已付")')).toBeVisible();
        await expect(pane(page).locator('th:has-text("期末欠款")')).toBeVisible();
        await expect(pane(page).locator('th:has-text("发票金额")')).toBeVisible();
        await expect(pane(page).locator('th:has-text("单据数")')).toBeVisible();
        await expect(pane(page).locator('th:has-text("未结清")')).toBeVisible();
      }
    });

    test('表格有数据时显示行', async ({ page }) => {
      await pane(page).locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const table = pane(page).locator('.el-table').first();
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        const rows = await pane(page).locator('.el-table__row').count();
        expect(rows).toBeGreaterThan(0);
      }
    });
  });

  // ========== 明细抽屉 ==========
  test.describe('明细抽屉', () => {
    test('点击明细按钮打开抽屉', async ({ page }) => {
      await pane(page).locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const table = pane(page).locator('.el-table').first();
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        const rows = await pane(page).locator('.el-table__row').count();
        if (rows > 0) {
          await pane(page).locator('.el-table__row').first().locator('button:has-text("明细")').click();
          await page.waitForTimeout(1500);

          await expect(page.locator('.el-drawer')).toBeVisible();
        }
      }
    });

    test('明细抽屉包含对账明细表格', async ({ page }) => {
      await pane(page).locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const table = pane(page).locator('.el-table').first();
      const isVisible = await table.isVisible().catch(() => false);

      if (isVisible) {
        const rows = await pane(page).locator('.el-table__row').count();
        if (rows > 0) {
          await pane(page).locator('.el-table__row').first().locator('button:has-text("明细")').click();
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
      await pane(page).locator('button:has-text("查询对账")').click();
      await page.waitForTimeout(2000);

      const emptyState = pane(page).locator('.el-empty');
      const isVisible = await emptyState.isVisible().catch(() => false);

      if (isVisible) {
        await expect(pane(page).locator('.el-empty__description')).toContainText('暂无数据');
      }
    });
  });
});
