/**
 * boot-smoke.js — Hardened browser-boot smoke gate for MeeSell federated Angular workspace.
 *
 * Catches the F-001 class: build-green / browser-dead from a native-federation
 * import-map subpath miss (or any other bootstrap failure mode that ng-build silently passes).
 *
 * FALSE-PASS prevention (round-1 anatomy + fixes applied here):
 *   Old harness:  python -m http.server → 404 on /login, /profile (no SPA fallback)
 *                 body.length > 0 passed trivially on Python's "Error code: 404" body
 *                 Angular never booted — specifier errors never fired
 *
 *   This harness:
 *   (a) HTTP-200 document assertion — captured via page.on('response') on the top-level
 *       document request. A non-200 document is an IMMEDIATE FAIL (no more 404-body pass).
 *   (b) Real component selectors per route — NOT generic input/button queries.
 *       NoRemoteFailureComponent — if the remotes are up (CI serves them all), a fallback
 *       render is a FAIL (means the remote load failed anyway).
 *   (c) ZERO "Unable to resolve specifier" console messages. Also logs broader set:
 *       "Failed to fetch dynamically imported module", NG0*, bootstrap errors.
 *   (d) page.on('pageerror') — FAIL on any uncaught JS exception or unhandled rejection.
 *       F-001's second symptom (after specifier error) was an unhandled rejection that
 *       the old harness never caught.
 *
 * Routes × widths tested:
 *   /        @ 360px + 1280px  → expects app-landing (mfe-dashboard)
 *   /login   @ 360px + 1280px  → expects mee-login + <form> + mee-input
 *   /profile @ 360px + 1280px  → authGuard redirects unauthenticated → /login + mee-login
 *
 * Environment variables (all optional; defaults work in CI):
 *   SMOKE_SHELL_URL      base URL for the shell (default http://localhost:4200)
 *   SMOKE_SCREENSHOT_DIR directory for screenshots (default <__dirname>/screenshots)
 *   SMOKE_RESULTS_FILE   path for JSON results (default <__dirname>/smoke-results.json)
 *
 * Exit codes:
 *   0 — ALL assertions passed
 *   1 — at least one assertion failed
 */

'use strict';

const { chromium } = require('playwright');
const fs   = require('fs');
const path = require('path');

// ─── configuration ────────────────────────────────────────────────────────────

const SHELL_URL        = process.env.SMOKE_SHELL_URL      || 'http://localhost:4200';
const SCREENSHOT_DIR   = process.env.SMOKE_SCREENSHOT_DIR || path.join(__dirname, 'screenshots');
const RESULTS_FILE     = process.env.SMOKE_RESULTS_FILE   || path.join(__dirname, 'smoke-results.json');

const ROUTES = ['/', '/login', '/profile'];
const WIDTHS = [360, 1280];

// Settle sequence timeout (ms).  Used for the per-route real-selector wait.
const SELECTOR_TIMEOUT = 15000;

// Console patterns that indicate a bootstrap/federation failure.
const HARD_ERROR_PATTERNS = [
  'Unable to resolve specifier',
  'Failed to fetch dynamically imported module',
];
const SOFT_ERROR_PATTERNS = [
  /^NG0/,          // Angular runtime errors
  /bootstrap/i,    // bootstrap errors
];

// ─── helpers ──────────────────────────────────────────────────────────────────

