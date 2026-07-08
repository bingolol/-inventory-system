import { test, expect } from '@playwright/test';

test.describe('税务报表', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/period-end-tax');
    await page.waitForTimeout(800);
    // 等待外层"税务报表"标签页激活
    await expect(page.locator('.el-tabs__item.is-active').first()).toContainText('税务报表');
  });

  const taxReportCard = (page) => page.locator('.el-tab-pane:visible');

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('页面标题正确显示', async ({ page }) => {
      await expect(taxReportCard(page).locator('.page-title')).toContainText('税务报表');
    });

    test('标签页正确显示', async ({ page }) => {
      await expect(page.locator('.el-tabs__item:has-text("增值税报表")').first()).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("企业所得税")').first()).toBeVisible();
    });

    test('默认选中增值税报表标签页', async ({ page }) => {
      const activeTab = page.locator('.el-tabs__item.is-active');
      // 外层标签页是税务报表，内层标签页是增值税报表
      await expect(activeTab.filter({ hasText: '增值税报表' }).first()).toContainText('增值税报表');
    });
  });

  // ========== 增值税报表 ==========
  test.describe('增值税报表', () => {
    test('增值税报表筛选区域正确展示', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');
      await expect(vatSection.locator('text=按季度')).toBeVisible();
      await expect(vatSection.locator('text=按月份')).toBeVisible();
    });

    test('默认按季度模式展示', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');
      // 按季度模式下，季度筛选表单可见
      await expect(vatSection.locator('.filter-bar .el-select').nth(1)).toBeVisible();
      const quarterSelect = vatSection.locator('.filter-bar .el-select').nth(1);
      await quarterSelect.click();
      await page.waitForTimeout(300);
      await expect(page.locator('.el-select-dropdown:visible').last().locator('li:has-text("季度")').first()).toBeVisible();
      await page.keyboard.press('Escape');
    });

    test('季度筛选表单正确展示', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');
      const selects = vatSection.locator('.filter-bar .el-select');
      await expect(selects).toHaveCount(2);
      await expect(vatSection.locator('.filter-bar button:has-text("查询")')).toBeVisible();
    });

    test('按季度查询增值税报表', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');

      // 选择年份
      const yearSelect = vatSection.locator('.filter-bar .el-select').first();
      await yearSelect.click();
      await page.waitForTimeout(300);
      const yearOptions = page.locator('.el-select-dropdown:visible').last().locator('.el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 点击查询
      await vatSection.locator('.filter-bar button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 验证报表区域或空状态存在
      const reportCard = vatSection.locator('.vat-report');
      const emptyState = vatSection.locator('.el-empty');
      const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
      expect(hasContent).toBeTruthy();
    });

    test('切换到按月份模式', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');
      await vatSection.locator('.el-radio-button:has-text("按月份")').click();
      await page.waitForTimeout(800);

      // 切换后月份筛选表单可见（两个下拉 + 查询按钮）
      const selects = vatSection.locator('.filter-bar .el-select');
      await expect(selects).toHaveCount(2);
      await expect(vatSection.locator('.filter-bar button:has-text("查询")')).toBeVisible();
    });

    test('月份筛选表单正确展示', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');
      await vatSection.locator('.el-radio-button:has-text("按月份")').click();
      await page.waitForTimeout(500);

      const selects = vatSection.locator('.filter-bar .el-select');
      await expect(selects).toHaveCount(2);
      await expect(vatSection.locator('.filter-bar button:has-text("查询")')).toBeVisible();
    });

    test('按月份查询增值税报表', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');
      await vatSection.locator('.el-radio-button:has-text("按月份")').click();
      await page.waitForTimeout(500);

      // 选择年份
      const yearSelect = vatSection.locator('.filter-bar .el-select').first();
      await yearSelect.click();
      await page.waitForTimeout(300);
      const yearOptions = page.locator('.el-select-dropdown:visible').last().locator('.el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 点击查询
      await vatSection.locator('.filter-bar button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 验证报表区域或空状态存在
      const reportCard = vatSection.locator('.vat-report');
      const emptyState = vatSection.locator('.el-empty');
      const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
      expect(hasContent).toBeTruthy();
    });

    test('报表内容区域正确展示', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');

      // 选择年份
      const yearSelect = vatSection.locator('.filter-bar .el-select').first();
      await yearSelect.click();
      await page.waitForTimeout(300);
      const yearOptions = page.locator('.el-select-dropdown:visible').last().locator('.el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 点击查询
      await vatSection.locator('.filter-bar button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 如果有报表卡片，验证内部结构
      const reportCard = vatSection.locator('.vat-report');
      if ((await reportCard.count()) > 0) {
        await expect(reportCard.locator('.vat-report-title')).toBeVisible();
        await expect(reportCard.locator('.el-table')).toBeVisible();
      }
    });
  });

  // ========== 企业所得税 ==========
  test.describe('企业所得税', () => {
    test.beforeEach(async ({ page }) => {
      // 先切换到企业所得税内层标签页
      await page.locator('.el-tabs__item:has-text("企业所得税")').first().click();
      await page.waitForTimeout(800);
    });

    test('企业所得税筛选区域正确展示', async ({ page }) => {
      const incomeSection = taxReportCard(page).locator('.el-tab-pane:visible');
      const selects = incomeSection.locator('.filter-bar .el-select');
      await expect(selects).toHaveCount(2);
      await expect(incomeSection.locator('.filter-bar button:has-text("查询")')).toBeVisible();
    });

    test('按季度查询企业所得税报表', async ({ page }) => {
      const incomeSection = taxReportCard(page).locator('.el-tab-pane:visible');

      // 选择年份
      const yearSelect = incomeSection.locator('.filter-bar .el-select').first();
      await yearSelect.click();
      await page.waitForTimeout(300);
      const yearOptions = page.locator('.el-select-dropdown:visible').last().locator('.el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 点击查询
      await incomeSection.locator('.filter-bar button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 验证报表区域或空状态存在
      const reportCard = incomeSection.locator('.it-page');
      const emptyState = incomeSection.locator('.el-empty');
      const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
      expect(hasContent).toBeTruthy();
    });

    test('企业所得税报表内容区域正确展示', async ({ page }) => {
      const incomeSection = taxReportCard(page).locator('.el-tab-pane:visible');

      // 选择年份
      const yearSelect = incomeSection.locator('.filter-bar .el-select').first();
      await yearSelect.click();
      await page.waitForTimeout(300);
      const yearOptions = page.locator('.el-select-dropdown:visible').last().locator('.el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 点击查询
      await incomeSection.locator('.filter-bar button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 如果有报表卡片，验证内部结构
      const reportCard = incomeSection.locator('.it-page');
      if ((await reportCard.count()) > 0) {
        await expect(reportCard.locator('.it-hero')).toBeVisible();
        await expect(reportCard.locator('.it-waterfall')).toBeVisible();
      }
    });
  });

  // ========== 标签页切换 ==========
  test.describe('标签页切换', () => {
    test('在不同标签页之间切换', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("企业所得税")').first().click();
      await page.waitForTimeout(500);
      await expect(page.locator('.el-tabs__item.is-active').filter({ hasText: '企业所得税' }).first()).toContainText('企业所得税');

      await page.locator('.el-tabs__item:has-text("增值税报表")').first().click();
      await page.waitForTimeout(500);
      await expect(page.locator('.el-tabs__item.is-active').filter({ hasText: '增值税报表' }).first()).toContainText('增值税报表');
    });

    test('切换标签页后筛选条件保持', async ({ page }) => {
      const vatSection = taxReportCard(page).locator('.el-tab-pane:visible');
      const filterBar = vatSection.locator('.filter-bar');

      // 初始状态筛选表单可见
      await expect(filterBar).toBeVisible();

      // 切换到企业所得税再切回来
      await page.locator('.el-tabs__item:has-text("企业所得税")').first().click();
      await page.waitForTimeout(500);

      await page.locator('.el-tabs__item:has-text("增值税报表")').first().click();
      await page.waitForTimeout(500);

      // 验证筛选表单仍然可见
      await expect(taxReportCard(page).locator('.el-tab-pane:visible .filter-bar')).toBeVisible();
    });
  });
});
