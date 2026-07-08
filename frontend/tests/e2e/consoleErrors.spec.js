import { test, expect } from '@playwright/test';

const routes = [
  '/dashboard',
  '/accounting-guide',
  '/invoices',
  '/funds/transactions',
  '/finance/financial-reports',
  '/finance/tax-report',
  '/finance/cashflow',
  '/finance/reconciliations',
  '/inventory',
  '/products',
  '/purchases',
  '/sales',
  '/customers',
  '/suppliers',
  '/expenses',
  '/personal',
  '/reports',
  '/finance/fixed-assets',
  '/settings/accounts',
  '/settings/backups',
  '/settings/logs',
];

for (const route of routes) {
  test(`console errors on ${route}`, async ({ page }) => {
    const errors = [];
    const warnings = [];

    page.on('console', msg => {
      const text = msg.text();
      if (msg.type() === 'error') errors.push(text);
      // Capture Vue prop warnings and similar runtime warnings
      if (msg.type() === 'warning' || (text.includes('Vue warn') || text.includes('Invalid prop') || text.includes('Failed prop'))) {
        warnings.push(text);
      }
    });
    page.on('pageerror', err => errors.push(err.message));

    await page.goto(route);
    await page.waitForTimeout(1500);

    // Wait for some content to ensure page rendered
    await page.waitForSelector('body', { timeout: 10000 });

    if (errors.length) console.error(`Errors on ${route}:`, errors);
    if (warnings.length) console.warn(`Warnings on ${route}:`, warnings);

    expect(errors).toEqual([]);
    expect(warnings).toEqual([]);
  });
}
