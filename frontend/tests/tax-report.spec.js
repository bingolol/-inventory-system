import { test, expect } from '@playwright/test';

test.describe('税务报表', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/tax-report');
    await page.waitForSelector('.el-card', { timeout: 10000 });
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('页面标题正确显示', async ({ page }) => {
      await expect(page.locator('.page-title')).toContainText('税务报表');
    });

    test('标签页正确显示', async ({ page }) => {
      await expect(page.locator('.el-tabs__item:has-text("增值税报表")')).toBeVisible();
      await expect(page.locator('.el-tabs__item:has-text("企业所得税")')).toBeVisible();
    });

    test('默认选中增值税报表标签页', async ({ page }) => {
      const activeTab = page.locator('.el-tabs__item.is-active');
      await expect(activeTab).toContainText('增值税报表');
    });
  });

  // ========== 增值税报表 ==========
  test.describe('增值税报表', () => {
    test('增值税报表筛选区域正确展示', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');
      await expect(vatSection.locator('text=按季度')).toBeVisible();
      await expect(vatSection.locator('text=按月份')).toBeVisible();
    });

    test('默认按季度模式展示', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');
      // 按季度模式下，季度表单可见
      await expect(vatSection.locator('.el-form-item:has-text("季度")')).toBeVisible();
    });

    test('季度筛选表单正确展示', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');
      await expect(vatSection.locator('.el-form-item:has-text("年份")')).toBeVisible();
      await expect(vatSection.locator('.el-form-item:has-text("季度")')).toBeVisible();
      await expect(vatSection.locator('button:has-text("查询")')).toBeVisible();
    });

    test('按季度查询增值税报表', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');

      // 选择年份
      const yearFormItem = vatSection.locator('.el-form-item:has-text("年份")');
      await yearFormItem.locator('.el-select').click();
      await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
      const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 选择季度
      const quarterFormItem = vatSection.locator('.el-form-item:has-text("季度")');
      await quarterFormItem.locator('.el-select').click();
      await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
      const quarterOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
      if (await quarterOptions.count() > 0) {
        await quarterOptions.first().click();
      }

      // 点击查询
      await vatSection.locator('button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 验证报表卡片或空状态存在
      const reportCard = vatSection.locator('.report-card');
      const emptyState = vatSection.locator('.el-empty');
      const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
      expect(hasContent).toBeTruthy();
    });

    test('切换到按月份模式', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');
      await vatSection.locator('text=按月份').click();
      await page.waitForTimeout(500);

      // 切换后月份表单可见，季度表单不可见
      await expect(vatSection.locator('.el-form-item:has-text("月份")')).toBeVisible();
      await expect(vatSection.locator('.el-form-item:has-text("季度")')).not.toBeVisible();
    });

    test('月份筛选表单正确展示', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');
      await vatSection.locator('text=按月份').click();
      await page.waitForTimeout(500);

      await expect(vatSection.locator('.el-form-item:has-text("年份")')).toBeVisible();
      await expect(vatSection.locator('.el-form-item:has-text("月份")')).toBeVisible();
      await expect(vatSection.locator('button:has-text("查询")')).toBeVisible();
    });

    test('按月份查询增值税报表', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');
      await vatSection.locator('text=按月份').click();
      await page.waitForTimeout(500);

      // 选择年份
      const yearFormItem = vatSection.locator('.el-form-item:has-text("年份")');
      await yearFormItem.locator('.el-select').click();
      await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
      const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 选择月份
      const monthFormItem = vatSection.locator('.el-form-item:has-text("月份")');
      await monthFormItem.locator('.el-select').click();
      await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
      const monthOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
      if (await monthOptions.count() > 0) {
        await monthOptions.first().click();
      }

      // 点击查询
      await vatSection.locator('button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 验证报表卡片或空状态存在
      const reportCard = vatSection.locator('.report-card');
      const emptyState = vatSection.locator('.el-empty');
      const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
      expect(hasContent).toBeTruthy();
    });

    test('报表内容区域正确展示', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');

      // 选择年份
      const yearFormItem = vatSection.locator('.el-form-item:has-text("年份")');
      await yearFormItem.locator('.el-select').click();
      await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
      const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 点击查询
      await vatSection.locator('button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 如果有报表卡片，验证内部结构
      const reportCard = vatSection.locator('.report-card');
      if ((await reportCard.count()) > 0) {
        await expect(reportCard.locator('.report-header')).toBeVisible();
        await expect(reportCard.locator('.financial-table')).toBeVisible();
      }
    });
  });

  // ========== 企业所得税 ==========
  test.describe('企业所得税', () => {
    test.beforeEach(async ({ page }) => {
      // 先切换到企业所得税标签页
      await page.locator('.el-tabs__item:has-text("企业所得税")').click();
      await page.waitForTimeout(500);
    });

    test('企业所得税筛选区域正确展示', async ({ page }) => {
      const incomeSection = page.locator('.income-tax-report-section');
      await expect(incomeSection.locator('.el-form-item:has-text("年份")')).toBeVisible();
      await expect(incomeSection.locator('.el-form-item:has-text("季度")')).toBeVisible();
      await expect(incomeSection.locator('button:has-text("查询")')).toBeVisible();
    });

    test('按季度查询企业所得税报表', async ({ page }) => {
      const incomeSection = page.locator('.income-tax-report-section');

      // 选择年份
      const yearFormItem = incomeSection.locator('.el-form-item:has-text("年份")');
      await yearFormItem.locator('.el-select').click();
      await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
      const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 选择季度
      const quarterFormItem = incomeSection.locator('.el-form-item:has-text("季度")');
      await quarterFormItem.locator('.el-select').click();
      await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
      const quarterOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
      if (await quarterOptions.count() > 0) {
        await quarterOptions.first().click();
      }

      // 点击查询
      await incomeSection.locator('button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 验证报表卡片或空状态存在
      const reportCard = incomeSection.locator('.report-card');
      const emptyState = incomeSection.locator('.el-empty');
      const hasContent = (await reportCard.count()) > 0 || (await emptyState.count()) > 0;
      expect(hasContent).toBeTruthy();
    });

    test('企业所得税报表内容区域正确展示', async ({ page }) => {
      const incomeSection = page.locator('.income-tax-report-section');

      // 选择年份
      const yearFormItem = incomeSection.locator('.el-form-item:has-text("年份")');
      await yearFormItem.locator('.el-select').click();
      await page.waitForSelector('.el-select-dropdown:visible', { timeout: 5000 });
      const yearOptions = page.locator('.el-select-dropdown:visible .el-select-dropdown__item');
      if (await yearOptions.count() > 0) {
        await yearOptions.first().click();
      }

      // 点击查询
      await incomeSection.locator('button:has-text("查询")').click();
      await page.waitForTimeout(2000);

      // 如果有报表卡片，验证内部结构
      const reportCard = incomeSection.locator('.report-card');
      if ((await reportCard.count()) > 0) {
        await expect(reportCard.locator('.report-header')).toBeVisible();
        await expect(reportCard.locator('.financial-table')).toBeVisible();
      }
    });
  });

  // ========== 标签页切换 ==========
  test.describe('标签页切换', () => {
    test('在不同标签页之间切换', async ({ page }) => {
      await page.locator('.el-tabs__item:has-text("企业所得税")').click();
      await page.waitForTimeout(500);
      await expect(page.locator('.el-tabs__item.is-active')).toContainText('企业所得税');

      await page.locator('.el-tabs__item:has-text("增值税报表")').click();
      await page.waitForTimeout(500);
      await expect(page.locator('.el-tabs__item.is-active')).toContainText('增值税报表');
    });

    test('切换标签页后筛选条件保持', async ({ page }) => {
      const vatSection = page.locator('.vat-report-section');
      const yearFormItem = vatSection.locator('.el-form-item:has-text("年份")');

      // 初始状态年份表单可见
      await expect(yearFormItem).toBeVisible();

      // 切换到企业所得税再切回来
      await page.locator('.el-tabs__item:has-text("企业所得税")').click();
      await page.waitForTimeout(500);

      await page.locator('.el-tabs__item:has-text("增值税报表")').click();
      await page.waitForTimeout(500);

      // 验证年份表单仍然可见
      await expect(yearFormItem).toBeVisible();
    });
  });
});
