/**
 * Flow: Plan guard.
 *
 * Taxonomy (design §5.3): Locked feature accessed on free plan → upgrade prompt
 * visible, not a blank screen or 404.
 *
 * STUB — fleshed out by the QA wave. Pre-authenticated via storageState as a
 * free-plan seller. The exploration phase must pin the upgrade-prompt surface and
 * confirm which V1 feature is plan-gated on the free tier.
 */
import { test, expect } from '@playwright/test';
import { ShellPage } from '../page-objects/shell.page';

// A route gated behind a paid plan on the free tier (confirm exact route in exploration phase).
const PLAN_GATED_ROUTE = process.env.MEESELL_E2E_GATED_ROUTE ?? 'catalogs/live';

test.describe('Plan guard', () => {
  test.fixme('accessing a locked feature on the free plan shows an upgrade prompt (not blank / not 404)', async ({ page }) => {
    const shell = new ShellPage(page);

    await shell.gotoRoute(PLAN_GATED_ROUTE);

    // Asserted outcome: an upgrade prompt is visible — explicitly NOT a blank screen or a 404.
    await expect(page.getByTestId('upgrade-prompt')).toBeVisible();
    await expect(page.getByTestId('not-found')).toHaveCount(0);
  });
});
