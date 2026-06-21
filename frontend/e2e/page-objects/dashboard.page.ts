/**
 * DashboardPage — page object for the dashboard remote (mfe-dashboard, :4204).
 *
 * Covers both the authenticated dashboard (route `dashboard`) and the catalog
 * list surface it links to. Used by the onboarding flow (final assertion lands
 * here) and by catalog-creation (saved catalog appears in the list).
 *
 * Selectors are PROVISIONAL (see ShellPage note). Verify in the QA-wave E2E
 * exploration phase before flipping any flow off test.fixme.
 */
import type { Page, Locator } from '@playwright/test';

export class DashboardPage {
  constructor(private readonly page: Page) {}

  get heading(): Locator {
    return this.page.getByTestId('dashboard-heading');
  }

  /** The list of the seller's catalogs rendered on the dashboard. */
  get catalogList(): Locator {
    return this.page.getByTestId('catalog-list');
  }

  /** A single catalog card by its visible name. */
  catalogCardByName(name: string): Locator {
    return this.page.getByTestId('catalog-card').filter({ hasText: name });
  }

  async goto(): Promise<void> {
    await this.page.goto('/dashboard');
  }

  async gotoCatalogs(): Promise<void> {
    await this.page.goto('/catalogs');
  }
}
