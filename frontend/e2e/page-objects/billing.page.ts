/**
 * BillingPage — page object for the billing remote (mfe-billing).
 *
 * Route (mounted under the shell, authGuarded): billing/plans.
 * This is the plan-guard surface: a free-plan seller sees an upgrade CTA per
 * upgradeable paid tier (the locked-feature gating outcome, not a blank/404).
 *
 * Selectors LIVE-VERIFIED (QA Wave 1) — see selector_registry.md.
 */
import type { Page, Locator } from '@playwright/test';

export class BillingPage {
  constructor(private readonly page: Page) {}

  /** Upgrade CTA(s) on /billing/plans — one per upgradeable paid tier. */
  get upgradePrompts(): Locator {
    return this.page.getByTestId('upgrade-prompt');
  }

  async gotoPlans(): Promise<void> {
    await this.page.goto('/billing/plans');
  }
}
