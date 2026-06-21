/**
 * ShellPage — page object for the host shell (:4200, or slot port via config).
 *
 * The shell owns routing, the topbar + sidebar, auth state, and the
 * loadRemoteWithFallback seam that mounts each remote. Every E2E flow starts by
 * navigating through the shell.
 *
 * Selectors are LIVE-VERIFIED (QA Wave 1) and recorded in
 * `.claude/agent-memory/meesell-e2e-test-writer/selector_registry.md`.
 */
import type { Page, Locator } from '@playwright/test';

export class ShellPage {
  constructor(private readonly page: Page) {}

  // ── Topbar ──
  /** Logout is a DIRECT button in the topbar (#381 moved it out of the popup menu). */
  get navLogout(): Locator {
    return this.page.getByTestId('nav-logout');
  }
  /** The user-menu trigger (opens the My-Profile popup). */
  get userMenuTrigger(): Locator {
    return this.page.getByTestId('user-menu-trigger');
  }

  // ── Sidebar nav items (desktop sidebar; <a routerLink>) ──
  get navHome(): Locator {
    return this.page.getByTestId('nav-home');
  }
  get navCatalogs(): Locator {
    return this.page.getByTestId('nav-catalogs');
  }
  get navNewProduct(): Locator {
    return this.page.getByTestId('nav-new-product');
  }
  get navCategories(): Locator {
    return this.page.getByTestId('nav-categories');
  }
  get navProfile(): Locator {
    return this.page.getByTestId('nav-profile');
  }
  get navPlans(): Locator {
    return this.page.getByTestId('nav-plans');
  }

  // ── Remote-load fallback (D12 RemoteFailureComponent) ──
  get remoteFailureFallback(): Locator {
    return this.page.getByTestId('remote-failure-fallback');
  }

  /** Go to the shell root (public landing). */
  async gotoRoot(): Promise<void> {
    await this.page.goto('/');
  }

  /** Go to an in-shell route by path (e.g. 'dashboard', 'catalogs/new'). */
  async gotoRoute(path: string): Promise<void> {
    await this.page.goto(`/${path.replace(/^\//, '')}`);
  }

  /** Log out via the topbar control (revokes the cookie + navigates to /login). */
  async logout(): Promise<void> {
    await this.navLogout.click();
  }
}
