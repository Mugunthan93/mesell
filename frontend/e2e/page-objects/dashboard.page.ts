/**
 * DashboardPage — page object for the dashboard remote (mfe-dashboard).
 *
 * Used by onboarding (final assertion lands here), catalog-creation (a saved
 * product appears in the list), and logout-guard.
 *
 * Selectors are LIVE-VERIFIED (QA Wave 1) — see selector_registry.md.
 */
import type { Page, Locator } from '@playwright/test';

export class DashboardPage {
  constructor(private readonly page: Page) {}

  /** The dashboard page header (title "Home"). */
  get heading(): Locator {
    return this.page.getByTestId('dashboard-heading');
  }

  /** A product row in the dashboard list (one per product). */
  get productRows(): Locator {
    return this.page.getByTestId('dashboard-product-row');
  }

  /** The empty-state shown when the seller has no products yet. */
  get emptyState(): Locator {
    return this.page.getByTestId('dashboard-empty-state');
  }

  async goto(): Promise<void> {
    await this.page.goto('/dashboard');
  }

  async gotoCatalogs(): Promise<void> {
    await this.page.goto('/catalogs');
  }
}
