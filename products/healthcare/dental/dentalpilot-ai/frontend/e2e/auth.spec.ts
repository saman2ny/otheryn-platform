import { expect, test } from '@playwright/test';

// These tests require a local backend on :8000 with seeded demo data.
// Demo credentials are local-only and must never be used in production.

const DEMO_EMAIL = 'owner@brightsmiledental.io';
const DEMO_PASSWORD = 'password123';

test('login page renders', async ({ page }) => {
  await page.goto('/auth/login');
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.locator('input[type="password"]')).toBeVisible();
});

test('invalid login shows an error', async ({ page }) => {
  await page.goto('/auth/login');
  await page.fill('input[type="email"]', 'nobody@example.com');
  await page.fill('input[type="password"]', 'wrong-password');
  await page.click('button[type="submit"]');
  await expect(page.getByText(/invalid|incorrect|failed/i)).toBeVisible();
});

test('valid login reaches the dashboard', async ({ page }) => {
  await page.goto('/auth/login');
  await page.fill('input[type="email"]', DEMO_EMAIL);
  await page.fill('input[type="password"]', DEMO_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard/);
  await expect(page.getByRole('link', { name: /Patients & CRM/i })).toBeVisible();
});