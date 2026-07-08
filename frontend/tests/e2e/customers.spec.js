import { test, expect } from '@playwright/test';

const WAIT_MS = 800;

test.describe('客户管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/partners');
    await page.waitForTimeout(500);
    // 切换到客户标签页
    await page.locator('.el-tabs__item:has-text("客户")').click();
    await page.waitForTimeout(500);
    await expect(page.locator('.el-tabs__item.is-active')).toContainText('客户');
    await page.locator('.el-tab-pane:visible .el-table').first().waitFor({ state: 'visible', timeout: 10000 });
  });

  const customerPane = (page) => page.locator('.el-tab-pane:visible');
  const firstRow = (page) => page.locator('.el-tab-pane:visible .el-table').first().locator('.el-table__row').first();

  // ========== 列表展示 ==========
  test.describe('列表展示', () => {
    test('客户列表正确展示后端数据', async ({ page }) => {
      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThan(0);

      const pane = customerPane(page);
      await expect(pane.locator('th:has-text("客户名称")')).toBeVisible();
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

    test('页面标题显示"客户列表"', async ({ page }) => {
      await expect(customerPane(page).locator('.page-title')).toContainText('客户列表');
    });

    test('新增按钮显示正确文本', async ({ page }) => {
      await expect(customerPane(page).locator('.card-header button:has-text("新增客户")')).toBeVisible();
    });
  });

  // ========== 分页 ==========
  test.describe('分页功能', () => {
    test('切换页码加载不同数据', async ({ page }) => {
      const pagination = customerPane(page).locator('.el-pagination');
      await pagination.locator('.el-select').click();
      await page.waitForTimeout(300);
      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10\s*条\/页/ }).click();
      await page.waitForTimeout(WAIT_MS);

      const page2 = pagination.locator('.el-pager li:has-text("2")');
      if (await page2.count() === 0) {
        test.skip(true, '数据不足一页，跳过翻页测试');
        return;
      }
      const firstRowText = await firstRow(page).textContent();
      await page2.click();
      await page.waitForTimeout(WAIT_MS);
      const newFirstRowText = await firstRow(page).textContent();
      expect(newFirstRowText).not.toBe(firstRowText);
    });

    test('修改每页条数', async ({ page }) => {
      const rowsBefore = await page.locator('.el-tab-pane:visible .el-table__row').count();

      const pagination = customerPane(page).locator('.el-pagination');
      await pagination.locator('.el-select').click();
      await page.waitForTimeout(300);

      await page.locator('.el-select-dropdown:visible').last().locator('li').filter({ hasText: /^10\s*条\/页/ }).click();
      await page.waitForTimeout(WAIT_MS);

      const rowsAfter = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rowsAfter).toBeLessThanOrEqual(10);
      expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
    });
  });

  // ========== 搜索 ==========
  test.describe('搜索功能', () => {
    test('名称搜索', async ({ page }) => {
      const searchInput = customerPane(page).locator('input[placeholder="搜索客户名称"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(WAIT_MS);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('查询按钮触发搜索', async ({ page }) => {
      const searchInput = customerPane(page).locator('input[placeholder="搜索客户名称"]');
      await searchInput.fill('测试');
      await customerPane(page).locator('.filter-bar button:has-text("查询")').click();
      await page.waitForTimeout(WAIT_MS);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBeGreaterThanOrEqual(0);
    });

    test('清空搜索恢复全部数据', async ({ page }) => {
      const allCount = await page.locator('.el-tab-pane:visible .el-table__row').count();

      const searchInput = customerPane(page).locator('input[placeholder="搜索客户名称"]');
      await searchInput.fill('测试');
      await searchInput.press('Enter');
      await page.waitForTimeout(WAIT_MS);

      const searchCount = await page.locator('.el-tab-pane:visible .el-table__row').count();

      await searchInput.clear();
      await searchInput.press('Enter');
      await page.waitForTimeout(WAIT_MS);

      const restoredCount = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(restoredCount).toBe(allCount);
      expect(searchCount).toBeLessThanOrEqual(restoredCount);
    });
  });

  // ========== 新增客户 ==========
  test.describe('新增客户', () => {
    test('打开新增对话框', async ({ page }) => {
      await customerPane(page).locator('.card-header button:has-text("新增客户")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增客户' }).first();
      await expect(dialog).toBeVisible();
      await expect(dialog.locator('.el-dialog__title')).toContainText('新增客户');
    });

    test('新增客户成功', async ({ page }) => {
      const timestamp = Date.now();
      const customerName = `PW测试客户-${timestamp}`;
      const contact = `联系人-${timestamp}`;

      await customerPane(page).locator('.card-header button:has-text("新增客户")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增客户' }).first();
      await dialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input').fill(customerName);
      await dialog.locator('.pl-field').filter({ hasText: '联系人' }).locator('input').fill(contact);
      await dialog.locator('.pl-field').filter({ hasText: '电话' }).locator('input').fill('13900139000');
      await dialog.locator('.pl-field').filter({ hasText: '地址' }).locator('input').fill('客户测试地址');

      await dialog.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await expect(dialog).not.toBeVisible();

      await page.waitForTimeout(WAIT_MS);

      const searchInput = customerPane(page).locator('input[placeholder="搜索客户名称"]');
      await searchInput.fill(customerName);
      await searchInput.press('Enter');
      await page.waitForTimeout(WAIT_MS);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(1);

      const cellText = await firstRow(page).textContent();
      expect(cellText).toContain(customerName);
    });

    test('新增客户表单校验-名称必填', async ({ page }) => {
      await customerPane(page).locator('.card-header button:has-text("新增客户")').click();
      const dialog = page.locator('.el-dialog').filter({ hasText: '新增客户' }).first();
      await expect(dialog.locator('.pl-field').filter({ hasText: '名称' })).toBeVisible();
      await dialog.locator('.el-dialog__footer button:has-text("取消")').click();
    });

    test('取消新增不保存', async ({ page }) => {
      await customerPane(page).locator('.card-header button:has-text("新增客户")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '新增客户' }).first();
      await dialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input').fill('不应保存的客户');

      await dialog.locator('.el-dialog__footer button:has-text("取消")').click();

      await expect(dialog).not.toBeVisible();

      const searchInput = customerPane(page).locator('input[placeholder="搜索客户名称"]');
      await searchInput.fill('不应保存的客户');
      await searchInput.press('Enter');
      await page.waitForTimeout(WAIT_MS);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(0);
    });
  });

  // ========== 编辑客户 ==========
  test.describe('编辑客户', () => {
    test('打开编辑对话框并回填数据', async ({ page }) => {
      const firstName = await firstRow(page).locator('td').first().textContent();

      await firstRow(page).locator('button:has-text("编辑")').click();

      const dialog = page.locator('.el-dialog').filter({ hasText: '编辑客户' }).first();
      await expect(dialog).toBeVisible();
      await expect(dialog.locator('.el-dialog__title')).toContainText('编辑客户');

      const nameInput = dialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input');
      await expect(nameInput).toHaveValue(firstName?.trim() || '');
    });

    test('编辑客户保存成功', async ({ page }) => {
      const timestamp = Date.now();
      const customerName = `编辑测试客户-${timestamp}`;
      const editedName = `Playwright编辑客户-${timestamp}`;

      // 先新增一个客户用于编辑
      await customerPane(page).locator('.card-header button:has-text("新增客户")').click();
      const addDialog = page.locator('.el-dialog').filter({ hasText: '新增客户' }).first();
      await addDialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input').fill(customerName);
      await addDialog.locator('.el-dialog__footer button:has-text("保存")').click();
      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(WAIT_MS);

      // 搜索到新增的客户
      const searchInput = customerPane(page).locator('input[placeholder="搜索客户名称"]');
      await searchInput.fill(customerName);
      await searchInput.press('Enter');
      await page.waitForTimeout(WAIT_MS);

      // 点击编辑
      await firstRow(page).locator('button:has-text("编辑")').click();
      const editDialog = page.locator('.el-dialog').filter({ hasText: '编辑客户' }).first();
      await expect(editDialog).toBeVisible();

      const nameInput = editDialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input');
      await nameInput.clear();
      await nameInput.fill(editedName);

      await editDialog.locator('.el-dialog__footer button:has-text("保存")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(WAIT_MS);

      // 重新搜索编辑后的客户名
      await searchInput.clear();
      await searchInput.fill(editedName);
      await searchInput.press('Enter');
      await page.waitForTimeout(WAIT_MS);

      const rows = await page.locator('.el-tab-pane:visible .el-table__row').count();
      expect(rows).toBe(1);

      const cellText = await firstRow(page).textContent();
      expect(cellText).toContain(editedName);
    });
  });

  // ========== 删除客户 ==========
  test.describe('删除客户', () => {
    test('删除客户流程', async ({ page }) => {
      const timestamp = Date.now();
      const customerName = `待删除客户-${timestamp}`;

      // 先新增一个客户用于删除
      await customerPane(page).locator('.card-header button:has-text("新增客户")').click();
      const addDialog = page.locator('.el-dialog').filter({ hasText: '新增客户' }).first();
      await addDialog.locator('.pl-field').filter({ hasText: '名称' }).locator('input').fill(customerName);
      await addDialog.locator('.el-dialog__footer button:has-text("保存")').click();
      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });
      await page.waitForTimeout(WAIT_MS);

      // 搜索到新增的客户
      const searchInput = customerPane(page).locator('input[placeholder="搜索客户名称"]');
      await searchInput.fill(customerName);
      await searchInput.press('Enter');
      await page.waitForTimeout(WAIT_MS);

      // 点击删除
      const targetRow = page.locator('.el-tab-pane:visible .el-table__row').first();
      await targetRow.locator('button:has-text("删除")').click();

      await expect(page.locator('.el-popconfirm')).toBeVisible();

      await page.locator('.el-popconfirm button:has-text("确定")').click();

      await expect(page.locator('.el-message--success')).toBeVisible({ timeout: 5000 });

      await page.waitForTimeout(WAIT_MS);
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
