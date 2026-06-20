/**
 * route-check.mjs — 12-route federation render harness (shell-driven, auth-mocked).
 *
 * WHAT IT PROVES:
 *   Drives every shell route via the host on :4200 (where the federation importmap lives)
 *   and asserts each route renders CLEANLY through Native Federation — no
 *   RemoteFailureComponent, no uncaught exceptions, no failed/4xx-5xx network, a non-empty
 *   outlet render, and (for protected routes) that the auth mock unlocked them instead of
 *   bouncing to /login. This is the harness that produced the verified all-clean result
 *   against the static-served dev builds (see tools/dev/STATIC_DEV.md).
 *
 * AUTH MOCK:
 *   The backend is intentionally NOT required. We mock /api/v1/auth/refresh + /api/v1/auth/me
 *   so the APP_INITIALIZER authenticates and the authGuard lets protected routes render. A
 *   catch-all "api" glob returns benign empty list-shapes so component data-loads add no noise.
 *   This isolates the FRONTEND federation path from backend availability.
 *
 * DEV-BUILD NOISE FILTER:
 *   When a `--configuration development` build is served STATICALLY (serve.js, no live-reload
 *   server behind it), its embedded live-reload client emits repeated console errors:
 *     EventSource's response has a MIME type ("text/html") that is not "text/event-stream".
 *   This is a BENIGN artifact of static-serving a dev build — it does not exist in a prod
 *   build and does not affect rendering. We filter it (plus Angular dev-mode chatter) so it
 *   does not mask real errors.
 *
 * Usage (run from frontend/ so `playwright` resolves from node_modules):
 *   node tools/dev/route-check.mjs            # chromium (default)
 *   node tools/dev/route-check.mjs webkit     # webkit
 *   pnpm run dev:check-routes                  # preferred (package.json)
 *
 * Prerequisite: the 8 static servers must be up (pnpm run dev:serve-static).
 *
 * Exit codes:
 *   0 — all 12 routes clean
 *   1 — at least one route had an issue
 *   2 — harness crashed (e.g. playwright not installed)
 *
 * Dependencies: `playwright` (already in devDependencies). No other npm packages.
 */

import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { writeFileSync } from 'node:fs';
import process from 'node:process';

// ─── ANSI colour codes ───────────────────────────────────────────────────────

const RESET = '\x1b[0m';
const BOLD  = '\x1b[1m';
const DIM   = '\x1b[2m';
const RED   = '\x1b[31m';
const GREEN = '\x1b[32m';

// ─── Playwright (resolved from node_modules — run from frontend/) ─────────────

let pw;
try {
  pw = await import('playwright');
} catch (err) {
  console.error(`${RED}route-check: could not import 'playwright'.${RESET}`);
  console.error(`${DIM}  It is in devDependencies. Run this from frontend/ with node_modules present:${RESET}`);
  console.error(`${DIM}    cd frontend && pnpm install && pnpm exec playwright install chromium${RESET}`);
  console.error(`${DIM}  Original error: ${err.message}${RESET}`);
  process.exit(2);
}
const { chromium, webkit } = pw;

const ENGINE = process.argv[2] === 'webkit' ? 'webkit' : 'chromium';
const launcher = ENGINE === 'webkit' ? webkit : chromium;
const SHELL = 'http://localhost:4200';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const FRONTEND_DIR = resolve(__dirname, '..', '..');
const REPORT_PATH = join(FRONTEND_DIR, 'tools', 'dev', `route-check-report-${ENGINE}.json`);

// ─── The 12 shell routes (matches RUNBOOK §4 + harness2 source of truth) ──────

const TARGETS = [
  { label: '/ (landing <- mfe-dashboard)',         path: '/' },
  { label: '/login (<- mfe-auth)',                 path: '/login' },
  { label: '/signup (<- mfe-auth)',                path: '/signup' },
  { label: '/otp-verify (<- mfe-auth)',            path: '/otp-verify' },
  { label: '/dashboard (<- mfe-dashboard)',        path: '/dashboard',          protected: true },
  { label: '/catalogs (<- mfe-catalog)',           path: '/catalogs',           protected: true },
  { label: '/catalogs/new (smart-picker)',         path: '/catalogs/new',       protected: true },
  { label: '/profile (<- mfe-onboarding)',         path: '/profile',            protected: true },
  { label: '/onboarding (<- mfe-onboarding)',      path: '/onboarding',         protected: true },
  { label: '/catalogs/1/pricing (<- mfe-pricing)', path: '/catalogs/1/pricing', protected: true },
  { label: '/catalogs/1/export (<- mfe-export)',   path: '/catalogs/1/export',  protected: true },
  { label: '/billing/plans (<- mfe-billing)',      path: '/billing/plans',      protected: true },
];

// ─── Console-noise filter ─────────────────────────────────────────────────────

const IGNORE_CONSOLE = [
  /Angular is running in development mode/i,
  /\[vite\]/i,
  /Download the Angular DevTools/i,
  /Failed to load resource: the server responded with a status of 401/i, // mocked-away anyway
  // Dev-build live-reload client (EventSource) has no server when the DEV bundle is served
  // STATICALLY (serve.js returns index.html for the live-reload path). Benign artifact —
  // absent in prod builds, no effect on rendering. Filtered so it can't mask real errors.
  /EventSource'?s response has a MIME type/i,
  /text\/event-stream/i,
];
const ignored = (t) => IGNORE_CONSOLE.some((re) => re.test(t));

const NOW = '2026-06-14T00:00:00Z';

