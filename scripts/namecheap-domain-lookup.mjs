#!/usr/bin/env node
/**
 * MeeSell — Namecheap Domain Lookup
 *
 * Reusable headless Playwright flow to log into Namecheap and extract domain
 * details (nameservers, expiration, registration status, DNS records summary).
 *
 * SECURITY DISCIPLINE:
 *   - Credentials are read from env vars ONLY. NEVER hardcoded.
 *   - TOTP codes are read from env vars or stdin (interactive).
 *   - Nothing is written to disk except the output JSON (no cookies, no session).
 *   - Output JSON does NOT contain credentials, tokens, or session IDs.
 *   - This script does NOT support saving sessions. Each invocation is fresh.
 *
 * USAGE:
 *   NAMECHEAP_USER=Mugunthan93 \
 *   NAMECHEAP_PASS="$(op read 'op://Personal/Namecheap/password')" \
 *   NAMECHEAP_TOTP=123456 \
 *   node scripts/namecheap-domain-lookup.mjs mesell.xyz
 *
 *   The password is recommended to come from a password manager CLI
 *   (1Password CLI `op`, Bitwarden CLI `bw`, pass, etc.).
 *
 *   Set NAMECHEAP_HEADLESS=false to watch the browser (helpful for debugging
 *   selector drift when Namecheap updates their UI).
 *
 * EXIT CODES:
 *   0 — success, JSON written to stdout
 *   1 — usage error (missing args or env vars)
 *   2 — 2FA required but NAMECHEAP_TOTP not provided (re-run with TOTP)
 *   3 — login failed (wrong credentials, account locked, etc.)
 *   4 — domain not found in account
 *   5 — selector drift (Namecheap UI changed; needs script update)
 *   6 — network or Playwright error
 *
 * AGENT REUSE PATTERN:
 *   An orchestrating agent invokes this script. If exit code 2, the agent asks
 *   the user for a fresh TOTP code, then re-invokes with NAMECHEAP_TOTP set.
 *   TOTP codes expire ~30s — the agent should re-invoke within that window.
 *
 * MAINTENANCE:
 *   Namecheap's HTML structure changes periodically. If exit code 5 ever fires,
 *   open the script in headed mode (NAMECHEAP_HEADLESS=false), step through,
 *   update the selectors at the marked SELECTOR CHECKPOINTS, and recommit.
 */

import { chromium } from 'playwright';

const REQUIRED_ENV = ['NAMECHEAP_USER', 'NAMECHEAP_PASS'];
const LOGIN_URL = 'https://www.namecheap.com/myaccount/login/';
const DOMAIN_LIST_URL = 'https://ap.www.namecheap.com/domains/list/';
const TIMEOUT_MS = 30000;

function die(code, msg) {
  console.error(`[FATAL ${code}] ${msg}`);
  process.exit(code);
}

function maskedEnv() {
  return {
    NAMECHEAP_USER: process.env.NAMECHEAP_USER || '<unset>',
    NAMECHEAP_PASS: process.env.NAMECHEAP_PASS ? '<set>' : '<unset>',
    NAMECHEAP_TOTP: process.env.NAMECHEAP_TOTP ? '<set>' : '<unset>',
    NAMECHEAP_HEADLESS: process.env.NAMECHEAP_HEADLESS || 'true (default)',
  };
}

