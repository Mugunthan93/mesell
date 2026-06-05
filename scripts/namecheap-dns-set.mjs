#!/usr/bin/env node
/**
 * MeeSell — Namecheap DNS Record Setter
 *
 * Reusable headless Playwright flow to log into Namecheap and ADD A/CNAME/TXT
 * records on a domain. Companion to namecheap-domain-lookup.mjs.
 *
 * SECURITY DISCIPLINE: same as the lookup script — env vars only, no disk persistence.
 *
 * USAGE:
 *   NAMECHEAP_USER=Mugunthan93 \
 *   NAMECHEAP_PASS='...' \
 *   NAMECHEAP_TOTP=123456 \
 *     node scripts/namecheap-dns-set.mjs mesell.xyz \
 *       --add A studio 35.234.223.66 \
 *       --add A @       35.234.223.66 \
 *       --add A '*'     35.234.223.66
 *
 *   Each --add takes 3 args: <TYPE> <HOST> <VALUE>. TTL is always "Automatic".
 *   Multiple --add flags supported in one invocation.
 *
 *   Set NAMECHEAP_HEADLESS=false to watch the browser (debugging).
 *
 * EXIT CODES:
 *   0 — success, all records added
 *   1 — usage error
 *   2 — 2FA required, NAMECHEAP_TOTP missing
 *   3 — login failed
 *   4 — domain not in account
 *   5 — selector drift (Namecheap UI changed)
 *   6 — Playwright / network error
 *   7 — record save failed (Namecheap returned an error like duplicate or invalid value)
 *
 * SAFETY: this script ADDS records. It does NOT delete or modify existing records.
 *   If a record with the same Type+Host+Value already exists, Namecheap will reject
 *   the add (exit 7) — that's actually safe; check the existing record manually.
 */

import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';

const REQUIRED_ENV = ['NAMECHEAP_USER', 'NAMECHEAP_PASS'];
const LOGIN_URL = 'https://www.namecheap.com/myaccount/login/';
const TIMEOUT_MS = 45000;
const SCREENSHOT_DIR = '/tmp/namecheap-screenshots';

function die(code, msg) {
  console.error(`[FATAL ${code}] ${msg}`);
  process.exit(code);
}

function parseArgs(argv) {
  const args = argv.slice(2);
  const domain = args[0];
  const records = [];
  for (let i = 1; i < args.length; i++) {
    if (args[i] === '--add') {
      records.push({
        type: args[i + 1],
        host: args[i + 2],
        value: args[i + 3],
      });
      i += 3;
    }
  }
  return { domain, records };
}

async function snap(page, label) {
  try {
    await mkdir(SCREENSHOT_DIR, { recursive: true });
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    const path = `${SCREENSHOT_DIR}/${ts}-${label}.png`;
    await page.screenshot({ path, fullPage: false });
    console.error(`[snap] ${path}`);
  } catch (e) {
    console.error(`[snap-fail] ${e.message}`);
  }
}

