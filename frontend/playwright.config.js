import { defineConfig } from '@playwright/test';
import { resolve } from 'path';

const authState = resolve('./tests/e2e/.auth/state.json');

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60000,
  retries: 0,
  globalSetup: resolve('./tests/e2e/global-setup.js'),
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    storageState: authState,
  },
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: true,
  },
});
