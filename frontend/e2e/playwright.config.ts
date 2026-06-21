/**
 * Playwright configuration — MeeSell E2E suite.
 *
 * Built by the QA pillar bootstrap (feature/qa-wave-infra). This config is the
 * SINGLE source of truth for all base URLs and ports — no spec, page-object, or
 * setup file may hardcode a port. Read everything from the environment here.
 *
 * Port map (local dev federation stack — canonical, from
 * frontend/apps/shell/public/federation.manifest.json):
 *   shell          :4200   (host — every test navigates here first)
 *   mfe-pricing    :4201
 *   mfe-export     :4202
 *   mfe-onboarding :4203
 *   mfe-dashboard  :4204
 *   mfe-catalog    :4205
 *   mfe-auth       :4206
 *   mfe-billing    :4207
 *   backend (API)  :8000   (slot-0; the shell dev server reverse-proxies /api → here)
 *
 * Bring the full stack up with `/mesell:dev` (or `python3 tools/meesell_env.py
 * baseline up`) before running. Override any port via env (e.g. for a non-zero
 * slot N: shell = 4200 + N*10, mfe[i] = 4201 + N*10 + i, backend = 8000 + N*10).
 */
import { defineConfig, devices } from '@playwright/test';

// ── Port resolution (env-overridable, never hardcoded downstream) ──────────────
const SHELL_PORT = Number(process.env.MEESELL_SHELL_PORT ?? 4200);
const SHELL_BASE_URL = process.env.MEESELL_SHELL_URL ?? `http://localhost:${SHELL_PORT}`;

// Remote base URLs are exported for page objects / direct-remote smoke checks.
// All app traffic in a real run goes through the shell; these are for targeted
// remote-availability assertions only.
export const REMOTE_PORTS: Record<string, number> = {
  'mfe-pricing': Number(process.env.MEESELL_MFE_PRICING_PORT ?? 4201),
  'mfe-export': Number(process.env.MEESELL_MFE_EXPORT_PORT ?? 4202),
  'mfe-onboarding': Number(process.env.MEESELL_MFE_ONBOARDING_PORT ?? 4203),
  'mfe-dashboard': Number(process.env.MEESELL_MFE_DASHBOARD_PORT ?? 4204),
  'mfe-catalog': Number(process.env.MEESELL_MFE_CATALOG_PORT ?? 4205),
  'mfe-auth': Number(process.env.MEESELL_MFE_AUTH_PORT ?? 4206),
  'mfe-billing': Number(process.env.MEESELL_MFE_BILLING_PORT ?? 4207),
};

// Backend base URL — used by auth.setup.ts for the one-time OTP exchange and by
// flows that assert on a network response. The shell proxies /api → backend, so
// most tests do NOT need this directly.
export const BACKEND_BASE_URL =
  process.env.MEESELL_BACKEND_URL ?? `http://localhost:${process.env.MEESELL_BACKEND_PORT ?? 8000}`;

// Storage state produced by auth.setup.ts (pre-authenticated cookie/session).
export const STORAGE_STATE = process.env.MEESELL_STORAGE_STATE ?? './storageState.json';

export default defineConfig({
  testDir: '.',
  // Stubs are intentional during bootstrap; do not let a stray test.only slip into CI.
  forbidOnly: !!process.env.CI,
  fullyParallel: false, // federation stack is single-node dev; keep deterministic ordering
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  timeout: 60_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: SHELL_BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // The shell dev server already serves over HTTP on localhost; no TLS bypass needed.
  },

  projects: [
    // Setup project — drives the real phone-OTP login ONCE and writes
    // storageState.json (the login-proof artifact). NOTE: the authed FLOWS do NOT
    // reuse this storageState directly, because the MeeSell refresh token is
    // single-use with server-side rotation (Decision #14 / FE-D5): the shell's
    // APP_INITIALIZER bootstrap() refreshes on every page load and rotates the
    // cookie, so a shared storageState only authenticates the FIRST flow's first
    // navigation. The authed flows instead log in once per WORKER into a shared
    // browser context (fixtures/auth.ts — rotation-safe). See federation_quirks.md.
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    // Authenticated flows — each manages its own auth (worker-scoped authed-context
    // fixture, or a fresh OTP login for onboarding). No project-level storageState:
    // imposing the rotated cookie on the default page would 401 the 2nd+ flow.
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
      testMatch: /flows\/.*\.spec\.ts/,
    },
  ],
});