async function main() {
  const { domain, records } = parseArgs(process.argv);
  if (!domain) die(1, 'missing domain argument (first positional arg)');
  if (records.length === 0) die(1, 'no --add records specified');
  for (const v of REQUIRED_ENV) {
    if (!process.env[v]) die(1, `missing env var ${v}`);
  }

  const headless = process.env.NAMECHEAP_HEADLESS !== 'false';
  console.error(`[info] launching chromium (headless=${headless})`);
  console.error(`[info] target domain: ${domain}`);
  console.error(`[info] records to add: ${records.length}`);

  let browser;
  try {
    browser = await chromium.launch({ headless });
  } catch (e) {
    die(6, `chromium.launch failed: ${e.message}`);
  }

  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    userAgent:
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  try {
    // ───────────── LOGIN ─────────────
    console.error('[1/5] navigating to login');
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: TIMEOUT_MS });

    // Namecheap renders both desktop and mobile login forms in the DOM.
    // Use visibility-aware locators (.locator.filter({visible: true}).first()) to pick the
    // one that's actually rendered on this viewport.
    const userLoc = page.locator('input[name="LoginUserName"]').locator('visible=true').first();
    const passLoc = page.locator('input[name="LoginPassword"]').locator('visible=true').first();
    const submitLoc = page
      .locator('button[type="submit"], input[type="submit"]')
      .locator('visible=true')
      .first();

    await userLoc.waitFor({ state: 'visible', timeout: TIMEOUT_MS });
    await userLoc.fill(process.env.NAMECHEAP_USER);
    await passLoc.fill(process.env.NAMECHEAP_PASS);
    await snap(page, 'pre-submit-login');
    await submitLoc.click();

    console.error('[2/5] waiting for post-login page');

    // Namecheap uses placeholder="Enter OTP Code" — no name/id/autocomplete hint.
    // Include the placeholder-based selector (verified 2026-06-04 via screenshot).
    const totpInput =
      'input[placeholder*="OTP" i], input[name="OTP"], input[autocomplete="one-time-code"], input[id*="totp" i], input[id*="otp" i]';

    // Wait for redirect to settle. With 2FA enabled → OTP page. Without 2FA → dashboard.
    // We sniff the DOM rather than waiting for a URL pattern (Namecheap's dashboard URL
    // is just `ap.www.namecheap.com/` — no keyword to match).
    await page.waitForTimeout(5000);

    const totpVisible =
      (await page.locator(totpInput).locator('visible=true').count()) > 0;

    // Namecheap shows "Device Verification" with an email-delivered code when 2FA
    // is disabled but the device/IP is unrecognized. Detect by heading text.
    const emailVerifyVisible = await page
      .locator('text=/Device Verification|verification code to the email/i')
      .count();

    const loginErrorVisible =
      (await page
        .locator('text=/incorrect|invalid credentials|wrong password|unable to sign in/i')
        .count()) > 0;

    if (loginErrorVisible) {
      await snap(page, 'login-error');
      die(3, 'login error — wrong credentials');
    }

    // Handle device-email verification (env var OR poll-file fallback so the
    // login session stays alive while we wait for the user to type the code)
    if (emailVerifyVisible > 0) {
      let emailCode = process.env.NAMECHEAP_EMAIL_CODE;
      const codeFile = process.env.NAMECHEAP_EMAIL_CODE_FILE;
      if (!emailCode && codeFile) {
        const fs = await import('node:fs/promises');
        console.error(`[info] WAITING_FOR_EMAIL_CODE — write 6-char code to ${codeFile} (up to 5 min)`);
        await snap(page, 'email-verify-waiting-file');
        for (let s = 0; s < 300; s++) {
          try {
            const content = (await fs.readFile(codeFile, 'utf8')).trim();
            if (content) {
              emailCode = content;
              await fs.unlink(codeFile).catch(() => {});
              console.error(`[info] email code received from file (length=${emailCode.length})`);
              break;
            }
          } catch {
            // file not present yet
          }
          await new Promise((r) => setTimeout(r, 1000));
        }
      }
      if (!emailCode) {
        await snap(page, 'email-verify-prompt');
        await browser.close();
        die(
          2,
          'Device email verification required — Namecheap sent a code to your email. Re-run with NAMECHEAP_EMAIL_CODE=<code> OR set NAMECHEAP_EMAIL_CODE_FILE and write the code there.'
        );
      }
      console.error('[info] entering email verification code');
      const emailInput = page
        .locator(
          'input[placeholder*="verification" i], input[placeholder*="code" i]'
        )
        .locator('visible=true')
        .first();
      await emailInput.fill(emailCode);
      const emailSubmit = page
        .locator('button[type="submit"], input[type="submit"]')
        .locator('visible=true')
        .first();
      await emailSubmit.click();
      await page.waitForTimeout(4000);
      // After email verification, check if we landed on dashboard (no further prompts)
      const stillOnEmailVerify = await page
        .locator('text=/Device Verification|verification code to the email/i')
        .count();
      if (stillOnEmailVerify > 0) {
        await snap(page, 'email-verify-failed');
        die(3, 'email verification submission did not advance — wrong/expired code');
      }
      console.error('[info] email verification accepted');
    }

    const dashOrTotp = totpVisible ? 'totp' : 'dashboard';
    console.error(`[info] post-login state: ${dashOrTotp}`);

    if (dashOrTotp === 'totp') {
      const totp = process.env.NAMECHEAP_TOTP;
      if (!totp) {
        await snap(page, '2fa-prompt');
        await browser.close();
        die(2, '2FA prompted — re-run with NAMECHEAP_TOTP=<6-digit code>');
      }
      console.error('[info] entering 2FA');
      const totpLoc = page.locator(totpInput).locator('visible=true').first();
      await totpLoc.fill(totp);
      const totpSubmit = page
        .locator('button[type="submit"], input[type="submit"]')
        .locator('visible=true')
        .first();
      await totpSubmit.click();
      // Namecheap's dashboard has continuous telemetry — networkidle never fires.
      // Skip dashboard detection; press straight to advancedns URL. If the TOTP was
      // wrong, that page will redirect to login and the subsequent waitForSelector
      // for "Add New Record" will time out — caught by die(5) below.
      console.error('[info] TOTP submitted; pressing forward to advancedns');
      await page.waitForTimeout(3500); // let redirect settle
    }

    // ───────────── ADVANCED DNS PAGE ─────────────
    const advancedDnsUrl = `https://ap.www.namecheap.com/Domains/DomainControlPanel/${domain}/advancedns`;
    console.error(`[3/5] navigating to: ${advancedDnsUrl}`);
    await page.goto(advancedDnsUrl, { waitUntil: 'networkidle', timeout: TIMEOUT_MS });
    await page.waitForTimeout(2000); // let React render
    await snap(page, 'advanced-dns-loaded');

    // Verify we're on the right page
    const onAdvDns = await page
      .waitForSelector('text=/HOST RECORDS|Advanced DNS|Add New Record/i', { timeout: 15000 })
      .then(() => true)
      .catch(() => false);
    if (!onAdvDns) {
      await snap(page, 'no-advanced-dns');
      die(5, 'Advanced DNS page did not load — selector drift or wrong domain');
    }

    // ───────────── ADD EACH RECORD ─────────────
    // Namecheap's Advanced DNS uses select2 (old jQuery library) for the Type dropdown.
    // Strategy: click the select2 container to open, type the type code to filter, press
    // Enter to select. This avoids select2-drop-mask intercepting click events on options.
    const results = [];
    for (let i = 0; i < records.length; i++) {
      const r = records[i];
      console.error(`[4/5] adding record ${i + 1}/${records.length}: ${r.type} ${r.host} -> ${r.value}`);

      try {
        // Snapshot before clicking add
        await snap(page, `record-${i}-pre-add`);

        // Click "ADD NEW RECORD" — Namecheap uses an <a> or <div> with that text
        await page
          .locator('text=/ADD NEW RECORD/i')
          .first()
          .click({ timeout: 10000 });
        await page.waitForTimeout(1200);
        await snap(page, `record-${i}-after-add-click`);

        // The new row sits at the BOTTOM of the host records table (above the
        // "ADD NEW RECORD" button). Its select2 container is the first un-bound
        // one — easiest to find as the LAST select2-container on the page (Namecheap
        // appends, doesn't prepend). Verified via select2-drop-mask error in prior run.
        const typeContainer = page.locator('.select2-container').last();
        await typeContainer.click({ timeout: 5000 });
        await page.waitForTimeout(700);
        await snap(page, `record-${i}-dropdown-open`);

        // select2 (jQuery, old version) shows results in a popup. Type the record
        // type into the search input, press Enter to select.
        // Some Namecheap deployments hide the search input — fall back to
        // keyboard arrow navigation if no input found.
        const searchInput = page.locator(
          '.select2-search input, .select2-input, input.select2-focused'
        );
        const searchCount = await searchInput.count();
        if (searchCount > 0) {
          await searchInput.first().fill(r.type);
          await page.waitForTimeout(500);
          await page.keyboard.press('Enter');
        } else {
          // No search input — use keyboard arrow keys to scroll to the type
          // Default order in Namecheap is: A Record, AAAA Record, ALIAS, CAA, ...
          // We map common types to their index. For A, just press Enter (it's first).
          const keyMap = { A: 0, AAAA: 1, ALIAS: 2, CAA: 3, CNAME: 4, MX: 5, NS: 6, TXT: 7, URL: 8 };
          const idx = keyMap[r.type.toUpperCase()] ?? 0;
          for (let k = 0; k < idx; k++) await page.keyboard.press('ArrowDown');
          await page.keyboard.press('Enter');
        }
        await page.waitForTimeout(500);
        await snap(page, `record-${i}-type-selected`);

        // Host input — find the LAST host input (the new row's). Selector varies;
        // try multiple patterns.
        const hostInput = page
          .locator(
            'input[name*="Host" i]:not([disabled]), input[placeholder*="host" i]:not([disabled]), input.host-input'
          )
          .last();
        await hostInput.fill(r.host, { timeout: 5000 });

        // Value input — same strategy: last one.
        const valueInput = page
          .locator(
            'input[name*="Value" i]:not([disabled]), input[name*="Address" i]:not([disabled]), input[placeholder*="value" i]:not([disabled]), input[placeholder*="address" i]:not([disabled]), input.value-input, input.ip-address'
          )
          .last();
        await valueInput.fill(r.value, { timeout: 5000 });

        await snap(page, `record-${i}-filled`);

        // Save button — Namecheap shows a green checkmark icon at the end of
        // the new row. Look for the LAST save button. Possible selectors:
        // - <button class="save-record">
        // - <i class="fa fa-check">
        // - <a class="confirm-record">
        // Strategy: text-based "✓" / title="Save" or icon with parent button.
        const saveBtn = page
          .locator(
            'button[title*="save" i], a[title*="save" i], button:has(.fa-check), a:has(.fa-check), .save-record, .confirm-record, button.nc-btn-icon'
          )
          .last();
        await saveBtn.click({ timeout: 5000, force: true });

        // Wait for save confirmation
        await page.waitForTimeout(3500);
        await snap(page, `record-${i}-after-save`);

        // Check for error toast
        const errToast = await page
          .locator('text=/duplicate|invalid|error|already exists|cannot/i')
          .first()
          .textContent({ timeout: 2000 })
          .catch(() => null);

        if (errToast && errToast.length < 300) {
          results.push({
            record: r,
            ok: false,
            error: errToast.trim(),
          });
        } else {
          results.push({ record: r, ok: true });
        }
      } catch (e) {
        await snap(page, `record-${i}-exception`);
        results.push({ record: r, ok: false, error: e.message.substring(0, 500) });
      }
    }

    // ───────────── REPORT ─────────────
    console.error('[5/5] done');
    const summary = {
      domain,
      attempted: records.length,
      succeeded: results.filter((r) => r.ok).length,
      failed: results.filter((r) => !r.ok).length,
      results,
      screenshotsDir: SCREENSHOT_DIR,
    };
    console.log(JSON.stringify(summary, null, 2));

    if (summary.failed > 0) process.exitCode = 7;
  } catch (e) {
    await snap(page, 'unhandled-error');
    console.error(`[error] ${e.message}`);
    if (process.env.NAMECHEAP_HEADLESS === 'false') {
      console.error('[info] headed mode — leaving browser open for inspection');
      return;
    }
    die(5, `selector drift or page error: ${e.message}`);
  } finally {
    if (browser && process.env.NAMECHEAP_HEADLESS !== 'false') {
      await browser.close();
    }
  }
}

main().catch((e) => die(6, `unhandled: ${e.message}`));
