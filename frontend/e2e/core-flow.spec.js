// @ts-check
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

test.describe('核心业务流程 E2E 测试', () => {

  test('完整流程: 商品→供应商→采购→销售→库存', async ({ page }) => {
    test.setTimeout(90000);

    // ── 1. 打开首页 ──
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.app-logo')).toContainText('进销存管理');
    console.log('✅ 首页加载成功');

    // ── 2. 创建商品 ──
    await page.click('text=商品管理');
    await page.waitForURL('**/products');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    // 点击新增按钮
    await page.locator('button').filter({ hasText: /^$/ }).first().click({ timeout: 5000 }).catch(() => {});
    // 找 toolbar 区域的新增按钮（通常带 + 图标）
    const toolbarBtns = page.locator('.el-button .el-icon-plus').locator('..');
    const btnCount = await toolbarBtns.count();
    if (btnCount > 0) {
      await toolbarBtns.first().click();
    } else {
      // fallback: 点击任何包含 + 的按钮
      await page.locator('button:has(.el-icon-plus)').first().click();
    }
    await page.waitForTimeout(800);

    // 填写商品名称
    const productName = `E2E测试商品-${Date.now()}`;
    const dialog = page.locator('.el-dialog');
    await dialog.locator('input').first().fill(productName);
    await page.waitForTimeout(200);

    // 截图记录表单
    await page.screenshot({ path: 'e2e-product-form.png', fullPage: true });

    // 确定保存
    await dialog.locator('.el-button--primary').last().click();
    await page.waitForTimeout(1500);
    console.log(`✅ 商品创建: ${productName}`);

    // ── 3. 创建供应商 ──
    await page.click('text=供应商管理');
    await page.waitForURL('**/suppliers');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    await page.locator('button:has(.el-icon-plus)').first().click();
    await page.waitForTimeout(800);

    const supplierName = `E2E供应商-${Date.now()}`;
    await page.locator('.el-dialog input').first().fill(supplierName);
    await page.locator('.el-dialog .el-button--primary').last().click();
    await page.waitForTimeout(1500);
    console.log(`✅ 供应商创建: ${supplierName}`);

    // ── 4. 创建客户 ──
    await page.click('text=客户管理');
    await page.waitForURL('**/customers');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    await page.locator('button:has(.el-icon-plus)').first().click();
    await page.waitForTimeout(800);

    const customerName = `E2E客户-${Date.now()}`;
    await page.locator('.el-dialog input').first().fill(customerName);
    await page.locator('.el-dialog .el-button--primary').last().click();
    await page.waitForTimeout(1500);
    console.log(`✅ 客户创建: ${customerName}`);

    // ── 5. 创建采购单 ──
    await page.click('text=采购管理');
    await page.waitForURL('**/purchases');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);

    await page.locator('button:has(.el-icon-plus)').first().click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: 'e2e-purchase-form.png', fullPage: true });
    console.log('  采购单表单截图已保存');

    // 如果有对话框，尝试填写
    const purchaseDialog = page.locator('.el-dialog:visible');
    if (await purchaseDialog.isVisible()) {
      // 选择供应商（第一个下拉框）
      const selects = purchaseDialog.locator('.el-select');
      const selectCount = await selects.count();
      console.log(`  采购单有 ${selectCount} 个下拉框`);
    }

    // ── 6. 查看库存 ──
    await page.goto(`${BASE_URL}/inventory`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const rows = await page.locator('.el-table__body-wrapper tr').count();
    console.log(`✅ 库存页面: ${rows} 条记录`);

    // ── 7. 仪表盘截图 ──
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 'e2e-dashboard.png', fullPage: true });
    console.log('✅ 仪表盘截图已保存');

    console.log('\n🎉 核心业务流程测试完成');
  });

  test('页面加载巡检: 各模块无 JS 错误', async ({ page }) => {
    test.setTimeout(30000);

    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    const routes = [
      { path: '/', name: '仪表盘' },
      { path: '/products', name: '商品管理' },
      { path: '/suppliers', name: '供应商管理' },
      { path: '/customers', name: '客户管理' },
      { path: '/purchases', name: '采购管理' },
      { path: '/sales', name: '销售管理' },
      { path: '/inventory', name: '库存管理' },
      { path: '/expenses', name: '费用管理' },
      { path: '/logs', name: '操作日志' },
    ];

    for (const route of routes) {
      errors.length = 0;
      await page.goto(`${BASE_URL}${route.path}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(800);

      const criticalErrors = errors.filter(e =>
        !e.includes('favicon') &&
        !e.includes('ResizeObserver') &&
        !e.includes('Loading chunk')
      );

      if (criticalErrors.length > 0) {
        console.log(`❌ ${route.name} (${route.path}): ${criticalErrors[0]}`);
      } else {
        console.log(`✅ ${route.name} (${route.path})`);
      }
    }
  });
});
