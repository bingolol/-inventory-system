import { chromium } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const authDir = resolve(__dirname, '.auth');
const authFile = resolve(authDir, 'state.json');

export default async function globalSetup() {
  fs.mkdirSync(authDir, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  const loginRes = await page.request.post('http://localhost:8000/api/auth/login', {
    data: { username: 'admin', password: 'admin' }
  });

  if (!loginRes.ok()) {
    const body = await loginRes.text().catch(() => '');
    throw new Error(`Login failed: ${loginRes.status()} ${body}`);
  }

  const loginData = await loginRes.json();

  await page.goto('http://localhost:5173/login');
  await page.evaluate((data) => {
    localStorage.setItem('auth_access_token', data.access_token);
    localStorage.setItem('auth_refresh_token', data.refresh_token);
    localStorage.setItem('auth_username', data.username);
    localStorage.setItem('auth_account_id', String(data.account_id));
    localStorage.setItem('auth_expires_at', String(Date.now() + (data.expires_in || 7200) * 1000));
  }, loginData);

  await context.storageState({ path: authFile });
  await browser.close();

  process.env.PLAYWRIGHT_AUTH_STATE = authFile;
}
