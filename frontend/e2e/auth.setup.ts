/**
 * auth.setup.ts — one-time pre-authentication for the E2E suite.
 *
 * Runs as the Playwright `setup` project (see playwright.config.ts). It performs
 * the phone-OTP flow ONCE and persists the resulting session to
 * `storageState.json`, which every authenticated flow then reuses via its project
 * `storageState`. This keeps each flow spec focused on its own behaviour instead
 * of re-driving login.
 *
 * Auth model (locked Decision #14 + FE-D5 amendment):
 *   - The access JWT is held IN MEMORY by the frontend (never localStorage).
 *   - The refresh token is an HttpOnly + Secure + SameSite=Strict cookie owned by
 *     the backend on the `/api/v1/auth` path.
 *   → Therefore storageState must capture the COOKIE (it cannot capture the
 *     in-memory access token). On reuse, the app silently refreshes from the
 *     cookie on first navigation. This is why we authenticate through the UI and
 *     save the post-login state, rather than poking a token into localStorage.
 *
 * Dev OTP bypass: the dev backend accepts the fixed OTP `000000`
 * (DEV_OTP_BYPASS_CODE). Never use a real OTP in CI.
 *
 * NOTE (bootstrap state): the selectors below are PROVISIONAL placeholders. The
 * QA wave's first E2E exploration phase (agent-browser) will confirm or replace
 * them and deposit the verified versions in
 * `.claude/agent-memory/meesell-e2e-test-writer/selector_registry.md`. Until
 * then this setup is marked fixme so a stub CI run does not fail on an
 * unverified selector.
 */
import { test as setup, expect } from '@playwright/test';
import { STORAGE_STATE } from './playwright.config';

// Dedicated E2E test identity. Override via env in CI to a provisioned dev seller.
const TEST_PHONE = process.env.MEESELL_E2E_PHONE ?? '+919999900000';
const DEV_OTP = process.env.MEESELL_E2E_OTP ?? '000000';

setup('authenticate via phone OTP and persist storageState', async ({ page }) => {
  // Bootstrap guard — remove once the selector_registry confirms the login DOM.
  setup.fixme(true, 'Selectors provisional — verify in QA-wave E2E exploration phase first.');

  // 1. Land on the login route (mfe-auth remote, public).
  await page.goto('/login');

  // 2. Enter the phone number and request an OTP.
  //    Provisional selectors — verify against the real mfe-auth LoginComponent DOM.
  await page.getByTestId('login-phone-input').fill(TEST_PHONE);
  await page.getByTestId('login-request-otp').click();

  // 3. Enter the dev-bypass OTP and verify. otp-verify is the only flow that
  //    WRITES the shared @mesell/core AuthService session across the boundary.
  await page.getByTestId('otp-input').fill(DEV_OTP);
  await page.getByTestId('otp-verify-submit').click();

  // 4. Assert we reached an authenticated surface (dashboard heading visible).
  await expect(page.getByTestId('dashboard-heading')).toBeVisible();

  // 5. Persist the session (captures the HttpOnly refresh cookie).
  await page.context().storageState({ path: STORAGE_STATE });
});
