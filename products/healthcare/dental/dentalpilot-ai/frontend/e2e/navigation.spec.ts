import { expect, test } from '@playwright/test';

// Requires a local backend on :8000 with seeded demo data.

test('sidebar is the single global navigation', async ({ page }) => {
  await page.goto('/dashboard');
  const sidebar = page.getByRole('navigation', { name: 'Primary navigation' });
  await expect(sidebar).toBeVisible();
  await expect(sidebar.getByRole('link', { name: /Patients & CRM/i })).toBeVisible();
  await expect(page.locator('.dp-workflow-tabs')).toHaveCount(0);
});

test('direct route and refresh work', async ({ page }) => {
  await page.goto('/dentalpilot-workflows?tab=journey');
  await expect(page.getByText(/Treatment/i).first()).toBeVisible();
  await page.reload();
  await expect(page.getByText(/Treatment/i).first()).toBeVisible();
});

test('no horizontal overflow on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/dashboard');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});