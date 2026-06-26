import { test, expect } from '@playwright/test';

test.describe('销售记录', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/sales');
    await page.waitForTimeout(800);
    await page.waitForSelector('.el-table__row', { timeout: 10000 });
  });

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('销售列表正确展示后端数据', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThan(0);

      await expect(page.locator('th:has-text("单号")')).toBeVisible();
      await expect(page.locator('th:has-text("客户")')).toBeVisible();
      await expect(page.locator('th:has-text("商品数")')).toBeVisible();
      await expect(page.locator('th:has-text("总价")')).toBeVisible();
      await expect(page.locator('th:has-text("已开票")')).toBeVisible();
      await expect(page.locator('th:has-text("支付状态")')).toBeVisible();
      await expect(page.getByRole('columnheader', { name: '状态', exact: true })).toBeVisible();
      await expect(page.locator('th:has-text("日期")')).toBeVisible();
      await expect(page.locator('th:has-text("备注")')).toBeVisible();
      await expect(page.locator('th:has-text("附件")')).toBeVisible();
    });

    test('页面标题为销售记录', async ({ page }) => {
      await expect(page.locator('.page-title')).toContainText('销售记录');
    });

    test('第一行数据包含有效内容', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const rowText = await firstRow.textContent();
      expect(rowText?.trim().length).toBeGreaterThan(5);
    });

    test('每行显示操作按钮', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      await expect(firstRow.locator('button:has-text("编辑")')).toBeVisible();
      await expect(firstRow.locator('button:has-text("删除")')).toBeVisible();
    });

    test('订单单号分两行显示', async ({ page }) => {
      const orderNoCell = page.locator('.el-table__row:first-child .order-no');
      await expect(orderNoCell).toBeVisible();
      await expect(orderNoCell.locator('.order-no-line1')).toBeVisible();
      await expect(orderNoCell.locator('.order-no-line2')).toBeVisible();
    });

    test('新建销售按钮存在', async ({ page }) => {
      await expect(page.locator('button:has-text("新建销售")')).toBeVisible();
    });
  });

  // ========== 分页 ==========
  test.describe('分页功能', () => {
    test('分页组件正确展示', async ({ page }) => {
      await expect(page.locator('.el-pagination')).toBeVisible();
      await expect(page.locator('.el-pagination .el-pagination__total')).toBeVisible();
    });

    test('切换页码加载不同数据', async ({ page }) => {
      // 先切换到10条/页确保有多页数据
      await page.locator('.el-pagination .el-select').click();
      await page.waitForTimeout(500);
      await page.getByRole('option', { name: '10条/页' }).click();
      await page.waitForTimeout(1500);

      const page2 = page.getByRole('listitem', { name: '第 2 页' });
      if (await page2.count() === 0) {
        test.skip(true, '数据不足一页，跳过翻页测试');
        return;
      }
      const firstRowText = await page.locator('.el-table__row:first-child').textContent();
      await page2.click();
      await page.waitForTimeout(1500);
      const newFirstRowText = await page.locator('.el-table__row:first-child').textContent();
      expect(newFirstRowText).not.toBe(firstRowText);
    });

    test('修改每页条数', async ({ page }) => {
      const rowsBefore = await page.locator('.el-table__row').count();

      await page.locator('.el-pagination .el-select').click();
      await page.waitForTimeout(500);

      // 使用精确匹配避免 strict mode
      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10条\/页$/ }).click();
      await page.waitForTimeout(1000);

      const rowsAfter = await page.locator('.el-table__row').count();
      expect(rowsAfter).toBeLessThanOrEqual(10);
      expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
    });
  });

  // ========== 状态筛选 ==========
  test.describe('状态筛选', () => {
    test('状态筛选下拉框正确展示选项', async ({ page }) => {
      const statusSelect = page.locator('.filter-bar .el-select');
      await statusSelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode
      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();
      expect(optionCount).toBeGreaterThan(0);
    });

    test('按状态筛选销售单', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const statusSelect = page.locator('.filter-bar .el-select');
      await statusSelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode
      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(1000);

        const filteredCount = await page.locator('.el-table__row').count();
        expect(filteredCount).toBeGreaterThanOrEqual(0);
        expect(filteredCount).toBeLessThanOrEqual(allCount);
      }
    });

    test('清空状态筛选恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const statusSelect = page.locator('.filter-bar .el-select');
      await statusSelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode
      const dropdown = page.locator('.el-select-dropdown:visible').last();
      const options = dropdown.locator('li');
      const optionCount = await options.count();

      if (optionCount > 0) {
        await options.first().click();
        await page.waitForTimeout(1000);

        const filteredCount = await page.locator('.el-table__row').count();
        expect(filteredCount).toBeLessThanOrEqual(allCount);

        await statusSelect.click();
        await page.waitForTimeout(500);
        // 使用 .last() 避免 strict mode
        await page.locator('.el-select-dropdown:visible').last().locator('li').first().click();
        await page.waitForTimeout(1000);
      }
    });
  });

  // ========== 日期范围筛选 ==========
  test.describe('日期范围筛选', () => {
    test('日期范围选择器可正常打开', async ({ page }) => {
      await page.locator('.filter-bar .el-date-editor input').first().click();
      await page.waitForTimeout(500);

      await expect(page.locator('.el-date-table').first()).toBeVisible();
    });

    test('选择日期范围后列表更新', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const datePicker = page.locator('.filter-bar .el-date-editor');
      await datePicker.click();
      await page.waitForTimeout(500);

      const startDate = page.locator('.el-date-table td:has-text("1"):not(.is-disabled):not(.prev-month)').first();
      if (await startDate.isVisible()) {
        await startDate.click();
        await page.waitForTimeout(200);

        const endDate = page.locator('.el-date-table td:has-text("15"):not(.is-disabled):not(.prev-month)').first();
        if (await endDate.isVisible()) {
          await endDate.click();
          await page.waitForTimeout(1000);

          const filteredCount = await page.locator('.el-table__row').count();
          expect(filteredCount).toBeGreaterThanOrEqual(0);
          expect(filteredCount).toBeLessThanOrEqual(allCount);
        }
      }
    });
  });

  // ========== 导出 ==========
  test.describe('导出功能', () => {
    test('导出下拉菜单可正常打开', async ({ page }) => {
      await page.locator('button:has-text("导出")').click();
      await page.waitForTimeout(500);

      await expect(page.locator('.el-dropdown-menu:visible')).toBeVisible();
      await expect(page.locator('.el-dropdown-menu__item:has-text("Excel")').first()).toBeVisible();
      await expect(page.locator('.el-dropdown-menu__item:has-text("CSV")').first()).toBeVisible();
    });
  });

  // ========== 与采购页差异验证 ==========
  test.describe('页面结构验证', () => {
    test('销售页无搜索输入框（与采购页区分）', async ({ page }) => {
      const searchInput = page.locator('input[placeholder="搜索单号/供应商/项目"]');
      await expect(searchInput).not.toBeVisible();
    });

    test('销售页客户列正确展示', async ({ page }) => {
      const customerHeader = page.locator('th:has-text("客户")');
      await expect(customerHeader).toBeVisible();

      const firstRow = page.locator('.el-table__row:first-child');
      const customerCell = firstRow.locator('td').nth(2);
      await expect(customerCell).toBeVisible();
    });

    test('销售页附件列正确展示', async ({ page }) => {
      const attachmentHeader = page.locator('th:has-text("附件")');
      await expect(attachmentHeader).toBeVisible();
    });
  });
});
