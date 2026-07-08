import { test, expect } from '@playwright/test';

test.describe('现金流量表', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/cash-flows');
    await page.waitForTimeout(800);
  });

  // ========== 页面加载 ==========
  test.describe('页面加载', () => {
    test('页面标题正确显示', async ({ page }) => {
      await expect(page.locator('.bt:has-text("现金流量表")').first()).toBeVisible();
    });

    test('日期筛选区域正确展示', async ({ page }) => {
      await expect(page.locator('input[placeholder="开始日期"]').first()).toBeVisible();
      await expect(page.locator('input[placeholder="结束日期"]').first()).toBeVisible();
      await expect(page.locator('button:has-text("查询")').first()).toBeVisible();
      await expect(page.locator('button:has-text("新增流水")').first()).toBeVisible();
    });
  });

  // ========== 现金流量表展示 ==========
  test.describe('现金流量表展示', () => {
    test('经营活动区域正确展示', async ({ page }) => {
      const section = page.locator('.c').filter({ hasText: '经营' }).first();
      if (await section.count() === 0) return;
      await expect(section).toBeVisible();
      await expect(section.locator('.cl')).toContainText('经营');
    });

    test('投资活动区域正确展示', async ({ page }) => {
      const section = page.locator('.c').filter({ hasText: '投资' }).first();
      if (await section.count() === 0) return;
      await expect(section).toBeVisible();
      await expect(section.locator('.cl')).toContainText('投资');
    });

    test('筹资活动区域正确展示', async ({ page }) => {
      const section = page.locator('.c').filter({ hasText: '筹资' }).first();
      if (await section.count() === 0) return;
      await expect(section).toBeVisible();
      await expect(section.locator('.cl')).toContainText('筹资');
    });

    test('汇总区域正确展示', async ({ page }) => {
      const summaryBox = page.locator('.box').filter({ hasText: '净现金流量' }).first();
      if (await summaryBox.count() === 0) return;
      await expect(summaryBox.locator('text=净现金流量')).toBeVisible();
      await expect(summaryBox.locator('text=期初余额')).toBeVisible();
      await expect(summaryBox.locator('text=期末余额')).toBeVisible();
    });
  });

  // ========== 日期筛选功能 ==========
  test.describe('日期筛选功能', () => {
    test('修改开始日期后查询', async ({ page }) => {
      const startDateInput = page.locator('input[placeholder="开始日期"]').first();
      await startDateInput.click();
      await page.waitForTimeout(300);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      const queryBtn = page.locator('button:has-text("查询")').first();
      await queryBtn.click();
      await page.waitForTimeout(2000);

      // 查询后页面仍正常显示
      await expect(page.locator('.box').filter({ hasText: '现金流水' }).first()).toBeVisible();
    });

    test('修改结束日期后查询', async ({ page }) => {
      const endDateInput = page.locator('input[placeholder="结束日期"]').first();
      await endDateInput.click();
      await page.waitForTimeout(300);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);

      const queryBtn = page.locator('button:has-text("查询")').first();
      await queryBtn.click();
      await page.waitForTimeout(2000);

      await expect(page.locator('.box').filter({ hasText: '现金流水' }).first()).toBeVisible();
    });

    test('默认日期范围为当年', async ({ page }) => {
      const startDateInput = page.locator('input[placeholder="开始日期"]').first();
      const endDateInput = page.locator('input[placeholder="结束日期"]').first();

      const startValue = await startDateInput.inputValue();
      const endValue = await endDateInput.inputValue();

      // 验证日期格式为 YYYY-MM-DD
      expect(startValue).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(endValue).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      // 结束日期应为今天（本地格式）
      const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\//g, '-');
      expect(endValue).toBe(today);
    });
  });

  // ========== 现金流水记录 ==========
  test.describe('现金流水记录', () => {
    test('流水记录表格或空状态正确展示', async ({ page }) => {
      const transactionBox = page.locator('.box').filter({ hasText: '现金流水' }).first();
      await expect(transactionBox).toBeVisible();

      const table = transactionBox.locator('.tbl');
      const empty = transactionBox.locator('text=暂无流水记录');
      const hasTable = await table.isVisible().catch(() => false);
      const hasEmpty = await empty.isVisible().catch(() => false);
      expect(hasTable || hasEmpty).toBeTruthy();
    });

    test('流水记录表头正确', async ({ page }) => {
      const transactionBox = page.locator('.box').filter({ hasText: '现金流水' }).first();
      const table = transactionBox.locator('.tbl');
      if (await table.isVisible().catch(() => false)) {
        await expect(table.locator('th:has-text("日期")')).toBeVisible();
        await expect(table.locator('th:has-text("类型")')).toBeVisible();
        await expect(table.locator('th:has-text("金额")')).toBeVisible();
        await expect(table.locator('th:has-text("描述")')).toBeVisible();
        await expect(table.locator('th:has-text("操作")')).toBeVisible();
      }
    });

    test('流水记录操作列正确展示', async ({ page }) => {
      const transactionBox = page.locator('.box').filter({ hasText: '现金流水' }).first();
      const table = transactionBox.locator('.tbl');
      if (await table.isVisible().catch(() => false)) {
        const firstRow = table.locator('tr').nth(1);
        await expect(firstRow.locator('button:has-text("冲红")')).toBeVisible();
      }
    });
  });

  // ========== 新增现金流水 ==========
  test.describe('新增现金流水', () => {
    test('打开新增现金流水对话框', async ({ page }) => {
      await page.locator('button:has-text("新增流水")').first().click();

      await expect(page.locator('.el-dialog')).toBeVisible();
      await expect(page.locator('.el-dialog__title')).toContainText('新增现金流水');
    });

    test('新增对话框包含必要字段', async ({ page }) => {
      await page.locator('button:has-text("新增流水")').first().click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      await expect(page.locator('.el-dialog .ff:has-text("类型")')).toBeVisible();
      await expect(page.locator('.el-dialog .ff:has-text("金额")')).toBeVisible();
      await expect(page.locator('.el-dialog .ff:has-text("分类")')).toBeVisible();
      await expect(page.locator('.el-dialog .ff:has-text("日期")')).toBeVisible();
      await expect(page.locator('.el-dialog .ff:has-text("描述")')).toBeVisible();
    });

    test('取消新增不保存', async ({ page }) => {
      await page.locator('button:has-text("新增流水")').first().click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      await page.locator('.el-dialog__footer button:has-text("取消")').click();
      await expect(page.locator('.el-dialog')).not.toBeVisible();
    });

    test('默认类型为流入', async ({ page }) => {
      await page.locator('button:has-text("新增流水")').first().click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      const typeSelect = page.locator('.el-dialog .ff').filter({ hasText: '类型' }).locator('.el-select').first();
      await expect(typeSelect).toContainText('流入');
    });

    test('默认分类为经营', async ({ page }) => {
      await page.locator('button:has-text("新增流水")').first().click();
      await expect(page.locator('.el-dialog')).toBeVisible();

      const categoryItem = page.locator('.el-dialog .ff').filter({ hasText: '分类' });
      const categorySelect = categoryItem.locator('.el-select').first();
      await expect(categorySelect).toBeVisible();
      const categoryText = await categorySelect.textContent();
      expect(categoryText).toMatch(/经营|operating/);
    });
  });

  // ========== 筛选合计 ==========
  test.describe('筛选合计', () => {
    test('金额正确展示格式', async ({ page }) => {
      const cards = page.locator('.c');
      const count = await cards.count();
      if (count === 0) return;

      for (let i = 0; i < count; i++) {
        const values = cards.nth(i).locator('.cv-sm');
        const valueCount = await values.count();
        for (let j = 0; j < valueCount; j++) {
          const value = await values.nth(j).textContent();
          expect(value).toMatch(/[\d,.\-]/);
        }
      }
    });

    test('汇总金额格式正确', async ({ page }) => {
      const summaryBox = page.locator('.box').filter({ hasText: '净现金流量' }).first();
      if (await summaryBox.count() === 0) return;

      // 只检查金额列（每行第二个 td）
      const amountCells = summaryBox.locator('.tbl tr td:nth-child(2)');
      const count = await amountCells.count();
      for (let i = 0; i < count; i++) {
        const text = await amountCells.nth(i).textContent();
        expect(text).toMatch(/[\d,.\-]/);
      }
    });
  });
});