function mkdirp(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function routeLabel(route) {
  return route === '/' ? 'root' : route.replace(/\//g, '');
}

// ─── per-route assertions ─────────────────────────────────────────────────────

/**
 * Assert the real selector mounted for a given route.
 * Returns { ok: boolean, detail: string }.
 *
 * Contract (per SPEC):
 *   /        → app-landing (mfe-dashboard)
 *   /login   → mee-login + <form> + mee-input   (mfe-auth LoginComponent)
 *   /profile → authGuard → redirect to /login  → assert URL ends /login AND mee-login mounted
 *
 * RemoteFailureComponent anchor: cloud_off icon OR app-remote-failure in DOM = FAIL
 * (servers are running in CI; a fallback render means the remote load itself failed).
 */
async function assertRealSelector(page, route, bodyHTML) {
  // Check for RemoteFailureComponent first — it's a universal FAIL signal.
  const hasRemoteFailure = bodyHTML.includes('cloud_off') ||
    bodyHTML.includes('remote-failure') ||
    await page.$('app-remote-failure') !== null;

  if (hasRemoteFailure) {
    return {
      ok: false,
      detail: 'RemoteFailureComponent detected — remote failed to load (cloud_off / app-remote-failure in DOM)',
    };
  }

  if (route === '/') {
    // / → mfe-dashboard LandingComponent (selector: app-landing)
    try {
      await page.waitForSelector('app-landing', { timeout: SELECTOR_TIMEOUT });
      const el = await page.$('app-landing');
      const nonEmpty = el ? (await el.evaluate(n => n.textContent.trim().length)) > 0 : false;
      return {
        ok: !!el && nonEmpty,
        detail: `app-landing found=${!!el} non-empty=${nonEmpty}`,
      };
    } catch (e) {
      return { ok: false, detail: `app-landing timeout: ${e.message.split('\n')[0]}` };
    }
  }

  if (route === '/login') {
    // /login → mfe-auth LoginComponent (selector: mee-login), must have <form> + mee-input
    try {
      await page.waitForSelector('mee-login', { timeout: SELECTOR_TIMEOUT });
      const hasMeeLogin   = await page.$('mee-login') !== null;
      const hasForm       = await page.$('mee-login form') !== null;
      const hasMeeInput   = await page.$('mee-input') !== null;
      const ok = hasMeeLogin && hasForm && hasMeeInput;
      return {
        ok,
        detail: `mee-login=${hasMeeLogin} form=${hasForm} mee-input=${hasMeeInput}`,
      };
    } catch (e) {
      return { ok: false, detail: `mee-login timeout: ${e.message.split('\n')[0]}` };
    }
  }

  if (route === '/profile') {
    // /profile → authGuard (no session) → redirect to /login → mee-login must be mounted
    // Prove: (1) URL ended up at /login, (2) mee-login selector present
    const currentUrl = page.url();
    const redirectedToLogin = currentUrl.includes('/login');
    if (!redirectedToLogin) {
      return {
        ok: false,
        detail: `authGuard did NOT redirect — still at ${currentUrl} (expected /login)`,
      };
    }
    try {
      await page.waitForSelector('mee-login', { timeout: SELECTOR_TIMEOUT });
      const hasMeeLogin = await page.$('mee-login') !== null;
      return {
        ok: hasMeeLogin && redirectedToLogin,
        detail: `redirected=${redirectedToLogin} finalUrl=${currentUrl} mee-login=${hasMeeLogin}`,
      };
    } catch (e) {
      return { ok: false, detail: `mee-login (after /profile redirect) timeout: ${e.message.split('\n')[0]}` };
    }
  }

  return { ok: false, detail: `unknown route: ${route}` };
}

// ─── main ─────────────────────────────────────────────────────────────────────

async function runSmoke() {
  mkdirp(SCREENSHOT_DIR);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  const allResults = [];
  let anyFailed = false;

  for (const route of ROUTES) {
    for (const width of WIDTHS) {
      const label = `${route} @ ${width}px`;
      console.log(`\n=== ${label} ===`);

      // Fresh context per route × width — no cookie/storage bleed between runs.
      const context = await browser.newContext({
        viewport: { width, height: 900 },
        ignoreHTTPSErrors: false,
      });
      const page = await context.newPage();

      // ── (c) console message collection ────────────────────────────────────
      const hardConsoleErrors  = [];   // specifier / dynamic-import failures
      const softConsoleErrors  = [];   // NG0*, bootstrap (logged, not auto-failed)

      page.on('console', (msg) => {
        const text = msg.text();
        for (const pat of HARD_ERROR_PATTERNS) {
          if (text.includes(pat)) {
            hardConsoleErrors.push(text);
            return;
          }
        }
        for (const pat of SOFT_ERROR_PATTERNS) {
          if (pat instanceof RegExp ? pat.test(text) : text.includes(pat)) {
            softConsoleErrors.push(text);
            return;
          }
        }
      });

      // ── (d) page error collection ─────────────────────────────────────────
      const pageErrors = [];
      page.on('pageerror', (err) => {
        pageErrors.push(err.message);
      });

      // ── (a) document HTTP status capture ─────────────────────────────────
      let documentStatus = null;
      let documentUrl    = null;
      page.on('response', (resp) => {
        // Only capture the top-level document response (not sub-resources).
        // The first response whose URL matches the navigation URL is the document.
        if (documentStatus === null) {
          const respUrl = resp.url();
          // Accept the shell URL or any redirect destination that is an HTML document.
          if (respUrl.startsWith('http://localhost:4200') ||
              respUrl.startsWith(SHELL_URL)) {
            documentStatus = resp.status();
            documentUrl    = respUrl;
          }
        }
      });

      const fullUrl = SHELL_URL + route;
      let gotoError = null;

      try {
        await page.goto(fullUrl, { waitUntil: 'load', timeout: 30000 });
      } catch (e) {
        gotoError = e.message.split('\n')[0];
        console.log(`  WARN: goto error (will still check DOM): ${gotoError}`);
      }

      // Wait for app-root children to appear — proves Angular bootstrapped at minimum.
      try {
        await page.waitForSelector('app-root *', { timeout: SELECTOR_TIMEOUT });
      } catch (e) {
        console.log(`  WARN: app-root children did not appear: ${e.message.split('\n')[0]}`);
      }

      // ── body / app-root state ─────────────────────────────────────────────
      const bodyHTML  = await page.evaluate(() => document.body.innerHTML);
      const bodyText  = await page.evaluate(() => document.body.innerText.trim());
      const hasAppRoot = await page.$('app-root') !== null;

      // ── assertion (a): HTTP 200 document ─────────────────────────────────
      // documentStatus may be null if the response listener didn't fire (offline).
      // Treat null as 0 (fail).
      const docStatusOk = documentStatus === 200;
      const is404Body = bodyHTML.includes('Error code: 404') ||
                        bodyHTML.includes('File not found') ||
                        bodyHTML.includes('Cannot GET') ||
                        bodyHTML.includes('HTTPStatus.NOT_FOUND');

      // ── assertion (b): real selector + no RemoteFailureComponent ─────────
      const selectorResult = await assertRealSelector(page, route, bodyHTML);

      // ── assertion (c): zero hard console errors ───────────────────────────
      const zeroHardConsoleErrors = hardConsoleErrors.length === 0;

      // ── assertion (d): zero page errors ──────────────────────────────────
      const zeroPageErrors = pageErrors.length === 0;

      // ── screenshot ────────────────────────────────────────────────────────
      const screenshotName = `boot-smoke-${routeLabel(route)}-${width}px.png`;
      const screenshotPath = path.join(SCREENSHOT_DIR, screenshotName);
      try {
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`  Screenshot: ${screenshotPath}`);
      } catch (e) {
        console.log(`  WARN: screenshot failed: ${e.message}`);
      }

      // ── pass/fail ─────────────────────────────────────────────────────────
      const passed = docStatusOk &&
                     !is404Body &&
                     hasAppRoot &&
                     selectorResult.ok &&
                     zeroHardConsoleErrors &&
                     zeroPageErrors;

      if (!passed) anyFailed = true;

      const result = {
        route,
        width,
        passed,
        assertions: {
          docStatus200:        docStatusOk,
          not404Body:          !is404Body,
          hasAppRoot,
          realSelectorMounted: selectorResult.ok,
          zeroHardConsoleErrors,
          zeroPageErrors,
        },
        detail: {
          documentStatus,
          documentUrl,
          selectorDetail: selectorResult.detail,
          hardConsoleErrors,
          softConsoleErrors,
          pageErrors,
          bodyTextLength: bodyText.length,
          gotoError,
        },
        screenshotPath,
      };
      allResults.push(result);

      // Console summary for this check.
      const statusIcon = passed ? 'PASS' : 'FAIL';
      console.log(`  ${statusIcon} | docStatus=${documentStatus} hasAppRoot=${hasAppRoot}`);
      console.log(`       selectorOk=${selectorResult.ok} detail="${selectorResult.detail}"`);
      console.log(`       hardConsoleErrors=${hardConsoleErrors.length} pageErrors=${pageErrors.length} is404=${is404Body}`);
      if (hardConsoleErrors.length > 0) {
        console.log(`  HARD CONSOLE ERRORS:`);
        for (const e of hardConsoleErrors) console.log(`    - ${e}`);
      }
      if (softConsoleErrors.length > 0) {
        console.log(`  SOFT CONSOLE ERRORS (informational):`);
        for (const e of softConsoleErrors) console.log(`    - ${e}`);
      }
      if (pageErrors.length > 0) {
        console.log(`  PAGE ERRORS (uncaught exceptions):`);
        for (const e of pageErrors) console.log(`    - ${e}`);
      }

      await context.close();
    }
  }

  await browser.close();

  // ── summary ───────────────────────────────────────────────────────────────
  console.log('\n\n========== BOOT SMOKE SUMMARY ==========');
  for (const r of allResults) {
    const icon = r.passed ? 'PASS' : 'FAIL';
    const assertions = Object.entries(r.assertions).map(([k, v]) => `${k}=${v}`).join(' ');
    console.log(`${icon} | ${r.route} @ ${r.width}px | ${assertions}`);
    if (!r.passed) {
      console.log(`     selector: ${r.detail.selectorDetail}`);
      if (r.detail.hardConsoleErrors.length > 0) {
        console.log(`     hardConsoleErrors: ${r.detail.hardConsoleErrors.join(' | ')}`);
      }
      if (r.detail.pageErrors.length > 0) {
        console.log(`     pageErrors: ${r.detail.pageErrors.join(' | ')}`);
      }
    }
  }
  const passCount = allResults.filter(r => r.passed).length;
  console.log(`\nResult: ${passCount}/${allResults.length} passed`);
  console.log(anyFailed ? 'OVERALL: FAIL' : 'OVERALL: PASS');
  console.log('=========================================\n');

  // Write JSON results for upload-artifact.
  fs.writeFileSync(RESULTS_FILE, JSON.stringify(allResults, null, 2));
  console.log(`Results written to ${RESULTS_FILE}`);

  process.exit(anyFailed ? 1 : 0);
}

runSmoke().catch((err) => {
  console.error('SMOKE FATAL:', err);
  process.exit(1);
});
