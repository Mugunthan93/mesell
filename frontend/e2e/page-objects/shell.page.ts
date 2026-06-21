/**
 * ShellPage — page object for the host shell (:4200).
 *
 * The shell owns routing, the navbar/sidebar, auth state, and the
 * loadRemoteWithFallback seam that mounts each remote. Every E2E flow starts by
 * navigating through the shell, so this is the entry page object the others build
 * on.
 *
 * Selectors are PROVISIONAL placeholders (the app currently ships zero
 * data-testid attributes). The QA-wave E2E exploration phase confirms/replaces
 * them via agent-browser and records the verified versions in
 * `.claude/agent-memory/meesell-e2e-test-writer/selector_registry.md`. Treat the
 * getters below as the contract the exploration phase must satisfy.
 */
import type { Page, Locator } from '@playwright/test';

export class ShellPage {
  constructor(private readonly page: Page) {}

  // ── Navigation (sidebar — 4-group IA: Home / Catalogs / Categories / Account) ──
  get navHome(): Locator {
    return this.page.getByTestId('nav-home');
  }
  get navCatalogs(): Locator {
    return this.page.getByTestId('nav-catalogs');
  }
  get navCategories(): Locator {
    return this.page.getByTestId('nav-categories');
  }
  get navAccount(): Locator {
    return this.page.getByTestId('nav-account');
  }
  get navLogout(): Locator {
    return this.page.getByTestId('nav-logout');
  }

  // ── Remote-load fallback (D12) — the RemoteFailureComponent surface ──
  get remoteFailureFallback(): Locator {
    return this.page.getByTestId('remote-failure-fallback');
  }

  /** Go to the shell root (public landing). */
  async gotoRoot(): Promise<void> {
    await this.page.goto('/');
  }

  /** Go to an in-shell route by path (e.g. 'dashboard', 'catalogs'). */
  async gotoRoute(path: string): Promise<void> {
    await this.page.goto(`/${path.replace(/^\//, '')}`);
  }

  /** Log out via the navbar control. */
  async logout(): Promise<void> {
    await this.navLogout.click();
  }
}
