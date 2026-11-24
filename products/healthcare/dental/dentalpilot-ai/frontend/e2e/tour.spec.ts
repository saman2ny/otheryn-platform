import { expect, test } from '@playwright/test';

const OWNER = { email: 'owner@brightsmiledental.io', password: 'password123' };
const SUPER_ADMIN = { email: 'super-admin@dentalpilot.ai', password: 'password123' };

async function login(page, email: string, password: string) {
  await page.goto('/auth/login');
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard/);
}

test('Clinic Owner tour starts and can be skipped', async ({ page }) => {
  await login(page, OWNER.email, OWNER.password);
  await expect(page.locator('.shepherd-element')).toBeVisible({ timeout: 20000 });
  await expect(page.locator('.shepherd-button-primary')).toBeVisible({ timeout: 10000 });

  const skip = page.locator('.shepherd-button-secondary', { hasText: 'Skip tour' });
  if ((await skip.count()) > 0) {
    await skip.click();
  } else {
    await page.keyboard.press('Escape');
  }
  await page.waitForTimeout(600);

  const skipped = await page.evaluate(() =>
    Object.keys(localStorage).some(
      (key) => key.startsWith('dp_tour_') && key.endsWith('_skipped'),
    ),
  );
  expect(skipped).toBe(true);

  // Refresh: a skipped tour must not auto-start again.
  await page.reload();
  await page.waitForTimeout(3000);
  await expect(page.locator('.shepherd-element')).toHaveCount(0);
});

test('Super Admin tour starts and can be skipped', async ({ page }) => {
  await login(page, SUPER_ADMIN.email, SUPER_ADMIN.password);
  await expect(page.locator('.shepherd-element')).toBeVisible({ timeout: 20000 });

  const skip = page.locator('.shepherd-button-secondary');
  if ((await skip.count()) > 0) {
    await skip.click();
  } else {
    await page.keyboard.press('Escape');
  }

  await page.waitForTimeout(500);
  const skipped = await page.evaluate(() =>
    Object.keys(localStorage).some(
      (key) => key.startsWith('dp_tour_') && key.endsWith('_skipped'),
    ),
  );
  expect(skipped).toBe(true);
});