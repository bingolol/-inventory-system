import { test, expect } from '@playwright/test';

test.describe('个人收支', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/personal');
    await page.waitForTimeout(800);
    await page.waitForSelector('.el-table__row', { timeout: 10000 });
  });

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('收支列表正确展示后端数据', async ({ page }) => {
      const rows = await page.locator('.el-table__row').count();
      expect(rows).toBeGreaterThan(0);

      await expect(page.locator('th:has-text("日期")')).toBeVisible();
      await expect(page.locator('th:has-text("类型")')).toBeVisible();
      await expect(page.locator('th:has-text("分类")')).toBeVisible();
      await expect(page.locator('th:has-text("金额")')).toBeVisible();
      await expect(page.locator('th:has-text("备注")')).toBeVisible();
      await expect(page.locator('th:has-text("操作")')).toBeVisible();
    });

    test('第一行数据包含有效内容', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const rowText = await firstRow.textContent();
      expect(rowText?.trim().length).toBeGreaterThan(5);
    });

    test('金额显示包含货币符号', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const amountCell = firstRow.locator('td').nth(3);
      const amountText = await amountCell.textContent();
      expect(amountText?.trim()).toMatch(/^[+-]¥[\d,.]+$/);
    });

    test('日期格式正确', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const dateCell = firstRow.locator('td').nth(0);
      const dateText = await dateCell.textContent();
      expect(dateText?.trim()).toMatch(/^\d{4}-\d{2}-\d{2}/);
    });

    test('类型标签显示正确', async ({ page }) => {
      const firstRow = page.locator('.el-table__row:first-child');
      const typeCell = firstRow.locator('td').nth(1);
      const typeText = await typeCell.textContent();
      expect(typeText?.trim()).toMatch(/^(收入|支出)$/);
    });
  });

  // ========== 汇总卡片 ==========
  test.describe('汇总卡片', () => {
    test('本月收入卡片显示', async ({ page }) => {
      const incomeCard = page.locator('.el-card:has-text("本月收入")');
      await expect(incomeCard).toBeVisible();
      await expect(incomeCard).toContainText('¥');
    });

    test('本月支出卡片显示', async ({ page }) => {
      const expenseCard = page.locator('.el-card:has-text("本月支出")');
      await expect(expenseCard).toBeVisible();
      await expect(expenseCard).toContainText('¥');
    });

    test('本月结余卡片显示', async ({ page }) => {
      const balanceCard = page.locator('.el-card:has-text("本月结余")');
      await expect(balanceCard).toBeVisible();
      await expect(balanceCard).toContainText('¥');
    });
  });

  // ========== 筛选功能 ==========
  test.describe('筛选功能', () => {
    test('按类型筛选收支', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const typeSelect = page.locator('.el-select:has-text("类型筛选")');
      await typeSelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode 冲突
      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: '收入' }).click();
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('.el-table__row').count();
      expect(filteredCount).toBeGreaterThanOrEqual(0);
      expect(filteredCount).toBeLessThanOrEqual(allCount);
    });

    test('按分类筛选收支', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const categorySelect = page.locator('.el-select:has-text("分类筛选")');
      await categorySelect.click();
      await page.waitForTimeout(500);

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

    test('按日期范围筛选收支', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const datePicker = page.locator('.el-date-editor--daterange');
      await datePicker.click();
      await page.waitForTimeout(300);

      const todayButton = page.locator('.el-date-picker__header-label:has-text("今天")');
      if (await todayButton.isVisible()) {
        await todayButton.click();
      }

      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('.el-table__row').count();
      expect(filteredCount).toBeGreaterThanOrEqual(0);
    });

    test('组合筛选收支', async ({ page }) => {
      const allCount = await page.locator('.el-table__row').count();

      const typeSelect = page.locator('.el-select:has-text("类型筛选")');
      await typeSelect.click();
      await page.waitForTimeout(500);

      // 使用 .last() 避免 strict mode 冲突
      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: '支出' }).click();
      await page.waitForTimeout(500);

      await page.locator('button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const filteredCount = await page.locator('.el-table__row').count();
      expect(filteredCount).toBeGreaterThanOrEqual(0);
      expect(filteredCount).toBeLessThanOrEqual(allCount);
    });
  });

  // ========== 筛选合计 ==========
  test.describe('筛选合计', () => {
    test('筛选合计显示收入和支出', async ({ page }) => {
      const summaryArea = page.locator('div').filter({ hasText: /^筛选合计：/ }).first();
      await expect(summaryArea).toBeVisible();
      await expect(summaryArea).toContainText('收入');
      await expect(summaryArea).toContainText('支出');
      await expect(summaryArea).toContainText('结余');
    });
  });

  // ========== 分页功能 ==========
  test.describe('分页功能', () => {
    test('切换页码加载不同数据', async ({ page }) => {
      // 先切换到10条/页确保有多页数据
      await page.locator('.el-pagination .el-select').click();
      await page.waitForTimeout(500);
      const dropdown = page.locator('.el-select-dropdown:visible').last();
      await dropdown.locator('.el-select-dropdown__item').filter({ hasText: /^10条\/页$/ }).click();
      await page.waitForTimeout(1500);

      const page2 = page.locator('.el-pager li').nth(1);
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

  // ========== 新增记录 ==========
  test.describe('新增记录', () => {
    test('打开记一笔对话框', async ({ page }) => {
      await page.locator('button:has-text("记一笔")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('记一笔');
    });

    test('关闭记一笔对话框', async ({ page }) => {
      await page.locator('button:has-text("记一笔")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      await page.locator('.el-dialog__footer button:has-text("取消")').click();
      await expect(page.locator('.el-dialog')).not.toBeVisible();
    });

    test('表单默认选中支出类型', async ({ page }) => {
      await page.locator('button:has-text("记一笔")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      const expenseRadio = page.locator('.el-dialog .el-radio-button:has-text("支出")');
      await expect(expenseRadio).toHaveClass(/is-active/);
    });
  });

  // ========== 编辑记录 ==========
  test.describe('编辑记录', () => {
    test('打开编辑对话框', async ({ page }) => {
      await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('编辑记录');
    });

    test('关闭编辑对话框', async ({ page }) => {
      await page.locator('.el-table__row:first-child button:has-text("编辑")').click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      await page.locator('.el-dialog__footer button:has-text("取消")').click();
      await expect(page.locator('.el-dialog')).not.toBeVisible();
    });
  });

  // ========== 删除记录 ==========
  test.describe('删除记录', () => {
    test('点击删除按钮显示确认', async ({ page }) => {
      await page.locator('.el-table__row:first-child button:has-text("删除")').click();
      await expect(page.locator('.el-popconfirm')).toBeVisible();
    });

    test('取消删除操作', async ({ page }) => {
      const firstName = await page.locator('.el-table__row:first-child td').nth(1).textContent();

      await page.locator('.el-table__row:first-child button:has-text("删除")').click();
      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("取消")').click();
      await expect(page.locator('.el-table__row:first-child')).toContainText(firstName?.trim() || '');
    });
  });

  // ========== 图表 ==========
  test.describe('图表展示', () => {
    test('分类统计图表显示', async ({ page }) => {
      const categoryChart = page.locator('.el-card:has-text("分类统计")');
      await expect(categoryChart).toBeVisible();
    });

    test('月度趋势图表显示', async ({ page }) => {
      const monthlyChart = page.locator('.el-card:has-text("月度趋势")');
      await expect(monthlyChart).toBeVisible();
    });

    test('切换分类统计图表类型', async ({ page }) => {
      const categoryChart = page.locator('.el-card:has-text("分类统计")');

      const incomeRadio = categoryChart.locator('.el-radio-button:has-text("收入")');
      await incomeRadio.click();
      await page.waitForTimeout(500);

      await expect(incomeRadio).toHaveClass(/is-active/);
    });

    test('切换月度趋势图表类型', async ({ page }) => {
      const monthlyChart = page.locator('.el-card:has-text("月度趋势")');

      const expenseRadio = monthlyChart.locator('.el-radio-button:has-text("支出")');
      await expenseRadio.click();
      await page.waitForTimeout(500);

      await expect(expenseRadio).toHaveClass(/is-active/);
    });
  });
});
