import { defineConfig } from '@playwright/test'

if (!process.env.BROWSER_TEST_BASE_URL) {
  throw new Error('Use backend/scripts/test_frontend.py --browser (disposable databases required)')
}

export default defineConfig({
  testDir: './tests/browser',
  grep: process.env.BROWSER_TEST_GREP ? new RegExp(process.env.BROWSER_TEST_GREP) : undefined,
  timeout: 120000,
  expect: { timeout: 10000 },
  workers: 1,
  retries: 0,
  maxFailures: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.BROWSER_TEST_BASE_URL,
    browserName: 'chromium',
    channel: process.env.BROWSER_TEST_CHANNEL || undefined,
    headless: true,
    actionTimeout: 15000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  }
})
