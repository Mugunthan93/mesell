/**
 * Flow: Plan guard.
 *
 * Taxonomy (design §5.3): Locked feature on the free plan → upgrade prompt visible,
 * not a blank screen or a 404.
 *
 * The billing plans page (/billing/plans) is the upgrade surface: a free-plan seller
 * sees an upgrade CTA per upgradeable paid tier. We assert that surface renders
 * (the gating outcome) — explicitly NOT the remote-failure fallback.
 *
 * Pre-authenticated via the worker-scoped authed-context fixture (a fresh seller is
 * on the free plan).
 * Asserted VISIBLE outcome: an upgrade prompt is visible; the remote did not fall back.
 */
import { authedTest as test, expect } from '../fixtures/auth';
import { BillingPage } from '../page-objects/billing.page';
import { ShellPage } from '../page-objects/shell.page';

test.describe('Plan guard', () => {
  test('the free plan sees an upgrade prompt on the plans page (not blank / not a remote failure)', async ({ authedPage }) => {
    const billing = new BillingPage(authedPage);
    const shell = new ShellPage(authedPage);

    await billing.gotoPlans();

    // Visible outcome: at least one upgrade CTA is shown.
    await expect(billing.upgradePrompts.first()).toBeVisible();
    expect(await billing.upgradePrompts.count()).toBeGreaterThan(0);

    // And it is NOT a degraded remote-load fallback.
    await expect(shell.remoteFailureFallback).toHaveCount(0);
  });
});
