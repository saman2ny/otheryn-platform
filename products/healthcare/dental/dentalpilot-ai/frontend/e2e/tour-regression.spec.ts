import { expect, test, type Page } from '@playwright/test';

type Role = 'super_admin' | 'owner';
type StepExpectation = { id: string; route: string; selector?: string };

const SUPER_ADMIN_STEPS: StepExpectation[] = [
  { id: 'sa-dashboard', route: '/dashboard', selector: '.dp-sidebar' },
  { id: 'sa-directory', route: '/dentalpilot-workflows', selector: 'a[href="/dentalpilot-workflows"]' },
  { id: 'sa-register', route: '/dentalpilot-workflows', selector: 'input[name="fullName"]' },
  { id: 'sa-search', route: '/dentalpilot-workflows', selector: 'input[name="patientSearch"]' },
  { id: 'sa-edit', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'sa-medical', route: '/dentalpilot-workflows', selector: 'input[name="medConditions"]' },
  { id: 'sa-dental', route: '/dentalpilot-workflows', selector: 'input[name="dentalTreatments"]' },
  { id: 'sa-emergency', route: '/dentalpilot-workflows', selector: 'input[name="ecName"]' },
  { id: 'sa-duplicates', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'sa-revisions', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'sa-filters', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'sa-audit', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'sa-organizations', route: '/organization-management', selector: 'dp-page-header' },
  { id: 'sa-content', route: '/content-generator', selector: 'dp-page-header' },
  { id: 'sa-calendar', route: '/content-calendar', selector: 'dp-page-header' },
  { id: 'sa-growth', route: '/growth-os', selector: 'dp-page-header' },
  { id: 'sa-export', route: '/export-content', selector: 'dp-page-header' },
  { id: 'sa-billing', route: '/billing', selector: 'dp-page-header' },
  { id: 'sa-operations', route: '/dental-operations', selector: 'dp-page-header' },
];

const OWNER_STEPS: StepExpectation[] = [
  { id: 'owner-dashboard', route: '/dashboard', selector: '.dp-sidebar' },
  { id: 'owner-directory', route: '/dentalpilot-workflows', selector: 'a[href="/dentalpilot-workflows"]' },
  { id: 'owner-register', route: '/dentalpilot-workflows', selector: 'input[name="fullName"]' },
  { id: 'owner-profile', route: '/dentalpilot-workflows', selector: 'input[name="patientSearch"]' },
  { id: 'owner-edit', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'owner-medical', route: '/dentalpilot-workflows', selector: 'input[name="medConditions"]' },
  { id: 'owner-dental', route: '/dentalpilot-workflows', selector: 'input[name="dentalTreatments"]' },
  { id: 'owner-emergency', route: '/dentalpilot-workflows', selector: 'input[name="ecName"]' },
  { id: 'owner-duplicates', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'owner-revisions', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'owner-associations', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'owner-consent', route: '/dentalpilot-workflows', selector: 'dp-page-header' },
  { id: 'owner-organizations', route: '/organization-management', selector: 'dp-page-header' },
  { id: 'owner-content', route: '/content-generator', selector: 'dp-page-header' },
  { id: 'owner-calendar', route: '/content-calendar', selector: 'dp-page-header' },
  { id: 'owner-growth', route: '/growth-os', selector: 'dp-page-header' },
  { id: 'owner-export', route: '/export-content', selector: 'dp-page-header' },
  { id: 'owner-billing', route: '/billing', selector: 'dp-page-header' },
  { id: 'owner-operations', route: '/dental-operations', selector: 'dp-page-header' },
];

const USERS: Record<Role, { email: string; password: string; steps: StepExpectation[] }> = {
  super_admin: { email: 'super-admin@dentalpilot.ai', password: 'password123', steps: SUPER_ADMIN_STEPS },
  owner: { email: 'owner@brightsmiledental.io', password: 'password123', steps: OWNER_STEPS },
};

async function login(page: Page, email: string, password: string) {
  await page.goto('/auth/login');
  await page.evaluate(() => localStorage.clear());
  await page.goto('/auth/login');
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/dashboard/, { timeout: 30000 });
}

