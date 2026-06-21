/**
 * auth.setup.ts — one-time login-proof for the E2E suite.
 *
 * Runs as the Playwright `setup` project. It drives the REAL phone-OTP login UI
 * (dev bypass `000000`), COMPLETES ONBOARDING (a fresh user lands on /onboarding,
 * not the dashboard), reaches the dashboard, and persists the resulting session to
 * `storageState.json`.
 *
 * Auth model (locked Decision #14 + FE-D5):
 *   - The access JWT is held IN MEMORY by the frontend (never localStorage).
 *   - The refresh token is an HttpOnly + SameSite cookie owned by the backend.
 *   → storageState captures the COOKIE (not the in-memory access token).
 *
 * IMPORTANT — why the authed FLOWS do NOT reuse this storageState:
 *   The refresh token is SINGLE-USE with server-side rotation. The shell's
 *   APP_INITIALIZER bootstrap() refreshes on every page load and rotates the
 *   cookie, so a shared storageState authenticates only the FIRST flow's first
 *   navigation; the next flow reusing the same saved cookie gets 401 → /login.
 *   (Verified live — see federation_quirks.md.) The authed flows therefore log in
 *   once per worker into a shared browser context (fixtures/auth.ts). This setup is
 *   kept as the canonical login proof + the storageState.json deliverable.
 *
 * Dev OTP bypass: the dev backend accepts the fixed OTP `000000` (DEV_OTP_BYPASS_CODE).
 */
import { test as setup, expect } from '@playwright/test';
import { STORAGE_STATE } from './playwright.config';
import { loginViaOtp } from './fixtures/auth';

setup('authenticate via phone OTP, complete onboarding, persist storageState', async ({ page }) => {
  // Drive login → OTP verify → onboarding → dashboard (shared helper).
  await loginViaOtp(page);

  // Visible proof: the authenticated dashboard heading is showing.
  await expect(page.getByTestId('dashboard-heading')).toBeVisible();

  // Persist the session (captures the HttpOnly refresh cookie) as the login-proof artifact.
  await page.context().storageState({ path: STORAGE_STATE });
});
