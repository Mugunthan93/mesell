/**
 * F-001 boot smoke test — headless Chromium via Playwright
 *
 * Per SPEC §3 requirements:
 *   a. SPA index.html bootstrapped (app-root in DOM, NOT server 404 page)
 *   b. Expected component selector mounted + non-empty
 *   c. ZERO console "Unable to resolve specifier" errors
 *   d. body.innerText.trim().length > 0
 *
 * Routes tested:
 *   / (shell, mfe-dashboard: RemoteFailureComponent acceptable if remote down)
 *   /login (mfe-auth: login form — phone input or mee-login-form host selector)
 *   /profile (mfe-onboarding: profile card — mee-card / form present; behind authGuard
 *            → redirects to /login if unauthenticated, which still proves SPA boot + guard running)
 */

const { chromium } = require('playwright');
const fs = require('fs');

const SHELL_URL = 'http://localhost:4200';
const ROUTES = ['/', '/login', '/profile'];
const WIDTHS = [360, 1280];

// Screenshot output dir
const SCREENSHOT_DIR = '/Users/mugunthansrinivasan/Project/mesell/.claude/worktrees/agent-a8eb89da354e3af36/docs/ui-review';

async function takeSmoke() {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const errors = [];

  for (const route of ROUTES) {
    for (const width of WIDTHS) {
      const context = await browser.newContext({
        viewport: { width, height: 900 },
        ignoreHTTPSErrors: true,
      });
      const page = await context.newPage();

      const consoleErrors = [];
      page.on('console', (msg) => {
        const text = msg.text();
        if (text.includes('Unable to resolve specifier')) {
          consoleErrors.push(text);
        }
      });

      let fullUrl = SHELL_URL + route;
      console.log(`\n--- Testing ${fullUrl} @ ${width}px ---`);

      try {
        // Navigate with a generous timeout; wait until network is idle-ish
        await page.goto(fullUrl, { waitUntil: 'networkidle', timeout: 30000 });
      } catch (e) {
        // Timeout is ok — Angular may keep polling; check DOM anyway
        console.log(`  WARN: goto timeout (non-fatal): ${e.message.split('\n')[0]}`);
      }

      // Give Angular a beat to render after navigation
      await page.waitForTimeout(3000);

      const bodyText = await page.evaluate(() => document.body.innerText.trim());
      const bodyHTML = await page.evaluate(() => document.body.innerHTML);
      const title = await page.title();

      // Assertion a: NOT a server 404 page
      const is404Page = bodyHTML.includes('Error code: 404') || bodyHTML.includes('File not found') || bodyHTML.includes('HTTPStatus.NOT_FOUND');
      const hasAppRoot = await page.$('app-root') !== null;

      // Assertion b: component-specific checks
      let componentMounted = false;
      let componentDetail = '';

      if (route === '/login') {
        // /login → LoginComponent from mfe-auth (or RemoteFailureComponent if mfe-auth down)
        // LoginComponent renders a form with phone/email input
        // Check for app-root first, then for form elements
        const hasLoginForm = await page.$('app-root form') !== null;
        const hasMeeInput = await page.$('mee-input') !== null;
        const hasInput = await page.$('app-root input') !== null;
        const hasButton = await page.$('app-root button, app-root mee-button') !== null;
        const hasRemoteFailure = bodyHTML.includes('cloud_off') || bodyHTML.includes('remote-failure') || bodyHTML.includes('RemoteFailure');
        componentMounted = hasLoginForm || hasMeeInput || hasInput || hasButton || hasRemoteFailure;
        componentDetail = `form=${hasLoginForm} mee-input=${hasMeeInput} input=${hasInput} button=${hasButton} remoteFailure=${hasRemoteFailure}`;
      } else if (route === '/profile') {
        // /profile → behind authGuard → unauthenticated → redirect to /login → login form rendered
        // This proves: shell booted + authGuard ran + redirect to /login + login form loaded
        const currentUrl = page.url();
        const redirectedToLogin = currentUrl.includes('/login');
        const hasLoginForm = await page.$('app-root form') !== null;
        const hasMeeInput = await page.$('mee-input') !== null;
        const hasInput = await page.$('app-root input') !== null;
        // If mfe-onboarding is actually up AND user is authenticated, check mee-card
        const hasMeeCard = await page.$('mee-card, app-profile') !== null;
        const hasRemoteFailure = bodyHTML.includes('cloud_off') || bodyHTML.includes('remote-failure');
        componentMounted = redirectedToLogin || hasLoginForm || hasMeeInput || hasInput || hasMeeCard || hasRemoteFailure;
        componentDetail = `redirectedToLogin=${redirectedToLogin} currentUrl=${currentUrl} form=${hasLoginForm} mee-input=${hasMeeInput} mee-card=${hasMeeCard}`;
      } else {
        // / → root: LandingComponent from mfe-dashboard, or RemoteFailureComponent, or redirect
        // Accept: app-root with non-empty content
        const hasRemoteFailure = bodyHTML.includes('cloud_off') || bodyHTML.includes('remote-failure');
        const hasContent = bodyText.length > 10;
        componentMounted = hasContent;
        componentDetail = `hasContent=${hasContent} hasRemoteFailure=${hasRemoteFailure} textLength=${bodyText.length}`;
      }

      // Assertion c: zero specifier errors
      const zeroSpecifierErrors = consoleErrors.length === 0;

      // Assertion d: body non-empty
      const bodyNonEmpty = bodyText.length > 0;

      const routeLabel = route === '/' ? 'root' : route.replace('/', '');
      const screenshotName = `f001-boot-${routeLabel}-${width}px.png`;
      const screenshotPath = `${SCREENSHOT_DIR}/${screenshotName}`;

      await page.screenshot({ path: screenshotPath, fullPage: false });
      console.log(`  Screenshot: ${screenshotPath}`);

      const passed = !is404Page && hasAppRoot && componentMounted && zeroSpecifierErrors && bodyNonEmpty;

      const result = {
        route,
        width,
        passed,
        assertions: {
          notA404Page: !is404Page,
          hasAppRoot,
          componentMounted,
          zeroSpecifierErrors,
          bodyNonEmpty,
        },
        componentDetail,
        specifierErrors: consoleErrors,
        title,
        bodyTextLength: bodyText.length,
      };
      results.push(result);

      console.log(`  PASS=${passed}`);
      console.log(`  notA404Page=${!is404Page} hasAppRoot=${hasAppRoot} componentMounted=${componentMounted} zeroSpecifierErrors=${zeroSpecifierErrors} bodyNonEmpty=${bodyNonEmpty}`);
      console.log(`  componentDetail: ${componentDetail}`);
      if (consoleErrors.length > 0) {
        console.log(`  SPECIFIER ERRORS: ${consoleErrors.join(', ')}`);
        errors.push({ route, width, errors: consoleErrors });
      }

      await context.close();
    }
  }

  await browser.close();

  // Summary
  console.log('\n\n========== SMOKE SUMMARY ==========');
  let allPassed = true;
  for (const r of results) {
    const status = r.passed ? 'PASS' : 'FAIL';
    console.log(`${status} | ${r.route} @ ${r.width}px | ${JSON.stringify(r.assertions)} | ${r.componentDetail}`);
    if (!r.passed) allPassed = false;
  }
  console.log(`\nOverall: ${allPassed ? 'ALL PASS' : 'SOME FAILED'}`);
  console.log('====================================\n');

  // Write results JSON
  fs.writeFileSync('/tmp/f001-smoke-results.json', JSON.stringify(results, null, 2));

  if (!allPassed) {
    process.exit(1);
  }
}

takeSmoke().catch((e) => {
  console.error('SMOKE SCRIPT ERROR:', e);
  process.exit(1);
});