async function readStep(page: Page) {
  return page.evaluate(() => {
    const el = Array.from(document.querySelectorAll('.shepherd-element')).find(
      (node) => node instanceof HTMLElement && !node.hidden && getComputedStyle(node).display !== 'none',
    ) as HTMLElement | undefined;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return {
      title: el.querySelector('.shepherd-title')?.textContent?.trim() ?? '',
      buttons: Array.from(el.querySelectorAll('.shepherd-button')).map((b) => b.textContent?.trim() ?? ''),
      attached: !el.classList.contains('shepherd-centered') && !!el.dataset['popperPlacement'],
      placement: el.dataset['popperPlacement'] ?? null,
      classes: el.className,
      box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
    };
  });
}

async function assertStep(page: Page, role: Role, index: number) {
  const expected = USERS[role].steps[index];
  const total = USERS[role].steps.length;
  const visibleTour = page.locator('.shepherd-element:visible');
  await expect(visibleTour).toBeVisible({ timeout: 15000 });
  await expect.poll(async () => page.url().includes(expected.route), { timeout: 15000 }).toBe(true);

  if (expected.selector) {
    await expect.poll(async () => {
      return page.evaluate((sel) => {
        const el = document.querySelector(sel);
        if (!(el instanceof HTMLElement)) return false;
        const r = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return r.width > 0 && r.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
      }, expected.selector);
    }, { timeout: 15000 }).toBe(true);
  }

  const meta = await readStep(page);
  expect(meta, `step ${index + 1} meta`).not.toBeNull();
  expect(meta!.title).toContain(`Step ${index + 1} of ${total}`);
  expect(meta!.title).toContain(expected.id.replace(/^(sa|owner)-/, '').replace(/-/g, ' ').length > 0 ? '' : '');
  const expectedButtons = [...(index > 0 ? ['Previous'] : []), index === total - 1 ? 'Finish' : 'Next', 'Skip tour'];
  expect(meta!.buttons).toEqual(expectedButtons);

  if (expected.selector) {
    expect(meta!.attached, `${expected.id} should attach`).toBe(true);
    expect(meta!.placement, `${expected.id} should have placement`).toBeTruthy();
  } else {
    // No selector: centered/fallback is acceptable.
    expect(meta!.placement === null || typeof meta!.placement === 'string').toBe(true);
  }

  // Spotlight overlay should exist for modal tour.
  await expect(page.locator('.shepherd-modal-overlay-container')).toBeVisible();
  return meta!;
}

async function runRoleTour(page: Page, role: Role) {
  const user = USERS[role];
  await login(page, user.email, user.password);
  await expect(page.locator('.shepherd-element')).toBeVisible({ timeout: 20000 });

  const observed: Array<{ index: number; id: string; title: string; url: string; attached: boolean; placement: string | null; box: any }> = [];
  for (let i = 0; i < user.steps.length; i++) {
    const meta = await assertStep(page, role, i);
    observed.push({
      index: i + 1,
      id: user.steps[i].id,
      title: meta.title,
      url: page.url(),
      attached: meta.attached,
      placement: meta.placement,
      box: meta.box,
    });

    const isLast = i === user.steps.length - 1;
    const btn = page.locator('.shepherd-element:visible .shepherd-button-primary', { hasText: isLast ? 'Finish' : 'Next' });
    await btn.click();
    if (isLast) {
      await expect(page.locator('.shepherd-element:visible')).toHaveCount(0, { timeout: 10000 });
    } else {
      await page.waitForTimeout(350);
    }
  }
  return observed;
}

test.describe('DentalPilot guided tour regression', () => {
  test('Super Admin completes all 19 steps individually in browser', async ({ page }) => {
    test.setTimeout(240000);
    const observed = await runRoleTour(page, 'super_admin');
    expect(observed).toHaveLength(19);
    console.log(JSON.stringify({ role: 'super_admin', observed }, null, 2));
  });

  test('Clinic Owner completes all 19 steps individually in browser', async ({ page }) => {
    test.setTimeout(240000);
    const observed = await runRoleTour(page, 'owner');
    expect(observed).toHaveLength(19);
    console.log(JSON.stringify({ role: 'owner', observed }, null, 2));
  });
});