async function main() {
  const domain = process.argv[2];
  if (!domain) {
    console.error('Usage: node namecheap-domain-lookup.mjs <domain>');
    console.error('Env:   ' + JSON.stringify(maskedEnv()));
    die(1, 'missing domain argument');
  }

  for (const v of REQUIRED_ENV) {
    if (!process.env[v]) die(1, `missing env var ${v}`);
  }

  const headless = process.env.NAMECHEAP_HEADLESS !== 'false';
  console.error(`[info] launching chromium (headless=${headless})`);

  let browser;
  try {
    browser = await chromium.launch({ headless });
  } catch (e) {
    die(6, `chromium.launch failed: ${e.message}`);
  }

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent:
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
      '(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  try {
    // ───── Step 1: Login page ─────
    console.error('[info] navigating to login');
    await page.goto(LOGIN_URL, { waitUntil: 'domcontentloaded', timeout: TIMEOUT_MS });

    // SELECTOR CHECKPOINT 1 — login form
    // Last verified: 2026-06-04. If Namecheap updates the form, update these.
    const userInput = 'input[name="LoginUserName"]';
    const passInput = 'input[name="LoginPassword"]';
    const submitButton = 'button[type="submit"], input[type="submit"]';

    await page.waitForSelector(userInput, { timeout: TIMEOUT_MS });
    await page.fill(userInput, process.env.NAMECHEAP_USER);
    await page.fill(passInput, process.env.NAMECHEAP_PASS);
    await page.click(submitButton);

    console.error('[info] submitted credentials, waiting for 2FA or dashboard');

    // ───── Step 2: 2FA or dashboard ─────
    // SELECTOR CHECKPOINT 2 — 2FA form (may be input[name="OTP"] or .totp-input)
    const totpInput = 'input[name="OTP"], input[autocomplete="one-time-code"]';

    const dashOrTotp = await Promise.race([
      page
        .waitForURL(/(dashboard|domains)/i, { timeout: TIMEOUT_MS })
        .then(() => 'dashboard'),
      page
        .waitForSelector(totpInput, { timeout: TIMEOUT_MS })
        .then(() => 'totp'),
      page
        .waitForSelector('.error, [class*="error"]', { timeout: TIMEOUT_MS })
        .then(() => 'error'),
    ]).catch(() => 'timeout');

    if (dashOrTotp === 'error') {
      const err = await page.locator('.error, [class*="error"]').first().textContent().catch(() => 'unknown');
      die(3, `login error: ${err}`);
    }

    if (dashOrTotp === 'totp') {
      const totp = process.env.NAMECHEAP_TOTP;
      if (!totp) {
        console.error('[info] 2FA prompted; NAMECHEAP_TOTP not provided');
        await browser.close();
        die(2, '2FA required — re-run with NAMECHEAP_TOTP=<6-digit code>');
      }
      console.error('[info] entering 2FA');
      await page.fill(totpInput, totp);
      await page.click(submitButton);
      try {
        await page.waitForURL(/(dashboard|domains)/i, { timeout: TIMEOUT_MS });
      } catch {
        die(3, '2FA submission did not reach dashboard — wrong code or expired');
      }
    } else if (dashOrTotp === 'timeout') {
      die(3, 'neither dashboard nor 2FA prompt appeared within timeout');
    }

    // ───── Step 3: Domain list ─────
    console.error('[info] navigating to domain list');
    await page.goto(DOMAIN_LIST_URL, { waitUntil: 'networkidle', timeout: TIMEOUT_MS });

    // SELECTOR CHECKPOINT 3 — domain row
    // Namecheap's domain list is a table-like layout. Selectors vary by account.
    // We extract via best-effort text matching.
    const result = await page.evaluate((d) => {
      // Find any element whose text content includes the domain name
      const all = document.body.querySelectorAll('*');
      let match = null;
      for (const el of all) {
        if (el.children.length === 0) continue; // leaf nodes only have text
        const own = (el.textContent || '').trim();
        if (
          own.toLowerCase().includes(d.toLowerCase()) &&
          (el.tagName === 'TR' ||
            el.className.toString().toLowerCase().includes('domain') ||
            el.className.toString().toLowerCase().includes('row'))
        ) {
          match = el;
          break;
        }
      }
      if (!match) return { found: false, domain: d };

      // Extract whatever structured info we can
      const text = (match.textContent || '').replace(/\s+/g, ' ').trim();
      const expirationMatch = text.match(
        /(\d{1,2}\/\d{1,2}\/\d{4}|\d{4}-\d{2}-\d{2}|[A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})/,
      );

      return {
        found: true,
        domain: d,
        rawText: text.substring(0, 800),
        expirationCandidate: expirationMatch ? expirationMatch[0] : null,
        autoRenew: /auto.?renew\s*(on|enabled|yes)/i.test(text),
        nameservers: (() => {
          // Look for nameserver hostnames
          const re = /([a-z0-9-]+\.)?(namecheap|dns\d*|cloudflare|google|aws)\.com/gi;
          return [...text.matchAll(re)].map((m) => m[0]);
        })(),
      };
    }, domain);

    if (!result.found) {
      die(4, `domain ${domain} not found in account ${process.env.NAMECHEAP_USER}`);
    }

    // ───── Output ─────
    console.log(JSON.stringify(result, null, 2));
    process.exitCode = 0;
  } catch (e) {
    console.error(`[error] ${e.message}`);
    if (process.env.NAMECHEAP_HEADLESS === 'false') {
      console.error('[info] keeping browser open for inspection — close manually');
      return; // leave browser open
    }
    die(5, `selector drift or page error: ${e.message}`);
  } finally {
    if (browser && process.env.NAMECHEAP_HEADLESS !== 'false') {
      await browser.close();
    }
  }
}

main().catch((e) => die(6, `unhandled: ${e.message}`));
