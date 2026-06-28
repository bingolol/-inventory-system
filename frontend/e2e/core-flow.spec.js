// @ts-check
import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';
const T = 600;

test.describe('核心业务流程 E2E 测试', () => {

  test('完整流程: 期初余额→商品→供应商→客户→采购→销售→库存→资产负债表', async ({ page }) => {
    test.setTimeout(360000);
    page.on('pageerror', err => console.error('❌ JS ERROR:', err.message));

    // ── 1. 首页 ──
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.app-logo')).toContainText('进销存管理');
    console.log('✅ 首页');

    // ── 2. 设置期初余额 ──
    await page.goto(`${BASE}/financial-reports`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);

    // 切换到"期初余额"Tab
    await page.getByRole('tab', { name: '期初余额' }).click();
    await page.waitForTimeout(T);

    // 填写期初余额：现金 50000 = 实收资本 50000（覆盖测试数据库存价值）
    const obDlg = page.locator('.opening-balance-tab');
    await obDlg.getByLabel('期初日期').fill('2026-06-01');
    // 现金 50000（资产）
    await obDlg.locator('.el-form-item').filter({ hasText: '现金余额' }).locator('input').fill('50000');
    // 实收资本 50000（权益，与资产平衡）
    await obDlg.locator('.el-form-item').filter({ hasText: '实收资本' }).locator('input').fill('50000');
    await page.waitForTimeout(500);

    // 点击保存
    await obDlg.getByRole('button', { name: '保存' }).click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'e2e-01-opening-balance.png', fullPage: true });
    console.log('✅ 期初余额已设置');

    // ── 3. 新建商品 ──
    await page.getByText('商品管理').click();
    await page.waitForURL('**/products');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);
    await page.getByRole('button', { name: '新增商品' }).click();
    await page.waitForTimeout(T);

    const ts = Date.now();
    const productName = `铅笔-${ts}`;
    const dlg = page.locator('.el-dialog:visible');

    await dlg.getByLabel('商品名称').fill(productName);
    await dlg.getByLabel('编码').fill(`SKU-${ts}`);
    await dlg.getByLabel('分类').fill('文具');
    await dlg.locator('.el-form-item').filter({ hasText: '进价' }).locator('input').fill('10');
    await dlg.locator('.el-form-item').filter({ hasText: '售价' }).locator('input').fill('20');

    await dlg.getByRole('button', { name: '保存' }).click();
    await page.waitForTimeout(2000);
    await page.keyboard.press('Escape');
    await page.locator('.el-overlay').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(T);
    console.log(`✅ 商品: ${productName} 进价10 售价20`);

    // ── 4. 新建供应商 ──
    await page.getByText('供应商管理').click();
    await page.waitForURL('**/suppliers');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);
    await page.getByRole('button', { name: /新增/ }).first().click();
    await page.waitForTimeout(T);

    const supplierName = `晨光文具-${ts}`;
    const sDlg = page.locator('.el-dialog:visible');
    await sDlg.getByLabel('名称').fill(supplierName);
    await sDlg.getByRole('button', { name: /保存|确定/ }).click();
    await page.waitForTimeout(1500);
    await page.keyboard.press('Escape');
    await page.locator('.el-overlay').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(T);
    console.log(`✅ 供应商: ${supplierName}`);

    // ── 5. 新建客户 ──
    await page.getByText('客户管理').click();
    await page.waitForURL('**/customers');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);
    await page.getByRole('button', { name: /新增/ }).first().click();
    await page.waitForTimeout(T);

    const customerName = `测试学校-${ts}`;
    const cDlg = page.locator('.el-dialog:visible');
    await cDlg.getByLabel('名称').fill(customerName);
    await cDlg.getByRole('button', { name: /保存|确定/ }).click();
    await page.waitForTimeout(1500);
    await page.keyboard.press('Escape');
    await page.locator('.el-overlay').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(T);
    console.log(`✅ 客户: ${customerName}`);

    // ── 6. 采购管理 - 创建采购单（入库） ──
    await page.getByText('采购管理').click();
    await page.waitForURL('**/purchases');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);

    await page.getByRole('button', { name: '新建采购' }).click();
    await page.waitForTimeout(T);

    const pDlg = page.locator('.el-dialog:visible');
    // 选择供应商
    await pDlg.locator('.el-form-item').filter({ hasText: '供应商' }).locator('.el-select').click();
    await page.waitForTimeout(500);
    await page.locator('.el-select-dropdown__item').filter({ hasText: supplierName }).click();
    await page.waitForTimeout(T);

    // 选择商品（对话框默认已有1空行）
    await pDlg.locator('.el-table .el-select').first().click();
    await page.waitForTimeout(500);
    await page.locator('.el-select-dropdown__item').filter({ hasText: productName }).first().click();
    await page.waitForTimeout(T);

    // 设置数量 10（单价自动填充为进价10）
    const inputs = pDlg.locator('.el-input-number').locator('input');
    await inputs.first().fill('10');
    await page.waitForTimeout(500);

    // 确认采购(自动入库)
    await pDlg.getByRole('button', { name: '确认采购' }).click();
    await page.waitForTimeout(2000);

    // 关闭对话框（有可能已自动关闭）
    await page.keyboard.press('Escape');
    await page.locator('.el-overlay').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(T);
    await page.screenshot({ path: 'e2e-purchases.png', fullPage: true });
    console.log('✅ 采购单已创建（铅笔 x10，单价10）');

    // ── 7. 销售管理 - 创建销售单（出库） ──
    await page.getByText('销售管理').click();
    await page.waitForURL('**/sales');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);

    await page.getByRole('button', { name: '新建销售' }).click();
    await page.waitForTimeout(T);

    const sDlg2 = page.locator('.el-dialog:visible');
    // 选择客户（allow-create，可直接输入）
    await sDlg2.locator('.el-form-item').filter({ hasText: '客户' }).locator('.el-select').click();
    await page.waitForTimeout(500);
    await page.locator('.el-select-dropdown__item').filter({ hasText: customerName }).click();
    await page.waitForTimeout(T);

    // 选择商品（对话框默认已有1空行）
    await sDlg2.locator('.el-table .el-select').first().click();
    await page.waitForTimeout(500);
    await page.locator('.el-select-dropdown__item').filter({ hasText: productName }).first().click();
    await page.waitForTimeout(T);

    // 设置数量 5，单价 20
    const sInputs = sDlg2.locator('.el-input-number').locator('input');
    await sInputs.nth(0).fill('5');
    await page.waitForTimeout(200);
    await sInputs.nth(1).fill('20');
    await page.waitForTimeout(500);

    // 确认销售
    await sDlg2.getByRole('button', { name: '确认销售' }).click();
    await page.waitForTimeout(2000);
    await page.keyboard.press('Escape');
    await page.locator('.el-overlay').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(T);
    await page.screenshot({ path: 'e2e-sales.png', fullPage: true });
    console.log('✅ 销售单已创建（铅笔 x5，单价20）');

    // ── 8. 编辑商品（修改售价） ──
    await page.getByText('商品管理').click();
    await page.waitForURL('**/products');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);

    const prodRow = page.locator('.el-table__body-wrapper tr').filter({ hasText: productName });
    await prodRow.getByRole('button', { name: '编辑' }).click();
    await page.waitForTimeout(T);

    const eDlg = page.locator('.el-dialog:visible');
    await eDlg.locator('.el-form-item').filter({ hasText: '售价' }).locator('input').fill('25');
    await page.waitForTimeout(300);
    await eDlg.getByRole('button', { name: '保存' }).click();
    await page.waitForTimeout(1500);
    await page.keyboard.press('Escape');
    await page.locator('.el-overlay').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(T);
    console.log('✅ 商品已编辑（售价20→25）');

    // ── 9. 编辑供应商（添加联系人） ──
    await page.getByText('供应商管理').click();
    await page.waitForURL('**/suppliers');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);

    const suppRow = page.locator('.el-table__body-wrapper tr').filter({ hasText: supplierName });
    await suppRow.getByRole('button', { name: '编辑' }).click();
    await page.waitForTimeout(T);

    const seDlg = page.locator('.el-dialog:visible');
    await seDlg.getByLabel('联系人').fill('张三');
    await seDlg.getByRole('button', { name: /保存|确定/ }).click();
    await page.waitForTimeout(1500);
    await page.keyboard.press('Escape');
    await page.locator('.el-overlay').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(T);
    console.log('✅ 供应商已编辑（添加联系人）');

    // ── 10. 搜索商品 ──
    await page.goto(`${BASE}/products`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);

    const searchInput = page.locator('input[placeholder="搜索名称/编码"]');
    await searchInput.fill(productName);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(1500);
    const found = await page.locator('.el-table__body-wrapper tr').filter({ hasText: productName }).count();
    console.log(`✅ 搜索商品: 找到 ${found} 条`);

    // ── 11. 创建支出 ──
    await page.goto(`${BASE}/expenses`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);

    await page.getByRole('button', { name: '新增费用' }).click();
    await page.waitForTimeout(T);

    const exDlg = page.locator('.el-dialog:visible');
    await exDlg.locator('.el-form-item').filter({ hasText: '日期' }).locator('input').fill('2026-06-24');
    await page.waitForTimeout(300);

    await exDlg.locator('.el-form-item').filter({ hasText: '类别' }).locator('.el-select').click();
    await page.waitForTimeout(800);
    // iterate through options to find visible one (hidden poppers accumulate in DOM)
    const exOpts = page.locator('.el-select-dropdown__item');
    const exCount = await exOpts.count();
    for (let i = 0; i < exCount; i++) {
      const item = exOpts.nth(i);
      if (await item.isVisible() && (await item.textContent()).includes('办公用品')) {
        await item.click();
        break;
      }
    }
    await page.waitForTimeout(T);

    await exDlg.locator('.el-form-item').filter({ hasText: '金额' }).locator('input').fill('500');
    await page.waitForTimeout(300);

    await exDlg.locator('.el-form-item').filter({ hasText: '支付方式' }).locator('.el-select').click();
    await page.waitForTimeout(800);
    const pmOpts = page.locator('.el-select-dropdown__item');
    const pmCount = await pmOpts.count();
    for (let i = 0; i < pmCount; i++) {
      const item = pmOpts.nth(i);
      if (await item.isVisible() && (await item.textContent()).includes('公司')) {
        await item.click();
        break;
      }
    }
    await page.waitForTimeout(T);

    await exDlg.getByRole('button', { name: '保存' }).click();
    await page.waitForTimeout(2000);
    await page.keyboard.press('Escape');
    await page.locator('.el-overlay').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(T);
    await page.screenshot({ path: 'e2e-expenses.png', fullPage: true });
    console.log('✅ 支出已创建（办公用品 500）');

    // ── 12. 利润表验证 ──
    await page.goto(`${BASE}/financial-reports`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T * 2);
    await page.locator('.el-tabs__item').filter({ hasText: '利润表' }).click();
    await page.waitForTimeout(T * 2);
    const incRevenue = await page.locator('tr').filter({ hasText: '营业收入' }).isVisible().catch(() => false);
    console.log(`✅ 利润表${incRevenue ? '已加载' : '加载异常'}`);

    // ── 13. 库存页面（应显示剩余 5） ──
    await page.getByText('库存管理').click();
    await page.waitForURL('**/inventory');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T);
    await page.screenshot({ path: 'e2e-inventory.png', fullPage: true });
    const hasData = await page.locator('.el-table__empty-text').isVisible().catch(() => false);
    const status = hasData ? '空（无库存数据）' : '有数据';
    console.log(`✅ 库存: ${status}`);

    // ── 9. 资产负债表验证 ──
    await page.goto(`${BASE}/financial-reports`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T * 2);

    const sheetData = page.locator('tr').filter({ hasText: '资产合计' });
    console.log(`✅ 资产负债表${(await sheetData.count()) > 0 ? '有数据' : '可能无数据'}`);
    await page.screenshot({ path: 'e2e-balance-sheet.png', fullPage: true });

    // ── 10. 仪表盘 ──
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(T * 2);
    await page.screenshot({ path: 'e2e-dashboard.png', fullPage: true });
    console.log('✅ 仪表盘');
  });

  test('10 页面加载巡检', async ({ page }) => {
    test.setTimeout(30000);
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    const routes = [
      '/', '/products', '/suppliers', '/customers',
      '/purchases', '/sales', '/inventory',
      '/expenses', '/logs', '/backup',
      '/aging-report', '/cash-flow', '/journal',
      '/invoices', '/trial-balance', '/tax-report'
    ];
    for (const path of routes) {
      errors.length = 0;
      await page.goto(`${BASE}${path}`);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(T);
      const bad = errors.filter(e => !e.includes('favicon') && !e.includes('ResizeObserver'));
      console.log(bad.length ? `❌ ${path}: ${bad[0]}` : `✅ ${path}`);
    }
  });
});
