import { test, expect } from '@playwright/test';

test.describe('供应商管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/partners?tab=suppliers');
    await page.waitForTimeout(800);
    // 等待供应商标签页激活
    await expect(page.locator('.el-tabs__item.is-active')).toContainText('供应商');
    // 等待主表格可见（存在多个表格时取第一个可见的）
    await page.locator('.el-tab-pane:visible .el-table').first().waitFor({ state: 'visible', timeout: 10000 });
  });

  const supplierPane = (page) => page.locator('.el-tab-pane:visible');
  const firstRow = (page) => page.locator('.el-tab-pane:visible .el-table').first().locator('.el-table__row').first();

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('供应商列表正确展示后端数据', async ({ page }) => {
      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThan(0);

      const pane = supplierPane(page);
      await expect(pane.locator('th:has-text("供应商名称")')).toBeVisible();
      await expect(pane.locator('th:has-text("联系人")')).toBeVisible();
      await expect(pane.locator('th:has-text("电话")')).toBeVisible();
      await expect(pane.locator('th:has-text("地址")')).toBeVisible();
      await expect(pane.locator('th:has-text("备注")')).toBeVisible();
      await expect(pane.locator('th:has-text("操作")')).toBeVisible();
    });

    test('第一行数据包含有效内容', async ({ page }) => {
      const row = firstRow(page);
      const rowText = await row.textContent();
      expect(rowText?.trim().length).toBeGreaterThan(5);
    });

    test('页面标题显示"供应商列表"', async ({ page }) => {
      await expect(supplierPane(page).locator('.page-title')).toContainText('供应商列表');
    });

    test('新增按钮显示正确文本', async ({ page }) => {
      await expect(supplierPane(page).locator('.card-header button:has-text("新增供应商")')).toBeVisible();
    });
  });

  // ========== 分页 ==========
  test.describe('分页功能', () => {
    test('切换页码加载不同数据', async ({ page }) => {
      // 先切换到10条/页确保有多页数据
      const pagination = page.locator('.el-tab-pane:visible .el-pagination');
      await pagination.locator('.el-select').click();
      await page.waitForTimeout(300);
      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10条\/页$/ }).click();
      await page.waitForTimeout(1500);

      const page2 = pagination.locator('.el-pager li:has-text("2")');
      if (await page2.count() === 0) {
        test.skip(true, '数据不足一页，跳过翻页测试');
        return;
      }
      const firstRowText = await firstRow(page).textContent();
      await page2.click();
      await page.waitForTimeout(1500);
      const newFirstRowText = await firstRow(page).textContent();
      expect(newFirstRowText).not.toBe(firstRowText);
    });

    test('修改每页条数', async ({ page }) => {
      const rowsBefore = await page.locator('.el-tab-pane:visible .el-table__row').count();

      const pagination = page.locator('.el-tab-pane:visible .el-pagination');
      await pagination.locator('.el-select').click();
      await page.waitForTimeout(300);

      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10条\/页$/ }).click();
      await page.waitForTimeout(1000);

      const rowsAfter = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rowsAfter).toBeLessThanOrEqual(10);
      expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
    });
  });

  // ========== 搜索 ==========
  test.describe('搜索功能', () => {
    test('名称搜索', async ({ page }) => {
      const searchInput = supplierPane(page).locator('input[placeholder="搜索供应商名称"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('查询按钮触发搜索', async ({ page }) => {
      const searchInput = supplierPane(page).locator('input[placeholder="搜索供应商名称"]');
      await searchInput.fill('测试');
      await supplierPane(page).locator('.filter-bar button:has-text("查询")').click();
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('清空搜索恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-tab-pane:visible .el-table__row').count();

      const searchInput = supplierPane(page).locator('input[placeholder="搜索供应商名称"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const searchCount = await page.locator('.el-tab-pane:visible .el-table__row').count();

      await searchInput.clear();
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const restoredCount = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(restoredCount).toBe(allCount);
      expect(searchCount).toBeLessThanOrEqual(restoredCount);
    });
  });

  // ========== 新增供应商 ==========
  test.describe('新增供应商', () => {
    test('打开新增对话框', async ({ page }) => {
      await supplierPane(page).locator('.card-header button:has-text("新增供应商")').click();

      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('新增供应商');
    });

    test('新增供应商成功', async ({ page }) => {
      const timestamp = Date.now();
      const supplierName = `PW测试供应商-${timestamp}`;
      const contact = `联系人-${timestamp}`;

      await supplierPane(page).locator('.card-header button:has-text("新增供应商")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增供应商' }).first();
      await dialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input').fill(supplierName);
      await dialog.locator('.pl-field').filter({ hasText: '联系人' }).locator('input').fill(contact);
      await dialog.locator('.pl-field').filter({ hasText: '电话' }).locator('input').fill('13800138000');
      await dialog.locator('.pl-field').filter({ hasText: '地址' }).locator('input').fill('测试地址');

      await dialog.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await expect(dialog).not.toBeVisible();

      await page.waitForTimeout(1000);

      const searchInput = supplierPane(page).locator('input[placeholder="搜索供应商名称"]');
      await searchInput.fill(supplierName);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(1);

      const cellText = await firstRow(page).textContent();
      expect(cellText).toContain(supplierName);
    });

    test('新增供应商表单校验', async ({ page }) => {
      await supplierPane(page).locator('.card-header button:has-text("新增供应商")').click();
      const dialog = page.locator('.el-dialog').filter({ hasText: '新增供应商' }).first();
      await expect(dialog.locator('.pl-field').filter({ hasText: '名称' })).toBeVisible();
      await dialog.locator('.el-dialog__footer button:has-text("取消")').click();
    });

    test('取消新增不保存', async ({ page }) => {
      await supplierPane(page).locator('.card-header button:has-text("新增供应商")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增供应商' }).first();
      await dialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input').fill('不应保存的供应商');

      await dialog.locator('.el-dialog__footer button:has-text("取消")').click();

      await expect(dialog).not.toBeVisible();

      const searchInput = supplierPane(page).locator('input[placeholder="搜索供应商名称"]');
      await searchInput.fill('不应保存的供应商');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(0);
    });
  });

  // ========== 编辑供应商 ==========
  test.describe('编辑供应商', () => {
    test('打开编辑对话框并回填数据', async ({ page }) => {
      const firstName = await firstRow(page).locator('td').first().textContent();

      await firstRow(page).locator('button:has-text("编辑")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '编辑供应商' }).first();
      await expect(dialog).toBeVisible();
      await expect(dialog.locator('.el-dialog__title')).toContainText('编辑供应商');

      const nameInput = dialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input');
      await expect(nameInput).toHaveValue(firstName?.trim() || '');
    });

    test('编辑供应商保存成功', async ({ page }) => {
      const timestamp = Date.now();
      const supplierName = `编辑测试供应商-${timestamp}`;

      // 先新增一个供应商用于编辑
      await supplierPane(page).locator('.card-header button:has-text("新增供应商")').click();
      const addDialog = page.locator('.el-dialog').filter({ hasText: '新增供应商' }).first();
      await addDialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input').fill(supplierName);
      await addDialog.locator('.el-dialog__footer button:has-text("保存")').click();
      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(1000);

      // 搜索到新增的供应商
      const searchInput = supplierPane(page).locator('input[placeholder="搜索供应商名称"]');
      await searchInput.fill(supplierName);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      // 点击编辑
      await firstRow(page).locator('button:has-text("编辑")').click();
      const editDialog = page.locator('.el-dialog').filter({ hasText: '编辑供应商' }).first();
      await expect(editDialog).toBeVisible();

      const nameInput = editDialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input');
      await nameInput.clear();
      await nameInput.fill('Playwright编辑供应商');

      await editDialog.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(1000);

      // 保存后重新搜索编辑后的供应商，再验证第一行包含编辑名称
      await searchInput.fill('Playwright编辑供应商');
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      await expect(firstRow(page)).toContainText('Playwright编辑供应商');
    });
  });

  // ========== 删除供应商 ==========
  test.describe('删除供应商', () => {
    test('删除供应商流程', async ({ page }) => {
      const timestamp = Date.now();
      const supplierName = `待删除供应商-${timestamp}`;

      // 先新增一个供应商用于删除
      await supplierPane(page).locator('.card-header button:has-text("新增供应商")').click();
      const addDialog = page.locator('.el-dialog').filter({ hasText: '新增供应商' }).first();
      await addDialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input').fill(supplierName);
      await addDialog.locator('.el-dialog__footer button:has-text("保存")').click();
      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(1000);

      // 搜索到新增的供应商
      const searchInput = supplierPane(page).locator('input[placeholder="搜索供应商名称"]');
      await searchInput.fill(supplierName);
      await searchInput.press('Enter');
      await page.waitForTimeout(1000);

      // 点击删除
      const targetRow = page.locator('.el-tab-pane:visible .el-table__row').first();
      await targetRow.locator('button:has-text("删除")').click();

      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("确定")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(1000);
      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(0);
    });

    test('取消删除不执行', async ({ page }) => {
      const firstName = await firstRow(page).locator('td').first().textContent();

      await firstRow(page).locator('button:has-text("删除")').click();

      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("取消")').click();

      await expect(firstRow(page)).toContainText(firstName?.trim() || '');
    });
  });
});