async function installApiMocks(ctx) {
  // auth/refresh -> valid token so bootstrap() authenticates.
  await ctx.route('**/api/v1/auth/refresh', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: 'harness-token', expires_in: 3600 }),
    }));
  // auth/me -> a user so the authGuard passes.
  await ctx.route('**/api/v1/auth/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: '00000000-0000-0000-0000-000000000001',
        phone: '+919999999999',
        plan: 'free',
        created_at: NOW,
        last_login_at: NOW,
      }),
    }));
  // Catch-all /api -> benign 200 carrying every common list key empty, so a component reading
  // res.products / res.data / res.catalogs / res.items / res.skus / res.exports all get [].
  await ctx.route('**/api/**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        products: [], data: [], catalogs: [], items: [], skus: [], exports: [],
        results: [], total: 0, page: 1, limit: 20,
      }),
    }));
}

async function checkRoute(browser, t) {
  const ctx = await browser.newContext();
  await installApiMocks(ctx);
  const page = await ctx.newPage();

  const consoleErrors = [], pageErrors = [], netFailures = [], badResponses = [];

  page.on('console', (m) => {
    if (m.type() === 'error' && !ignored(m.text())) consoleErrors.push(m.text());
  });
  page.on('pageerror', (e) => pageErrors.push(e.message || String(e)));
  page.on('requestfailed', (r) => {
    const f = r.failure();
    if (f && /aborted/i.test(f.errorText)) return; // navigation aborts are not failures
    netFailures.push(`${r.method()} ${r.url()} — ${f ? f.errorText : 'failed'}`);
  });
  page.on('response', (resp) => {
    const s = resp.status();
    if (s >= 400) badResponses.push(`${s} ${resp.request().method()} ${resp.url()}`);
  });

  let navError = null;
  try {
    // domcontentloaded (NOT networkidle): ng/dev servers hold sockets open => networkidle never fires.
    await page.goto(`${SHELL}${t.path}`, { waitUntil: 'domcontentloaded', timeout: 20_000 });
  } catch (e) {
    navError = e.message;
  }
  // Settle: federation chunk fetch + APP_INITIALIZER refresh + router render.
  await page.waitForTimeout(3500);

  let finalUrl = '', bodyText = '', mainLen = 0;
  try {
    finalUrl = page.url();
    bodyText = (await page.locator('body').innerText().catch(() => '')).trim();
    mainLen = await page
      .evaluate(() => {
        const main = document.querySelector('router-outlet')?.parentElement || document.body;
        return main.innerText.trim().length;
      })
      .catch(() => 0);
  } catch {
    /* ignore */
  }

  const remoteFailed =
    /unavailable|failed to load|couldn.?t load|try again|something went wrong/i.test(bodyText) &&
    bodyText.length < 400;
  const redirectedToLogin = t.protected && /\/login(\?|$)/.test(finalUrl);

  const issues = [];
  if (navError) issues.push(`NAV ERROR: ${navError}`);
  if (consoleErrors.length) issues.push(`${consoleErrors.length} console error(s)`);
  if (pageErrors.length) issues.push(`${pageErrors.length} uncaught exception(s)`);
  if (netFailures.length) issues.push(`${netFailures.length} network failure(s)`);
  if (badResponses.length) issues.push(`${badResponses.length} 4xx/5xx response(s)`);
  if (remoteFailed) issues.push('RemoteFailureComponent fallback rendered');
  if (redirectedToLogin) issues.push('redirected to /login (auth mock did not unlock)');
  if (!navError && mainLen < 5) issues.push(`empty render (${mainLen} chars in outlet)`);

  const rec = {
    label: t.label,
    path: t.path,
    finalUrl,
    ok: issues.length === 0,
    issues,
    consoleErrors,
    pageErrors,
    netFailures,
    badResponses,
    remoteFailed,
    mainLen,
    bodyPreview: bodyText.slice(0, 160).replace(/\s+/g, ' '),
  };

  console.log(
    `[${rec.ok ? GREEN + 'PASS' + RESET : RED + 'FAIL' + RESET}] ${t.label}  ` +
      `${DIM}(render=${mainLen} chars, url=${finalUrl.replace(SHELL, '') || '/'})${RESET}`,
  );
  for (const i of issues) console.log(`        ${RED}- ${i}${RESET}`);
  for (const e of consoleErrors.slice(0, 8)) console.log(`        ! console: ${e.slice(0, 260)}`);
  for (const e of pageErrors.slice(0, 8)) console.log(`        ! throw:   ${e.slice(0, 260)}`);
  for (const e of netFailures.slice(0, 8)) console.log(`        ! net:     ${e.slice(0, 260)}`);
  for (const e of badResponses.slice(0, 8)) console.log(`        ! http:    ${e.slice(0, 260)}`);
  if (rec.ok) console.log(`        ${DIM}> preview: ${rec.bodyPreview}${RESET}`);

  await ctx.close();
  return rec;
}

async function run() {
  console.log(`\n${BOLD}MeeSell — federation route-check (${ENGINE}, shell=${SHELL})${RESET}\n`);
  const browser = await launcher.launch();
  const results = [];
  for (const t of TARGETS) results.push(await checkRoute(browser, t));
  await browser.close();

  const pass = results.filter((r) => r.ok).length;
  const allClean = pass === results.length;
  console.log(
    `\n${BOLD}==== ${ENGINE}: ${allClean ? GREEN : RED}${pass}/${results.length}${RESET}${BOLD} ` +
      `shell routes clean ====${RESET}`,
  );

  writeFileSync(REPORT_PATH, JSON.stringify({ engine: ENGINE, pass, total: results.length, results }, null, 2));
  console.log(`${DIM}report: ${REPORT_PATH}${RESET}\n`);

  process.exit(allClean ? 0 : 1);
}

run().catch((e) => {
  console.error(`${RED}HARNESS CRASH:${RESET}`, e);
  process.exit(2);
});
